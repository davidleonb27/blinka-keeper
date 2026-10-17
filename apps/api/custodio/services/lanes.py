"""The public functions of lanes L1 (engine, dataset), L2 (reading) and L3 (AI) that the services use.

Services receive them through `Lanes` so tests can stand in doubles while the lanes are built in parallel, and so
no service imports a lane's internals. `production_lanes()` wires the real ones.
"""

from __future__ import annotations

import importlib
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from custodio import ai, dataset, engine, extraction
from custodio.contracts import (
    Approval,
    AttackSpec,
    AuditReport,
    BatchResult,
    CompanyProfile,
    CompanyState,
    Decision,
    ExtractedInvoice,
    InvoiceCase,
    InvoiceSource,
    InvoiceSpec,
    LedgerEntry,
    LedgerKind,
    LedgerVerification,
    Policy,
    PolicyProposal,
    RedTeamEvent,
    RenderedDocument,
    SimulationReport,
    SupplierImport,
)
from custodio.services.triage import AttackTriage, triage_attack


class DecideAll(Protocol):
    def __call__(
        self,
        cases: Sequence[InvoiceCase],
        state: CompanyState,
        policy: Policy,
        approvals: Mapping[str, Approval] | None = None,
    ) -> BatchResult: ...


class ExtractDocument(Protocol):
    def __call__(self, data: bytes, *, filename: str, media_type: str, document_id: str) -> ExtractedInvoice: ...


class ExtractText(Protocol):
    def __call__(self, text: str, *, document_id: str, source: InvoiceSource = ...) -> ExtractedInvoice: ...


class NextLedgerEntry(Protocol):
    def __call__(
        self,
        prev: LedgerEntry | None,
        *,
        kind: LedgerKind,
        subject_id: str | None,
        payload: dict[str, Any],
        at: datetime,
    ) -> LedgerEntry: ...


class ImportSuppliers(Protocol):
    def __call__(self, data: bytes, *, filename: str, media_type: str) -> SupplierImport: ...


class RedTeam(Protocol):
    def __call__(
        self, policy: Policy, state: CompanyState, *, rounds: int, judge: Callable[[AttackSpec], Decision]
    ) -> Iterator[RedTeamEvent]: ...


@dataclass(frozen=True)
class Lanes:
    demo_company: Callable[[], tuple[CompanyState, Policy]]
    demo_cases: Callable[[], list[InvoiceCase]]
    extract_document: ExtractDocument
    extract_text: ExtractText
    render_invoice: Callable[[InvoiceSpec], RenderedDocument]
    decide_all: DecideAll
    audit: Callable[[BatchResult, Sequence[InvoiceCase], CompanyState, Policy], AuditReport]
    simulate: Callable[[Sequence[InvoiceCase], CompanyState, Policy, Policy], SimulationReport]
    next_ledger_entry: NextLedgerEntry
    verify_ledger: Callable[[Sequence[LedgerEntry]], LedgerVerification]
    compile_policy: Callable[[str, Policy], PolicyProposal]
    narrate: Callable[[Decision], str]
    profile_company: Callable[[str, str | None, Mapping[str, str]], CompanyProfile]
    import_suppliers: ImportSuppliers
    red_team: RedTeam
    triage_attack: Callable[[str], AttackTriage]


def _engine_ledger(name: str) -> Any:
    # L1 ships custodio.engine.ledger alongside this lane; resolved on use so the API boots before it merges.
    return getattr(importlib.import_module("custodio.engine.ledger"), name)


def _next_ledger_entry(
    prev: LedgerEntry | None, *, kind: LedgerKind, subject_id: str | None, payload: dict[str, Any], at: datetime
) -> LedgerEntry:
    entry: LedgerEntry = _engine_ledger("next_entry")(prev, kind=kind, subject_id=subject_id, payload=payload, at=at)
    return entry


def _verify_ledger(entries: Sequence[LedgerEntry]) -> LedgerVerification:
    verification: LedgerVerification = _engine_ledger("verify")(entries)
    return verification


def production_lanes() -> Lanes:
    return Lanes(
        demo_company=dataset.demo_company,
        demo_cases=dataset.demo_cases,
        extract_document=extraction.extract_document,
        extract_text=extraction.extract_text,
        render_invoice=extraction.render_invoice,
        decide_all=engine.decide_all,
        audit=engine.audit,
        simulate=engine.simulate,
        next_ledger_entry=_next_ledger_entry,
        verify_ledger=_verify_ledger,
        compile_policy=ai.compile_policy,
        narrate=ai.narrate,
        profile_company=ai.profile_company,
        import_suppliers=ai.import_suppliers,
        red_team=ai.red_team,
        triage_attack=triage_attack,
    )
