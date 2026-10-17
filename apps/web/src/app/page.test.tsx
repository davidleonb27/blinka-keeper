import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { RAIL_PITCH } from "@/lib/presentation";
import { renderWithApi } from "@/test/render";
import HomePage from "./page";

describe("HomePage", () => {
  it("says Custodio decides and the rail pays", () => {
    renderWithApi(<HomePage />);

    expect(screen.getByText(RAIL_PITCH)).toBeInTheDocument();
  });
});
