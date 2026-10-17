import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

// One typography for the whole web: Inter for the interface, Source Serif 4 for large titles, the system monospace
// for code. The pair lives in layout.tsx (loading) and globals.css (tokens); nothing else names a font.
const SRC = path.resolve(__dirname, "..");
const read = (relative: string) => readFileSync(path.join(SRC, relative), "utf8");

function sourceFiles(dir: string): string[] {
  return readdirSync(dir).flatMap((name) => {
    const full = path.join(dir, name);
    if (statSync(full).isDirectory()) return sourceFiles(full);
    return /\.(tsx?|css)$/.test(name) && !/\.test\.tsx?$/.test(name) ? [full] : [];
  });
}

describe("typography", () => {
  it("loads exactly Inter and Source Serif 4 from next/font/google", () => {
    const layout = read("app/layout.tsx");

    expect(layout).toMatch(/import \{ Inter, Source_Serif_4 \} from "next\/font\/google";/);
    expect(layout).toMatch(/Inter\(\{[^}]*subsets: \["latin"\][^}]*display: "swap"[^}]*variable: "--font-sans"/);
    expect(layout).toMatch(
      /Source_Serif_4\(\{[^}]*subsets: \["latin"\][^}]*display: "swap"[^}]*variable: "--font-serif"[^}]*preload: true/,
    );
  });

  it("keeps the font tokens in one place, with the system monospace for code", () => {
    const css = read("app/globals.css");

    expect(css.match(/--font-sans:/g)).toHaveLength(1);
    expect(css.match(/--font-serif:/g)).toHaveLength(1);
    expect(css).toContain('--font-mono: ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;');
  });

  it("leaves no other font or font alias anywhere in the web", () => {
    const offenders = sourceFiles(SRC).filter((file) =>
      /Geist|Bricolage|--font-geist|--font-bricolage|--font-display|--font-heading|\bfont-display\b|\bfont-heading\b/.test(
        readFileSync(file, "utf8"),
      ),
    );

    expect(offenders.map((file) => path.relative(SRC, file))).toEqual([]);
  });
});
