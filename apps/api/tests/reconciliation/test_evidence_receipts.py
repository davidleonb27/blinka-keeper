"""The month's evidence pack carries the signed receipt of every decision and what an accountant needs to check them."""

import base64
import io
import json
import subprocess
import sys
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from custodio.receipts import ReceiptPublicKey, verify_receipt

from .test_api import close, evidence, processed_demo, reconcile_demo, resolve_all


def closed_pack(client: TestClient) -> zipfile.ZipFile:
    workspace = processed_demo(client)
    resolve_all(client, workspace, reconcile_demo(client, workspace))
    close(client, workspace)
    response = evidence(client, workspace)
    assert response.status_code == 200, response.text
    return zipfile.ZipFile(io.BytesIO(response.content))


def test_every_acta_of_the_month_has_its_signed_receipt_next_to_the_public_key(client: TestClient) -> None:
    pack = closed_pack(client)
    names = pack.namelist()
    key_view = json.loads(pack.read("recibos/clave_publica.json"))
    key = ReceiptPublicKey(base64.b64decode(key_view["public_key"]))

    actas = sorted(n.removeprefix("actas/") for n in names if n.startswith("actas/"))
    receipts = sorted(n.removeprefix("recibos/") for n in names if n.startswith("recibos/F"))

    assert actas and receipts == actas
    for name in receipts:
        check = verify_receipt(json.loads(pack.read(f"recibos/{name}")), key)
        assert check.valid, (name, check.message)
    assert key_view == client.get("/api/v1/.well-known/custodio-receipt-key").json()


def test_the_pack_brings_the_standalone_verifier_and_it_runs(client: TestClient, tmp_path: Path) -> None:
    pack = closed_pack(client)
    pack.extractall(tmp_path)
    receipt = next(p for p in sorted((tmp_path / "recibos").glob("F*.json")))

    result = subprocess.run(
        [
            sys.executable,
            "-I",
            str(tmp_path / "recibos" / "verificar_recibo.py"),
            str(receipt),
            str(tmp_path / "recibos" / "clave_publica.json"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "recibos/" in pack.read("LEEME.txt").decode()
