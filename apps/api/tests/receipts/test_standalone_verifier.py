"""The verifier that travels with the evidence pack: standard library only, and it agrees with Blinka Keeper."""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

from custodio.receipts import sign_receipt
from custodio.receipts.verificar_recibo import ed25519_verify, field_digests

from .builders import fixed_signer, other_signer, sample_body

SCRIPT = Path(__file__).parents[2] / "custodio" / "receipts" / "verificar_recibo.py"
SIGNER = fixed_signer()
RECEIPT = sign_receipt(sample_body(SIGNER.key_id), SIGNER).model_dump(mode="json")


def run(tmp_path: Path, receipt: dict[str, Any], *extra: str) -> subprocess.CompletedProcess[str]:
    receipt_file, key_file = tmp_path / "recibo.json", tmp_path / "clave_publica.json"
    receipt_file.write_text(json.dumps(receipt, ensure_ascii=False, indent=2), encoding="utf-8")
    key_file.write_text(SIGNER.public_key.view().model_dump_json(), encoding="utf-8")
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(receipt_file), str(key_file), *extra],
        capture_output=True,
        text=True,
        check=False,
    )


@pytest.mark.parametrize("message", [b"", b"acta", "decisión «Pagar»".encode(), bytes(range(256))])
def test_the_pure_python_ed25519_agrees_with_the_library(message: bytes) -> None:
    signature = SIGNER.sign(message)

    assert ed25519_verify(SIGNER.public_key.raw, message, signature) is True
    assert ed25519_verify(SIGNER.public_key.raw, message + b"x", signature) is False
    assert ed25519_verify(other_signer().public_key.raw, message, signature) is False
    assert ed25519_verify(SIGNER.public_key.raw, message, signature[:-1] + bytes([signature[-1] ^ 1])) is False


def test_its_field_digests_are_the_ones_custodio_signs() -> None:
    assert field_digests(RECEIPT["body"]) == RECEIPT["field_digests"]


def test_a_valid_receipt_exits_zero(tmp_path: Path) -> None:
    result = run(tmp_path, RECEIPT)

    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith("VÁLIDO")


def test_an_altered_amount_exits_one_and_names_the_field(tmp_path: Path) -> None:
    tampered = copy.deepcopy(RECEIPT)
    tampered["body"]["payment"]["amount"] = "42000"

    result = run(tmp_path, tampered)

    assert result.returncode == 1
    assert result.stdout.strip() == "INVÁLIDO: se alteró payment.amount"


def test_a_receipt_from_another_key_exits_one(tmp_path: Path) -> None:
    stranger = other_signer()

    result = run(tmp_path, sign_receipt(sample_body(stranger.key_id), stranger).model_dump(mode="json"))

    assert result.returncode == 1


def test_it_exports_what_openssl_needs(tmp_path: Path) -> None:
    run(tmp_path, RECEIPT, "--exportar", str(tmp_path / "openssl"))

    exported = tmp_path / "openssl"
    body = (exported / "cuerpo.json").read_bytes()
    assert SIGNER.public_key.verifies((exported / "firma.bin").read_bytes(), body)
    assert (exported / "clave.pem").read_text().startswith("-----BEGIN PUBLIC KEY-----")
