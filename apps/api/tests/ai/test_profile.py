from typing import Any

import pytest

from custodio.ai import profile_company
from custodio.ai.profile import InvalidWebsite

from .conftest import FakeLLM, recorded


def profile_reply(**fields: Any) -> dict[str, Any]:
    blank: dict[str, Any] = {
        "industry": None,
        "country": None,
        "base_currency": None,
        "summary": None,
        "likely_suppliers": [],
        "suggested_rules_text": None,
        "evidence_urls": [],
    }
    return blank | fields


def test_the_profiler_reads_only_the_given_site_with_web_fetch(fake_llm: FakeLLM) -> None:
    fake_llm.reply(profile_reply(evidence_urls=["https://www.rutasclaras.co/"]))

    profile_company("Rutas Claras", "www.rutasclaras.co", {"rol": "CFO"})

    call = fake_llm.calls[0]
    assert call.model == "claude-opus-5-5"
    assert call.effort == "medium"
    assert call.tools is not None
    [tool] = call.tools
    assert tool["type"] == "web_fetch_20260209"
    assert tool["name"] == "web_fetch"
    assert tool["allowed_domains"] == ["rutasclaras.co"]
    assert tool["max_uses"] >= 1
    assert "https://www.rutasclaras.co" in call.text
    assert "CFO" in call.text


def test_evidence_outside_the_site_is_dropped_and_values_are_normalized(fake_llm: FakeLLM) -> None:
    fake_llm.reply(recorded("profile_offsite_evidence"))

    profile = profile_company("Rutas Claras", "https://rutasclaras.co", {})

    assert profile.company_name == "Rutas Claras"
    assert profile.website == "https://rutasclaras.co"
    assert profile.evidence_urls == [
        "https://rutasclaras.co/",
        "https://www.rutasclaras.co/nosotros",
        "https://blog.rutasclaras.co/precios",
    ]
    assert profile.country is None
    assert profile.base_currency == "COP"
    assert profile.likely_suppliers == ["hosting", "nómina tercerizada"]
    assert profile.suggested_rules_text == "Nada sobre 20 millones de pesos sin aprobación de la gerente."


def test_without_a_website_only_the_answers_are_used_and_nothing_is_cited(fake_llm: FakeLLM) -> None:
    fake_llm.reply(
        profile_reply(country="MX", base_currency="MXN", evidence_urls=["https://example.com/"], summary="Taller.")
    )

    profile = profile_company("Taller Ruiz", None, {"país": "México", "a qué se dedica": "taller mecánico"})

    call = fake_llm.calls[0]
    assert call.tools is None
    assert "taller mecánico" in call.text
    assert profile.website is None
    assert profile.evidence_urls == []
    assert profile.country == "MX"
    assert profile.base_currency == "MXN"


def test_an_unknown_currency_keeps_the_default(fake_llm: FakeLLM) -> None:
    fake_llm.reply(profile_reply(base_currency="pesos"))

    assert profile_company("Taller Ruiz", None, {}).base_currency == "USD"


def test_a_blank_website_counts_as_none(fake_llm: FakeLLM) -> None:
    fake_llm.reply(profile_reply())

    profile_company("Taller Ruiz", "  ", {})

    assert fake_llm.calls[0].tools is None


@pytest.mark.parametrize("website", ["notaurl", "ftp://rutasclaras.co", "https://localhost/", "http://10.0.0.1/"])
def test_a_website_that_is_not_a_public_http_url_is_refused(fake_llm: FakeLLM, website: str) -> None:
    with pytest.raises(InvalidWebsite):
        profile_company("Rutas Claras", website, {})
    assert fake_llm.calls == []
