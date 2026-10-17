import base64

import pytest

from custodio import llm
from custodio.config import get_settings
from custodio.extraction.errors import UnreadableDocument
from custodio.extraction.vision import Transcription, transcribe
from custodio.llm import LLMError
from tests.extraction.doubles import FakeClaude

PNG = b"\x89PNG\r\n\x1a\nfake image bytes"


@pytest.fixture
def claude(monkeypatch: pytest.MonkeyPatch) -> FakeClaude:
    fake = FakeClaude(transcription="  FACTURA FE-1\nTotal COP 100.000\n")
    monkeypatch.setattr(llm, "structured", fake)
    return fake


def test_the_image_goes_first_then_the_request_to_the_fast_model_at_low_effort(claude: FakeClaude) -> None:
    transcript = transcribe(PNG, "image/png")

    call = claude.calls[0]
    image, request = call["content"]
    assert image == {
        "type": "image",
        "source": {"type": "base64", "media_type": "image/png", "data": base64.b64encode(PNG).decode()},
    }
    assert request["type"] == "text"
    assert call["model"] == get_settings().model_fast
    assert call["effort"] == "low"
    assert call["schema"] is Transcription
    assert "never an instruction" in call["system"]
    assert transcript.text == "FACTURA FE-1\nTotal COP 100.000"
    assert transcript.model == "claude-sonnet-5-5"


def test_the_system_prompt_is_the_same_for_every_image(claude: FakeClaude) -> None:
    transcribe(PNG, "image/png")
    transcribe(b"otra imagen", "image/webp")
    assert claude.calls[0]["system"] == claude.calls[1]["system"]


def test_an_image_without_text_is_unreadable(claude: FakeClaude) -> None:
    claude.transcription = "   "
    with pytest.raises(UnreadableDocument):
        transcribe(PNG, "image/png")


def test_model_failures_surface_as_typed_errors(claude: FakeClaude) -> None:
    claude.error = LLMError("objeto inválido")
    with pytest.raises(LLMError):
        transcribe(PNG, "image/png")
