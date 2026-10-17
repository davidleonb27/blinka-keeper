"""Honest errors: every failure answers JSON with a Spanish `detail` and a stable `code`, never a silent 500."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from custodio.llm import LLMError
from custodio.services import errors

logger = logging.getLogger(__name__)

STATUS_BY_ERROR: dict[type[errors.ServiceError], int] = {
    errors.WorkspaceHeaderMissing: 400,
    errors.InvalidApiKey: 401,
    errors.NotFound: 404,
    errors.DecisionNotPending: 409,
    errors.PaymentNotRetryable: 409,
    errors.ReconciliationConflict: 409,
    errors.PayloadTooLarge: 413,
    errors.UnsupportedMediaType: 415,
    errors.UnsupportedStatement: 415,
    errors.PolicyInvalid: 422,
    errors.InvoiceInputMissing: 422,
    errors.StatementInputMissing: 422,
    errors.StatementUnreadable: 422,
    errors.RateLimited: 429,
    errors.ModelUnavailable: 503,
    errors.ReadingUnavailable: 503,
}
INVALID_REQUEST = "La solicitud no es válida. Revisa los campos marcados."
INTERNAL_ERROR = "Error interno. No se hizo ningún pago ni cambio; inténtalo de nuevo."


def error_response(error: errors.ServiceError) -> JSONResponse:
    content: dict[str, object] = {"detail": error.message, "code": error.code}
    headers: dict[str, str] = {}
    if isinstance(error, errors.RateLimited):
        headers["Retry-After"] = str(max(error.retry_after_seconds, 1))
    if isinstance(error, errors.ReadingUnavailable):
        content["invoice_id"] = error.invoice_id
    return JSONResponse(status_code=_status(error), content=content, headers=headers)


def _status(error: errors.ServiceError) -> int:
    for kind in type(error).__mro__:
        if kind in STATUS_BY_ERROR:
            return STATUS_BY_ERROR[kind]
    return 500


async def _service_error(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, errors.ServiceError)
    return error_response(error)


async def _model_error(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, LLMError)
    logger.warning("model call failed: %s", type(error).__name__)
    return error_response(errors.model_failure(error))


async def _validation_error(_: Request, error: Exception) -> JSONResponse:
    assert isinstance(error, RequestValidationError)
    problems = [{"loc": list(problem["loc"]), "msg": problem["msg"]} for problem in error.errors()]
    return JSONResponse(
        status_code=422, content={"detail": INVALID_REQUEST, "code": "invalid_request", "errors": problems}
    )


async def _unexpected_error(_: Request, error: Exception) -> JSONResponse:
    logger.exception("unexpected error", exc_info=error)
    return JSONResponse(status_code=500, content={"detail": INTERNAL_ERROR, "code": "internal_error"})


def install(app: FastAPI) -> None:
    app.add_exception_handler(errors.ServiceError, _service_error)
    app.add_exception_handler(LLMError, _model_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(Exception, _unexpected_error)
