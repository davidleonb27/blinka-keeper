import json

import httpx
import pytest

from custodio.services.invoice_service import MAX_DOCUMENT_BYTES
from custodio.whatsapp.errors import GraphUnavailable, MediaProblem, MediaRejected
from custodio.whatsapp.graph import HttpGraph

from .conftest import CONFIG
from .doubles import ACCESS_TOKEN, PHONE_NUMBER_ID

MEDIA_ID = "1003383421387256"
FILE_URL = "https://lookaside.fbsbx.com/whatsapp_business/attachments/?mid=1003383421387256"


def _graph(handler: httpx.MockTransport) -> HttpGraph:
    return HttpGraph(CONFIG, transport=handler)


def _media_api(
    *, mime_type: str = "image/jpeg", file_size: int = 12, url: str = FILE_URL, content: bytes = b"factura-foto"
) -> tuple[httpx.MockTransport, list[httpx.Request]]:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.host == "graph.facebook.com":
            return httpx.Response(
                200, json={"url": url, "mime_type": mime_type, "file_size": file_size, "id": MEDIA_ID}
            )
        return httpx.Response(200, content=content)

    return httpx.MockTransport(handle), seen


def test_a_file_is_fetched_with_the_access_token_in_two_steps() -> None:
    transport, seen = _media_api()

    media = _graph(transport).fetch_media(MEDIA_ID, timeout=5)

    assert media.data == b"factura-foto"
    assert media.media_type == "image/jpeg"
    assert [str(r.url) for r in seen] == [f"https://graph.facebook.com/v23.0/{MEDIA_ID}", FILE_URL]
    assert all(r.headers["Authorization"] == f"Bearer {ACCESS_TOKEN}" for r in seen)


def test_a_type_custodio_does_not_read_is_refused_before_the_download() -> None:
    transport, seen = _media_api(mime_type="audio/ogg; codecs=opus")

    with pytest.raises(MediaRejected) as refused:
        _graph(transport).fetch_media(MEDIA_ID, timeout=5)

    assert refused.value.problem is MediaProblem.MEDIA_TYPE
    assert len(seen) == 1


def test_a_file_declared_too_large_is_refused_before_the_download() -> None:
    transport, seen = _media_api(file_size=MAX_DOCUMENT_BYTES + 1)

    with pytest.raises(MediaRejected) as refused:
        _graph(transport).fetch_media(MEDIA_ID, timeout=5)

    assert refused.value.problem is MediaProblem.TOO_LARGE
    assert len(seen) == 1


def test_a_file_that_turns_out_larger_than_declared_is_cut_off() -> None:
    transport, _ = _media_api(file_size=10, content=b"x" * (MAX_DOCUMENT_BYTES + 1))

    with pytest.raises(MediaRejected) as refused:
        _graph(transport).fetch_media(MEDIA_ID, timeout=5)

    assert refused.value.problem is MediaProblem.TOO_LARGE


def test_the_token_never_travels_over_plain_http() -> None:
    transport, seen = _media_api(url="http://lookaside.fbsbx.com/file")

    with pytest.raises(GraphUnavailable):
        _graph(transport).fetch_media(MEDIA_ID, timeout=5)

    assert len(seen) == 1


def test_a_media_id_that_is_not_numeric_is_never_put_in_a_path() -> None:
    transport, seen = _media_api()

    with pytest.raises(GraphUnavailable):
        _graph(transport).fetch_media("../me/accounts", timeout=5)

    assert seen == []


def test_a_reply_is_a_text_message_to_the_sender() -> None:
    seen: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"messages": [{"id": "wamid.out"}]})

    _graph(httpx.MockTransport(handle)).send_text("573001234567", "Recibida")

    [request] = seen
    assert str(request.url) == f"https://graph.facebook.com/v23.0/{PHONE_NUMBER_ID}/messages"
    assert json.loads(request.content) == {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": "573001234567",
        "type": "text",
        "text": {"preview_url": False, "body": "Recibida"},
    }


def test_an_error_from_meta_is_typed_and_never_carries_the_token(caplog: pytest.LogCaptureFixture) -> None:
    def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": f"bad token {ACCESS_TOKEN}"}})

    with pytest.raises(GraphUnavailable) as failed:
        _graph(httpx.MockTransport(handle)).send_text("573001234567", "Recibida")

    assert ACCESS_TOKEN not in str(failed.value)
    assert ACCESS_TOKEN not in caplog.text


def test_a_network_failure_is_typed() -> None:
    def handle(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("down", request=request)

    with pytest.raises(GraphUnavailable):
        _graph(httpx.MockTransport(handle)).fetch_media(MEDIA_ID, timeout=5)
