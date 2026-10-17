from fastapi.testclient import TestClient

from custodio.services.lanes import Lanes

from .doubles import failing
from .helpers import assert_ledger_valid, new_workspace

SUPPLIERS_CSV = b"Nube Hosting S.A.S.,900123456,Banco Andino,111222333\nfila rota\n"


def test_the_profile_is_proposed_from_name_site_and_answers(client: TestClient) -> None:
    workspace = new_workspace(client, mode="blank")

    response = client.post(
        "/api/v1/onboarding/profile",
        headers=workspace.headers,
        json={"company_name": "Panadería Sol", "website": "https://sol.example", "answers": {"industria": "Alimentos"}},
    )

    assert response.status_code == 200
    assert response.json()["company_name"] == "Panadería Sol"
    assert response.json()["industry"] == "Alimentos"


def test_a_model_failure_in_onboarding_is_an_honest_503(client: TestClient, lanes: Lanes) -> None:
    object.__setattr__(lanes, "profile_company", failing)
    workspace = new_workspace(client, mode="blank")

    response = client.post(
        "/api/v1/onboarding/profile", headers=workspace.headers, json={"company_name": "Panadería Sol"}
    )

    assert response.status_code == 503
    assert response.json()["code"] == "model_unavailable"


def test_suppliers_are_imported_from_a_file_with_warnings(client: TestClient) -> None:
    workspace = new_workspace(client, mode="blank")

    response = client.post(
        "/api/v1/onboarding/suppliers",
        headers=workspace.headers,
        files={"file": ("proveedores.csv", SUPPLIERS_CSV, "text/csv")},
    )

    assert response.status_code == 200
    assert [b["tax_id"] for b in response.json()["beneficiaries"]] == ["900123456"]
    assert response.json()["warnings"] == ["Fila 2: incompleta."]


def test_completing_onboarding_sets_up_the_company_and_simulates_its_first_week(client: TestClient) -> None:
    workspace = new_workspace(client, mode="blank")
    policy = client.get("/api/v1/policy", headers=workspace.headers).json()
    supplier = {
        "id": "B-SOL",
        "name": "Harinas del Valle",
        "tax_id": "901000111",
        "bank_name": "Banco Andino",
        "account_number": "444555666",
        "currency": "USD",
        "agreement": {"kind": "fixed", "amount": 1500, "currency": "USD"},
    }

    response = client.post(
        "/api/v1/onboarding/complete",
        headers=workspace.headers,
        json={
            "profile": {"company_name": "Panadería Sol", "base_currency": "USD"},
            "policy": {**policy, "approval_threshold": 2000},
            "suppliers": [supplier],
            "opening_balance": 90000,
        },
    )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["workspace"]["company_name"] == "Panadería Sol"
    assert body["workspace"]["balance"] == 90000.0
    assert body["workspace"]["policy_version"] == 2
    assert [d["status"] for d in body["first_week"]["decisions"]] == ["paid_auto"]
    saved = client.get("/api/v1/policy", headers=workspace.headers).json()
    assert [b["id"] for b in saved["beneficiaries"]] == ["B-SOL"]
    assert saved["approval_threshold"] == 2000.0
    assert client.get("/api/v1/decisions", headers=workspace.headers).json() == []  # a simulation, not payments
    assert_ledger_valid(client, workspace)
