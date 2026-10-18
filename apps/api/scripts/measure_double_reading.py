"""Blind-set measurement (L21): 20 invoices nobody tuned on, read with real models, decided by the pure engine.

Usage, from apps/api:
  uv run python scripts/measure_double_reading.py --base-url https://custodio-blinka-green.vercel.app
  CUSTODIO_LIVE_TESTS=1 uv run python scripts/measure_double_reading.py --local   # needs ANTHROPIC_API_KEY here

`--base-url` uploads each document to a deployed API (its model reads it) and keeps the extraction it returns;
`--local` reads in this process, so it also measures spend. Either way each invoice is then decided alone by
`decide_all` against the demo company, so the seeded batch of a demo workspace never changes a verdict. The expected
verdicts are frozen in `custodio/dataset/blind/l21.json`. The code reader (`labels`) also reads every document that
carries its own text, here, without a model, so its agreement with the model reader is measured too. Prints one JSON
report; never prints credentials.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custodio import llm
from custodio.contracts import ExtractedInvoice, InvoiceCase, InvoiceSource, InvoiceSpec, RenderedDocument
from custodio.dataset import load_demo
from custodio.engine import decide_all
from custodio.engine.text import normalize_code, normalize_name
from custodio.extraction import extract_document, extract_text, labels, pdf, render_invoice
from custodio.extraction.source import SourceText

BLIND_SET = Path(__file__).resolve().parents[1] / "custodio" / "dataset" / "blind" / "l21.json"
COMPARED = ("supplier_name", "amount", "currency", "account_number")
CODE_READER = labels.READER
CONFIDENCE = 0.95
SECONDS_BETWEEN_UPLOADS = 4.0  # under the API's per-IP model-call limit
CREATED = 201
TIMEOUT_SECONDS = 180.0
TEXT_CHANNELS = {InvoiceSource.TEXT, InvoiceSource.EMAIL, InvoiceSource.INTENT}
RULE_OF_THREE = 3


class BlindCase(BaseModel):
    id: str
    received_at: datetime
    expected: str  # pay, hold or escalate
    trap: str | None
    why: str
    spec: InvoiceSpec
    raw_text: str | None = None  # the exact message when the renderer cannot write it (another language)

    def document(self) -> RenderedDocument:
        if self.raw_text is None:
            return render_invoice(self.spec)
        name = f"factura-{self.spec.invoice_number}.txt"
        return RenderedDocument(filename=name, media_type="text/plain; charset=utf-8", data=self.raw_text.encode())


def load_blind_set(path: Path = BLIND_SET) -> list[BlindCase]:
    return [BlindCase.model_validate(case) for case in json.loads(path.read_text(encoding="utf-8"))["cases"]]


# Statistics -----------------------------------------------------------------------------------------------------


def clopper_pearson(successes: int, trials: int, confidence: float = CONFIDENCE) -> tuple[float, float]:
    """Exact two-sided binomial interval, by bisection on the binomial tail (no scipy)."""
    alpha = 1 - confidence
    lower = 0.0 if successes == 0 else _bisect(lambda p: _tail_at_least(successes, trials, p) - alpha / 2)
    upper = 1.0 if successes == trials else _bisect(lambda p: alpha / 2 - _tail_at_most(successes, trials, p))
    return lower, upper


def rule_of_three(trials: int) -> float:
    """95 % upper bound on a rate never observed in `trials` independent tries."""
    return RULE_OF_THREE / trials


def percentile(values: Sequence[float], share: float) -> float | None:
    """Nearest-rank percentile; None for no values."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(0, math.ceil(share * len(ordered)) - 1)]


def _tail_at_least(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k, n + 1))


def _tail_at_most(k: int, n: int, p: float) -> float:
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def _bisect(increasing: Callable[[float], float]) -> float:
    low, high = 0.0, 1.0
    for _ in range(60):
        middle = (low + high) / 2
        low, high = (low, middle) if increasing(middle) > 0 else (middle, high)
    return (low + high) / 2


# Reading and deciding -------------------------------------------------------------------------------------------


@dataclass(frozen=True)
class Reading:
    extraction: ExtractedInvoice | None
    seconds: float
    cost_usd: float | None  # None: spend is not visible from here (a deployed API)
    error: str | None = None


Reader = Callable[[BlindCase], Reading]


