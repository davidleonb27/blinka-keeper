"""Sender emails and lookalike domains (R15): what counts as the same domain, a lookalike or just another one."""

import pytest

from custodio.engine.domains import DomainLikeness, compare_domains, edit_distance, email_domain, first_email


def test_the_first_email_in_the_document_is_the_sender() -> None:
    text = "FACTURA N° 1\nDe: Facturación <Pagos@Andes-Code.co>\nCopia: otra@andescode.co"
    assert first_email(text) == "Pagos@Andes-Code.co"
    assert email_domain("Pagos@Andes-Code.co") == "andes-code.co"


def test_a_document_without_an_email_has_no_sender() -> None:
    assert first_email("FACTURA N° 1\nEmisor: Andes Code SAS\nPagar a: @andes2026") is None


@pytest.mark.parametrize(
    ("left", "right", "distance"),
    [("andescode", "andescode", 0), ("andescode", "andezcode", 1), ("andescode", "andecsode", 1), ("ab", "ba", 1)],
)
def test_edit_distance_counts_insertions_deletions_substitutions_and_swaps(
    left: str, right: str, distance: int
) -> None:
    assert edit_distance(left, right) == distance


@pytest.mark.parametrize("seen", ["cobaltolabs.co", "COBALTOLABS.CO", "facturas.cobaltolabs.co"])
def test_the_registered_domain_and_its_subdomains_are_the_same(seen: str) -> None:
    assert compare_domains(seen, "cobaltolabs.co").likeness is DomainLikeness.SAME


@pytest.mark.parametrize(
    ("seen", "why"),
    [
        ("cobalto-labs.co", "guion agregado"),
        ("cobaltolabs.co", "guion quitado"),
        ("cobaltolabs.com", "otra terminación (.com en lugar de .co)"),
        ("cobaltolabs.com.co", "otra terminación (.com.co en lugar de .co)"),
        ("cobaItolabs.co", "homóglifos (I por l)"),
        ("cobalt0labs.co", "homóglifos (0 por o)"),
        ("cobaltolabz.co", "a 1 edición de distancia"),
        ("cobaltolabes.cc", "a 2 ediciones de distancia"),
    ],
)
def test_lookalike_domains_say_what_changed(seen: str, why: str) -> None:
    registered = "cobalto-labs.co" if why == "guion quitado" else "cobaltolabs.co"
    comparison = compare_domains(seen, registered)
    assert comparison.likeness is DomainLikeness.LOOKALIKE
    assert comparison.why == why


def test_rn_posing_as_m_is_a_homoglyph() -> None:
    comparison = compare_domains("joaquinrnendez.dev", "joaquinmendez.dev")
    assert (comparison.likeness, comparison.why) == (DomainLikeness.LOOKALIKE, "homóglifos (rn por m)")


@pytest.mark.parametrize("seen", ["gmail.com", "pulsosoftware.com", "otro-proveedor.co"])
def test_a_domain_that_is_neither_the_same_nor_close_is_just_different(seen: str) -> None:
    comparison = compare_domains(seen, "cobaltolabs.co")
    assert comparison.likeness is DomainLikeness.DIFFERENT and comparison.why is None
