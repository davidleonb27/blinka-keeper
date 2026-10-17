"""The delivery documents are a contract with the judges: timings add up, figures cite sources, links resolve."""

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from itertools import pairwise
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
OWNED_DOCS = (
    "PITCH",
    "DATASET",
    "BUSINESS",
    "BUILD_IN_PUBLIC",
    "COPY",
    "ARCHITECTURE",
    "MEASUREMENTS",
    "BLINKA",
    "PAYMENTS",
)
MAX_SPOKEN_WORDS_PER_SECOND = 2.6
X_MAX_CHARS = 280
X_LINK_CHARS = 23
DEMO_URL = "https://custodio-blinka-green.vercel.app"
URL_PLACEHOLDER = "{{DEMO_URL}}"
MEASURED_ON = "2026-10-17"
MEASURED_FIGURES = ("61,1 %", "36", "25.139", "8.136", "4,2 s", "6,0 s")
POST_INTERVAL = timedelta(hours=4)
DEADLINE = datetime(2026, 10, 18, 11, 59)
LAUNCH = datetime(2026, 10, 17, 12, 0)
FIGURE = re.compile(r"\d[\d.,]*\s?(%|millones|mil millones)|US\$|USD")
INFLATED_WORDS = (
    "revolucion",
    "disruptiv",
    "innovador",
    "vanguardia",
    "última generación",
    "infalible",
    "impenetrable",
    "sin precedentes",
    "increíble",
    "game-changer",
    "cutting-edge",
)
OUT_OF_SCOPE_SERVICES = ("telegram", "gemini", "celular")
FORBIDDEN_TRAILERS = ("Co-Authored-By", "Generated with")
BLINKA_SECTIONS = (
    "El problema de sus clientes",
    "Dónde va Custodio",
    "Qué gana Blinka",
    "Lo que ya está medido",
    "Integración en 2 semanas",
    "Precio propuesto",
    "Seguridad",
    "Lo que falta para producción",
)
MEASURED_SOURCES = ("README.md", "docs/DATASET.md", "docs/MEASUREMENTS.md", "docs/PAYMENTS.md")
CLOSING_LINE = "Custodio decide; Blinka paga"
NUMBER = re.compile(r"\d[\d.,]*\d|\d")
WRITTEN_SEGMENT = re.compile(r"^### (\d+):(\d\d)–(\d+):(\d\d) · .+$", re.MULTILINE)


@dataclass(frozen=True)
class Segment:
    start: int
    end: int
    body: str


def read(relative: str) -> str:
    return (REPO / relative).read_text(encoding="utf-8")


def owned_markdown() -> list[str]:
    return ["README.md", *(f"docs/{name}.md" for name in OWNED_DOCS)]


def section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.MULTILINE | re.DOTALL)
    assert match, f"missing section: {heading}"
    return match.group(1)


def segments(text: str) -> list[Segment]:
    matches = list(WRITTEN_SEGMENT.finditer(text))
    body_ends = [match.start() for match in matches[1:]] + [len(text)]
    return [
        Segment(int(m[1]) * 60 + int(m[2]), int(m[3]) * 60 + int(m[4]), text[m.end() : body_end])
        for m, body_end in zip(matches, body_ends, strict=True)
    ]


def table_rows(text: str) -> list[list[str]]:
    lines = [line for line in text.splitlines() if line.startswith("|") and "---" not in line]
    return [[cell.strip() for cell in line.strip("|").split("|")] for line in lines[1:]]


def labelled_line(body: str, label: str) -> str:
    match = re.search(rf"^\*\*{label}:\*\* (.+)$", body, re.MULTILINE)
    assert match, f"missing label: {label}"
    return match.group(1)


def word_count(text: str) -> int:
    return len(re.findall(r"[\wáéíóúüñÁÉÍÓÚÜÑ$]+", text))


@dataclass(frozen=True)
class Post:
    when: datetime
    title: str
    x: str
    linkedin: str


def posts(text: str) -> list[Post]:
    found = []
    for match in re.finditer(r"^### (\d{4}-\d\d-\d\d \d\d:\d\d) · (.+?)\n(.*?)(?=^### |\Z)", text, re.M | re.S):
        body = match[3]
        found.append(
            Post(datetime.strptime(match[1], "%Y-%m-%d %H:%M"), match[2], quoted(body, "X"), quoted(body, "LinkedIn"))
        )
    return found


def quoted(body: str, network: str) -> str:
    match = re.search(rf"^#### {network}\n((?:>.*\n?)+)", body, re.MULTILINE)
    assert match, f"missing {network} draft"
    return "\n".join(line.removeprefix(">").strip() for line in match.group(1).splitlines()).strip()


@pytest.mark.parametrize("path", owned_markdown())
def test_relative_links_point_to_files_that_exist(path: str) -> None:
    for target in re.findall(r"\]\(((?!https?://|#|mailto:)[^)\s]+)\)", read(path)):
        assert (REPO / Path(path).parent / target.split("#")[0]).exists(), f"{path} -> {target}"


