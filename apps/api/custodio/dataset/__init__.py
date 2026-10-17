"""Demo company and labelled trap cases. Owned by lane L1.

`demo_cases()` returns cases already read perfectly (verified evidence), so the engine and the UI work without any
model. `demo_specs()` returns the same invoices as specs, so lane L2 can render them as real documents and read them.
"""

from __future__ import annotations

from custodio.contracts import CompanyState, InvoiceCase, InvoiceSpec, Policy
from custodio.dataset.demo import load_demo, to_case


def demo_company() -> tuple[CompanyState, Policy]:
    demo = load_demo()
    return demo.state, demo.policy


def demo_specs() -> list[InvoiceSpec]:
    return [case.spec for case in load_demo().cases]


def demo_cases() -> list[InvoiceCase]:
    demo = load_demo()
    return [to_case(case, customer=demo.state.company_name) for case in demo.cases]
