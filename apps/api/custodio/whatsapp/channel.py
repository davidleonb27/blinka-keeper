"""The configured channel: its settings and the Graph API client. Built once per process from the environment."""

from __future__ import annotations

from dataclasses import dataclass

from custodio.whatsapp.config import WhatsAppConfig, load_config
from custodio.whatsapp.graph import GraphApi, HttpGraph

# Meta waits a few seconds for the 200 and Vercel may stop a Python function once it has answered, so a message is
# processed inside its own request within this budget; a retry Meta sends meanwhile finds the message claimed.
PROCESSING_BUDGET_SECONDS = 45.0


@dataclass(frozen=True)
class WhatsAppChannel:
    config: WhatsAppConfig
    graph: GraphApi
    budget_seconds: float = PROCESSING_BUDGET_SECONDS

    @property
    def shows_card(self) -> bool:
        """The panel offers the channel only when it has a number to send to."""
        return self.config.display_number is not None


def load_channel() -> WhatsAppChannel | None:
    config = load_config()
    return None if config is None else WhatsAppChannel(config=config, graph=HttpGraph(config))
