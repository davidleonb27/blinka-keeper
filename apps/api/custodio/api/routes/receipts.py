"""Signed receipts for third parties: the public key, a server-side check and an example to try the check with.

None of these routes needs a workspace: whoever holds a receipt can check it without access to Blinka Keeper.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body
from pydantic import JsonValue

from custodio.api.deps import Services
from custodio.receipts import DecisionReceipt, ReceiptCheck, ReceiptKey
from custodio.services import receipt_service

router = APIRouter(tags=["receipts"])


@router.get("/.well-known/custodio-receipt-key", response_model=ReceiptKey)
def receipt_key(ctx: Services) -> ReceiptKey:
    return receipt_service.key(ctx)


@router.post("/receipts/verify", response_model=ReceiptCheck)
def verify_receipt(receipt: Annotated[JsonValue, Body()], ctx: Services) -> ReceiptCheck:
    """Checks a receipt with Blinka Keeper's public key and names the field that was altered, if any."""
    return receipt_service.check(ctx, receipt)


@router.get("/receipts/example", response_model=DecisionReceipt)
def example_receipt(ctx: Services) -> DecisionReceipt:
    """A receipt of a made-up decision (workspace «ejemplo»), signed with the real key, to try the check with."""
    return receipt_service.example(ctx)
