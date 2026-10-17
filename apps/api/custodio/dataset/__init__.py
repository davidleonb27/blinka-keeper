"""Demo company and labelled trap cases. Owned by lane L1.

`demo_cases()` returns cases already read perfectly (verified evidence), so the engine and the UI work without any
model. `demo_specs()` returns the same invoices as specs, so lane L2 can render them as real documents and read them.
"""

from __future__ import annotations

from custodio.contracts import CompanyState, InvoiceCase, InvoiceSpec, Policy


def demo_company() -> tuple[CompanyState, Policy]:
    raise NotImplementedError("lane L1")


def demo_specs() -> list[InvoiceSpec]:
    raise NotImplementedError("lane L1")


def demo_cases() -> list[InvoiceCase]:
    raise NotImplementedError("lane L1")
