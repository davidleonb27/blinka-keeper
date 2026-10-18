"""/pagos: the workspace's payments, Stripe's live proof of each transfer and the pain.001 file for Blinka."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response

from custodio.api.deps import ClientIp, CurrentWorkspace, RuntimeDep, Services
from custodio.services import rate_limits, stripe_service
from custodio.services.stripe_service import PaymentsOverview, StripeProof

router = APIRouter(prefix="/payments", tags=["payments"])
XML = "application/xml"


def limit_stripe_lookups(runtime: RuntimeDep, workspace: CurrentWorkspace, ip: ClientIp) -> None:
    rate_limits.check_stripe_lookup(runtime, ip=ip, workspace_id=workspace.id)


StripeLookupLimit = Depends(limit_stripe_lookups)


@router.get("", response_model=PaymentsOverview, dependencies=[StripeLookupLimit])
def read_payments(ctx: Services, workspace: CurrentWorkspace) -> PaymentsOverview:
    return stripe_service.overview(ctx, workspace)


@router.get(
    "/pain001.xml",
    response_class=Response,
    responses={200: {"content": {XML: {}}, "description": "ISO 20022 pain.001.001.09"}},
)
def export_pain001(
    ctx: Services, workspace: CurrentWorkspace, decided_on: Annotated[date | None, Query()] = None
) -> Response:
    """The approved payments as an ISO 20022 pain.001.001.09 file, ready for Blinka to pay."""
    filename, xml = stripe_service.pain001(ctx, workspace, decided_on)
    return Response(xml, media_type=XML, headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.get("/{invoice_id}/stripe", response_model=StripeProof, dependencies=[StripeLookupLimit])
def read_stripe_proof(invoice_id: str, ctx: Services, workspace: CurrentWorkspace) -> StripeProof:
    """Asks Stripe, live, for the transfer behind this payment and checks it against the acta."""
    return stripe_service.proof(ctx, workspace, invoice_id)
