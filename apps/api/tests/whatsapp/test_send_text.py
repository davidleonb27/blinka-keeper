import pytest
from fastapi.testclient import TestClient

from custodio.db.models import WorkspaceRow
from custodio.services.context import Runtime
from custodio.whatsapp import send_text
from custodio.whatsapp.errors import PhoneNotLinked, WhatsAppNotConfigured
from custodio.whatsapp.linking import phones_of
from tests.api.helpers import new_workspace

from .doubles import SENDER, FakeGraph, link_phone


def _workspace(runtime: Runtime, workspace_id: str) -> WorkspaceRow:
    with runtime.database.session() as session:
        row = session.get(WorkspaceRow, workspace_id)
        assert row is not None
        return row


def test_another_lane_can_write_to_a_phone_linked_to_the_workspace(
    client: TestClient, runtime: Runtime, graph: FakeGraph
) -> None:
    workspace = new_workspace(client)
    link_phone(client, workspace)

    with runtime.database.session() as session:
        ctx = runtime.context(session)
        assert [row.phone for row in phones_of(ctx, workspace.id)] == [SENDER]
        send_text(ctx, _workspace(runtime, workspace.id), SENDER, "Tu proveedor corrigió la FV-7011.")

    assert graph.replies_to(SENDER)[-1] == "Tu proveedor corrigió la FV-7011."


def test_a_workspace_never_writes_to_another_workspaces_phone(client: TestClient, runtime: Runtime) -> None:
    owner, stranger = new_workspace(client), new_workspace(client)
    link_phone(client, owner)

    with runtime.database.session() as session, pytest.raises(PhoneNotLinked):
        send_text(runtime.context(session), _workspace(runtime, stranger.id), SENDER, "Hola")


def test_without_the_channel_send_text_says_so(plain_runtime: Runtime) -> None:
    with plain_runtime.database.session() as session, pytest.raises(WhatsAppNotConfigured):
        send_text(plain_runtime.context(session), WorkspaceRow(id="w"), SENDER, "Hola")
