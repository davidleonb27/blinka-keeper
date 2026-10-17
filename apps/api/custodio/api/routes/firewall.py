from __future__ import annotations

from fastapi import APIRouter

from custodio.api.deps import ApiKeyWorkspace, ModelCallLimitByKey, Services
from custodio.contracts import IntentVerdict, PaymentIntent
from custodio.services import firewall_service

router = APIRouter(prefix="/firewall", tags=["firewall"])


@router.post("/intents", response_model=IntentVerdict, dependencies=[ModelCallLimitByKey])
def submit_intent(intent: PaymentIntent, ctx: Services, workspace: ApiKeyWorkspace) -> IntentVerdict:
    return firewall_service.submit(ctx, workspace, intent)
