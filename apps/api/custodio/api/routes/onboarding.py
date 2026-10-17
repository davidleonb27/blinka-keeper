from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from pydantic import BaseModel, ConfigDict, Field

from custodio.api.deps import CurrentWorkspace, ModelCallLimit, Services
from custodio.api.routes.invoices import media_type_of
from custodio.contracts import CompanyProfile, SupplierImport
from custodio.services import onboarding_service
from custodio.services.onboarding_service import OnboardingRequest, OnboardingResult

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


class ProfileRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_name: str = Field(min_length=1, max_length=200)
    website: str | None = Field(default=None, max_length=300)
    answers: dict[str, str] = {}


@router.post("/profile", response_model=CompanyProfile, dependencies=[ModelCallLimit])
def propose_profile(body: ProfileRequest, ctx: Services, workspace: CurrentWorkspace) -> CompanyProfile:
    return onboarding_service.propose_profile(ctx, body.company_name, body.website, body.answers)


@router.post("/suppliers", response_model=SupplierImport, dependencies=[ModelCallLimit])
def import_suppliers(file: Annotated[UploadFile, File()], ctx: Services, workspace: CurrentWorkspace) -> SupplierImport:
    filename = file.filename or "proveedores"
    return onboarding_service.import_suppliers(
        ctx, file.file.read(), filename=filename, media_type=media_type_of(file.content_type, filename)
    )


@router.post("/complete", response_model=OnboardingResult)
def complete(body: OnboardingRequest, ctx: Services, workspace: CurrentWorkspace) -> OnboardingResult:
    return onboarding_service.complete(ctx, workspace, body)
