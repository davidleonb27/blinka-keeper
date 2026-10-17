"""A stand-in for the model's reading of PDF and image statements, for the API tests and the browser e2e."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from custodio.reconciliation.csv_statement import read_csv_statement
from custodio.reconciliation.demo import demo_statement_csv
from custodio.reconciliation.models import Statement


@dataclass
class FakeStatementReader:
    """Answers the demo statement for any document, as if Claude had read it, or raises `error`."""

    error: Exception | None = None
    calls: list[dict[str, Any]] = field(default_factory=list)

    def __call__(self, data: bytes, *, filename: str, media_type: str, default_currency: str) -> Statement:
        self.calls.append({"filename": filename, "media_type": media_type, "default_currency": default_currency})
        if self.error is not None:
            raise self.error
        statement = read_csv_statement(demo_statement_csv(), default_currency=default_currency)
        return statement.model_copy(update={"reader": "pdfplumber+claude-sonnet-5-5"})
