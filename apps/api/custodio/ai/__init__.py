"""Claude-powered features that never decide a payment. Owned by lane L3.

Every function here calls Claude through `custodio.llm.structured`, validates the result with code and
returns contract objects. When the model cannot answer, the function says so (raises or returns
`questions`/`unsupported`); it never fills a gap with a guess.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping

from custodio.contracts import (
    AttackSpec,
    CompanyProfile,
    CompanyState,
    Decision,
    Policy,
    PolicyProposal,
    RedTeamEvent,
    SupplierImport,
)


def compile_policy(text: str, current: Policy) -> PolicyProposal:
    """Turn Spanish rules into a policy proposal. `simulation` is left None; the API fills it with the engine."""
    raise NotImplementedError("lane L3")


def narrate(decision: Decision) -> str:
    """Plain-language version of an acta. Every number in the output must appear in the decision."""
    raise NotImplementedError("lane L3")


def profile_company(company_name: str, website: str | None, answers: Mapping[str, str]) -> CompanyProfile:
    """Infer a company profile from its public website and onboarding answers, citing the pages used."""
    raise NotImplementedError("lane L3")


def import_suppliers(data: bytes, *, filename: str, media_type: str) -> SupplierImport:
    """Read a supplier list (CSV, XLSX, PDF contract or invoice) into beneficiaries with agreements."""
    raise NotImplementedError("lane L3")


def red_team(
    policy: Policy,
    state: CompanyState,
    *,
    rounds: int,
    judge: Callable[[AttackSpec], Decision],
) -> Iterator[RedTeamEvent]:
    """Adaptive attacker: each round reads earlier verdicts and tries a new fraud; `judge` runs the real pipeline."""
    raise NotImplementedError("lane L3")
