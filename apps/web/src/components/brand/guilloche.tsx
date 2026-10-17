"use client";

import { useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

const MAX_PIXEL_RATIO = 2;
const CURVE_STEPS = 2400;
const WAVE_LINES = 16;
const WAVE_STEP_PX = 4;
// Hypotrochoid parameters [R, r, d, alpha], tuned by eye in the prototype.
const ROSETTES: [number, number, number, number][] = [
  [11, 3, 6.2, 0.22],
  [11, 3, 4.6, 0.16],
  [13, 5, 7.4, 0.12],
];

function drawRosette(ctx: CanvasRenderingContext2D, cx: number, cy: number, scale: number, [R, r, d, alpha]: (typeof ROSETTES)[number]) {
  ctx.globalAlpha = alpha;
  ctx.beginPath();
  const turns = Math.PI * 2 * r;
  for (let k = 0; k <= CURVE_STEPS; k++) {
    const t = (turns * k) / CURVE_STEPS;
    const x = cx + ((R - r) * Math.cos(t) + d * Math.cos(((R - r) / r) * t)) * scale;
    const y = cy + ((R - r) * Math.sin(t) - d * Math.sin(((R - r) / r) * t)) * scale;
    if (k === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
}

function drawWaves(ctx: CanvasRenderingContext2D, width: number, height: number) {
  ctx.globalAlpha = 0.1;
  for (let line = 0; line < WAVE_LINES; line++) {
    ctx.beginPath();
    for (let x = 0; x <= width; x += WAVE_STEP_PX) {
      const y = height - 56 + line * 3 + 7 * Math.sin(x * 0.028 + line * 0.42);
      if (x === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.stroke();
  }
}

function paint(canvas: HTMLCanvasElement) {
  const { width, height } = canvas.getBoundingClientRect();
  const ctx = canvas.getContext("2d");
  if (!width || !ctx) return;
  const ratio = Math.min(MAX_PIXEL_RATIO, window.devicePixelRatio || 1);
  canvas.width = width * ratio;
  canvas.height = height * ratio;
  ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
  ctx.clearRect(0, 0, width, height);
  ctx.strokeStyle = getComputedStyle(canvas).getPropertyValue("--brand").trim();
  ctx.lineWidth = 0.7;
  const scale = Math.min(height, 360) * 0.034;
  ROSETTES.forEach((rosette) => drawRosette(ctx, width * 0.84, height * 0.42, scale, rosette));
  drawWaves(ctx, width, height);
  ctx.globalAlpha = 1;
}

/** Security-print background for the figures that carry trust. Purely decorative. */
export function Guilloche({ className }: { className?: string }) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const repaint = () => paint(canvas);
    repaint();
    const resize = new ResizeObserver(repaint);
    resize.observe(canvas);
    const theme = new MutationObserver(repaint);
    theme.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return () => {
      resize.disconnect();
      theme.disconnect();
    };
  }, []);

  return <canvas ref={ref} aria-hidden className={cn("pointer-events-none absolute inset-0 size-full", className)} />;
}
