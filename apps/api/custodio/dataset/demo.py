"""Cobalto Labs, Inc.: the demo company and its labelled invoices, loaded from cases.json."""

from __future__ import annotations

from datetime import datetime
from importlib.resources import files
from typing import Literal

from pydantic import Field

from custodio.contracts import CompanyState, InvoiceCase, InvoiceSpec, Model, Policy
from custodio.dataset.reading import read_spec

CASES_FILE = "cases.json"


class DemoCase(Model):
    id: str
    received_at: datetime
    expected: Literal["pay", "hold", "escalate"]
    trap: str | None = None
    spec: InvoiceSpec
    # Per-field reading confidence when it differs from the channel's usual one.
    confidence: dict[str, float] = Field(default_factory=dict)


class DemoFile(Model):
    state: CompanyState
    policy: Policy
    cases: list[DemoCase]


def load_demo() -> DemoFile:
    raw = files("custodio.dataset").joinpath(CASES_FILE).read_text(encoding="utf-8")
    return DemoFile.model_validate_json(raw)


def to_case(demo: DemoCase, *, customer: str) -> InvoiceCase:
    extraction = read_spec(demo.spec, document_id=f"demo-{demo.id}", customer=customer, confidence=demo.confidence)
    return InvoiceCase(
        id=demo.id, received_at=demo.received_at, extraction=extraction, expected=demo.expected, trap=demo.trap
    )
