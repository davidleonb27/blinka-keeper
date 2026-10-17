"""Self-hosting in one command: the images, the compose file and the documented environment agree with each other.

CI builds both images and runs `docker compose config`; these checks keep the contract readable without Docker.
"""

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
DOCUMENTED_VARIABLES = (
    "ANTHROPIC_API_KEY",
    "DATABASE_URL",
    "CUSTODIO_PAYMENT_RAIL",
    "STRIPE_SECRET_KEY",
    "CUSTODIO_LLM_DAILY_BUDGET_USD",
    "CUSTODIO_PUBLIC_BASE_URL",
    "API_INTERNAL_URL",
)


def read(relative: str) -> str:
    return (REPO / relative).read_text(encoding="utf-8")


def compose_service(name: str) -> str:
    match = re.search(rf"^  {name}:\n((?:    .*\n|\n)+)", read("docker-compose.yml"), re.MULTILINE)
    assert match, f"missing service: {name}"
    return match.group(1)


def env_example_entries() -> dict[str, str]:
    """Each variable with the comment block right above it."""
    entries: dict[str, str] = {}
    comment: list[str] = []
    for line in read(".env.example").splitlines():
        if line.startswith("#"):
            comment.append(line.lstrip("# "))
        elif "=" in line:
            entries[line.split("=", 1)[0].strip()] = " ".join(comment)
            comment = []
        else:
            comment = []
    return entries


def test_the_api_image_runs_the_locked_dependencies_as_a_non_root_user() -> None:
    dockerfile = read("apps/api/Dockerfile")
    assert re.search(r"^FROM python:3\.12-slim", dockerfile, re.MULTILINE)
    assert "uv sync --locked" in dockerfile
    assert re.search(r"^USER (?!root\b)\S+", dockerfile, re.MULTILINE)
    assert "EXPOSE 8000" in dockerfile
    assert "main:app" in dockerfile


def test_the_web_image_builds_next_on_node_24_and_runs_as_a_non_root_user() -> None:
    dockerfile = read("apps/web/Dockerfile")
    assert re.search(r"^FROM node:24", dockerfile, re.MULTILINE)
    assert "next build" in dockerfile or "npm run build" in dockerfile
    assert "API_INTERNAL_URL" in dockerfile
    assert re.search(r"^USER (?!root\b)\S+", dockerfile, re.MULTILINE)
    assert "EXPOSE 3000" in dockerfile


def test_compose_runs_postgres_with_a_volume_and_a_healthcheck() -> None:
    postgres = compose_service("postgres")
    assert "image: postgres:16" in postgres
    assert "healthcheck:" in postgres
    assert "pg_isready" in postgres
    assert re.search(r"- \S+:/var/lib/postgresql/data", postgres)


def test_the_api_waits_for_postgres_points_at_it_and_migrates_on_start() -> None:
    api = compose_service("api")
    assert "condition: service_healthy" in api
    assert re.search(r"DATABASE_URL: postgresql://\S+@postgres:5432/", api)
    assert "custodio.db.migrate" in read("apps/api/Dockerfile") + api
    assert "healthcheck:" in api


def test_the_web_reaches_the_api_inside_the_compose_network() -> None:
    web = compose_service("web")
    assert "API_INTERNAL_URL: http://api:8000" in web
    assert "3000:3000" in web


@pytest.mark.parametrize("variable", DOCUMENTED_VARIABLES)
def test_every_variable_is_documented_in_the_env_example(variable: str) -> None:
    entries = env_example_entries()
    assert variable in entries, f"{variable} is missing from .env.example"
    assert len(entries[variable]) > 20, f"{variable} has no explanation above it"


def test_the_env_example_holds_no_secret_values() -> None:
    entries = {
        line.split("=", 1)[0]: line.split("=", 1)[1] for line in read(".env.example").splitlines() if "=" in line
    }
    assert entries["ANTHROPIC_API_KEY"] == ""
    assert entries["STRIPE_SECRET_KEY"] == ""


def test_the_env_example_says_the_model_is_optional_and_stripe_only_takes_test_keys() -> None:
    entries = env_example_entries()
    assert "opcional" in entries["ANTHROPIC_API_KEY"].lower()
    assert "requiere ANTHROPIC_API_KEY" in entries["ANTHROPIC_API_KEY"]
    assert "sk_test_" in entries["STRIPE_SECRET_KEY"]
    assert "simulated" in entries["CUSTODIO_PAYMENT_RAIL"]


def test_ci_builds_both_images() -> None:
    workflow = read(".github/workflows/ci.yml")
    assert "apps/api/Dockerfile" in workflow or "context: apps/api" in workflow
    assert "apps/web/Dockerfile" in workflow or "context: apps/web" in workflow
    assert "docker compose config" in workflow


def test_vercel_builds_the_web_as_next_even_with_its_dockerfile_beside_it() -> None:
    # Vercel reads a Dockerfile in a service root as a second framework and refuses to build unless one is named.
    services = json.loads(read("vercel.json"))["services"]
    assert services["web"]["framework"] == "nextjs"