@pytest.mark.parametrize("path", owned_markdown())
def test_no_inflated_marketing_words(path: str) -> None:
    text = read(path).lower()
    assert [word for word in INFLATED_WORDS if word in text] == []


@pytest.mark.parametrize("path", owned_markdown())
def test_rule_references_exist_in_the_catalogue(path: str) -> None:
    numbers = {int(n) for n in re.findall(r"\bR(\d+)\b", read(path))}
    assert numbers <= set(range(1, 13))


@pytest.mark.parametrize("path", owned_markdown())
def test_no_attribution_trailers_in_documents(path: str) -> None:
    assert [trailer for trailer in FORBIDDEN_TRAILERS if trailer in read(path)] == []


@pytest.mark.parametrize(("heading", "total"), [("Versión de 3:00", 180), ("Versión de 60 s", 60)])
def test_pitch_segments_are_contiguous_and_fill_the_whole_video(heading: str, total: int) -> None:
    parts = segments(section(read("docs/PITCH.md"), heading))
    assert parts[0].start == 0
    assert parts[-1].end == total
    assert all(a.end == b.start for a, b in pairwise(parts))


@pytest.mark.parametrize("heading", ["Versión de 3:00", "Versión de 60 s"])
def test_pitch_lines_can_be_spoken_in_their_time(heading: str) -> None:
    for part in segments(section(read("docs/PITCH.md"), heading)):
        words = word_count(labelled_line(part.body, "Se oye"))
        assert words <= MAX_SPOKEN_WORDS_PER_SECOND * (part.end - part.start), f"{part.start}s: {words} words"


def test_every_long_pitch_segment_says_what_is_seen_and_has_a_backup_shot() -> None:
    for part in segments(section(read("docs/PITCH.md"), "Versión de 3:00")):
        assert labelled_line(part.body, "Se ve")
        assert labelled_line(part.body, "Respaldo")


def test_every_figure_in_the_business_case_has_a_linked_source_or_is_not_measured() -> None:
    unsourced = [
        line
        for line in read("docs/BUSINESS.md").splitlines()
        if FIGURE.search(line) and "](https://" not in line and "NO MEDIDO" not in line
    ]
    assert unsourced == []


def test_business_case_cites_the_fbi_and_the_afp_primary_sources() -> None:
    text = read("docs/BUSINESS.md")
    assert "https://www.ic3.gov/AnnualReport/Reports/2025_IC3Report.pdf" in text
    assert "financialprofessionals.org" in text


def test_build_in_public_posts_are_four_hours_apart_until_sunday() -> None:
    times = [post.when for post in posts(read("docs/BUILD_IN_PUBLIC.md"))]
    assert times[0] <= datetime(2026, 10, 17, 0, 0)
    assert all(b - a == POST_INTERVAL for a, b in pairwise(times))
    assert DEADLINE - times[-1] < POST_INTERVAL
    assert times[-1] <= DEADLINE


def test_the_public_challenge_launches_saturday_at_noon() -> None:
    launch = [post for post in posts(read("docs/BUILD_IN_PUBLIC.md")) if post.when == LAUNCH]
    assert len(launch) == 1
    assert LAUNCH.strftime("%A") == "Saturday"
    assert "Róbale a Custodio" in launch[0].x
    assert "Róbale a Custodio" in launch[0].linkedin


def test_every_post_fits_x_and_names_the_hackathon_and_blinka() -> None:
    for post in posts(read("docs/BUILD_IN_PUBLIC.md")):
        length = len(post.x.replace(DEMO_URL, "x" * X_LINK_CHARS))
        assert length <= X_MAX_CHARS, f"{post.when}: {length} chars"
        for text in (post.x, post.linkedin):
            assert "30X" in text
            assert "Blinka" in text


def test_dataset_doc_maps_every_trap_of_the_brief_to_a_rule() -> None:
    table = section(read("docs/DATASET.md"), "Trampas y la regla que las atrapa")
    rows = table_rows(table)
    assert len(rows) >= 16
    assert all(re.search(r"\bR\d+\b", row[-1]) for row in rows)


def test_dataset_doc_gives_the_reproduction_commands() -> None:
    text = read("docs/DATASET.md")
    assert "scripts/stress.py --companies 1000 --seed 7" in text
    assert "./scripts/check.sh" in text


def test_architecture_has_a_diagram_and_the_invoice_journey() -> None:
    text = read("docs/ARCHITECTURE.md")
    assert "```mermaid" in text
    assert len(re.findall(r"^\d+\. ", section(text, "Recorrido de una factura"), re.MULTILINE)) >= 8


@pytest.mark.parametrize("heading", ["Inicio", "Onboarding", "Estados vacíos", "Errores"])
def test_copy_covers_the_screens_the_web_lane_needs(heading: str) -> None:
    assert section(read("docs/COPY.md"), heading).strip()


