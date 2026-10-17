# Custodio API: FastAPI on uvicorn, with the locked dependencies, as a non-root user.
# Build from the repository root with `docker compose build api`, or: docker build -t custodio-api apps/api
# Behind a proxy with its own certificate authority, pass it as the optional build secret `extra_ca`.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11.32 /uv /usr/local/bin/uv

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Dependencies first, so editing the code does not reinstall them.
COPY pyproject.toml uv.lock .python-version ./
RUN --mount=type=secret,id=extra_ca,required=false \
    if [ -s /run/secrets/extra_ca ]; then export SSL_CERT_FILE=/run/secrets/extra_ca; fi; \
    uv sync --locked --no-dev --no-install-project

COPY alembic.ini main.py ./
COPY alembic ./alembic
COPY custodio ./custodio
RUN uv sync --locked --no-dev --offline

RUN useradd --system --uid 10001 --no-create-home custodio
USER custodio

EXPOSE 8000
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=5 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=2)"]

# Migrations (alembic upgrade head) run before the server takes traffic. On Postgres they hold an advisory lock, so
# several replicas can start at once.
CMD ["sh", "-c", "python -m custodio.db.migrate && exec uvicorn main:app --host 0.0.0.0 --port 8000 --proxy-headers --forwarded-allow-ips='*'"]
