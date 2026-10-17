"""Refuses request bodies over the limit with 413 before they reach a route, whether declared or streamed.

The body is buffered up to the limit and replayed to the app: requests are small (≤ 4 MB documents), and buffering
means the refusal never depends on how a route happens to read its body.
"""

from __future__ import annotations

import json

from starlette.types import ASGIApp, Message, Receive, Scope, Send

from custodio.services.errors import PayloadTooLarge
from custodio.services.invoice_service import MAX_DOCUMENT_BYTES

MULTIPART_ALLOWANCE = 64 * 1024  # form boundaries and small fields around a document of the maximum size
MAX_REQUEST_BYTES = MAX_DOCUMENT_BYTES + MULTIPART_ALLOWANCE


class BodySizeLimit:
    def __init__(self, app: ASGIApp, max_bytes: int = MAX_REQUEST_BYTES) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        if _declared_length(scope) > self.max_bytes:
            await _refuse(send)
            return
        body = await self._buffer(receive)
        if body is None:
            await _refuse(send)
            return
        await self.app(scope, _replay(body, receive), send)

    async def _buffer(self, receive: Receive) -> bytes | None:
        chunks: list[bytes] = []
        size = 0
        while True:
            message = await receive()
            if message["type"] != "http.request":
                return b"".join(chunks)
            chunk = message.get("body", b"")
            size += len(chunk)
            if size > self.max_bytes:
                return None
            chunks.append(chunk)
            if not message.get("more_body", False):
                return b"".join(chunks)


def _replay(body: bytes, receive: Receive) -> Receive:
    delivered = False

    async def replay() -> Message:
        nonlocal delivered
        if delivered:
            return await receive()
        delivered = True
        return {"type": "http.request", "body": body, "more_body": False}

    return replay


def _declared_length(scope: Scope) -> int:
    for name, value in scope.get("headers", []):
        if name == b"content-length":
            return int(value) if value.isdigit() else 0
    return 0


async def _refuse(send: Send) -> None:
    error = PayloadTooLarge()
    body = json.dumps({"detail": error.message, "code": error.code}, ensure_ascii=False).encode()
    headers = [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]
    await send({"type": "http.response.start", "status": 413, "headers": headers})
    await send({"type": "http.response.body", "body": body})
