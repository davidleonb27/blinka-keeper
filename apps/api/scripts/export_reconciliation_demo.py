"""Writes the web's mock reconciliation: the demo batch processed and reconciled against the demo statement.

Usage: uv run python scripts/export_reconciliation_demo.py

Runs the real API in memory (demo company, engine, auditor, ledger, matcher; no model is called) on the demo world's
day, and saves the answer of POST /api/v1/reconciliations to apps/web/src/lib/api/mock/reconciliation-demo.json, so
NEXT_PUBLIC_API_MODE=mock shows the same reconciliation the API gives.
"""

from __future__ import annotations

import json
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

# `uv run python scripts/…` puts scripts/ on sys.path, not the project root where `custodio` lives.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from custodio.api.app import create_app
from custodio.db import Database
from custodio.reconciliation.demo import demo_payment_day
from custodio.services.context import RateLimits, Runtime
from custodio.services.lanes import production_lanes

TARGET = Path(__file__).resolve().parents[2] / "web" / "src" / "lib" / "api" / "mock" / "reconciliation-demo.json"
DEMO_HOUR = 15


def main() -> None:
    demo_moment = datetime.combine(demo_payment_day(), datetime.min.time(), tzinfo=UTC).replace(hour=DEMO_HOUR)
    with tempfile.TemporaryDirectory() as folder:
        runtime = Runtime(
            database=Database(f"sqlite:///{Path(folder) / 'demo.db'}"),
            lanes=production_lanes(),
            clock=lambda: demo_moment,
            limits=RateLimits(),
            public_base_url="https://custodio-blinka-green.vercel.app",
        )
        with TestClient(create_app(runtime)) as client:
            workspace = client.post("/api/v1/workspaces", json={"mode": "demo"}).json()["workspace_id"]
            headers = {"X-Custodio-Workspace": workspace}
            client.post("/api/v1/invoices/process", headers=headers).raise_for_status()
            response = client.post("/api/v1/reconciliations", headers=headers, data={"demo": "true"})
            response.raise_for_status()
    TARGET.write_text(json.dumps(response.json(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
