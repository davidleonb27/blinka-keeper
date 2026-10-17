"""The accountant's evidence pack: one ZIP, reproducible byte for byte except one field with the generation date."""

import csv
import hashlib
import io
import json
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import pdfplumber

from custodio import dataset, engine
from custodio.contracts import Decision, DecisionStatus, LedgerEntry, LedgerKind
from custodio.engine.ledger import next_entry, verify
from custodio.reconciliation.csv_statement import read_csv_statement
from custodio.reconciliation.demo import demo_payment_day, demo_statement_csv
from custodio.reconciliation.evidence import EvidenceSource, evidence_pack
from custodio.reconciliation.match import reconcile
from custodio.reconciliation.models import MatchSettings, MovementStatus, PeriodClose, Review
from custodio.reconciliation.summary import summarize

from .test_demo_statement import demo_batch

GENERATED = datetime(2026, 11, 2, 9, 30, tzinfo=UTC)
CLOSED = datetime(2026, 11, 1, 18, 0, tzinfo=UTC)


def ledger(count: int = 4) -> list[LedgerEntry]:
    entries: list[LedgerEntry] = []
    for seq in range(count):
        entries.append(
            next_entry(
                entries[-1] if entries else None,
                kind=LedgerKind.DECISION,
                subject_id=f"F-{seq:03d}",
                payload={"status": "paid_auto", "amount": Decimal("634.146341"), "ratio": 0.5, "note": "Café ñ"},
                at=datetime(2026, 10, 16, 15, seq, 7, 123456, tzinfo=UTC),
            )
        )
    return entries


def decisions() -> list[Decision]:
    state, policy = dataset.demo_company()
    return engine.decide_all(dataset.demo_cases(), state, policy).decisions


def source() -> EvidenceSource:
    statement = read_csv_statement(demo_statement_csv(), default_currency="USD")
    paid, unpaid = demo_batch(demo_payment_day())
    outcome = reconcile(statement.movements, paid, unpaid, MatchSettings())
    alerts = [item.movement_id for item in outcome.movements if item.status is MovementStatus.UNMATCHED_OUTFLOW]
    entries = ledger()
    reviews = [
        Review(
            movement_id=alerts[0],
            reviewer="Ana Gómez",
            note="Pago hecho por fuera; se pidió reverso.",
            at=CLOSED,
            ledger_seq=3,
        )
    ]
    chosen = decisions()
    return EvidenceSource(
        company_name="Cobalto Labs, Inc.",
        period="2026-10",
        statement=statement,
        outcome=outcome,
        reviews=reviews,
        summary=summarize(chosen, statement, outcome, reviews, currency="USD"),
        actas={d.invoice_id: {"decision": d.model_dump(mode="json")} for d in chosen},
        ledger=entries,
        verification=verify(entries),
        closed=PeriodClose(
            period="2026-10",
            closed_at=CLOSED,
            closed_by="Ana Gómez",
            reconciliation_id="rec-1",
            ledger_seq=4,
            ledger_hash=entries[-1].hash,
        ),
    )


def files_of(pack: bytes) -> dict[str, bytes]:
    with zipfile.ZipFile(io.BytesIO(pack)) as archive:
        return {name: archive.read(name) for name in archive.namelist()}


def test_the_pack_holds_summary_reconciliation_actas_and_the_ledger_with_its_verification() -> None:
    names = set(files_of(evidence_pack(source(), GENERATED)))

    assert {
        "LEEME.txt",
        "manifiesto.json",
        "resumen.pdf",
        "conciliacion.csv",
        "registro/registro.json",
        "registro/verificacion.json",
        "registro/verificar_registro.py",
        "actas/F-001.json",
        "actas/F-036.json",
    } <= names
    assert sum(name.startswith("actas/") for name in names) == 36


def test_the_same_state_gives_the_same_bytes_and_only_the_generation_date_changes() -> None:
    first = evidence_pack(source(), GENERATED)
    again = evidence_pack(source(), GENERATED)
    later = evidence_pack(source(), datetime(2027, 1, 5, 8, 0, tzinfo=UTC))

    assert first == again
    changed = {name for name, data in files_of(first).items() if files_of(later)[name] != data}
    assert changed == {"manifiesto.json"}
    before, after = json.loads(files_of(first)["manifiesto.json"]), json.loads(files_of(later)["manifiesto.json"])
    assert {key for key in before if before[key] != after[key]} == {"generado_en"}


def test_the_manifest_lists_the_hash_of_every_other_file() -> None:
    files = files_of(evidence_pack(source(), GENERATED))
    manifest = json.loads(files["manifiesto.json"])

    assert manifest["archivos"] == {
        name: hashlib.sha256(data).hexdigest() for name, data in files.items() if name != "manifiesto.json"
    }
    assert manifest["generado_en"] == "2026-11-02T09:30:00Z"
    assert manifest["periodo"] == "2026-10"


