"""Where the signing key comes from: configured, or derived the same way on every boot. Never generated."""

from __future__ import annotations

import base64

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from custodio.receipts import ReceiptKeyError, ReceiptSigner, signer_from_secrets

from .builders import FIXED_SEED

DATABASE_URL = "postgresql://custodio:s3cret@neon.example/custodio"


def test_a_configured_seed_in_base64_hex_or_base64url_gives_the_same_key() -> None:
    expected = ReceiptSigner.from_seed(FIXED_SEED).key_id

    for configured in (
        base64.b64encode(FIXED_SEED).decode(),
        FIXED_SEED.hex(),
        base64.urlsafe_b64encode(FIXED_SEED).decode().rstrip("="),
    ):
        assert signer_from_secrets(configured, DATABASE_URL).key_id == expected


def test_a_configured_pem_is_used_as_is() -> None:
    key = Ed25519PrivateKey.from_private_bytes(FIXED_SEED)
    pem = key.private_bytes(
        serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()
    ).decode()

    assert signer_from_secrets(pem, DATABASE_URL).key_id == ReceiptSigner.from_seed(FIXED_SEED).key_id


@pytest.mark.parametrize("configured", ["abc", "-----BEGIN PRIVATE KEY-----\nnope\n-----END PRIVATE KEY-----", "zz" * 32])
def test_an_unusable_configured_key_stops_the_boot_without_echoing_it(configured: str) -> None:
    with pytest.raises(ReceiptKeyError) as error:
        signer_from_secrets(configured, DATABASE_URL)

    assert configured not in str(error.value)


def test_without_a_configured_key_the_key_is_derived_and_stable_across_boots() -> None:
    first = signer_from_secrets(None, DATABASE_URL)
    second = signer_from_secrets("  ", DATABASE_URL)

    assert first.key_id == second.key_id
    assert first.sign(b"acta") == second.sign(b"acta")


def test_another_server_secret_derives_another_key() -> None:
    assert signer_from_secrets(None, DATABASE_URL).key_id != signer_from_secrets(None, DATABASE_URL + "x").key_id


def test_the_public_view_carries_the_key_id_the_raw_key_and_a_pem() -> None:
    signer = ReceiptSigner.from_seed(FIXED_SEED)
    view = signer.public_key.view()

    assert view.key_id == signer.key_id and view.key_id.startswith("cust-")
    assert base64.b64decode(view.public_key) == signer.public_key.raw
    assert view.public_key_pem.startswith("-----BEGIN PUBLIC KEY-----")
    assert view.algorithm == "Ed25519"
