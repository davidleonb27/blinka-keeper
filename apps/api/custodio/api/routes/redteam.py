from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from custodio.api.deps import CurrentWorkspace, ModelCallLimit, RuntimeDep
from custodio.contracts import RedTeamEvent
from custodio.services import redteam_service

router = APIRouter(prefix="/redteam", tags=["redteam"])

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
STREAM_DOC: dict[int | str, dict[str, Any]] = {
    200: {"model": RedTeamEvent, "description": "Server-sent events; each `data:` line is a RedTeamEvent."}
}


class EventStreamResponse(StreamingResponse):
    """Declares its media type so the OpenAPI document puts the event schema under text/event-stream."""

    media_type = "text/event-stream"


class RunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rounds: int = Field(default=6, ge=1, le=redteam_service.MAX_ROUNDS)


@router.post("/runs", dependencies=[ModelCallLimit], response_class=EventStreamResponse, responses=STREAM_DOC)
def start_run(body: RunRequest, runtime: RuntimeDep, workspace: CurrentWorkspace) -> EventStreamResponse:
    events = redteam_service.run(runtime, workspace.id, body.rounds)
    return EventStreamResponse(_server_sent(events), headers=SSE_HEADERS)


def _server_sent(events: Iterator[RedTeamEvent]) -> Iterator[str]:
    for event in events:
        yield f"event: {event.type}\ndata: {event.model_dump_json()}\n\n"
