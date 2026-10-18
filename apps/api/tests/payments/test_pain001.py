"""The file for Blinka: ISO 20022 pain.001.001.09, validated against the official XSD (tests/payments/schemas)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

from custodio.payments.pain001 import NAMESPACE, CreditTransfer, Debtor, PaymentFile, render

SCHEMA = etree.XMLSchema(etree.parse(str(Path(__file__).parent / "schemas" / "pain.001.001.09.xsd")))
NS = {"p": NAMESPACE}
DEBTOR = Debtor(name="Andes Code SAS", account_id="BLINKA-ws123")


def transfer(end_to_end_id: str, amount: str, currency: str = "USD", **overrides: str) -> CreditTransfer:
    values = {
        "creditor_name": "Nube Segura SAS",
        "creditor_tax_id": "901554210",
        "creditor_country": "CO",
        "creditor_bank": "Davivienda",
        "creditor_account": "0550-7781",
        "remittance": f"https://custodio.test/acta/{end_to_end_id}",
        **overrides,
    }
    return CreditTransfer(end_to_end_id=end_to_end_id, amount=Decimal(amount), currency=currency, **values)


def payment_file(*transfers: CreditTransfer) -> PaymentFile:
    return PaymentFile(
        message_id="CUSTODIO-20261018-ab12cd",
        created_at=datetime(2026, 10, 18, 3, 0, tzinfo=UTC),
        execution_date=date(2026, 10, 18),
        debtor=DEBTOR,
        transfers=transfers,
    )


def parsed(xml: bytes) -> etree._Element:
    document = etree.fromstring(xml)
    SCHEMA.assertValid(document)
    return document


def texts(document: etree._Element, path: str) -> list[str]:
    return [element.text or "" for element in document.xpath(path, namespaces=NS)]


def test_the_file_is_valid_against_the_official_schema_and_its_header_adds_up() -> None:
    document = parsed(render(payment_file(transfer("F-001", "1200.50"), transfer("F-002", "99.5"))))

    assert texts(document, "//p:GrpHdr/p:MsgId") == ["CUSTODIO-20261018-ab12cd"]
    assert texts(document, "//p:GrpHdr/p:NbOfTxs") == ["2"]
    assert texts(document, "//p:GrpHdr/p:CtrlSum") == ["1300.00"]
    assert texts(document, "//p:GrpHdr/p:InitgPty/p:Nm") == ["Andes Code SAS"]
    assert texts(document, "//p:PmtInf/p:Dbtr/p:Nm") == ["Andes Code SAS"]
    assert texts(document, "//p:PmtInf/p:DbtrAcct/p:Id/p:Othr/p:Id") == ["BLINKA-ws123"]
    assert texts(document, "//p:CdtTrfTxInf/p:PmtId/p:EndToEndId") == ["F-001", "F-002"]
    assert texts(document, "//p:CdtTrfTxInf/p:Amt/p:InstdAmt") == ["1200.50", "99.50"]
    assert texts(document, "//p:CdtTrfTxInf/p:CdtrAcct/p:Id/p:Othr/p:Id") == ["0550-7781", "0550-7781"]


def test_each_currency_gets_its_own_payment_block_with_its_own_sums() -> None:
    document = parsed(
        render(
            payment_file(
                transfer("F-001", "100.00", "USD"),
                transfer("F-002", "4200000.00", "COP"),
                transfer("F-003", "50.25", "USD"),
            )
        )
    )

    blocks = document.xpath("//p:PmtInf", namespaces=NS)
    assert [block.xpath("p:CdtTrfTxInf/p:Amt/p:InstdAmt/@Ccy", namespaces=NS) for block in blocks] == [
        ["COP"],
        ["USD", "USD"],
    ]
    assert [texts(block, "p:NbOfTxs") for block in blocks] == [["1"], ["2"]]
    assert [texts(block, "p:CtrlSum") for block in blocks] == [["4200000.00"], ["150.25"]]
    assert texts(document, "//p:GrpHdr/p:NbOfTxs") == ["3"]
    assert texts(document, "//p:GrpHdr/p:CtrlSum") == ["4200150.25"]


def test_special_characters_are_escaped_and_long_texts_cut_to_the_schema_limits() -> None:
    tricky = 'Ñandú & Hijos <S.A.S.> «Café» "Ltda" ' + "x" * 200
    iban = "ES12 3456 7890 1234 5678 9012 3456"
    document = parsed(render(payment_file(transfer("F-001", "10", creditor_name=tricky, creditor_account=iban))))

    [name] = texts(document, "//p:Cdtr/p:Nm")
    assert name.startswith('Ñandú & Hijos <S.A.S.> «Café» "Ltda"')
    assert len(name) == 140
    [account] = texts(document, "//p:CdtrAcct/p:Id/p:Othr/p:Id")
    assert len(account) <= 34


def test_control_characters_never_reach_the_file() -> None:
    document = parsed(render(payment_file(transfer("F-001", "10", creditor_name="Nube\x00 Segura\x07\nSAS"))))

    assert texts(document, "//p:Cdtr/p:Nm") == ["Nube Segura SAS"]


def test_characters_xml_cannot_carry_never_reach_the_file() -> None:
    document = parsed(
        render(
            payment_file(
                transfer("F-001", "10", creditor_name="Nube\ufffe Segura\uffff SAS", creditor_bank="Banco\ud800")
            )
        )
    )

    assert texts(document, "//p:Cdtr/p:Nm") == ["Nube Segura SAS"]
    assert texts(document, "//p:CdtrAgt/p:FinInstnId/p:Nm") == ["Banco"]


def test_a_blank_name_still_gives_a_valid_file() -> None:
    blank = PaymentFile(
        message_id="CUSTODIO-20261018-ab12cd",
        created_at=datetime(2026, 10, 18, 3, 0, tzinfo=UTC),
        execution_date=date(2026, 10, 18),
        debtor=Debtor(name=" ", account_id="BLINKA-ws123"),
        transfers=[transfer("F-001", "10", creditor_name="\x00 ")],
    )

    document = parsed(render(blank))

    assert texts(document, "//p:Cdtr/p:Nm") == ["Sin nombre"]
    assert texts(document, "//p:Dbtr/p:Nm") == ["Sin nombre"]


def test_an_empty_batch_is_refused_rather_than_written_as_an_invalid_file() -> None:
    with pytest.raises(ValueError, match="sin pagos"):
        render(payment_file())


def test_a_long_invoice_id_still_fits_the_end_to_end_id_and_stays_unique() -> None:
    long_a = "factura-" + "a" * 60
    long_b = "factura-" + "a" * 59 + "b"
    document = parsed(render(payment_file(transfer(long_a, "1"), transfer(long_b, "2"))))

    ids = texts(document, "//p:EndToEndId")
    assert all(len(value) <= 35 for value in ids)
    assert len(set(ids)) == 2
