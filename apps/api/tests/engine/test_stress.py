import importlib.util
from pathlib import Path
from types import ModuleType

SCRIPT = Path(__file__).parents[2] / "scripts" / "stress.py"


def load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("stress", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_a_small_stress_run_reports_zero_improper_payments_and_every_count() -> None:
    report = load_script().run(companies=5, seed=7)
    assert report["companies"] == 5 and report["seed"] == 7
    assert report["invoices"] == sum(report["statuses"].values()) == sum(report["traps"].values())
    assert report["improper_payments"] == 0
    assert report["auditor_vetoes"] == 0
    assert report["reserve_breaches"] == 0
    assert report["traps_paid_by_agent"] == {}
    assert report["seconds"] >= 0


def test_the_same_seed_gives_the_same_decisions() -> None:
    stress = load_script()
    first, second = stress.run(companies=3, seed=11), stress.run(companies=3, seed=11)
    del first["seconds"], first["invoices_per_second"], second["seconds"], second["invoices_per_second"]
    assert first == second