def remote_reader(client: httpx.Client, pause: Callable[[float], None] = time.sleep) -> Reader:
    headers = {"X-Custodio-Workspace": _demo_workspace(client)}
    uploads = 0

    def read(case: BlindCase) -> Reading:
        nonlocal uploads
        if uploads:
            pause(SECONDS_BETWEEN_UPLOADS)
        uploads += 1
        document = case.document()
        started = time.perf_counter()
        response = client.post("/invoices", headers=headers, files={"file": _file(document)})
        seconds = time.perf_counter() - started
        if response.status_code != CREATED:
            return Reading(None, seconds, None, error=f"HTTP {response.status_code}")
        return Reading(ExtractedInvoice.model_validate(response.json()["extraction"]), seconds, None)

    return read


def local_reader(case: BlindCase) -> Reading:
    document = case.document()
    spent, started = llm.budget.spent_today(), time.perf_counter()
    try:
        extraction = _read_locally(case, document)
    except (llm.LLMError, ValueError) as error:
        return Reading(None, time.perf_counter() - started, None, error=type(error).__name__)
    return Reading(extraction, time.perf_counter() - started, llm.budget.spent_today() - spent)


def _read_locally(case: BlindCase, document: RenderedDocument) -> ExtractedInvoice:
    if document.media_type.startswith("text/"):
        return extract_text(document.data.decode(), document_id=case.id, source=case.spec.channel)
    return extract_document(
        document.data, filename=document.filename, media_type=document.media_type, document_id=case.id
    )


def _demo_workspace(client: httpx.Client) -> str:
    created = client.post("/workspaces", json={"mode": "demo"}).raise_for_status().json()
    return str(created["workspace_id"])  # the api_key in the same answer is dropped here, unread


def _file(document: RenderedDocument) -> tuple[str, bytes, str]:
    return document.filename, document.data, document.media_type


def verdict_of(case: BlindCase, extraction: ExtractedInvoice) -> str:
    """The engine's verdict on this invoice alone, against the demo company."""
    demo = load_demo()
    invoice = InvoiceCase(id=case.id, received_at=case.received_at, extraction=extraction)
    return decide_all([invoice], demo.state, demo.policy).decisions[0].agent_verdict.value


def code_values(case: BlindCase) -> dict[str, str | None] | None:
    """What the code reader reads from the document's own text; None for images and scans (no text of their own)."""
    document = case.document()
    if document.media_type.startswith("text/"):
        source = SourceText(pages=(document.data.decode(),))
    elif document.media_type == "application/pdf":
        reading = pdf.read_pdf(document.data)
        if not reading.has_visible_text:
            return None
        source = SourceText(pages=reading.pages)
    else:
        return None
    fields = labels.read_fields(source).fields
    return {name: fields[name].value if fields[name].verified else None for name in COMPARED}


# Comparing ------------------------------------------------------------------------------------------------------


def same(name: str, got: str | None, want: str | None) -> bool:
    if got is None or want is None:
        return False
    if name == "amount":
        try:
            return Decimal(got) == Decimal(want)
        except InvalidOperation:
            return False
    if name == "supplier_name":
        return normalize_name(got) == normalize_name(want)
    return normalize_code(got) == normalize_code(want)


def truth(case: BlindCase) -> dict[str, str]:
    spec = case.spec
    return {
        "supplier_name": spec.supplier_name,
        "amount": f"{spec.amount:f}",
        "currency": spec.currency,
        "account_number": spec.account_number,
    }


def reader_values(extraction: ExtractedInvoice) -> dict[str, dict[str, str | None]]:
    """Every reader's values: the cross-check's readings when there is one, else the first reader's fields."""
    if extraction.cross_check and extraction.cross_check.fields:
        values: dict[str, dict[str, str | None]] = {}
        for comparison in extraction.cross_check.fields:
            for reading in comparison.readings:
                values.setdefault(reading.reader, {})[comparison.field] = reading.value
        return values
    first = {name: getattr(extraction, name).value for name in COMPARED}
    return {extraction.reader.split("+")[-1]: first}


