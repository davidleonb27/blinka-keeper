/**
 * The hero's line art: a twisted ribbon of thin waves, computed (not drawn by hand) so it stays light and identical on
 * the server and in the browser. Every coordinate is rounded to one decimal, so the markup never differs between them.
 */
const WIDTH = 640;
const HEIGHT = 560;
const LINES = 34;
const STEP = 16;
const WAVELENGTH = 150;
const TWIST = 0.11;

function y(x: number, line: number): number {
  const centre = HEIGHT * 0.62 - x * 0.42;
  const amplitude = 70 + 60 * Math.cos(line * TWIST * 1.7);
  return centre + amplitude * Math.sin(x / WAVELENGTH + line * TWIST) + (line - LINES / 2) * 3.2;
}

function wavePath(line: number): string {
  const points: string[] = [];
  for (let x = 0; x <= WIDTH; x += STEP) points.push(`${x === 0 ? "M" : "L"}${x} ${y(x, line).toFixed(1)}`);
  return points.join(" ");
}

const PATHS = Array.from({ length: LINES }, (_, line) => wavePath(line));

export function WaveArt({ className }: { className?: string }) {
  return (
    <svg aria-hidden viewBox={`0 0 ${WIDTH} ${HEIGHT}`} fill="none" preserveAspectRatio="xMidYMid meet" className={className}>
      {PATHS.map((d, line) => (
        <path
          key={line}
          d={d}
          stroke={line % 5 === 0 ? "var(--brand)" : "var(--ink)"}
          strokeOpacity={line % 5 === 0 ? 0.7 : 0.16}
          strokeWidth={line % 5 === 0 ? 1.2 : 0.8}
          vectorEffect="non-scaling-stroke"
        />
      ))}
    </svg>
  );
}
