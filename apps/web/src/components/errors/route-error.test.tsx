import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { RouteError } from "./route-error";

describe("RouteError", () => {
  it("explains that nothing was paid and offers a retry and a way back", async () => {
    const reset = vi.fn();
    render(<RouteError error={Object.assign(new Error("boom"), { digest: "abc123" })} reset={reset} />);

    expect(screen.getByRole("alert")).toHaveTextContent("No se hizo ningún pago ni cambio");
    expect(screen.getByText("Código: abc123")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Ir al panel" })).toHaveAttribute("href", "/panel");
    await userEvent.click(screen.getByRole("button", { name: /Reintentar/ }));
    expect(reset).toHaveBeenCalledOnce();
  });
});
