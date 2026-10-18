"""The two Graph API calls Blinka Keeper makes: download a message's file and answer the sender.

A file is fetched in two steps (its metadata, then its bytes, both with the access token) and refused as soon as it is
known to be too large or of a type Blinka Keeper does not read, so a big file is never held in memory whole.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Protocol

import httpx

from custodio.services.invoice_service import DOCUMENT_MEDIA_TYPES, MAX_DOCUMENT_BYTES
from custodio.whatsapp.config import WhatsAppConfig
from custodio.whatsapp.errors import GraphUnavailable, MediaProblem, MediaRejected

GRAPH_HOST = "https://graph.facebook.com"
SEND_TIMEOUT_SECONDS = 10.0
HTTPS = "https"
OK_STATUSES = range(200, 300)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Media:
    data: bytes
    media_type: str


class GraphApi(Protocol):
    def fetch_media(self, media_id: str, *, timeout: float) -> Media: ...

    def send_text(self, to: str, body: str) -> None: ...


class HttpGraph:
    def __init__(self, config: WhatsAppConfig, transport: httpx.BaseTransport | None = None) -> None:
        self._config = config
        self._client = httpx.Client(
            base_url=f"{GRAPH_HOST}/{config.graph_version}",
            headers={"Authorization": f"Bearer {config.access_token}"},
            transport=transport,
            follow_redirects=False,
        )

    def fetch_media(self, media_id: str, *, timeout: float) -> Media:
        url, media_type = self._media_location(media_id, timeout)
        return Media(data=self._download(url, timeout), media_type=media_type)

    def send_text(self, to: str, body: str) -> None:
        message = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {"preview_url": False, "body": body},
        }
        self._call("POST", f"/{self._config.phone_number_id}/messages", SEND_TIMEOUT_SECONDS, json=message)

    def _media_location(self, media_id: str, timeout: float) -> tuple[str, str]:
        if not media_id.isdigit():  # Graph media ids are numeric; anything else would change the path
            raise GraphUnavailable("media id")
        metadata = self._call("GET", f"/{media_id}", timeout).json()
        media_type = str(metadata.get("mime_type", "")).split(";")[0].strip().lower()
        if media_type not in DOCUMENT_MEDIA_TYPES:
            raise MediaRejected(MediaProblem.MEDIA_TYPE)
        if int(metadata.get("file_size") or 0) > MAX_DOCUMENT_BYTES:
            raise MediaRejected(MediaProblem.TOO_LARGE)
        url = str(metadata.get("url", ""))
        if httpx.URL(url).scheme != HTTPS:  # the token goes with the download: never over plain HTTP
            raise GraphUnavailable("media url")
        return url, media_type

    def _download(self, url: str, timeout: float) -> bytes:
        chunks: list[bytes] = []
        size = 0
        try:
            with self._client.stream("GET", url, timeout=timeout) as response:
                if response.status_code not in OK_STATUSES:
                    raise GraphUnavailable(f"download {response.status_code}")
                for chunk in response.iter_bytes():
                    size += len(chunk)
                    if size > MAX_DOCUMENT_BYTES:
                        raise MediaRejected(MediaProblem.TOO_LARGE)
                    chunks.append(chunk)
        except httpx.HTTPError as error:
            raise _unavailable("download", error) from error
        return b"".join(chunks)

    def _call(self, method: str, path: str, timeout: float, json: object | None = None) -> httpx.Response:
        try:
            response = self._client.request(method, path, json=json, timeout=timeout)
        except httpx.HTTPError as error:
            raise _unavailable(path, error) from error
        if response.status_code not in OK_STATUSES:
            logger.warning("graph call answered %s", response.status_code)  # never the body: it can echo the token
            raise GraphUnavailable(f"graph {response.status_code}")
        return response


def _unavailable(step: str, error: httpx.HTTPError) -> GraphUnavailable:
    logger.warning("graph call failed: %s", type(error).__name__)
    return GraphUnavailable(step)
