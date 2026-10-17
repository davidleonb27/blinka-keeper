/**
 * QR Code encoder (ISO/IEC 18004), byte mode at error correction level M, versions 1 to 10: enough for any URL a
 * phone camera has to read from a projector. Written here instead of adding a dependency for one screen.
 */

export class QrTooLong extends Error {
  constructor(length: number) {
    super(`El texto (${length} bytes) no cabe en un código QR de versión ${MAX_VERSION}.`);
    this.name = "QrTooLong";
  }
}

export interface QrCode {
  size: number;
  /** modules[y][x]: true is a dark module. */
  modules: boolean[][];
}

const MAX_VERSION = 10;
const BYTE_MODE = 0b0100;
const LEVEL_M_FORMAT = 0b00;
const MASK_COUNT = 8;
const PAD_BYTES = [0xec, 0x11];
const GF_POLY = 0x11d;
const FORMAT_POLY = 0x537;
const FORMAT_XOR = 0x5412;
const VERSION_POLY = 0x1f25;
// Level M, indexed by version (index 0 unused).
const ECC_PER_BLOCK = [0, 10, 16, 26, 18, 24, 16, 18, 22, 22, 26];
const BLOCKS = [0, 1, 1, 1, 2, 2, 4, 4, 4, 5, 5];

export function encodeQr(text: string): QrCode {
  const bytes = Array.from(new TextEncoder().encode(text));
  const version = smallestVersion(bytes.length);
  const codewords = withErrorCorrection(dataCodewords(bytes, version), version);
  return bestMasked(version, codewords);
}

function smallestVersion(length: number): number {
  for (let version = 1; version <= MAX_VERSION; version++) {
    if (4 + countBits(version) + 8 * length <= dataCapacity(version) * 8) return version;
  }
  throw new QrTooLong(length);
}

function countBits(version: number): number {
  return version < 10 ? 8 : 16;
}

function rawModules(version: number): number {
  let result = (16 * version + 128) * version + 64;
  if (version >= 2) {
    const align = Math.floor(version / 7) + 2;
    result -= (25 * align - 10) * align - 55;
    if (version >= 7) result -= 36;
  }
  return result;
}

function dataCapacity(version: number): number {
  return Math.floor(rawModules(version) / 8) - ECC_PER_BLOCK[version] * BLOCKS[version];
}

function dataCodewords(bytes: number[], version: number): number[] {
  const bits: number[] = [];
  const push = (value: number, length: number) => {
    for (let i = length - 1; i >= 0; i--) bits.push((value >>> i) & 1);
  };
  push(BYTE_MODE, 4);
  push(bytes.length, countBits(version));
  bytes.forEach((byte) => push(byte, 8));
  const capacity = dataCapacity(version) * 8;
  push(0, Math.min(4, capacity - bits.length));
  push(0, (8 - (bits.length % 8)) % 8);
  const result: number[] = [];
  for (let i = 0; i < bits.length; i += 8) result.push(bits.slice(i, i + 8).reduce((acc, bit) => (acc << 1) | bit, 0));
  for (let pad = 0; result.length < capacity / 8; pad++) result.push(PAD_BYTES[pad % 2]);
  return result;
}

function gfMultiply(x: number, y: number): number {
  let z = 0;
  for (let i = 7; i >= 0; i--) {
    z = (z << 1) ^ ((z >>> 7) * GF_POLY);
    z ^= ((y >>> i) & 1) * x;
  }
  return z;
}

function rsDivisor(degree: number): number[] {
  const result = new Array<number>(degree).fill(0);
  result[degree - 1] = 1;
  let root = 1;
  for (let i = 0; i < degree; i++) {
    for (let j = 0; j < degree; j++) {
      result[j] = gfMultiply(result[j], root);
      if (j + 1 < degree) result[j] ^= result[j + 1];
    }
    root = gfMultiply(root, 0x02);
  }
  return result;
}

function rsRemainder(data: number[], divisor: number[]): number[] {
  const result = divisor.map(() => 0);
  for (const byte of data) {
    const factor = byte ^ (result.shift() ?? 0);
    result.push(0);
    divisor.forEach((coefficient, i) => (result[i] ^= gfMultiply(coefficient, factor)));
  }
  return result;
}

