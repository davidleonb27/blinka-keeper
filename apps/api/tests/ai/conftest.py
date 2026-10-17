"""Shared doubles for lane L3: a fake of `llm.structured`, recorded model outputs and contract factories."""

from __future__ import annotations

import json
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from custodio import llm
from custodio.contracts import (
    RULES,
    Agreement,
    AgreementKind,
    AgentVerdict,
    Approver,
    Beneficiary,
    CompanyState,
    Decision,
    DecisionStatus,
    PaymentRecord,
    Policy,
    RuleOutcome,
    RuleResult,
)

BAD_OUTPUTS = Path(__file__).parent / "fixtures" / "bad_outputs"


@dataclass
class Call:
    model: str
    system: str
    content: Any
    schema: type[BaseModel]
    effort: str
    tools: list[Any] | None

    @property
    def text(self) -> str:
        """The user turn flattened to text, for assertions about what the model was shown."""
        if isinstance(self.content, str):
            return self.content
        return "\n".join(block.get("text", "") for block in self.content)


@dataclass
class FakeLLM:
    """Replaces `custodio.llm.structured`: returns queued payloads (validated against the schema) or raises."""

    replies: list[dict[str, Any] | Exception] = field(default_factory=list)
    calls: list[Call] = field(default_factory=list)

    def reply(self, *payloads: dict[str, Any] | Exception) -> FakeLLM:
        self.replies.extend(payloads)
        return self

    def __call__(
        self,
        *,
        model: str,
        system: str,
        content: Any,
        schema: type[BaseModel],
        effort: str = "medium",
        max_tokens: int = 16000,
        tools: list[Any] | None = None,
    ) -> llm.LLMResult[Any]:
        self.calls.append(Call(model, system, content, schema, effort, tools))
        if not self.replies:
            raise AssertionError("The code called the model more times than the test expected.")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return llm.LLMResult(
            value=schema.model_validate(reply),
            model=model,
            input_tokens=0,
            output_tokens=0,
            cache_read_tokens=0,
            cost_usd=0.0,
        )


@pytest.fixture
def fake_llm(monkeypatch: pytest.MonkeyPatch) -> Iterator[FakeLLM]:
    fake = FakeLLM()
    monkeypatch.setattr(llm, "structured", fake)
    yield fake


def recorded(name: str) -> dict[str, Any]:
    """A model output recorded as JSON that the code must reject or neutralize."""
    payload: dict[str, Any] = json.loads((BAD_OUTPUTS / f"{name}.json").read_text(encoding="utf-8"))
    return payload


def make_policy() -> Policy:
    return Policy(
        beneficiaries=[
            Beneficiary(
                id="nube",
                name="Nube S.A.S.",
                tax_id="900123456-7",
                aliases=["Nube Hosting"],
                country="CO",
                bank_name="Bancolombia",
                account_number="12345678901",
                currency="USD",
            ),
            Beneficiary(
                id="andes",
                name="Inmobiliaria Andes Ltda.",
                tax_id="800765432-1",
                aliases=["arriendo oficina"],
                country="CO",
                bank_name="Davivienda",
                account_number="55500011122",
                currency="USD",
                agreement=Agreement(kind=AgreementKind.FIXED, amount=Decimal("2400"), currency="USD"),
            ),
            Beneficiary(
                id="litoral",
                name="Transportes Litoral",
                tax_id="901222333-4",
                country="CO",
                bank_name="BBVA",
                account_number="99988877766",
                currency="COP",
            ),
        ],
        approvers=[Approver(name="Ana Restrepo", role="Gerente financiera")],
    )


def make_state() -> CompanyState:
    return CompanyState(
        workspace_id="ws-test",
        company_name="Demo Andina S.A.S.",
        today=date(2026, 10, 16),
        opening_balance=Decimal("98000"),
        fx_units_per_base={"USD": Decimal("1"), "COP": Decimal("4000")},
        history=[
            PaymentRecord(
                invoice_id="h-1",
                beneficiary_id="nube",
                invoice_number="NB-2201",
                amount=Decimal("3100"),
                currency="USD",
                amount_base=Decimal("3100"),
                paid_on=date(2026, 10, 2),
                by="agent",
            )
        ],
    )


def make_decision(*, failing: dict[str, tuple[RuleOutcome, str]] | None = None, paid: bool = False) -> Decision:
    """A decision whose rules pass except the ones in `failing` (rule id -> outcome, reason)."""
    failing = failing or {}
    rules = [
        RuleResult(
            rule_id=spec.id,
            key=spec.key,
            label=spec.label,
            outcome=failing.get(spec.id, (RuleOutcome.PASS, ""))[0],
            reason=failing.get(spec.id, (RuleOutcome.PASS, f"{spec.label}: cumple."))[1],
        )
        for spec in RULES
    ]
    holds = any(outcome is RuleOutcome.HOLD for outcome, _ in failing.values())
    verdict = AgentVerdict.PAY if paid else AgentVerdict.HOLD if holds else AgentVerdict.ESCALATE
    status = {
        AgentVerdict.PAY: DecisionStatus.PAID_AUTO,
        AgentVerdict.HOLD: DecisionStatus.HOLD,
        AgentVerdict.ESCALATE: DecisionStatus.PENDING_APPROVAL,
    }[verdict]
    return Decision(
        invoice_id="inv-7",
        beneficiary_id="nube",
        supplier_name="Nube S.A.S.",
        amount=Decimal("12500"),
        currency="USD",
        amount_base=Decimal("12500"),
        agent_verdict=verdict,
        status=status,
        rules=rules,
        explanation="Se pidió aprobación: 12.500 USD supera el tope de aprobación automática de 5.000 USD.",
        counterfactual=None if paid else "Se habría pagado si el monto fuera de 5.000 USD o menos.",
        balance_before=Decimal("98000"),
        balance_after=Decimal("98000"),
    )
