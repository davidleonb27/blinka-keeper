import { readdirSync, readFileSync, statSync } from "node:fs";
import path from "node:path";
import { describe, expect, it } from "vitest";

// One typography for the whole web, Blinka's (docs/design-system/blinka): Inter as "Blinka Inter" for the interface and
// titles, Geist Mono for figures, codes and ids. Both are self-hosted woff2 files loaded in layout.tsx; the tokens live
// in globals.css; nothing else names a font.
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
  it("self-hosts Blinka Inter and Geist Mono with next/font/local", () => {
    const layout = read("app/layout.tsx");

    expect(layout).toMatch(/import localFont from "next\/font\/local";/);
    expect(layout).toMatch(/src: "\.\/fonts\/blinka-inter-latin-variable\.woff2"[^}]*variable: "--font-sans"/s);
    expect(layout).toMatch(/src: "\.\/fonts\/geist-mono-latin-variable\.woff2"[^}]*variable: "--font-mono"/s);
    expect(layout).not.toMatch(/next\/font\/google/);
  });

  it("keeps the font tokens in one place, with Geist Mono for figures and code", () => {
    const css = read("app/globals.css");

    expect(css.match(/--font-sans:/g)).toHaveLength(1);
    expect(css.match(/--font-mono:/g)).toHaveLength(1);
    expect(css).toContain('--font-sans: "Blinka Inter", ui-sans-serif, system-ui, sans-serif;');
    expect(css).toContain('--font-mono: "Geist Mono", ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;');
  });

  it("leaves no serif, Google font or other font alias anywhere in the web", () => {
    const offenders = sourceFiles(SRC).filter((file) =>
      /Source[ _]Serif|Georgia|Bricolage|next\/font\/google|--font-geist|--font-bricolage|--font-display|--font-heading|\bfont-display\b|\bfont-heading\b/.test(
        readFileSync(file, "utf8"),
      ),
    );

    expect(offenders.map((file) => path.relative(SRC, file))).toEqual([]);
  });
});