/** Splits the data into blocks, appends each block's Reed-Solomon codewords and interleaves them. */
function withErrorCorrection(data: number[], version: number): number[] {
  const blockCount = BLOCKS[version];
  const eccLength = ECC_PER_BLOCK[version];
  const raw = Math.floor(rawModules(version) / 8);
  const shortBlocks = blockCount - (raw % blockCount);
  const shortLength = Math.floor(raw / blockCount);
  const divisor = rsDivisor(eccLength);
  const blocks: number[][] = [];
  for (let i = 0, offset = 0; i < blockCount; i++) {
    const length = shortLength - eccLength + (i < shortBlocks ? 0 : 1);
    const block = data.slice(offset, offset + length);
    offset += length;
    const ecc = rsRemainder(block, divisor);
    if (i < shortBlocks) block.push(0);
    blocks.push([...block, ...ecc]);
  }
  const result: number[] = [];
  for (let i = 0; i < blocks[0].length; i++) {
    blocks.forEach((block, j) => {
      if (i !== shortLength - eccLength || j >= shortBlocks) result.push(block[i]);
    });
  }
  return result;
}

class Matrix {
  readonly size: number;
  readonly modules: boolean[][];
  readonly reserved: boolean[][];

  constructor(readonly version: number) {
    this.size = version * 4 + 17;
    this.modules = Array.from({ length: this.size }, () => new Array<boolean>(this.size).fill(false));
    this.reserved = Array.from({ length: this.size }, () => new Array<boolean>(this.size).fill(false));
  }

  setFunction(x: number, y: number, dark: boolean) {
    this.modules[y][x] = dark;
    this.reserved[y][x] = true;
  }

  copy(): Matrix {
    const clone = new Matrix(this.version);
    this.modules.forEach((row, y) => row.forEach((dark, x) => (clone.modules[y][x] = dark)));
    this.reserved.forEach((row, y) => row.forEach((fixed, x) => (clone.reserved[y][x] = fixed)));
    return clone;
  }
}

function drawFunctionPatterns(matrix: Matrix) {
  const { size } = matrix;
  for (let i = 0; i < size; i++) {
    matrix.setFunction(6, i, i % 2 === 0);
    matrix.setFunction(i, 6, i % 2 === 0);
  }
  drawFinder(matrix, 3, 3);
  drawFinder(matrix, size - 4, 3);
  drawFinder(matrix, 3, size - 4);
  const positions = alignmentPositions(matrix.version, size);
  const last = positions.length - 1;
  positions.forEach((x, i) =>
    positions.forEach((y, j) => {
      const nearFinder = (i === 0 && j === 0) || (i === 0 && j === last) || (i === last && j === 0);
      if (!nearFinder) drawAlignment(matrix, x, y);
    }),
  );
  drawFormatBits(matrix, 0);
  drawVersion(matrix);
}

function drawFinder(matrix: Matrix, cx: number, cy: number) {
  for (let dy = -4; dy <= 4; dy++) {
    for (let dx = -4; dx <= 4; dx++) {
      const x = cx + dx;
      const y = cy + dy;
      const ring = Math.max(Math.abs(dx), Math.abs(dy));
      if (x >= 0 && x < matrix.size && y >= 0 && y < matrix.size) matrix.setFunction(x, y, ring !== 2 && ring !== 4);
    }
  }
}

function drawAlignment(matrix: Matrix, cx: number, cy: number) {
  for (let dy = -2; dy <= 2; dy++) {
    for (let dx = -2; dx <= 2; dx++) matrix.setFunction(cx + dx, cy + dy, Math.max(Math.abs(dx), Math.abs(dy)) !== 1);
  }
}

function alignmentPositions(version: number, size: number): number[] {
  if (version === 1) return [];
  const count = Math.floor(version / 7) + 2;
  const step = Math.floor((version * 8 + count * 3 + 5) / (count * 4 - 4)) * 2;
  const result = [6];
  for (let i = 0, position = size - 7; i < count - 1; i++, position -= step) result.splice(1, 0, position);
  return result;
}

function bit(value: number, index: number): boolean {
  return ((value >>> index) & 1) !== 0;
}

function bchBits(data: number, degree: number, poly: number): number {
  let remainder = data;
  for (let i = 0; i < degree; i++) remainder = (remainder << 1) ^ ((remainder >>> (degree - 1)) * poly);
  return (data << degree) | remainder;
}

