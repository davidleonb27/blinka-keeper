"""Signing a receipt and checking it, the way a third party would: with nothing but the public key."""

from __future__ import annotations

import copy
import json
import sys
from typing import Any

import pytest

from custodio.receipts import field_digests, sign_receipt, signed_bytes, verify_receipt

from .builders import fixed_signer, other_signer, sample_body

SIGNER = fixed_signer()
RECEIPT = sign_receipt(sample_body(SIGNER.key_id), SIGNER).model_dump(mode="json")
LEAVES = sorted(RECEIPT["field_digests"])


def altered(path: str) -> dict[str, Any]:
    receipt = copy.deepcopy(RECEIPT)
    *parents, last = path.split(".")
    target: Any = receipt["body"]
    for part in parents:
        target = target[int(part)] if isinstance(target, list) else target[part]
    if isinstance(target, list):
        target[int(last)] = _other(target[int(last)])
    else:
        target[last] = _other(target[last])
    return receipt


def _other(value: object) -> object:
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if value is None:
        return "x"
    return f"{value}0"


def test_a_signed_receipt_verifies_with_the_public_key_and_says_the_decision() -> None:
    check = verify_receipt(RECEIPT, SIGNER.public_key)

    assert check.valid is True
    assert check.verdict == "pay"
    assert check.invoice_id == "INV-0001"
    assert check.message == f"Válido: firmado por Blinka Keeper con la clave {SIGNER.key_id}. La decisión fue «Pagar»."


def test_the_receipt_survives_a_round_trip_through_json_text() -> None:
    assert verify_receipt(json.loads(json.dumps(RECEIPT, indent=2)), SIGNER.public_key).valid is True


@pytest.mark.parametrize("path", LEAVES)
def test_altering_any_field_is_caught_and_named(path: str) -> None:
    check = verify_receipt(altered(path), SIGNER.public_key)

    assert check.valid is False
    assert check.altered_fields == [path]
    assert check.altered_labels and check.altered_labels[0] in check.message


def test_the_amount_reads_as_a_person_would_say_it() -> None:
    check = verify_receipt(altered("payment.amount"), SIGNER.public_key)

    assert check.message == "Inválido: el campo monto fue alterado después de firmarse."


def test_two_altered_fields_are_both_named() -> None:
    receipt = altered("payment.amount")
    receipt["body"]["decision"]["verdict"] = "hold"

    check = verify_receipt(receipt, SIGNER.public_key)

    assert check.altered_labels == ["decisión", "monto"]
    assert "los campos decisión y monto fueron alterados" in check.message


def test_an_added_or_removed_field_is_caught() -> None:
    added = copy.deepcopy(RECEIPT)
    added["body"]["payment"]["memo"] = "pagar ya"
    removed = copy.deepcopy(RECEIPT)
    del removed["body"]["invoice"]["number"]

    assert verify_receipt(added, SIGNER.public_key).altered_fields == ["payment.memo"]
    assert verify_receipt(removed, SIGNER.public_key).altered_fields == ["invoice.number"]


def test_editing_a_field_and_its_digest_together_still_fails() -> None:
    receipt = altered("payment.amount")
    receipt["field_digests"] = field_digests(receipt["body"])

    check = verify_receipt(receipt, SIGNER.public_key)

    assert check.valid is False
    assert check.altered_fields == []
    assert check.message.startswith("Inválido: la firma no corresponde")


def test_a_receipt_signed_with_another_key_is_refused() -> None:
    stranger = other_signer()
    forged = sign_receipt(sample_body(stranger.key_id), stranger).model_dump(mode="json")

    check = verify_receipt(forged, SIGNER.public_key)

    assert check.valid is False
    assert stranger.key_id in check.message and SIGNER.key_id in check.message


def test_a_forged_receipt_that_claims_our_key_id_is_refused() -> None:
    stranger = other_signer()
    forged = sign_receipt(sample_body(SIGNER.key_id), stranger).model_dump(mode="json")
    forged["key_id"] = SIGNER.key_id

    assert verify_receipt(forged, SIGNER.public_key).valid is False


@pytest.mark.parametrize(
    "raw",
    [None, [], "recibo", {}, {**RECEIPT, "algorithm": "RSA"}, {**RECEIPT, "signature": "%%%"}, {**RECEIPT, "body": 3}],
)
def test_anything_that_is_not_a_receipt_says_so(raw: object) -> None:
    check = verify_receipt(raw, SIGNER.public_key)

    assert check.valid is False
    assert check.message == "Inválido: esto no tiene la forma de un recibo firmado de Blinka Keeper."


def test_a_body_that_cannot_be_written_canonically_is_not_a_receipt() -> None:
    receipt = copy.deepcopy(RECEIPT)
    receipt["body"]["payment"]["amount"] = float("nan")

    assert verify_receipt(receipt, SIGNER.public_key).valid is False


@pytest.mark.parametrize("value", ["\ud800", [[[[[]]]]]])
def test_a_body_with_a_lone_surrogate_or_nested_past_the_stack_is_not_a_receipt(value: object) -> None:
    receipt = copy.deepcopy(RECEIPT)
    nested: object = value
    if isinstance(value, list):
        for _ in range(sys.getrecursionlimit()):
            nested = [nested]
    receipt["body"]["payment"]["amount"] = nested

    check = verify_receipt(receipt, SIGNER.public_key)

    assert check.valid is False
    assert check.message == "Inválido: esto no tiene la forma de un recibo firmado de Blinka Keeper."


def test_canonical_bytes_ignore_key_order_and_whitespace() -> None:
    body = RECEIPT["body"]
    shuffled = json.loads(json.dumps(dict(reversed(list(body.items()))), indent=4))

    assert signed_bytes(shuffled) == signed_bytes(body)
    assert b" " not in signed_bytes({"a": 1, "b": [1, 2]})


def test_signing_is_deterministic() -> None:
    again = sign_receipt(sample_body(SIGNER.key_id), SIGNER).model_dump(mode="json")

    assert again == RECEIPT


def test_a_decision_not_to_pay_has_no_payment_section() -> None:
    held = sign_receipt(sample_body(SIGNER.key_id, verdict="hold"), SIGNER).model_dump(mode="json")

    check = verify_receipt(held, SIGNER.public_key)

    assert held["body"]["payment"] is None
    assert check.valid is True and check.verdict == "hold"
    assert "«Retener»" in check.message
