"""Reading measurement: the golden dataset, rendered to documents, read by the deployed API with the real model.

Usage: uv run python scripts/measure_reading.py --base-url https://custodio-blinka-green.vercel.app --max-uploads 36

Creates one demo workspace, counts the golden invoices it was seeded with, then uploads the rendered documents one at
a time and compares supplier, amount, currency and account with the specs that produced them. Prints one JSON report.
Needs no local model key: the deployed API makes the model calls. The workspace credentials stay in memory, unprinted.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from collections.abc import Callable, Sequence
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

import httpx

# `uv run python scripts/measure_reading.py` puts scripts/ on sys.path, not the project root where `custodio` lives.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custodio.contracts import ExtractedField, ExtractedInvoice, InvoiceSpec
from custodio.dataset import demo_specs
from custodio.extraction import render_invoice
from custodio.extraction.text import fold

PRODUCTION = "https://custodio-blinka-green.vercel.app"
UPLOAD_CAP = 40  # the most uploads one run may spend against production, retries included
SECONDS_BETWEEN_UPLOADS = 4.0  # stays under the 20 model calls per minute per IP the API allows
RATE_LIMITED = 429
CREATED = 201
TIMEOUT_SECONDS = 120.0


def _digits(text: str) -> str:
    return "".join(char for char in text if char.isdigit())


def _same_amount(got: str, want: str) -> bool:
    try:
        return Decimal(got) == Decimal(want)
    except InvalidOperation:
        return False


COMPARE: dict[str, Callable[[str, str], bool]] = {
    "supplier_name": lambda got, want: fold(got) == fold(want),
    "amount": _same_amount,
    "currency": str.__eq__,
    "account_number": lambda got, want: _digits(got) == _digits(want),
}


def is_correct(spec: InvoiceSpec, name: str, field: ExtractedField) -> bool:
    """A value counts only when it matches and code verified its quote; an ambiguous "$" must stay unverified."""
    if name == "currency" and spec.amount_text and "$" in spec.amount_text:
        return not field.verified
    return field.verified and field.value is not None and COMPARE[name](field.value, str(getattr(spec, name)))


def measure(
    client: httpx.Client,
    *,
    max_uploads: int,
    pause: Callable[[float], None] = time.sleep,
    specs: Sequence[InvoiceSpec] | None = None,
) -> dict[str, Any]:
    headers = {"X-Custodio-Workspace": _create_demo_workspace(client)}
    seeded = client.get("/workspaces/current", headers=headers).raise_for_status().json()["pending_invoices"]
    tally = _Tally()
    for spec in specs if specs is not None else demo_specs():
        response = _upload(client, headers, spec, tally, max_uploads, pause)
        if response is None:
            break
        tally.record(spec, response)
    return {"measured_at": datetime.now(UTC).isoformat(timespec="seconds"), "seeded_invoices": seeded} | tally.report()


def _create_demo_workspace(client: httpx.Client) -> str:
    created = client.post("/workspaces", json={"mode": "demo"}).raise_for_status().json()
    return str(created["workspace_id"])  # the api_key in the same answer is dropped here, unread


def _upload(
    client: httpx.Client,
    headers: dict[str, str],
    spec: InvoiceSpec,
    tally: _Tally,
    max_uploads: int,
    pause: Callable[[float], None],
) -> httpx.Response | None:
    document = render_invoice(spec)
    while tally.uploads < max_uploads:
        if tally.uploads:
            pause(SECONDS_BETWEEN_UPLOADS)
        tally.uploads += 1
        files = {"file": (document.filename, document.data, document.media_type)}
        response = client.post("/invoices", headers=headers, files=files)
        if response.status_code != RATE_LIMITED:
            return response
        tally.rate_limited += 1
        pause(float(response.headers.get("Retry-After", SECONDS_BETWEEN_UPLOADS)))
    return None


class _Tally:
    def __init__(self) -> None:
        self.uploads = 0
        self.rate_limited = 0
        self.documents = 0
        self.read = 0
        self.rejected: Counter[str] = Counter()
        self.fields_correct: Counter[str] = Counter({name: 0 for name in COMPARE})
        self.all_four = 0
        self.hidden_expected = self.hidden_detected = self.findings_on_clean = 0
        self.misses: list[dict[str, Any]] = []

    def record(self, spec: InvoiceSpec, response: httpx.Response) -> None:
        self.documents += 1
        if response.status_code != CREATED:
            self.rejected[f"{response.status_code} {_error_code(response)}"] += 1
            self.misses.append({"invoice": spec.invoice_number, "channel": spec.channel, "rejected": True})
            return
        self.read += 1
        invoice = ExtractedInvoice.model_validate(response.json()["extraction"])
        wrong = [name for name in COMPARE if not is_correct(spec, name, getattr(invoice, name))]
        self.fields_correct.update(name for name in COMPARE if name not in wrong)
        self.all_four += not wrong
        if wrong:
            self.misses.append({"invoice": spec.invoice_number, "channel": spec.channel, "wrong": wrong})
        self.hidden_expected += bool(spec.hidden_text)
        self.hidden_detected += bool(spec.hidden_text) and bool(invoice.hidden_findings)
        self.findings_on_clean += not spec.hidden_text and bool(invoice.hidden_findings)

    def report(self) -> dict[str, Any]:
        return {
            "documents": self.documents,
            "uploads": self.uploads,
            "rate_limited": self.rate_limited,
            "read": self.read,
            "rejected": dict(self.rejected),
            "fields_correct": dict(self.fields_correct),
            "documents_all_four_correct": self.all_four,
            "hidden_text": {
                "expected": self.hidden_expected,
                "detected": self.hidden_detected,
                "findings_on_clean_documents": self.findings_on_clean,
            },
            "misses": self.misses,
        }


def _error_code(response: httpx.Response) -> str:
    try:
        return str(response.json().get("code", "unknown"))
    except ValueError:
        return "unknown"


def _upload_cap(text: str) -> int:
    cap = int(text)
    if not 1 <= cap <= UPLOAD_CAP:
        raise argparse.ArgumentTypeError(f"between 1 and {UPLOAD_CAP}")
    return cap


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0] if __doc__ else None)
    parser.add_argument("--base-url", default=PRODUCTION)
    parser.add_argument("--max-uploads", type=_upload_cap, default=UPLOAD_CAP)
    args = parser.parse_args(argv)
    with httpx.Client(base_url=f"{args.base_url.rstrip('/')}/api/v1", timeout=TIMEOUT_SECONDS) as client:
        report = {"base_url": args.base_url} | measure(client, max_uploads=args.max_uploads)
    print(json.dumps(report, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
