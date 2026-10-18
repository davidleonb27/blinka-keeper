"""The parts of a WhatsApp webhook delivery Custodio reads: the messages sent to its own number.

Statuses (sent, delivered, read) and every field Custodio does not use are ignored.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from custodio.whatsapp.errors import WebhookPayloadInvalid

MESSAGES_FIELD = "messages"


class _Lenient(BaseModel):
    model_config = ConfigDict(extra="ignore")


class TextBody(_Lenient):
    body: str = ""


class MediaRef(_Lenient):
    id: str
    mime_type: str | None = None
    filename: str | None = None
    caption: str | None = None


class InboundMessage(_Lenient):
    id: str = Field(min_length=1, max_length=255)
    sender: str = Field(alias="from", min_length=1, max_length=32)
    type: str
    text: TextBody | None = None
    image: MediaRef | None = None
    document: MediaRef | None = None

    @property
    def media(self) -> MediaRef | None:
        return self.image if self.type == "image" else self.document if self.type == "document" else None


class _Metadata(_Lenient):
    phone_number_id: str


class _Value(_Lenient):
    metadata: _Metadata | None = None  # only `messages` changes carry it; other fields must not fail the delivery
    messages: list[InboundMessage] = []


class _Change(_Lenient):
    field: str
    value: _Value


class _Entry(_Lenient):
    changes: list[_Change] = []


class _Delivery(_Lenient):
    entry: list[_Entry] = []


def inbound_messages(body: bytes, phone_number_id: str) -> list[InboundMessage]:
    """Messages addressed to this business number; a delivery for another number is not ours to read."""
    try:
        delivery = _Delivery.model_validate_json(body)
    except ValidationError as error:
        raise WebhookPayloadInvalid() from error
    return [
        message
        for entry in delivery.entry
        for change in entry.changes
        if change.field == MESSAGES_FIELD and _addressed_to(change.value, phone_number_id)
        for message in change.value.messages
    ]


def _addressed_to(value: _Value, phone_number_id: str) -> bool:
    return value.metadata is not None and value.metadata.phone_number_id == phone_number_id
