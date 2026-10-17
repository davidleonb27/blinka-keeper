"""Screening names against a sanctions list (R14). Every list here is the fictitious fixture, never real names."""

from datetime import date
from pathlib import Path

import pytest

from custodio.engine.sanctions import (
    SIMILARITY_THRESHOLD,
    SanctionsList,
    bundled_sanctions,
    jaro_winkler,
    screening_tokens,
)

FIXTURE = Path(__file__).parents[1] / "fixtures" / "sanctions" / "fictitious_sdn.json"


@pytest.fixture(scope="module")
def fictitious() -> SanctionsList:
    return SanctionsList.from_json(FIXTURE.read_text(encoding="utf-8"))


@pytest.mark.parametrize(
    ("name", "tokens"),
    [
        ("Banco Ficticio de Prueba, S.A.", ["banco", "ficticio", "prueba"]),
        ("Quimera Ficticia S.A.S.", ["ficticia", "quimera"]),
        ("Quimera Ficticia S.A. de C.V.", ["ficticia", "quimera"]),
        ("Quimera Ficticia LTDA", ["ficticia", "quimera"]),
        ("Quimera Ficticia, Inc.", ["ficticia", "quimera"]),
        ("Quimera Ficticia LLC", ["ficticia", "quimera"]),
        ("PÉREZ INVENTADO, Fulano", ["fulano", "inventado", "perez"]),
    ],
)
def test_names_are_folded_stripped_of_company_suffixes_and_sorted(name: str, tokens: list[str]) -> None:
    assert screening_tokens(name) == tokens


@pytest.mark.parametrize(
    ("left", "right", "score"),
    [("martha", "marhta", 0.961), ("dwayne", "duane", 0.84), ("dixon", "dicksonx", 0.813), ("abc", "abc", 1.0)],
)
def test_jaro_winkler_matches_the_textbook_values(left: str, right: str, score: float) -> None:
    assert jaro_winkler(left, right) == pytest.approx(score, abs=0.001)


def test_the_list_keeps_its_date_size_and_whether_it_is_fictitious(fictitious: SanctionsList) -> None:
    assert fictitious.published_on == date(2026, 10, 1)
    assert fictitious.size == 3
    assert fictitious.fictitious


def test_an_exact_name_is_a_hit_whatever_the_company_suffix_and_accents(fictitious: SanctionsList) -> None:
    hit = fictitious.screen("Quimera Ficticia Trading S.A.S.")
    assert hit is not None
    assert (hit.entry.uid, hit.score, hit.matched_name) == (990001, 1.0, "QUIMERA FICTICIA TRADING LLC")
    assert hit.entry.programs == ("PRUEBA-FICTICIA",)


def test_word_order_does_not_hide_a_person(fictitious: SanctionsList) -> None:
    hit = fictitious.screen("Fulano de Tal Pérez Inventado")
    assert hit is not None and hit.entry.uid == 990002 and hit.score == 1.0


def test_an_alias_is_screened_too(fictitious: SanctionsList) -> None:
    hit = fictitious.screen("QFT Test")
    assert hit is not None and hit.matched_name == "QFT TEST"


def test_a_one_letter_typo_is_still_a_hit_above_the_threshold(fictitious: SanctionsList) -> None:
    hit = fictitious.screen("Quimera Fictisia Trading")
    assert hit is not None and SIMILARITY_THRESHOLD <= hit.score < 1


def test_sharing_one_generic_word_is_not_a_hit(fictitious: SanctionsList) -> None:
    assert fictitious.screen("Global Trading LLC") is None
    assert fictitious.screen("Andes Code SAS") is None


def test_an_empty_list_or_name_never_hits() -> None:
    empty = SanctionsList.from_json('{"source": "vacía", "published_on": null, "downloaded_on": null, "entries": []}')
    assert empty.screen("Quimera Ficticia Trading") is None
    assert empty.published_on is None and empty.size == 0


def test_the_bundled_copy_is_dated_and_real() -> None:
    bundled = bundled_sanctions()
    assert bundled.published_on is not None
    assert not bundled.fictitious
    assert bundled is bundled_sanctions()  # loaded once per process
