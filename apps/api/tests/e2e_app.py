"""The API the browser e2e walks (apps/web `npm run e2e`): production wiring, without the model.

Everything the web depends on is real: the demo company and its cases, the decision engine, the independent auditor,
the simulator, the hash-chained ledger and the database (SQLite from CUSTODIO_DATABASE_URL). Only the lanes that
call Claude are swapped for the deterministic doubles of the API tests, so the walk needs no key, spends nothing
and gets the same answers every run. Run: `uvicorn tests.e2e_app:app` from apps/api.
"""

from __future__ import annotations

from dataclasses import replace

from custodio.api.app import create_app
from custodio.config import get_settings
from custodio.services.context import production_runtime

from .api import doubles

runtime = production_runtime(get_settings())
model_free = replace(
    runtime.lanes,
    extract_document=doubles.extract_document,
    extract_text=doubles.extract_text,
    compile_policy=doubles.compile_policy,
    narrate=doubles.narrate,
    profile_company=doubles.profile_company,
    import_suppliers=doubles.import_suppliers,
    red_team=doubles.red_team,
    triage_attack=doubles.triage_attack,
)
app = create_app(replace(runtime, lanes=model_free))
