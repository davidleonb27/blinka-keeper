"""Claude-powered features that never decide a payment. Owned by lane L3.

Every function here calls Claude through `custodio.llm.structured`, validates the result with code and
returns contract objects. When the model cannot answer, the function says so (raises or returns
`questions`/`unsupported`); it never fills a gap with a guess.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

from custodio.ai.narrator import narrate
from custodio.ai.policy_compiler import compile_policy
from custodio.ai.profile import profile_company
from custodio.ai.suppliers import import_suppliers
from custodio.contracts import AttackSpec, CompanyState, Decision, Policy, RedTeamEvent

__all__ = ["compile_policy", "import_suppliers", "narrate", "profile_company", "red_team"]


def red_team(
    policy: Policy,
    state: CompanyState,
    *,
    rounds: int,
    judge: Callable[[AttackSpec], Decision],
) -> Iterator[RedTeamEvent]:
    """Adaptive attacker: each round reads earlier verdicts and tries a new fraud; `judge` runs the real pipeline."""
    raise NotImplementedError("lane L3")
