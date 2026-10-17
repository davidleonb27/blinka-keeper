"""Typed errors raised by the decision engine and the ledger."""

from __future__ import annotations


class EngineError(Exception):
    """Base class for every error the engine raises on purpose."""


class CanonicalJsonError(EngineError):
    """A value cannot be written as canonical JSON, so it cannot be hashed deterministically."""


class DuplicateCaseIdError(EngineError):
    """Two cases in one batch share an id; decisions and approvals are keyed by it."""

    def __init__(self, case_id: str) -> None:
        super().__init__(f"duplicate case id in batch: {case_id}")
        self.case_id = case_id


class EngineInvariantError(EngineError):
    """The engine reached a state its rules make impossible (a bug); it stops instead of paying."""
