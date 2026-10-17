from __future__ import annotations

import mimetypes
from typing import Annotated

from fastapi import APIRouter, File, Form, UploadFile
from fastapi.responses import JSONResponse

from custodio.api.deps import CurrentWorkspace, ModelCallLimit, Services
from custodio.api.errors import error_response
from custodio.services import invoice_service
from custodio.services.errors import InvoiceInputMissing, ReadingUnavailable
from custodio.services.invoice_service import InvoiceView, Outcome

router = APIRouter(prefix="/invoices", tags=["invoices"])

GENERIC_MEDIA_TYPE = "application/octet-stream"


@router.post("", status_code=201, response_model=InvoiceView, dependencies=[ModelCallLimit])
def upload_invoice(
    ctx: Services,
    workspace: CurrentWorkspace,
    file: Annotated[UploadFile | None, File()] = None,
    text: Annotated[str | None, Form()] = None,
) -> InvoiceView | JSONResponse:
    received = _receive(ctx, workspace, file, text)
    if not received.read_ok:
        return error_response(ReadingUnavailable(received.id))  # stored: a person reviews it
    return received


@router.post("/process", response_model=Outcome)
def process_invoices(ctx: Services, workspace: CurrentWorkspace) -> Outcome:
    return invoice_service.process_pending(ctx, workspace)


def _receive(ctx: Services, workspace: CurrentWorkspace, file: UploadFile | None, text: str | None) -> InvoiceView:
    if file is not None:
        data = file.file.read()
        filename = file.filename or "factura"
        return invoice_service.receive_document(
            ctx, workspace, data, filename=filename, media_type=media_type_of(file.content_type, filename)
        )
    if text and text.strip():
        return invoice_service.receive_text(ctx, workspace, text)
    raise InvoiceInputMissing()


def media_type_of(declared: str | None, filename: str) -> str:
    if declared and declared != GENERIC_MEDIA_TYPE:
        return declared.split(";")[0].strip().lower()
    guessed, _ = mimetypes.guess_type(filename)
    return guessed or GENERIC_MEDIA_TYPE
