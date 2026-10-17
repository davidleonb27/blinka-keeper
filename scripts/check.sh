#!/usr/bin/env bash
# The single quality gate. Same command for the author, the reviewer, CI and the coordinator.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "== api: lint, format, types, tests"
(
  cd apps/api
  uv sync --locked --quiet
  uv run ruff check .
  uv run ruff format --check .
  uv run mypy custodio main.py
  uv run pytest -q
)

if [ -f apps/web/package.json ]; then
  echo "== web: API schema, lint, types, tests, build"
  (
    cd apps/web
    npm ci --no-audit --no-fund --loglevel=error
    npm run check:api  # regenerates the types from the API's OpenAPI and fails if the committed ones differ
    npm run lint
    npm run typecheck
    npm run test --if-present
    npm run build
  )
fi
echo "== gate passed"
