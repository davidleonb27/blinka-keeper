"""The file for Blinka: approved payments as an ISO 20022 customer credit transfer initiation (pain.001.001.09).

Banks and payment partners take this message to pay a batch at once. Custodio writes it from what the engine already
decided and the registered beneficiaries' bank details (never the invoice's). One payment block per currency, so each
block's control sum adds amounts of a single currency. Texts are cut to the schema's limits and stripped of control
characters; the XML writer escapes the rest.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import groupby
from xml.etree import ElementTree as ET  # builds only; nothing is ever parsed here

NAMESPACE = "urn:iso:std:iso:20022:tech:xsd:pain.001.001.09"
TRANSFER_METHOD = "TRF"
CENTS = Decimal("0.01")
MAX_ID = 35
MAX_ACCOUNT = 34
MAX_NAME = 140
MAX_REMITTANCE = 140
HASH_LENGTH = 12
COUNTRY = re.compile(r"[A-Z]{2}")
CONTROL = re.compile(r"[\x00-\x1f\x7f]")
SPACES = re.compile(r"\s+")
EMPTY_BATCH = "El lote no tiene pagos aprobados: sin pagos no hay archivo para Blinka."

ET.register_namespace("", NAMESPACE)


@dataclass(frozen=True)
class Debtor:
    name: str
    account_id: str  # the company's account at the paying partner
    agent_name: str = "Blinka"


@dataclass(frozen=True)
class CreditTransfer:
    end_to_end_id: str  # the invoice id, so the statement line leads back to the acta
    amount: Decimal
    currency: str
    creditor_name: str
    creditor_tax_id: str
    creditor_country: str | None
    creditor_bank: str
    creditor_account: str
    remittance: str  # the acta URL


@dataclass(frozen=True)
class PaymentFile:
    message_id: str
    created_at: datetime
    execution_date: date
    debtor: Debtor
    transfers: Sequence[CreditTransfer]


def control_sum(transfers: Sequence[CreditTransfer]) -> Decimal:
    return sum((_money(t.amount) for t in transfers), Decimal(0))


def render(payment_file: PaymentFile) -> bytes:
    if not payment_file.transfers:
        raise ValueError(EMPTY_BATCH)
    document = ET.Element(_tag("Document"))
    initiation = _child(document, "CstmrCdtTrfInitn")
    _group_header(initiation, payment_file)
    by_currency = sorted(payment_file.transfers, key=lambda t: _currency(t.currency))
    blocks = groupby(by_currency, key=lambda t: _currency(t.currency))
    for index, (_, block) in enumerate(blocks, start=1):
        _payment_block(initiation, payment_file, f"{_text(payment_file.message_id, MAX_ID - 4)}-{index}", list(block))
    xml: bytes = ET.tostring(document, encoding="utf-8", xml_declaration=True)
    return xml


def _group_header(parent: ET.Element, payment_file: PaymentFile) -> None:
    header = _child(parent, "GrpHdr")
    _child(header, "MsgId", _text(payment_file.message_id, MAX_ID))
    created = payment_file.created_at.astimezone(UTC).replace(tzinfo=None)
    _child(header, "CreDtTm", created.isoformat(timespec="seconds"))
    _child(header, "NbOfTxs", str(len(payment_file.transfers)))
    _child(header, "CtrlSum", _amount(control_sum(payment_file.transfers)))
    _child(_child(header, "InitgPty"), "Nm", _text(payment_file.debtor.name, MAX_NAME))


def _payment_block(parent: ET.Element, payment_file: PaymentFile, block_id: str, block: list[CreditTransfer]) -> None:
    debtor = payment_file.debtor
    payment = _child(parent, "PmtInf")
    _child(payment, "PmtInfId", block_id)
    _child(payment, "PmtMtd", TRANSFER_METHOD)
    _child(payment, "NbOfTxs", str(len(block)))
    _child(payment, "CtrlSum", _amount(control_sum(block)))
    _child(_child(payment, "ReqdExctnDt"), "Dt", payment_file.execution_date.isoformat())
    _child(_child(payment, "Dbtr"), "Nm", _text(debtor.name, MAX_NAME))
    _account(payment, "DbtrAcct", debtor.account_id)
    _agent(payment, "DbtrAgt", debtor.agent_name)
    for transfer in block:
        _transaction(payment, transfer)


def _transaction(parent: ET.Element, transfer: CreditTransfer) -> None:
    transaction = _child(parent, "CdtTrfTxInf")
    _child(_child(transaction, "PmtId"), "EndToEndId", _end_to_end_id(transfer.end_to_end_id))
    amount = _child(_child(transaction, "Amt"), "InstdAmt", _amount(transfer.amount))
    amount.set("Ccy", _currency(transfer.currency))
    _agent(transaction, "CdtrAgt", transfer.creditor_bank)
    _creditor(transaction, transfer)
    _account(transaction, "CdtrAcct", transfer.creditor_account)
    _child(_child(transaction, "RmtInf"), "Ustrd", _text(transfer.remittance, MAX_REMITTANCE))


def _creditor(parent: ET.Element, transfer: CreditTransfer) -> None:
    creditor = _child(parent, "Cdtr")
    _child(creditor, "Nm", _text(transfer.creditor_name, MAX_NAME))
    country = (transfer.creditor_country or "").strip().upper()
    if COUNTRY.fullmatch(country):
        _child(_child(creditor, "PstlAdr"), "Ctry", country)
    tax_id = _text(transfer.creditor_tax_id, MAX_ID)
    if tax_id:
        _child(_child(_child(_child(creditor, "Id"), "OrgId"), "Othr"), "Id", tax_id)


def _account(parent: ET.Element, name: str, account_id: str) -> None:
    identifier = SPACES.sub("", CONTROL.sub("", account_id))[:MAX_ACCOUNT] or "SIN-CUENTA"
    _child(_child(_child(_child(parent, name), "Id"), "Othr"), "Id", identifier)


def _agent(parent: ET.Element, name: str, bank_name: str) -> None:
    _child(_child(_child(parent, name), "FinInstnId"), "Nm", _text(bank_name, MAX_NAME) or "Sin banco")


def _end_to_end_id(invoice_id: str) -> str:
    """Kept whole when it fits; a longer id keeps its start plus a digest of the whole, so two ids never collide."""
    clean = _text(invoice_id, len(invoice_id))
    if len(clean) <= MAX_ID:
        return clean
    digest = hashlib.sha256(invoice_id.encode()).hexdigest()[:HASH_LENGTH]
    return f"{clean[: MAX_ID - HASH_LENGTH - 1]}-{digest}"


def _child(parent: ET.Element, name: str, text: str | None = None) -> ET.Element:
    element = ET.SubElement(parent, _tag(name))
    if text is not None:
        element.text = text
    return element


def _tag(name: str) -> str:
    return f"{{{NAMESPACE}}}{name}"


def _text(value: str, limit: int) -> str:
    return SPACES.sub(" ", CONTROL.sub(" ", value)).strip()[:limit]


def _currency(code: str) -> str:
    return code.strip().upper()


def _money(amount: Decimal) -> Decimal:
    return amount.quantize(CENTS)


def _amount(amount: Decimal) -> str:
    return f"{_money(amount):.2f}"
