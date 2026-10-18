"""The browser checks receipts with its own code: this golden receipt pins both sides to the same bytes.

apps/web/src/lib/receipts/golden-receipt.json is read by the web's tests too. If a change here is deliberate, rewrite
it with `golden()` below and commit both sides together.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from custodio.receipts import sign_receipt, signed_bytes

from .builders import fixed_signer, sample_body

GOLDEN = Path(__file__).parents[3] / "web" / "src" / "lib" / "receipts" / "golden-receipt.json"


def golden() -> dict[str, Any]:
    signer = fixed_signer()
    receipt = sign_receipt(sample_body(signer.key_id), signer).model_dump(mode="json")
    return {
        "key": signer.public_key.view().model_dump(mode="json"),
        "receipt": receipt,
        "canonical_body": signed_bytes(receipt["body"]).decode(),
    }


def test_the_web_golden_receipt_is_what_the_api_signs_today() -> None:
    assert json.loads(GOLDEN.read_text(encoding="utf-8")) == golden()
