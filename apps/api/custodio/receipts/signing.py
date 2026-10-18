"""Signing and checking receipts. Pure: the key comes in, nothing is read from the outside.

A receipt carries two Ed25519 signatures by the same key: one over the canonical JSON of the body, and one over the
SHA-256 of each field of the body. The first says whether anything changed; the second, still intact when only the
body was edited, says which field. Changing both a field and its digest breaks the second signature too.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
from collections.abc import Iterator, Mapping
from dataclasses import dataclass
from typing import Any, cast, get_args

from custodio.engine.errors import CanonicalJsonError
from custodio.engine.ledger import canonical_json
from custodio.receipts.keys import ReceiptPublicKey, ReceiptSigner
from custodio.receipts.models import ALGORITHM, RECEIPT_FORMAT, DecisionReceipt, ReceiptBody, ReceiptCheck, Verdict

VERDICT_LABELS: dict[str, str] = {
    "pay": "Pagar",
    "hold": "Retener",
    "escalate": "Escalar a una persona",
    "reject": "Rechazar",
}
FIELD_LABELS: dict[str, str] = {
    "format": "formato",
    "key_id": "id de clave",
    "workspace_id": "espacio de trabajo",
    "issued_at": "fecha",
    "invoice.id": "factura",
    "invoice.number": "número de factura",
    "invoice.received_at": "fecha de recepción",
    "invoice.source": "canal de llegada",
    "invoice.document_id": "documento",
    "invoice.document_sha256": "huella del documento",
    "policy.version": "versión de la política",
    "policy.sha256": "huella de la política",
    "policy.ledger_seq": "posición de la política en el registro",
    "policy.ledger_hash": "hash de la política en el registro",
    "decision.verdict": "decisión",
    "decision.status": "estado",
    "decision.agent_verdict": "veredicto del agente",
    "decision.approved_by": "aprobado por",
    "payment": "pago",
    "payment.beneficiary_id": "beneficiario",
    "payment.beneficiary_name": "beneficiario",
    "payment.account_last4": "cuenta",
    "payment.account_sha256": "cuenta",
    "payment.amount": "monto",
    "payment.currency": "moneda",
    "payment.amount_base": "monto en moneda base",
    "payment.base_currency": "moneda base",
    "payment.rail": "riel de pago",
    "payment.external_id": "id del pago",
    "ledger.seq": "posición en el registro",
    "ledger.hash": "hash en el registro",
    "ledger.kind": "tipo de asiento",
}
READING_LABELS: dict[str, str] = {
    "supplier_name": "proveedor leído",
    "supplier_tax_id": "identificación fiscal leída",
    "invoice_number": "número de factura leído",
    "issue_date": "fecha de emisión leída",
    "due_date": "vencimiento leído",
    "amount": "monto leído",
    "currency": "moneda leída",
    "bank_name": "banco leído",
    "account_number": "cuenta leída",
}

VALID = "Válido: firmado por Custodio con la clave {key}. La decisión fue «{verdict}»."
ONE_ALTERED = "Inválido: el campo {fields} fue alterado después de firmarse."
MANY_ALTERED = "Inválido: los campos {fields} fueron alterados después de firmarse."
WRONG_KEY = "Inválido: el recibo dice estar firmado con la clave {claimed} y la clave de Custodio es {ours}."
BAD_SIGNATURE = "Inválido: la firma no corresponde a este contenido ni a la clave de Custodio."
NOT_A_RECEIPT = "Inválido: esto no tiene la forma de un recibo firmado de Custodio."


def sign_receipt(body: ReceiptBody, signer: ReceiptSigner) -> DecisionReceipt:
    plain = body.model_dump(mode="json")
    digests = field_digests(plain)
    return DecisionReceipt(
        key_id=signer.key_id,
        body=body,
        signature=_b64(signer.sign(signed_bytes(plain))),
        field_digests=digests,
        digests_signature=_b64(signer.sign(signed_bytes(digests))),
    )


def signed_bytes(value: object) -> bytes:
    return canonical_json(value).encode()


def field_digests(body: Mapping[str, Any]) -> dict[str, str]:
    return {path: hashlib.sha256(signed_bytes(value)).hexdigest() for path, value in _leaves(body, "")}


def verify_receipt(raw: object, key: ReceiptPublicKey) -> ReceiptCheck:
    """`raw` is whatever someone pasted, already parsed from JSON; nothing about it is trusted."""
    try:
        return _check(raw, key)
    except (CanonicalJsonError, UnicodeEncodeError, RecursionError):
        # a NaN, a non-string key, a lone surrogate or a body nested past the stack: no receipt is spelled like that
        return ReceiptCheck(valid=False, message=NOT_A_RECEIPT)


def _check(raw: object, key: ReceiptPublicKey) -> ReceiptCheck:
    envelope = _Envelope.parse(raw)
    if envelope is None:
        return ReceiptCheck(valid=False, message=NOT_A_RECEIPT)
    if envelope.key_id != key.key_id:
        return ReceiptCheck(
            valid=False, key_id=envelope.key_id, message=WRONG_KEY.format(claimed=envelope.key_id, ours=key.key_id)
        )
    seen = {"key_id": key.key_id, "invoice_id": _text_at(envelope.body, "invoice", "id")}
    if key.verifies(envelope.signature, signed_bytes(envelope.body)) and envelope.body.get("key_id") == key.key_id:
        verdict = _verdict(envelope.body)
        label = VERDICT_LABELS.get(verdict or "", "sin decisión")
        return ReceiptCheck(valid=True, verdict=verdict, message=VALID.format(key=key.key_id, verdict=label), **seen)
    altered = _altered_fields(envelope, key)
    if not altered:
        return ReceiptCheck(valid=False, message=BAD_SIGNATURE, **seen)
    labels = list(dict.fromkeys(field_label(path, envelope.body) for path in altered))
    template = ONE_ALTERED if len(labels) == 1 else MANY_ALTERED
    return ReceiptCheck(
        valid=False,
        message=template.format(fields=_spanish_list(labels)),
        altered_fields=altered,
        altered_labels=labels,
        **seen,
    )


def field_label(path: str, body: Mapping[str, Any]) -> str:
    parts = path.split(".")
    if parts[0] == "reading" and len(parts) > 1:
        return READING_LABELS.get(parts[1], f"{parts[1]} leído")
    if parts[0] == "rules" and len(parts) > 1 and parts[1].isdigit():
        rules = body.get("rules")
        index = int(parts[1])
        rule = rules[index] if isinstance(rules, list) and index < len(rules) else None
        rule_id = rule.get("rule_id") if isinstance(rule, dict) else None
        return f"resultado de la regla {rule_id}" if isinstance(rule_id, str) else "resultado de una regla"
    return FIELD_LABELS.get(path, path)


@dataclass(frozen=True)
class _Envelope:
    key_id: str
    body: dict[str, Any]
    signature: bytes
    digests: dict[str, Any]
    digests_signature: bytes

    @classmethod
    def parse(cls, raw: object) -> _Envelope | None:
        if not isinstance(raw, dict) or raw.get("format") != RECEIPT_FORMAT or raw.get("algorithm") != ALGORITHM:
            return None
        key_id, body, digests = raw.get("key_id"), raw.get("body"), raw.get("field_digests")
        signature, digests_signature = _unb64(raw.get("signature")), _unb64(raw.get("digests_signature"))
        if not (isinstance(key_id, str) and isinstance(body, dict) and isinstance(digests, dict)):
            return None
        if signature is None or digests_signature is None:
            return None
        return cls(key_id, cast(dict[str, Any], body), signature, cast(dict[str, Any], digests), digests_signature)


def _altered_fields(envelope: _Envelope, key: ReceiptPublicKey) -> list[str]:
    """The fields whose digest no longer matches, if the signed digests themselves are intact."""
    if not key.verifies(envelope.digests_signature, signed_bytes(envelope.digests)):
        return []
    now = field_digests(envelope.body)
    paths = set(now) | set(envelope.digests)
    return sorted(path for path in paths if now.get(path) != envelope.digests.get(path))


def _leaves(value: object, prefix: str) -> Iterator[tuple[str, object]]:
    if isinstance(value, Mapping) and value:
        for name, item in value.items():
            yield from _leaves(item, f"{prefix}.{name}" if prefix else str(name))
    elif isinstance(value, list) and value:
        for index, item in enumerate(value):
            yield from _leaves(item, f"{prefix}.{index}")
    else:
        yield prefix, value


def _verdict(body: Mapping[str, Any]) -> Verdict | None:
    verdict = _text_at(body, "decision", "verdict")
    return cast(Verdict, verdict) if verdict in get_args(Verdict) else None


def _text_at(body: Mapping[str, Any], section: str, name: str) -> str | None:
    part = body.get(section)
    value = part.get(name) if isinstance(part, dict) else None
    return value if isinstance(value, str) else None


def _spanish_list(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " y " + items[-1]


def _b64(data: bytes) -> str:
    return base64.b64encode(data).decode()


def _unb64(value: object) -> bytes | None:
    if not isinstance(value, str):
        return None
    try:
        return base64.b64decode(value, validate=True)
    except binascii.Error:
        return None