@dataclass
class Tally:
    total: int = 0
    correct: int = 0
    paid: int = 0
    improper: list[str] = field(default_factory=list)
    unread: list[str] = field(default_factory=list)
    verdicts: list[dict[str, str]] = field(default_factory=list)
    fields_right: Counter[str] = field(default_factory=Counter)
    fields_seen: Counter[str] = field(default_factory=Counter)
    agreements: Counter[str] = field(default_factory=Counter)
    cross_checks: Counter[str] = field(default_factory=Counter)
    seconds: list[float] = field(default_factory=list)
    costs: list[float] = field(default_factory=list)

    def record(self, case: BlindCase, reading: Reading) -> None:
        self.total += 1
        self.seconds.append(reading.seconds)
        if reading.cost_usd is not None:
            self.costs.append(reading.cost_usd)
        if reading.extraction is None:
            self.unread.append(f"{case.id}: {reading.error}")
            self._decided(case, "not_read")  # nothing read is nothing paid: a person looks
            return
        self._decided(case, verdict_of(case, reading.extraction))
        status = reading.extraction.cross_check.status.value if reading.extraction.cross_check else "none"
        self.cross_checks[status] += 1
        readers = reader_values(reading.extraction)
        code = code_values(case)
        if code is not None and CODE_READER not in readers:
            readers[CODE_READER] = code
        self._fields(case, readers)

    def _decided(self, case: BlindCase, verdict: str) -> None:
        self.verdicts.append({"id": case.id, "expected": case.expected, "verdict": verdict})
        self.correct += verdict == case.expected or (verdict == "not_read" and case.expected == "escalate")
        if verdict == "pay":
            self.paid += 1
            if case.expected != "pay":
                self.improper.append(case.id)

    def _fields(self, case: BlindCase, readers: dict[str, dict[str, str | None]]) -> None:
        want = truth(case)
        for reader, values in readers.items():
            for name in COMPARED:
                if name in values:
                    self.fields_seen[f"{reader}:{name}"] += 1
                    self.fields_right[f"{reader}:{name}"] += same(name, values[name], want[name])
        model_readers = [reader for reader in readers if reader != CODE_READER]
        if model_readers and CODE_READER in readers:
            first, code = readers[model_readers[0]], readers[CODE_READER]
            for name in COMPARED:
                if code.get(name) is not None:
                    self.agreements[f"{name}:compared"] += 1
                    self.agreements[f"{name}:agree"] += same(name, first.get(name), code[name])

    def report(self) -> dict[str, Any]:
        low, high = clopper_pearson(self.correct, self.total)
        wrongly_paid = len(self.improper)
        bound = rule_of_three(self.total) if not wrongly_paid else clopper_pearson(wrongly_paid, self.total)[1]
        return {
            "invoices": self.total,
            "decisions_correct": self.correct,
            "decisions_correct_ci95": [round(low, 3), round(high, 3)],
            "paid_alone": self.paid,
            "improper_payments": self.improper,
            "improper_payment_rate_upper95": round(bound, 3),
            "not_read": self.unread,
            "cross_check_status": dict(self.cross_checks),
            "fields_right_by_reader": {
                key: f"{self.fields_right[key]}/{seen}" for key, seen in sorted(self.fields_seen.items())
            },
            "model_vs_code_reader_agreement": _agreement(self.agreements),
            "cost_usd_per_invoice": round(sum(self.costs) / len(self.costs), 5) if self.costs else "NO MEDIDO",
            "latency_seconds": {
                "p50": _rounded(percentile(self.seconds, 0.5)),
                "p95": _rounded(percentile(self.seconds, 0.95)),
            },
            "verdicts": self.verdicts,
        }


def _agreement(counts: Counter[str]) -> dict[str, str]:
    return {name: f"{counts[f'{name}:agree']}/{counts[f'{name}:compared']}" for name in COMPARED}


def _rounded(value: float | None) -> float | None:
    return None if value is None else round(value, 2)


def measure(reader: Reader, cases: Sequence[BlindCase]) -> dict[str, Any]:
    tally = Tally()
    for case in cases:
        tally.record(case, reader(case))
    return {"measured_at": datetime.now(UTC).isoformat(timespec="seconds")} | tally.report()


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    where = parser.add_mutually_exclusive_group(required=True)
    where.add_argument("--base-url")
    where.add_argument("--local", action="store_true")
    args = parser.parse_args(argv)
    cases = load_blind_set()
    if args.local:
        report = {"mode": "local"} | measure(local_reader, cases)
    else:
        with httpx.Client(base_url=f"{args.base_url.rstrip('/')}/api/v1", timeout=TIMEOUT_SECONDS) as client:
            report = {"mode": "remote", "base_url": args.base_url} | measure(remote_reader(client), cases)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
