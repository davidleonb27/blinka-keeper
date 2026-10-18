import json

import pytest

from custodio.whatsapp.errors import WebhookPayloadInvalid
from custodio.whatsapp.payload import inbound_messages

from .doubles import PHONE_NUMBER_ID, SENDER, fixture


def _body(name: str) -> bytes:
    return json.dumps(fixture(name)).encode()


def test_a_text_message_reads_its_sender_id_and_body() -> None:
    [message] = inbound_messages(_body("text_message"), PHONE_NUMBER_ID)

    assert message.sender == SENDER
    assert message.type == "text"
    assert message.text is not None and message.text.body == "Hola"
    assert message.media is None


def test_an_image_and_a_document_carry_their_media_reference() -> None:
    [image] = inbound_messages(_body("image_message"), PHONE_NUMBER_ID)
    [document] = inbound_messages(_body("document_message"), PHONE_NUMBER_ID)

    assert image.media is not None and image.media.id == "1003383421387256"
    assert image.media.mime_type == "image/jpeg"
    assert document.media is not None and document.media.filename == "FV-2041.pdf"


def test_statuses_are_not_messages() -> None:
    assert inbound_messages(_body("status_update"), PHONE_NUMBER_ID) == []


def test_a_delivery_for_another_business_number_is_ignored() -> None:
    assert inbound_messages(_body("text_message"), "999999999999999") == []


def test_a_sticker_is_a_message_without_media_custodio_reads() -> None:
    [sticker] = inbound_messages(_body("sticker_message"), PHONE_NUMBER_ID)

    assert sticker.type == "sticker"
    assert sticker.media is None


def test_a_body_that_is_not_a_delivery_is_refused() -> None:
    with pytest.raises(WebhookPayloadInvalid):
        inbound_messages(b"not json", PHONE_NUMBER_ID)
