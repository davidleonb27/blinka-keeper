"""A Graph API that never leaves the process: files by media id, and every reply it was asked to send."""

from __future__ import annotations

import copy
import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient
from httpx import Response

from custodio.whatsapp.errors import GraphUnavailable, MediaRejected
from custodio.whatsapp.graph import Media
from custodio.whatsapp.signature import sign
from tests.api.helpers import Workspace

FIXTURES = Path(__file__).parent / "fixtures"
APP_SECRET = "test-app-secret"
VERIFY_TOKEN = "test-verify-token"
ACCESS_TOKEN = "test-access-token"
PHONE_NUMBER_ID = "106540352242922"
DISPLAY_NUMBER = "15550783881"
SENDER = "573001234567"
WEBHOOK = "/api/v1/whatsapp/webhook"


@dataclass
class FakeGraph:
    files: dict[str, Media] = field(default_factory=dict)
    refusals: dict[str, Exception] = field(default_factory=dict)
    sent: list[tuple[str, str]] = field(default_factory=list)
    fetched: list[str] = field(default_factory=list)

    def fetch_media(self, media_id: str, *, timeout: float) -> Media:
        self.fetched.append(media_id)
        if media_id in self.refusals:
            raise self.refusals[media_id]
        return self.files[media_id]

    def send_text(self, to: str, body: str) -> None:
        self.sent.append((to, body))

    def refuse(self, media_id: str, error: MediaRejected | GraphUnavailable) -> None:
        self.refusals[media_id] = error

    def replies_to(self, phone: str) -> list[str]:
        return [body for to, body in self.sent if to == phone]


def fixture(name: str) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads((FIXTURES / f"{name}.json").read_text())
    return payload


def message(name: str, **changes: Any) -> dict[str, Any]:
    """A fixture whose single message gets `changes` (id, from, text body, caption...)."""
    payload = copy.deepcopy(fixture(name))
    inbound = payload["entry"][0]["changes"][0]["value"]["messages"][0]
    for key, value in changes.items():
        if key == "body":
            inbound["text"]["body"] = value
        elif key == "caption":
            inbound[inbound["type"]]["caption"] = value
        elif key == "media_id":
            inbound[inbound["type"]]["id"] = value
        else:
            inbound[{"sender": "from"}.get(key, key)] = value
    return payload


def text(body: str, *, sender: str = SENDER, message_id: str | None = None) -> dict[str, Any]:
    return message("text_message", body=body, sender=sender, id=message_id or f"wamid.{uuid.uuid4().hex}")


def deliver(client: TestClient, payload: dict[str, Any], *, secret: str = APP_SECRET) -> Response:
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json", "X-Hub-Signature-256": sign(body, secret)}
    return client.post(WEBHOOK, content=body, headers=headers)


def link_phone(client: TestClient, workspace: Workspace, phone: str = SENDER) -> None:
    created = client.post("/api/v1/whatsapp/link-codes", headers=workspace.headers)
    assert created.status_code == 201, created.text
    response = deliver(client, text(created.json()["message"], sender=phone))
    assert response.status_code == 200, response.text
