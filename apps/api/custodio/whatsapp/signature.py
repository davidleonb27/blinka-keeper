"""Meta's two proofs: the verify token of the subscription handshake and the X-Hub-Signature-256 of each delivery."""

from __future__ import annotations

import hashlib
import hmac

SIGNATURE_PREFIX = "sha256="


def token_matches(given: str | None, expected: str) -> bool:
    return given is not None and hmac.compare_digest(given.encode(), expected.encode())


def signature_valid(body: bytes, header: str | None, app_secret: str) -> bool:
    """HMAC-SHA256 of the raw body with the app secret, compared in constant time."""
    if not header or not header.startswith(SIGNATURE_PREFIX):
        return False
    expected = hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(header[len(SIGNATURE_PREFIX) :].strip().lower().encode(), expected.encode())


def sign(body: bytes, app_secret: str) -> str:
    """The header Meta would send for this body: what tests and the e2e walk use to deliver a message."""
    return SIGNATURE_PREFIX + hmac.new(app_secret.encode(), body, hashlib.sha256).hexdigest()
