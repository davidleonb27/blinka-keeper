import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { renderWithApi } from "@/test/render";
import { DevelopersPage } from "./developers-page";

describe("DevelopersPage", () => {
  it("shows the API status from /health and names no out-of-scope provider", async () => {
    renderWithApi(<DevelopersPage />);

    expect(await screen.findByText(/API en línea/)).toBeInTheDocument();
    expect(document.body.textContent).not.toMatch(/gemini|telegram/i);
  });

  it("documents the firewall acta link at /acta/{id}", () => {
    renderWithApi(<DevelopersPage />);

    expect(screen.getByText(/"acta_url": "\/acta\/INT-0042"/)).toBeInTheDocument();
  });
});
