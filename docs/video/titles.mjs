// Renders title cards and overlays from titles.html, frame by frame. Usage: node titles.mjs jobs.json
// Each job: { scene, w, h, d, data, out }. Animated jobs (d > 0) become H.264 at 30 fps; d = 0 gives one transparent PNG.
import { spawn } from "node:child_process";
import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";
import { chromium } from "playwright";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const FPS = 30;
const jobs = JSON.parse(readFileSync(process.argv[2], "utf8"));
const browser = await chromium.launch();

async function render(job) {
  const page = await browser.newPage({ viewport: { width: job.w, height: job.h } });
  const query = new URLSearchParams({ scene: job.scene, w: job.w, h: job.h, d: job.d, dur: job.dur ?? job.d, data: JSON.stringify(job.data ?? {}) });
  await page.goto(`${pathToFileURL(path.join(HERE, "titles.html"))}?${query}`);
  await page.evaluate(() => window.ready);
  if (!job.d) {
    await page.evaluate((t) => window.frame(t), job.t ?? 0);
    await page.screenshot({ path: job.out, omitBackground: true });
  } else {
    const ffmpeg = spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(FPS), "-i", "-",
      "-c:v", "libx264", "-preset", "medium", "-crf", "14", "-pix_fmt", "yuv420p", job.out], { stdio: ["pipe", "inherit", "inherit"] });
    const frames = Math.round(job.d * FPS);
    for (let i = 0; i < frames; i++) {
      await page.evaluate((t) => window.frame(t), i / FPS);
      const png = await page.screenshot({ type: "png" });
      if (!ffmpeg.stdin.write(png)) await new Promise((r) => ffmpeg.stdin.once("drain", r));
    }
    ffmpeg.stdin.end();
    await new Promise((r) => ffmpeg.on("close", r));
  }
  await page.close();
  console.log("título", job.scene, path.basename(job.out));
}

const queue = [...jobs];
await Promise.all(Array.from({ length: 3 }, async () => { while (queue.length) await render(queue.shift()); }));
await browser.close();
