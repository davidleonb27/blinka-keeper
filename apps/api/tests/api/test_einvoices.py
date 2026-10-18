"""Electronic invoices enter through the same upload as any document and follow the same path to the engine."""

from dataclasses import replace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from custodio.dataset.einvoices import DEMO_CFDI, VALID_DIAN, cfdi, dian_invoice

from .doubles import invoice_text
from .helpers import Workspace, assert_ledger_valid, new_workspace, process, statuses

BILLION_LAUGHS = (
    '<?xml version="1.0"?><!DOCTYPE l [<!ENTITY a "aaaa"><!ENTITY b "&a;&a;&a;&a;&a;&a;">]><Invoice>&b;</Invoice>'
)

SEEDED = {"F01", "F02", "F03"}  # the doubled demo company's pending invoices


def upload(client: TestClient, workspace: Workspace, name: str, data: bytes, media_type: str) -> Any:
    return client.post("/api/v1/invoices", headers=workspace.headers, files={"file": (name, data, media_type)})


@pytest.mark.parametrize(
    ("name", "media_type"),
    [("fe.xml", "application/xml"), ("fe.xml", "text/xml"), ("FE-1042.XML", "application/octet-stream")],
)
def test_an_electronic_invoice_is_read_without_a_model(client: TestClient, name: str, media_type: str) -> None:
    workspace = new_workspace(client)

    response = upload(client, workspace, name, dian_invoice(VALID_DIAN).encode(), media_type)

    assert response.status_code == 201, response.text
    extraction = response.json()["extraction"]
    assert "sin IA" in extraction["reader"]
    assert extraction["visible_text"].startswith("Leída de la factura electrónica oficial (sin IA)")
    assert extraction["amount"] == {**extraction["amount"], "value": "3800000.00", "verified": True}


def test_a_hostile_xml_is_refused_and_nothing_is_stored(client: TestClient) -> None:
    workspace = new_workspace(client)

    response = upload(client, workspace, "fe.xml", BILLION_LAUGHS.encode(), "application/xml")

    assert response.status_code == 422
    assert response.json()["code"] == "einvoice_rejected"
    assert set(statuses(process(client, workspace))) == SEEDED


def test_an_xml_that_is_no_invoice_is_refused(client: TestClient) -> None:
    workspace = new_workspace(client)

    response = upload(client, workspace, "catalogo.xml", b"<catalogo/>", "application/xml")

    assert response.status_code == 422
    assert response.json()["code"] == "einvoice_rejected"


def test_an_invoice_for_another_company_goes_to_a_person(client: TestClient) -> None:
    workspace = new_workspace(client)
    xml = dian_invoice(replace(VALID_DIAN, customer_name="Otra Empresa SAS")).encode()

    received = upload(client, workspace, "fe.xml", xml, "application/xml").json()

    assert received["extraction"]["amount"]["verified"] is False
    decisions = process(client, workspace)["batch"]["decisions"]
    decision = next(d for d in decisions if d["invoice_id"] == received["id"])
    assert decision["status"] == "pending_approval"
    reading = next(rule for rule in decision["rules"] if rule["rule_id"] == "R1")
    assert reading["outcome"] == "escalate"


def test_the_pdf_and_the_xml_of_one_invoice_become_one_invoice(client: TestClient) -> None:
    workspace = new_workspace(client)
    xml = upload(client, workspace, "cfdi.xml", cfdi(DEMO_CFDI).encode(), "application/xml").json()
    pdf_text = invoice_text(
        supplier="Colibrí Analítica S.A. de C.V.",
        tax_id=DEMO_CFDI.supplier_rfc,
        number="CA-2210",
        amount="46000.00",
        currency="MXN",
        account="072180001234567897",
    )

    paired = upload(client, workspace, "cfdi.pdf", pdf_text.encode(), "application/pdf")

    assert paired.status_code == 201, paired.text
    body = paired.json()
    assert body["id"] == xml["id"]
    assert body["extraction"]["supplier_name"]["value"] == "COLIBRI ANALITICA"
    assert body["extraction"]["account_number"]["value"] == "072180001234567897"
    assert "coincide con el XML oficial" in body["extraction"]["visible_text"]
    assert set(statuses(process(client, workspace))) == SEEDED | {xml["id"]}
    assert_ledger_valid(client, workspace)


def test_a_pdf_already_received_is_paired_when_its_xml_arrives(client: TestClient) -> None:
    workspace = new_workspace(client)
    pdf_text = invoice_text(
        supplier=VALID_DIAN.supplier_name, tax_id="901.223.610-9", number="DNC-1042", amount="3900000", currency="COP"
    )
    pdf = upload(client, workspace, "fe.pdf", pdf_text.encode(), "application/pdf").json()

    paired = upload(client, workspace, "fe.xml", dian_invoice(VALID_DIAN).encode(), "application/xml").json()

    assert paired["id"] == pdf["id"]
    assert paired["extraction"]["amount"]["value"] == "3800000.00"  # the XML wins
    assert paired["extraction"]["amount"]["verified"] is False  # and the disagreement goes to a person
