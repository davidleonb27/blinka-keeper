"""`llm.structured` against a scripted client: no network, no key."""

from types import SimpleNamespace
from typing import Any

import pytest
from anthropic.types.beta import (
    BetaServerToolUseBlock,
    BetaTextBlock,
    BetaWebFetchBlock,
    BetaWebFetchToolResultBlock,
    BetaWebFetchToolResultErrorBlock,
)
from pydantic import BaseModel

from custodio import llm


class Answer(BaseModel):
    text: str


def fetch_use(n: int, url: str) -> BetaServerToolUseBlock:
    return BetaServerToolUseBlock(id=f"srv_{n}", input={"url": url}, name="web_fetch", type="server_tool_use")


def fetched(n: int, url: str) -> BetaWebFetchToolResultBlock:
    page = BetaWebFetchBlock.model_construct(type="web_fetch_result", url=url, content=None)
    return BetaWebFetchToolResultBlock(tool_use_id=f"srv_{n}", type="web_fetch_tool_result", content=page)


def fetch_failed(n: int) -> BetaWebFetchToolResultBlock:
    error = BetaWebFetchToolResultErrorBlock(error_code="url_not_accessible", type="web_fetch_tool_result_error")
    return BetaWebFetchToolResultBlock(tool_use_id=f"srv_{n}", type="web_fetch_tool_result", content=error)


def response(stop_reason: str, content: list[Any], parsed: Answer | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason,
        stop_details=None,
        content=content,
        parsed_output=parsed,
        model="claude-opus-5-5",
        usage=SimpleNamespace(
            input_tokens=100, output_tokens=10, cache_read_input_tokens=0, cache_creation_input_tokens=0
        ),
    )


class ScriptedClient:
    def __init__(self, *responses: SimpleNamespace) -> None:
        self.responses = list(responses)
        self.requests: list[dict[str, Any]] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(parse=self.parse))

    def parse(self, **request: Any) -> SimpleNamespace:
        self.requests.append(request)
        return self.responses.pop(0)


@pytest.fixture
def scripted(monkeypatch: pytest.MonkeyPatch) -> Any:
    def install(*responses: SimpleNamespace) -> ScriptedClient:
        fake = ScriptedClient(*responses)
        monkeypatch.setattr(llm, "client", lambda: fake)
        return fake

    return install


def ask() -> llm.LLMResult[Answer]:
    return llm.structured(model="claude-opus-5-5", system="s", content="lee el sitio", schema=Answer)


def test_a_finished_turn_is_one_request_and_reads_no_urls(scripted: Any) -> None:
    fake = scripted(response("end_turn", [BetaTextBlock(text='{"text":"ok"}', type="text")], Answer(text="ok")))

    result = ask()

    assert result.value == Answer(text="ok")
    assert result.fetched_urls == ()
    assert len(fake.requests) == 1


def test_a_paused_server_tool_turn_is_continued_until_it_ends(scripted: Any) -> None:
    first = [fetch_use(1, "https://a.co/"), fetched(1, "https://a.co/")]
    second = [fetch_use(2, "https://a.co/precios"), fetched(2, "https://a.co/precios")]
    last = [BetaTextBlock(text='{"text":"ok"}', type="text")]
    fake = scripted(
        response("pause_turn", first), response("pause_turn", second), response("end_turn", last, Answer(text="ok"))
    )

    result = ask()

    assert result.value == Answer(text="ok")
    assert len(fake.requests) == 3
    assert fake.requests[0]["messages"] == [{"role": "user", "content": "lee el sitio"}]
    continued = fake.requests[2]["messages"]
    assert [m["role"] for m in continued] == ["user", "assistant"]
    assert [block["type"] for block in continued[1]["content"]] == [
        "server_tool_use",
        "web_fetch_tool_result",
        "server_tool_use",
        "web_fetch_tool_result",
    ]
    assert result.input_tokens == 300
    assert result.output_tokens == 30
    assert result.fetched_urls == ("https://a.co/", "https://a.co/precios")


def test_failed_and_repeated_fetches_are_not_reported_as_read(scripted: Any) -> None:
    content = [
        fetched(1, "https://a.co/"),
        fetch_failed(2),
        fetched(3, "https://a.co/"),
        BetaTextBlock(text='{"text":"ok"}', type="text"),
    ]
    scripted(response("end_turn", content, Answer(text="ok")))

    assert ask().fetched_urls == ("https://a.co/",)


def test_a_turn_that_never_ends_is_cut_and_raises(scripted: Any) -> None:
    paused = [response("pause_turn", [fetch_use(n, "https://a.co/")]) for n in range(llm.MAX_CONTINUATIONS + 1)]
    fake = scripted(*paused)

    with pytest.raises(llm.LLMTruncated):
        ask()
    assert len(fake.requests) == llm.MAX_CONTINUATIONS + 1


def test_a_refusal_after_a_pause_still_raises(scripted: Any) -> None:
    scripted(response("pause_turn", [fetch_use(1, "https://a.co/")]), response("refusal", []))

    with pytest.raises(llm.LLMRefused):
        ask()
