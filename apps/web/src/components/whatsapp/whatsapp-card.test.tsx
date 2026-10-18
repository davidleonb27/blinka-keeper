import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { WhatsAppStatus } from "@/lib/api/client";
import { useDecisions, useWhatsAppStatus } from "@/lib/api/hooks";
import { createMockClient } from "@/lib/api/mock/mock-client";
import { renderWithApi } from "@/test/render";
import { WhatsAppCard } from "./whatsapp-card";

const FAST_POLL_MS = 20;

/** The panel's decision list next to the card's poll, at test speed. */
function PanelWithFastPoll() {
  useWhatsAppStatus(FAST_POLL_MS);
  const decisions = useDecisions();
  return <p>{decisions.data ? "listo" : "cargando"}</p>;
}

const ON: WhatsAppStatus = { enabled: true, display_number: "15550783881", phones: [], last_received_at: null };
const CODE = {
  code: "K7P2QX",
  expires_at: "2026-10-18T15:10:00Z",
  message: "Vincular K7P2QX",
  link_url: "https://wa.me/15550783881?text=Vincular%20K7P2QX",
  display_number: "15550783881",
};

describe("WhatsAppCard", () => {
  it("stays hidden when the server has no WhatsApp number", async () => {
    const api = createMockClient({ latencyMs: 0 });
    const status = vi.spyOn(api, "getWhatsAppStatus");
    const { container } = renderWithApi(<WhatsAppCard />, api);

    await waitFor(() => expect(status).toHaveBeenCalled());
    expect(container).toBeEmptyDOMElement();
  });

  it("shows a one-time code with its QR and wa.me link", async () => {
    const api = createMockClient({ latencyMs: 0 });
    vi.spyOn(api, "getWhatsAppStatus").mockResolvedValue(ON);
    vi.spyOn(api, "createWhatsAppCode").mockResolvedValue(CODE);
    renderWithApi(<WhatsAppCard />, api);

    await userEvent.click(await screen.findByRole("button", { name: "Ligar mi teléfono" }));

    expect(await screen.findByLabelText("Código de un solo uso")).toHaveTextContent("K7P2QX");
    expect(screen.getByRole("img", { name: `Código QR a ${CODE.link_url}` })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Abrir WhatsApp" })).toHaveAttribute("href", CODE.link_url);
  });

  it("lists linked phones masked and says approvals stay in the app", async () => {
    const api = createMockClient({ latencyMs: 0 });
    const phones = [{ masked: "+57 ••• 4567", linked_at: "2026-10-18T15:00:00Z" }];
    vi.spyOn(api, "getWhatsAppStatus").mockResolvedValue({ ...ON, phones });
    renderWithApi(<WhatsAppCard />, api);

    expect(await screen.findByText("+57 ••• 4567")).toBeInTheDocument();
    expect(screen.getByText(/al \+15550783881/)).toHaveTextContent("Las aprobaciones se hacen sólo aquí, en la app.");
    expect(screen.getByRole("button", { name: "Ligar otro teléfono" })).toBeInTheDocument();
  });

  it("refreshes the panel when an invoice arrives on WhatsApp", async () => {
    const api = createMockClient({ latencyMs: 0 });
    vi.spyOn(api, "getWhatsAppStatus")
      .mockResolvedValueOnce(ON)
      .mockResolvedValue({ ...ON, last_received_at: "2026-10-18T15:01:00Z" });
    const decisions = vi.spyOn(api, "listDecisions");
    renderWithApi(<PanelWithFastPoll />, api);

    await waitFor(() => expect(decisions).toHaveBeenCalledTimes(2));
  });
});