def test_the_standalone_verifier_agrees_with_the_public_one_and_catches_tampering(tmp_path: Path) -> None:
    files = files_of(evidence_pack(source(), GENERATED))
    script, chain = tmp_path / "verificar_registro.py", tmp_path / "registro.json"
    script.write_bytes(files["registro/verificar_registro.py"])
    chain.write_bytes(files["registro/registro.json"])

    intact = subprocess.run([sys.executable, "-I", str(script), str(chain)], capture_output=True, text=True)
    entries = json.loads(chain.read_text())
    entries[1]["payload"]["amount"] = "1"
    chain.write_text(json.dumps(entries))
    broken = subprocess.run([sys.executable, "-I", str(script), str(chain)], capture_output=True, text=True)

    assert intact.returncode == 0, intact.stdout + intact.stderr
    assert "4 asientos" in intact.stdout
    assert json.loads(files["registro/verificacion.json"])["valid"] is True
    assert broken.returncode == 1
    assert "#2" in broken.stdout


def test_the_reconciliation_csv_has_one_row_per_movement_with_its_reason_and_review() -> None:
    files = files_of(evidence_pack(source(), GENERATED))
    rows = list(csv.DictReader(io.StringIO(files["conciliacion.csv"].decode("utf-8-sig")), delimiter=";"))

    assert len(rows) == 22
    orbit = next(row for row in rows if "ORBIT" in row["descripcion"])
    assert orbit["estado"] == "Salida sin factura"
    assert orbit["nota_revision"] == "Pago hecho por fuera; se pidió reverso."
    assert orbit["revisado_por"] == "Ana Gómez"
    kora = next(row for row in rows if "KORA" in row["descripcion"])
    assert (kora["estado"], kora["nivel"], kora["factura"], kora["diferencia"]) == (
        "Conciliado con diferencia",
        "Con tolerancia",
        "F-001",
        "-0.13",
    )


def test_the_summary_pdf_states_paid_held_rejected_reconciled_differences_and_fees() -> None:
    files = files_of(evidence_pack(source(), GENERATED))
    with pdfplumber.open(io.BytesIO(files["resumen.pdf"])) as document:
        text = "\n".join(page.extract_text() or "" for page in document.pages)

    for words in ("Pagado", "Retenido", "Rechazado", "Conciliado", "Diferencias", "Comisiones", "octubre de 2026"):
        assert words in text
    assert "USD 30" in text  # the two bank charges: USD 18 + USD 12
    assert "Pago hecho por fuera; se pidió reverso." in text
    assert "Ana Gómez" in text
    assert "2026-11-02" not in text  # the generation date lives in the manifest only


def test_the_summary_counts_the_period() -> None:
    chosen = decisions()
    statement = read_csv_statement(demo_statement_csv(), default_currency="USD")
    paid, unpaid = demo_batch(demo_payment_day())
    outcome = reconcile(statement.movements, paid, unpaid, MatchSettings())

    summary = summarize(chosen, statement, outcome, [], currency="USD")

    paid_count = sum(d.status in (DecisionStatus.PAID_AUTO, DecisionStatus.PAID_HUMAN) for d in chosen)
    assert summary.paid.count == paid_count == 17
    assert summary.held.count == 5
    assert summary.fees.count == 2 and summary.fees.total == Decimal("30.00")
    assert summary.reconciled.count == 17
    assert summary.differences.count == 4
    assert summary.differences.total == Decimal("-0.28")  # -0.13 - 0.15 + 0.22 - 0.22
    assert summary.alerts_open == 2  # the transfer to Orbit and the duplicate
    assert summary.pending_in_bank.count == 1


def test_text_from_the_statement_cannot_become_a_spreadsheet_formula() -> None:
    evidence = source()
    tampered = [
        movement.model_copy(update={"description": '=HYPERLINK("https://example.test","x")', "reference": "+1-2"})
        if index == 0
        else movement
        for index, movement in enumerate(evidence.statement.movements)
    ]
    evidence = evidence.model_copy(update={"statement": evidence.statement.model_copy(update={"movements": tampered})})

    files = files_of(evidence_pack(evidence, GENERATED))
    first = next(csv.DictReader(io.StringIO(files["conciliacion.csv"].decode("utf-8-sig")), delimiter=";"))

    assert first["descripcion"] == '\'=HYPERLINK("https://example.test","x")'
    assert first["referencia"] == "'+1-2"
    assert first["monto"] == "18500.00"