function drawFormatBits(matrix: Matrix, mask: number) {
  const bits = bchBits((LEVEL_M_FORMAT << 3) | mask, 10, FORMAT_POLY) ^ FORMAT_XOR;
  const { size } = matrix;
  for (let i = 0; i <= 5; i++) matrix.setFunction(8, i, bit(bits, i));
  matrix.setFunction(8, 7, bit(bits, 6));
  matrix.setFunction(8, 8, bit(bits, 7));
  matrix.setFunction(7, 8, bit(bits, 8));
  for (let i = 9; i < 15; i++) matrix.setFunction(14 - i, 8, bit(bits, i));
  for (let i = 0; i < 8; i++) matrix.setFunction(size - 1 - i, 8, bit(bits, i));
  for (let i = 8; i < 15; i++) matrix.setFunction(8, size - 15 + i, bit(bits, i));
  matrix.setFunction(8, size - 8, true);
}

function drawVersion(matrix: Matrix) {
  if (matrix.version < 7) return;
  const bits = bchBits(matrix.version, 12, VERSION_POLY);
  for (let i = 0; i < 18; i++) {
    const a = matrix.size - 11 + (i % 3);
    const b = Math.floor(i / 3);
    matrix.setFunction(a, b, bit(bits, i));
    matrix.setFunction(b, a, bit(bits, i));
  }
}

/** Places the codewords in the zigzag of two-module columns, from the bottom-right corner. */
function drawCodewords(matrix: Matrix, codewords: number[]) {
  const { size } = matrix;
  let index = 0;
  for (let right = size - 1; right >= 1; right -= 2) {
    if (right === 6) right = 5;
    for (let vertical = 0; vertical < size; vertical++) {
      for (let j = 0; j < 2; j++) {
        const x = right - j;
        const upward = ((right + 1) & 2) === 0;
        const y = upward ? size - 1 - vertical : vertical;
        if (matrix.reserved[y][x] || index >= codewords.length * 8) continue;
        matrix.modules[y][x] = bit(codewords[index >>> 3], 7 - (index & 7));
        index++;
      }
    }
  }
}

const MASKS: ((x: number, y: number) => boolean)[] = [
  (x, y) => (x + y) % 2 === 0,
  (_x, y) => y % 2 === 0,
  (x) => x % 3 === 0,
  (x, y) => (x + y) % 3 === 0,
  (x, y) => (Math.floor(x / 3) + Math.floor(y / 2)) % 2 === 0,
  (x, y) => ((x * y) % 2) + ((x * y) % 3) === 0,
  (x, y) => (((x * y) % 2) + ((x * y) % 3)) % 2 === 0,
  (x, y) => (((x + y) % 2) + ((x * y) % 3)) % 2 === 0,
];

function applyMask(matrix: Matrix, mask: number) {
  matrix.modules.forEach((row, y) =>
    row.forEach((dark, x) => {
      if (!matrix.reserved[y][x] && MASKS[mask](x, y)) row[x] = !dark;
    }),
  );
}

/** Scores runs of one color, 2×2 blocks and dark/light balance (spec rules 1, 2 and 4); lower reads better. */
function penalty(modules: boolean[][]): number {
  const size = modules.length;
  let score = 0;
  const runs = (line: boolean[]) => {
    let run = 1;
    for (let i = 1; i <= line.length; i++) {
      if (i < line.length && line[i] === line[i - 1]) run++;
      else {
        if (run >= 5) score += run - 2;
        run = 1;
      }
    }
  };
  modules.forEach(runs);
  modules.forEach((_row, x) => runs(modules.map((row) => row[x])));
  for (let y = 0; y < size - 1; y++) {
    for (let x = 0; x < size - 1; x++) {
      const color = modules[y][x];
      if (color === modules[y][x + 1] && color === modules[y + 1][x] && color === modules[y + 1][x + 1]) score += 3;
    }
  }
  const dark = modules.flat().filter(Boolean).length;
  score += Math.floor(Math.abs((dark * 20) / (size * size) - 10)) * 10;
  return score;
}

function bestMasked(version: number, codewords: number[]): QrCode {
  const base = new Matrix(version);
  drawFunctionPatterns(base);
  drawCodewords(base, codewords);
  let best: Matrix | null = null;
  let bestScore = Infinity;
  for (let mask = 0; mask < MASK_COUNT; mask++) {
    const candidate = base.copy();
    applyMask(candidate, mask);
    drawFormatBits(candidate, mask);
    const score = penalty(candidate.modules);
    if (score < bestScore) [best, bestScore] = [candidate, score];
  }
  const chosen = best ?? base;
  return { size: chosen.size, modules: chosen.modules };
}
