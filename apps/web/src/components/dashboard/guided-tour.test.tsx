import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it } from "vitest";
import { markTourStep } from "@/lib/tour";
import { GuidedTour } from "./guided-tour";

describe("GuidedTour", () => {
  beforeEach(() => window.localStorage.clear());

  it("links each of the five steps to its section and checks a step once it happens", () => {
    render(<GuidedTour decided firstActa="F01" />);

    const steps = within(screen.getByRole("list")).getAllByRole("link");
    expect(steps.map((link) => link.getAttribute("href"))).toEqual([
      "/panel#facturas-por-decidir",
      "/panel?acta=F01",
      "/reglas",
      "/conciliacion",
      "/registro",
      "/reto",
    ]);
    expect(screen.getByText("1 de 5 hechos.")).toBeInTheDocument();
    expect(steps[0]).toHaveTextContent(/hecho/);

    act(() => markTourStep("verify"));

    expect(screen.getByText("2 de 5 hechos.")).toBeInTheDocument();
  });

  it("goes away when dismissed and stays away", async () => {
    const { unmount } = render(<GuidedTour decided={false} firstActa={null} />);

    await userEvent.click(screen.getByRole("button", { name: "Ocultar el recorrido" }));

    expect(screen.queryByRole("heading", { name: /Recorrido/ })).not.toBeInTheDocument();
    unmount();
    render(<GuidedTour decided={false} firstActa={null} />);
    expect(screen.queryByRole("heading", { name: /Recorrido/ })).not.toBeInTheDocument();
  });
});
