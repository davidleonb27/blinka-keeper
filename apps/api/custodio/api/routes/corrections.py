"""Supplier corrections. The company asks from the acta; the supplier answers through a one-time public link."""

from __future__ import annotations

import hashlib
from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from custodio.api.deps import ClientIp, CurrentWorkspace, RuntimeDep, Services
from custodio.api.routes.invoices import media_type_of
from custodio.corrections import MAX_CONFIRMED_LENGTH, CorrectableField
from custodio.services import correction_service, rate_limits
from custodio.services.correction_service import (
    CorrectionIssued,
    CorrectionOffer,
    CorrectionOverview,
    SupplierCorrectionView,
    SupplierReceipt,
)

router = APIRouter(tags=["corrections"])

LINK_KEY_LENGTH = 16  # the per-link rate-limit key: a prefix of the token's hash, never the token


class CorrectionRequestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    whatsapp: bool = False  # also send it by WhatsApp when that lane is on and the invoice came that way


class ConfirmationBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    values: dict[CorrectableField, Annotated[str, Field(max_length=MAX_CONFIRMED_LENGTH)]]


@router.get("/corrections", response_model=CorrectionOverview)
def list_corrections(ctx: Services, workspace: CurrentWorkspace) -> CorrectionOverview:
    return correction_service.overview(ctx, workspace)


@router.get("/decisions/{invoice_id}/correction", response_model=CorrectionOffer)
def read_correction(invoice_id: str, ctx: Services, workspace: CurrentWorkspace) -> CorrectionOffer:
    return correction_service.offer(ctx, workspace, invoice_id)


@router.post("/decisions/{invoice_id}/correction", status_code=201, response_model=CorrectionIssued)
def request_correction(
    invoice_id: str, body: CorrectionRequestBody, ctx: Services, workspace: CurrentWorkspace
) -> CorrectionIssued:
    return correction_service.request(ctx, workspace, invoice_id, whatsapp=body.whatsapp)


def limit_supplier_uploads(token: str, runtime: RuntimeDep, ip: ClientIp) -> None:
    link = hashlib.sha256(token.encode()).hexdigest()[:LINK_KEY_LENGTH]
    rate_limits.check_model_call(runtime, ip=ip, workspace_id=f"supplier-link:{link}")


SupplierUploadLimit = Depends(limit_supplier_uploads)


@router.get("/supplier/corrections/{token}", response_model=SupplierCorrectionView)
def read_supplier_correction(token: str, ctx: Services) -> SupplierCorrectionView:
    return correction_service.supplier_view(ctx, token)


@router.post(
    "/supplier/corrections/{token}/document", response_model=SupplierReceipt, dependencies=[SupplierUploadLimit]
)
def submit_corrected_document(token: str, ctx: Services, file: Annotated[UploadFile, File()]) -> SupplierReceipt:
    filename = file.filename or "factura-corregida"
    return correction_service.submit_document(
        ctx, token, file.file.read(), filename=filename, media_type=media_type_of(file.content_type, filename)
    )


@router.post(
    "/supplier/corrections/{token}/confirm", response_model=SupplierReceipt, dependencies=[SupplierUploadLimit]
)
def submit_confirmation(token: str, body: ConfirmationBody, ctx: Services) -> SupplierReceipt:
    return correction_service.submit_confirmation(ctx, token, body.values)
