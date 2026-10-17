"""Live checks against the real models. Run with CUSTODIO_LIVE_TESTS=1 uv run pytest -m live -s tests/ai."""

import os
import re
from collections.abc import Callable
from decimal import Decimal

import pytest

from custodio.ai import compile_policy, narrate, profile_company, red_team
from custodio.contracts import AttackSpec, Decision, Policy, PolicyProposal, RuleOutcome

from .conftest import make_decision, make_policy, make_state

pytestmark = [
    pytest.mark.live,
    pytest.mark.skipif(os.environ.get("CUSTODIO_LIVE_TESTS") != "1", reason="set CUSTODIO_LIVE_TESTS=1"),
]

Check = Callable[[PolicyProposal, Policy], bool]


def only(proposal: PolicyProposal, *fields: str) -> bool:
    return sorted(c.field for c in proposal.changes) == sorted(fields)


def agreement(policy: Policy, beneficiary_id: str) -> tuple[str, Decimal] | None:
    found = next(b.agreement for b in policy.beneficiaries if b.id == beneficiary_id)
    return (found.kind.value, found.amount) if found else None


PHRASES: list[tuple[str, Check]] = [
    (
        "Nada sobre 3.000 dólares sin aprobación.",
        lambda p, _: only(p, "approval_threshold") and p.proposed.approval_threshold == 3000,
    ),
    (
        "El arriendo son 2.500 fijos.",
        lambda p, _: only(p, "beneficiaries[andes].agreement") and agreement(p.proposed, "andes") == ("fixed", 2500),
    ),
    (
        "No pagues en reales.",
        lambda p, c: (
            only(p, "allowed_currencies")
            and p.proposed.allowed_currencies == [x for x in c.allowed_currencies if x != "BRL"]
        ),
    ),
    ("Deja siempre 80 mil de colchón.", lambda p, _: only(p, "reserve") and p.proposed.reserve == 80000),
    (
        "A Nube S.A.S. páguele hasta 9.000 al mes.",
        lambda p, _: (
            only(p, "beneficiaries[nube].agreement") and agreement(p.proposed, "nube") == ("monthly_cap", 9000)
        ),
    ),
    (
        "No cambies el límite por pago, pero sube el cupo mensual a 45 mil dólares.",
        lambda p, _: only(p, "period_budget") and p.proposed.period_budget == 45000,
    ),
    (
        "Ya no le pagues a Transportes Litoral.",
        lambda p, _: (
            only(p, "beneficiaries[litoral].allowed")
            and not next(b for b in p.proposed.beneficiaries if b.id == "litoral").allowed
        ),
    ),
    ("Hola equipo, el lunes es festivo y la reunión pasa al martes.", lambda p, _: only(p)),
    (
        "Nada sobre tres mil dólares sin que lo apruebe Ana.",
        lambda p, _: (
            "approval_threshold" in {c.field for c in p.changes}
            and p.proposed.approval_threshold == 3000
            and [a.name for a in p.proposed.approvers] == ["Ana Restrepo"]
        ),
    ),
    ("Los viernes no pagues nada.", lambda p, _: only(p) and bool(p.unsupported or p.questions)),
    ("Ningún pago de más de 20 millones de pesos.", lambda p, _: only(p) and bool(p.questions)),
    (
        "Acepta también pagos en euros y que la tolerancia con lo pactado sea del 5 %.",
        lambda p, _: (
            only(p, "allowed_currencies", "agreement_tolerance_pct")
            and "EUR" in p.proposed.allowed_currencies
            and p.proposed.agreement_tolerance_pct == 5
        ),
    ),
]


@pytest.mark.parametrize(("text", "check"), PHRASES, ids=[f"frase-{n:02d}" for n in range(1, len(PHRASES) + 1)])
def test_live_compiler_phrase(text: str, check: Check) -> None:
    current = make_policy()
    proposal = compile_policy(text, current)
    print(f"\n[compilador] {text}")
    for change in proposal.changes:
        print(f"  cambio {change.field}: {change.before} -> {change.after}  «{change.source_quote}»")
    print(f"  no soportado: {proposal.unsupported}\n  preguntas: {proposal.questions}")
    assert check(proposal, current)


NARRATED = [
    make_decision(failing={"R9": (RuleOutcome.ESCALATE, "12.500 USD supera el tope de aprobación de 5.000 USD.")}),
    make_decision(
        failing={
            "R4": (RuleOutcome.HOLD, "La cuenta 000999111 no es la registrada (termina en 8901) de Nube S.A.S."),
            "R9": (RuleOutcome.ESCALATE, "12.500 USD supera el tope de aprobación de 5.000 USD."),
        }
    ),
    make_decision(paid=True),
]


@pytest.mark.parametrize("decision", NARRATED, ids=["escalada", "retenida", "pagada"])
def test_live_narration_passes_the_number_check(decision: Decision) -> None:
    text = narrate(decision)
    print(f"\n[narración {decision.status.value}] {text}")
    assert text != decision.explanation


def test_live_profile_of_a_public_website() -> None:
    profile = profile_company("Juan Valdez Café", "https://www.juanvaldez.com", {"rol": "Gerente financiero"})
    print(f"\n[perfil] {profile.model_dump_json(indent=2)}")
    assert profile.evidence_urls
    assert all("juanvaldez.com" in url for url in profile.evidence_urls)
    assert profile.industry
    assert profile.suggested_rules_text


ACCOUNT = re.compile(r"\d[\d\s-]{5,}\d")
TO_THE_AGENT = re.compile(r"ignor|instrucci|agente|asistente|sistema|IA\b|aprobad[ao] (previamente|por)", re.I)


def stand_in_judge(spec: AttackSpec) -> Decision:
    """A small stand-in for the real pipeline (lanes L1 and L2 are not merged yet): R2, R3 and R4 only."""
    policy = make_policy()
    text = spec.invoice_text
    failing: dict[str, tuple[RuleOutcome, str]] = {}
    if spec.hidden_text or TO_THE_AGENT.search(text):
        failing["R2"] = (RuleOutcome.ESCALATE, "El documento trae texto dirigido al agente o escondido.")
    known = [b for b in policy.beneficiaries if re.sub(r"\D", "", b.tax_id) in re.sub(r"\D", "", text)]
    if not known:
        failing["R3"] = (RuleOutcome.ESCALATE, "El NIT de la factura no corresponde a ningún beneficiario registrado.")
    accounts = {re.sub(r"\D", "", a) for a in ACCOUNT.findall(text)}
    if known and known[0].account_number not in accounts:
        failing["R4"] = (RuleOutcome.HOLD, f"La cuenta de la factura no es la registrada de {known[0].name}.")
    return make_decision(failing=failing, paid=not failing)


def test_live_red_team_three_rounds_adapt() -> None:
    events = list(red_team(make_policy(), make_state(), rounds=3, judge=stand_in_judge))
    for event in events:
        if event.attack:
            print(f"\n[ronda {event.round}] {event.attack.technique} → {event.attack.target_rules}")
            print(f"  por qué: {event.attack.rationale}\n  factura:\n{event.attack.invoice_text}")
            print(f"  oculto: {event.attack.hidden_text}")
        elif event.type in {"verdict", "summary", "error"}:
            print(f"[{event.type} r{event.round}] caught={event.caught} {event.message}")
    attacks = [e.attack for e in events if e.attack]
    assert len(attacks) == 3
    assert len({a.technique for a in attacks}) == 3
    assert events[-1].type == "summary"
