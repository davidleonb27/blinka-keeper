import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { createMockClient } from "@/lib/api/mock/mock-client";
import { renderWithApi } from "@/test/render";
import { SuppliersPage } from "./suppliers-page";

describe("SuppliersPage", () => {
  it("says so when the visitor is in the demo, not in a company of their own, and points to the set-up", async () => {
    renderWithApi(<SuppliersPage />);

    expect(await screen.findByText(/Estás en la empresa de demostración/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Usar con mi empresa" })).toHaveAttribute("href", "/empezar");
  });

  it("does not warn in a company of its own", async () => {
    const api = createMockClient({ latencyMs: 0 });
    await api.createWorkspace("blank");
    renderWithApi(<SuppliersPage />, api);

    expect(await screen.findByRole("heading", { name: /Registrados/ })).toBeInTheDocument();
    expect(screen.queryByText(/Estás en la empresa de demostración/)).not.toBeInTheDocument();
  });
});
