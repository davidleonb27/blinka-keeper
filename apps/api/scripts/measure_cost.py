"""Cost per invoice, measured: every model call of the real reading pipeline, priced from its token usage.

Run from apps/api (needs ANTHROPIC_API_KEY in the environment; it is never printed):
  uv run python scripts/measure_cost.py --max 100 --out cost-report.json

Reads the golden demo invoices (36) and the blind set (20) with the pipeline as deployed: first reader on
`model_fast` (Sonnet), second reader on `model_second_reader` (Opus). Cycles through the documents until --max reads.
Records each `llm.structured` call (model, tokens, cost from llm._PRICES) and reports cost per invoice: total, per
model, per document type, and the projection for 100 invoices. `--dry-run` only renders the documents.
"""

from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from types import SimpleNamespace

API_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(API_DIR))
sys.path.insert(0, str(API_DIR / "scripts"))

from custodio import llm  # noqa: E402
from custodio.config import get_settings  # noqa: E402
from custodio.dataset import demo_specs  # noqa: E402
from custodio.extraction import render_invoice  # noqa: E402
from measure_double_reading import _read_locally, load_blind_set  # noqa: E402


@dataclass
class Call:
    model: str
    input_tokens: int
    output_tokens: int
    cache_read_tokens: int
    cost_usd: float
    seconds: float


@dataclass
class InvoiceRun:
    id: str
    media_type: str
    calls: list[Call] = field(default_factory=list)
    error: str | None = None
    seconds: float = 0.0

    @property
    def cost_usd(self) -> float:
        return sum(c.cost_usd for c in self.calls)


def documents() -> list[tuple[str, object, object]]:
    """(id, case-like object with .id and .spec, RenderedDocument) for golden + blind invoices."""
    out = []
    for spec in demo_specs():
        case = SimpleNamespace(id=spec.invoice_number, spec=spec)
        out.append((case.id, case, render_invoice(spec)))
    for case in load_blind_set():
        out.append((case.id, case, case.document()))
    return out


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--max", type=int, default=100)
    parser.add_argument("--out", default="cost-report.json")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    docs = documents()
    kinds = defaultdict(int)
    for _, _, doc in docs:
        kinds[doc.media_type] += 1
    print(f"documentos distintos: {len(docs)} · {dict(kinds)}", file=sys.stderr)
    if args.dry_run:
        return 0
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Falta ANTHROPIC_API_KEY en el entorno; no se hizo ninguna llamada.", file=sys.stderr)
        return 2

    settings = get_settings()
    print(f"modelos: primera lectura {settings.model_fast} · segunda {settings.model_second_reader}", file=sys.stderr)

    calls_of_current: list[Call] = []
    real_structured = llm.structured

    def recording_structured(*a, **kw):
        started = time.perf_counter()
        result = real_structured(*a, **kw)
        calls_of_current.append(
            Call(
                result.model,
                result.input_tokens,
                result.output_tokens,
                result.cache_read_tokens,
                result.cost_usd,
                time.perf_counter() - started,
            )
        )
        return result

    llm.structured = recording_structured  # every reader calls it as llm.structured(...)

    runs: list[InvoiceRun] = []
    for n in range(args.max):
        doc_id, case, doc = docs[n % len(docs)]
        calls_of_current.clear()
        run = InvoiceRun(id=f"{doc_id}#{n // len(docs) + 1}", media_type=doc.media_type)
        started = time.perf_counter()
        try:
            _read_locally(case, doc)
        except Exception as error:  # noqa: BLE001 - a failed read still cost what it cost
            run.error = type(error).__name__
        run.seconds = time.perf_counter() - started
        run.calls = list(calls_of_current)
        runs.append(run)
        print(
            f"{n + 1:3d}/{args.max} {run.id:14s} {doc.media_type:16s} {run.cost_usd:7.4f} USD "
            f"{run.seconds:5.1f}s {'ERROR ' + run.error if run.error else ''}",
            file=sys.stderr,
        )

    by_model: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for run in runs:
        for c in run.calls:
            m = by_model[c.model]
            m["calls"] += 1
            m["input_tokens"] += c.input_tokens
            m["output_tokens"] += c.output_tokens
            m["cache_read_tokens"] += c.cache_read_tokens
            m["cost_usd"] += c.cost_usd
    for m in by_model.values():
        m["cost_usd_per_invoice"] = m["cost_usd"] / len(runs)
        m["cost_usd_per_call"] = m["cost_usd"] / m["calls"] if m["calls"] else 0.0

    by_kind: dict[str, dict[str, float]] = {}
    for kind in {r.media_type for r in runs}:
        costs = [r.cost_usd for r in runs if r.media_type == kind]
        by_kind[kind] = {"invoices": len(costs), "mean_usd": statistics.mean(costs), "max_usd": max(costs)}

    costs = [r.cost_usd for r in runs]
    total = sum(costs)
    report = {
        "invoices_read": len(runs),
        "errors": sum(1 for r in runs if r.error),
        "models": {"first_reader": settings.model_fast, "second_reader": settings.model_second_reader},
        "prices_usd_per_million": {k: {"input": v[0], "output": v[1]} for k, v in llm._PRICES.items()},
        "total_usd": round(total, 4),
        "per_invoice_usd": {
            "mean": round(total / len(runs), 5),
            "median": round(statistics.median(costs), 5),
            "p95": round(sorted(costs)[int(0.95 * (len(costs) - 1))], 5),
            "max": round(max(costs), 5),
        },
        "per_100_invoices_usd": round(100 * total / len(runs), 2),
        "by_model": {k: {kk: round(vv, 5) for kk, vv in v.items()} for k, v in by_model.items()},
        "by_document_type": {k: {kk: round(vv, 5) for kk, vv in v.items()} for k, v in by_kind.items()},
        "seconds_per_invoice": {
            "median": round(statistics.median(r.seconds for r in runs), 2),
            "p95": round(sorted(r.seconds for r in runs)[int(0.95 * (len(runs) - 1))], 2),
        },
    }
    Path(args.out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
