from __future__ import annotations

from fastapi import APIRouter

from custodio.api.deps import CurrentWorkspace, Services
from custodio.services import simulation_service, trust_service
from custodio.services.simulation_service import SimulationResult
from custodio.services.trust_service import TrustOverview

router = APIRouter(prefix="/trust", tags=["trust"])


@router.get("", response_model=TrustOverview)
def read_trust(ctx: Services, workspace: CurrentWorkspace) -> TrustOverview:
    """Each supplier's earned auto-approval cap (R9), folded from its trust entries in the ledger."""
    return trust_service.overview(ctx, workspace)


@router.post("/simulate", response_model=SimulationResult)
def simulate_month(ctx: Services, workspace: CurrentWorkspace) -> SimulationResult:
    """Plays the demo's seeded month once, on the simulated rail. Calling it again changes nothing."""
    return simulation_service.simulate_month(ctx, workspace)
