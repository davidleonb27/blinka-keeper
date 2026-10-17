"""Vercel entrypoint (`main:app`). Vercel forwards the original path, so every route lives under /api/v1."""

from custodio.api.app import create_app

app = create_app()
