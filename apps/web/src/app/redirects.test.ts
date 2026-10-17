import { describe, expect, it } from "vitest";
import nextConfig from "../../next.config";

describe("redirects", () => {
  it("sends the firewall's /acta/{id} link to the acta drawer", async () => {
    const redirects = (await nextConfig.redirects?.()) ?? [];

    expect(redirects).toContainEqual({ source: "/acta/:id", destination: "/panel?acta=:id", permanent: false });
  });
});