def test_readme_sells_and_explains_the_trial_on_the_first_screen() -> None:
    first_screen = "\n".join(read("README.md").splitlines()[:30])
    assert "El modelo lee, el código decide, la persona autoriza" in first_screen
    assert "Pruébalo en 30 segundos" in first_screen
    trial = section(read("README.md"), "Pruébalo en 30 segundos")
    assert DEMO_URL in trial


@pytest.mark.parametrize("path", ["README.md", "docs/BUILD_IN_PUBLIC.md"])
def test_documents_link_the_deployed_demo_instead_of_a_placeholder(path: str) -> None:
    text = read(path)
    assert URL_PLACEHOLDER not in text
    assert DEMO_URL in text


def test_readme_metrics_are_measured_figures_or_say_not_measured() -> None:
    table = section(read("README.md"), "Métricas")
    values = [row[1] for row in table_rows(table)]
    assert len(values) >= 5
    assert all(value == "NO MEDIDO" or re.match(r"\d", value) for value in values)
    assert MEASURED_ON in table


@pytest.mark.parametrize(("path", "heading"), [("README.md", "Métricas"), ("docs/DATASET.md", "Qué se ha medido")])
def test_published_metrics_carry_the_measured_figures(path: str, heading: str) -> None:
    table = section(read(path), heading)
    assert MEASURED_ON in table
    assert [figure for figure in MEASURED_FIGURES if figure not in table] == []


def test_readme_names_the_team_the_license_and_ends_in_english() -> None:
    text = read("README.md")
    for name in ("Adriano Joao Souza Reyna", "Juan David Leon", "Leober Ramos"):
        assert name in text
    assert "Apache 2.0" in text
    assert re.findall(r"^## (.+)$", text, re.MULTILINE)[-1] == "English summary"
    license_text = (REPO / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License" in license_text.splitlines()[1]
    assert "Copyright 2026 Juan David Leon y colaboradores de Custodio" in license_text


@pytest.mark.parametrize(
    "path", ["CONTRIBUTING.md", "CODE_OF_CONDUCT.md", "SECURITY.md", ".github/PULL_REQUEST_TEMPLATE.md"]
)
def test_community_files_exist(path: str) -> None:
    assert read(path).strip()


def test_security_policy_reports_privately_and_covers_any_improper_payment() -> None:
    text = read("SECURITY.md")
    assert "security/advisories/new" in text
    assert "pague algo indebido" in text


def test_issue_templates_cover_bugs_new_rules_and_payment_rails() -> None:
    templates = {path.name for path in (REPO / ".github" / "ISSUE_TEMPLATE").glob("*.yml")}
    assert {"bug.yml", "rule.yml", "payment-rail.yml"} <= templates


@pytest.mark.parametrize("path", owned_markdown())
def test_documents_do_not_present_out_of_scope_services_as_existing(path: str) -> None:
    text = read(path).lower()
    assert [name for name in OUT_OF_SCOPE_SERVICES if name in text] == []


def test_reading_measurement_gives_exact_counts_and_how_to_repeat_it() -> None:
    text = read("docs/MEASUREMENTS.md")
    assert "scripts/measure_reading.py --base-url" in text
    assert MEASURED_ON in text
    assert "](MEASUREMENTS.md)" in read("docs/DATASET.md")


def test_the_blinka_page_covers_what_the_blinka_team_needs() -> None:
    text = read("docs/BLINKA.md")
    for heading in BLINKA_SECTIONS:
        assert section(text, heading).strip()


def test_every_figure_on_the_blinka_page_is_already_published_as_measured() -> None:
    measured = section(read("docs/BLINKA.md"), "Lo que ya está medido")
    published = "\n".join(read(path) for path in MEASURED_SOURCES)
    missing = [number for number in NUMBER.findall(measured) if number not in published]
    assert missing == []


def test_the_blinka_price_is_presented_as_a_proposal() -> None:
    price = section(read("docs/BLINKA.md"), "Precio propuesto").lower()
    assert "propuesta" in price
    assert "por decisión" in price
    assert "volumen" in price


def test_the_blinka_page_names_what_is_missing_for_production() -> None:
    missing = section(read("docs/BLINKA.md"), "Lo que falta para producción")
    for item in ("API", "KYC", "SOC 2"):
        assert item in missing


def test_the_pitch_shows_the_real_test_payment_and_closes_on_the_rail_split() -> None:
    parts = segments(section(read("docs/PITCH.md"), "Versión de 3:00"))
    assert any("Stripe" in part.body and "tr_" in part.body for part in parts)
    assert CLOSING_LINE in labelled_line(parts[-1].body, "Se oye")


def test_readme_links_the_blinka_page_and_the_rails_section() -> None:
    text = read("README.md")
    assert "](docs/BLINKA.md)" in text
    assert "](docs/PAYMENTS.md#los-rieles)" in text
    assert "## Los rieles" in read("docs/PAYMENTS.md")
