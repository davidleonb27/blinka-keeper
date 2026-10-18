"""The receipt signing key: Ed25519, the same key for every process of a deployment.

CUSTODIO_RECEIPT_SIGNING_KEY holds it (a PKCS#8 PEM, or the 32-byte seed in base64 or hex). Without it the key is
derived with HKDF-SHA256 from the database URL: the one server secret every deployment already has (it carries the
Neon password), and the one whose lifetime matches what the receipts point to, since every receipt names a position
in that database's ledger. A key is never generated at boot: receipts signed yesterday must still verify today.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import logging
from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from custodio.receipts.errors import ReceiptKeyError
from custodio.receipts.models import ReceiptKey

logger = logging.getLogger(__name__)

SEED_BYTES = 32
KEY_ID_PREFIX = "cust-"
KEY_ID_HEX_CHARS = 16
HKDF_SALT = b"custodio-receipt-signing/v1"
HKDF_INFO = b"ed25519 seed"
PUBLIC_SECRETS = ("sqlite",)  # a local database URL is no secret: the derived key only suits development


@dataclass(frozen=True)
class ReceiptPublicKey:
    raw: bytes

    @property
    def key_id(self) -> str:
        return KEY_ID_PREFIX + hashlib.sha256(self.raw).hexdigest()[:KEY_ID_HEX_CHARS]

    def verifies(self, signature: bytes, data: bytes) -> bool:
        try:
            Ed25519PublicKey.from_public_bytes(self.raw).verify(signature, data)
        except (InvalidSignature, ValueError):
            return False
        return True

    def view(self) -> ReceiptKey:
        pem = (
            Ed25519PublicKey.from_public_bytes(self.raw)
            .public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo)
            .decode()
        )
        return ReceiptKey(key_id=self.key_id, public_key=base64.b64encode(self.raw).decode(), public_key_pem=pem)


@dataclass(frozen=True)
class ReceiptSigner:
    private: Ed25519PrivateKey

    @property
    def public_key(self) -> ReceiptPublicKey:
        raw = self.private.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
        return ReceiptPublicKey(raw)

    @property
    def key_id(self) -> str:
        return self.public_key.key_id

    def sign(self, data: bytes) -> bytes:
        return self.private.sign(data)

    @classmethod
    def from_seed(cls, seed: bytes) -> ReceiptSigner:
        return cls(Ed25519PrivateKey.from_private_bytes(seed))


def signer_from_secrets(signing_key: str | None, server_secret: str) -> ReceiptSigner:
    """`signing_key` is CUSTODIO_RECEIPT_SIGNING_KEY and `server_secret` the database URL; neither is ever logged."""
    configured = (signing_key or "").strip()
    if configured:
        return _parse(configured)
    if server_secret.startswith(PUBLIC_SECRETS):
        logger.warning("No CUSTODIO_RECEIPT_SIGNING_KEY and a local database: receipts use a development key")
    return ReceiptSigner.from_seed(derive_seed(server_secret))


def derive_seed(server_secret: str) -> bytes:
    hkdf = HKDF(algorithm=hashes.SHA256(), length=SEED_BYTES, salt=HKDF_SALT, info=HKDF_INFO)
    return hkdf.derive(server_secret.encode())


def _parse(configured: str) -> ReceiptSigner:
    if configured.startswith("-----BEGIN"):
        return _from_pem(configured)
    seed = _decoded(configured)
    if len(seed) != SEED_BYTES:
        raise ReceiptKeyError("CUSTODIO_RECEIPT_SIGNING_KEY must be a PEM or a 32-byte seed in base64 or hex")
    return ReceiptSigner.from_seed(seed)


def _from_pem(pem: str) -> ReceiptSigner:
    try:
        key = serialization.load_pem_private_key(pem.encode(), password=None)
    except ValueError as error:
        raise ReceiptKeyError("CUSTODIO_RECEIPT_SIGNING_KEY is not a readable PEM private key") from error
    if not isinstance(key, Ed25519PrivateKey):
        raise ReceiptKeyError("CUSTODIO_RECEIPT_SIGNING_KEY must be an Ed25519 key")
    return ReceiptSigner(key)


def _decoded(text: str) -> bytes:
    if len(text) == 2 * SEED_BYTES:
        try:
            return bytes.fromhex(text)
        except ValueError:
            pass
    try:
        return base64.b64decode(text.replace("-", "+").replace("_", "/") + "=" * (-len(text) % 4), validate=True)
    except binascii.Error:
        return b""
