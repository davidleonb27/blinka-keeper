import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { fetchStarCount } from "@/lib/github";
import { GitHubStars } from "./github-stars";

const answer = (status: number, body: unknown): typeof fetch => async () =>
  new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } });

describe("fetchStarCount", () => {
  it("reads the stargazers count from the public GitHub API", async () => {
    expect(await fetchStarCount(answer(200, { stargazers_count: 1234 }))).toBe(1234);
  });

  it("falls back to no count when GitHub refuses, fails or answers something else", async () => {
    expect(await fetchStarCount(answer(403, { message: "rate limited" }))).toBeNull();
    expect(await fetchStarCount(answer(200, { stargazers_count: "many" }))).toBeNull();
    expect(await fetchStarCount(async () => Promise.reject(new TypeError("offline")))).toBeNull();
  });
});

describe("GitHubStars", () => {
  it("shows the count in Spanish format", () => {
    render(<GitHubStars count={1234} />);

    expect(screen.getByRole("link", { name: /1\.234 estrellas en GitHub/ })).toBeInTheDocument();
  });

  it("still links the repository when the count is unknown, without inventing a number", () => {
    render(<GitHubStars count={null} />);

    const link = screen.getByRole("link", { name: /GitHub/ });
    expect(link).toHaveTextContent("Estrella en GitHub");
    expect(link.textContent).not.toMatch(/\d/);
  });
});
