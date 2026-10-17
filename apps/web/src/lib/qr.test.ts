import { describe, expect, it } from "vitest";
import { encodeQr, QrTooLong } from "./qr";

function finderAt(modules: boolean[][], x: number, y: number): boolean {
  const ring = [0, 6].every((edge) => [0, 1, 2, 3, 4, 5, 6].every((i) => modules[y + edge][x + i] && modules[y + i][x + edge]));
  const core = [2, 3, 4].every((dy) => [2, 3, 4].every((dx) => modules[y + dy][x + dx]));
  const gap = [1, 2, 3, 4, 5].every((i) => !modules[y + 1][x + i] && !modules[y + 5][x + i]);
  return ring && core && gap;
}

describe("encodeQr", () => {
  it("picks the smallest version that holds the text", () => {
    expect(encodeQr("https://x.co").size).toBe(21);
    expect(encodeQr("https://x.co/reto").size).toBe(25);
    expect(encodeQr("x".repeat(30)).size).toBe(29);
  });

  it("draws the three finder patterns a camera looks for", () => {
    const { modules, size } = encodeQr("https://custodio.example.com/reto");
    expect(finderAt(modules, 0, 0)).toBe(true);
    expect(finderAt(modules, size - 7, 0)).toBe(true);
    expect(finderAt(modules, 0, size - 7)).toBe(true);
  });

  it("always draws the dark module next to the bottom-left finder", () => {
    const { modules, size } = encodeQr("https://custodio.example.com/reto");
    expect(modules[size - 8][8]).toBe(true);
  });

  it("refuses text longer than the largest supported version", () => {
    expect(() => encodeQr("x".repeat(400))).toThrow(QrTooLong);
  });
});
