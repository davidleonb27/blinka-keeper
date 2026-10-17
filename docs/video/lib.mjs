// Shared helpers for the pitch recordings: a CDP screencast recorder, a visible cursor, and smooth zoom inside the page.
import { mkdirSync, writeFileSync } from "node:fs";
import path from "node:path";

export const VIEWPORT = { width: 1920, height: 1080 };
export const SCALE = 1;
// The pitch rules ask for the browser at 125 %. The screencast captures CSS pixels, so the page renders at 1920x1080
// with `zoom: 1.25` on <html>: the same layout as 1536x864 at 1.25, captured at full resolution.
export const ZOOM = 1.25;

const CURSOR_SCRIPT = `
(() => {
  const Z = ${ZOOM};
  const zoom = () => { const r = document.documentElement; if (r && r.style.zoom !== String(Z)) r.style.zoom = String(Z); };
  const keepZoom = () => {
    zoom();
    new MutationObserver(zoom).observe(document.documentElement, { attributes: true, attributeFilter: ["style"] });
  };
  // Init scripts can run before <html> exists.
  if (document.documentElement) keepZoom();
  else new MutationObserver((_, o) => { if (document.documentElement) { o.disconnect(); keepZoom(); } }).observe(document, { childList: true });
  const install = () => {
    if (document.getElementById("pitch-cursor")) return;
    const c = document.createElement("div");
    c.id = "pitch-cursor";
    c.innerHTML = '<svg width="28" height="28" viewBox="0 0 28 28"><path d="M5 3 L5 22 L10 17.5 L13.5 25 L17 23.5 L13.6 16 L20.5 16 Z" fill="#0b1618" stroke="#fff" stroke-width="1.8" stroke-linejoin="round"/></svg>';
    Object.assign(c.style, { position: "fixed", left: "0", top: "0", width: "28px", height: "28px", zIndex: 2147483647,
      pointerEvents: "none", transform: "translate(var(--x, -100px), var(--y, -100px))", filter: "drop-shadow(0 2px 3px rgb(0 0 0 / .25))" });
    document.documentElement.appendChild(c);
    const r = document.createElement("div");
    r.id = "pitch-ripple";
    Object.assign(r.style, { position: "fixed", left: "-22px", top: "-22px", width: "44px", height: "44px", borderRadius: "50%",
      border: "3px solid #08707e", zIndex: 2147483646, pointerEvents: "none", opacity: "0" });
    document.documentElement.appendChild(r);
    const last = sessionStorage.getItem("pitch-cursor");
    if (last) { const [x, y] = JSON.parse(last); c.style.setProperty("--x", x / Z + "px"); c.style.setProperty("--y", y / Z + "px"); }
  };
  window.__pitchMove = (x, y) => {
    install();
    const c = document.getElementById("pitch-cursor");
    c.style.setProperty("--x", x / Z + "px"); c.style.setProperty("--y", y / Z + "px");
    sessionStorage.setItem("pitch-cursor", JSON.stringify([x, y]));
  };
  window.__pitchClick = (x, y) => {
    install();
    const r = document.getElementById("pitch-ripple");
    r.animate([{ transform: \`translate(\${x / Z}px, \${y / Z}px) scale(.4)\`, opacity: .9 }, { transform: \`translate(\${x / Z}px, \${y / Z}px) scale(1.4)\`, opacity: 0 }],
      { duration: 520, easing: "ease-out" });
  };
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", install); else install();
})();`;

export async function preparePage(context) {
  await context.addInitScript(CURSOR_SCRIPT);
  const page = await context.newPage();
  page.__cursor = { x: VIEWPORT.width / 2, y: VIEWPORT.height / 2 };
  return page;
}

/** Records device-pixel JPEG frames with their timestamps; `stop()` writes a CFR 30 fps H.264 file and the marks. */
export async function startRecording(page, outDir, take) {
  const dir = path.join(outDir, "frames", take);
  mkdirSync(dir, { recursive: true });
  const cdp = await page.context().newCDPSession(page);
  const frames = [];
  const marks = [];
  const t0 = Date.now() / 1000;
  cdp.on("Page.screencastFrame", async ({ data, metadata, sessionId }) => {
    const file = path.join(dir, `${String(frames.length).padStart(6, "0")}.jpg`);
    writeFileSync(file, Buffer.from(data, "base64"));
    frames.push({ file, t: metadata.timestamp - t0 });
    await cdp.send("Page.screencastFrameAck", { sessionId }).catch(() => {});
  });
  await cdp.send("Page.startScreencast", { format: "jpeg", quality: 92, maxWidth: 1920, maxHeight: 1080, everyNthFrame: 1 });
  return {
    mark(name) { marks.push({ name, t: Date.now() / 1000 - t0 }); console.log(`[${take}] ${name} @ ${(Date.now() / 1000 - t0).toFixed(2)}s`); },
    async stop() {
      await page.waitForTimeout(400);
      await cdp.send("Page.stopScreencast").catch(() => {});
      const end = Date.now() / 1000 - t0;
      if (frames.length === 0) return { list: null, frames: 0, end };
      const lines = [];
      frames.forEach((f, i) => {
        const next = i + 1 < frames.length ? frames[i + 1].t : end;
        lines.push(`file '${f.file}'`, `duration ${Math.max(next - f.t, 0.001).toFixed(4)}`);
      });
      lines.push(`file '${frames.at(-1).file}'`);
      writeFileSync(path.join(dir, "list.txt"), lines.join("\n"));
      writeFileSync(path.join(outDir, `${take}.marks.json`), JSON.stringify({ start: frames[0]?.t ?? 0, end, marks }, null, 2));
      return { list: path.join(dir, "list.txt"), frames: frames.length, end };
    },
  };
}

const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

export async function moveTo(page, x, y, ms = 700) {
  const from = { ...page.__cursor };
  const steps = Math.max(8, Math.round(ms / 16));
  for (let i = 1; i <= steps; i++) {
    const k = ease(i / steps);
    const px = from.x + (x - from.x) * k;
    const py = from.y + (y - from.y) * k;
    await page.mouse.move(px, py);
    await page.evaluate(([a, b]) => window.__pitchMove?.(a, b), [px, py]);
    await page.waitForTimeout(16);
  }
  page.__cursor = { x, y };
}

export async function moveToLocator(page, locator, ms = 700) {
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  await moveTo(page, box.x + box.width / 2, box.y + box.height / 2, ms);
  return box;
}

export async function clickLocator(page, locator, ms = 700) {
  if (page.__camera) return locator.click(); // zoomed: the cursor is hidden, so click without moving it
  await moveToLocator(page, locator, ms);
  await page.waitForTimeout(180);
  await page.evaluate(([a, b]) => window.__pitchClick?.(a, b), [page.__cursor.x, page.__cursor.y]);
  await page.mouse.down();
  await page.waitForTimeout(70);
  await page.mouse.up();
}

/** Re-shows the cursor after a navigation, where the overlay starts over. */
export async function restoreCursor(page) {
  await page.evaluate(([a, b]) => window.__pitchMove?.(a, b), [page.__cursor.x, page.__cursor.y]);
}

/** Smoothly zooms the page around a box (viewport px, as measured now); `zoomOut` returns to 1. While zoomed the
 * cursor fades out: its overlay lives inside the transformed page, so it would no longer sit where the mouse is. */
export async function zoomTo(page, box, scale = 1.6, ms = 1100) {
  const cam = page.__camera;
  // A box measured on an already zoomed page is mapped back to the untransformed page first.
  const b = cam ? { x: (box.x - cam.tx) / cam.s, y: (box.y - cam.ty) / cam.s, width: box.width / cam.s, height: box.height / cam.s } : box;
  const cx = b.x + b.width / 2;
  const cy = b.y + b.height / 2;
  page.__camera = await page.evaluate(
    ([cx, cy, s, ms, w, h, z]) => {
      const root = document.documentElement;
      // Translate so the box center lands at the viewport center, clamped so no edge leaves the frame.
      const tx = Math.min(0, Math.max(w - w * s, w / 2 - cx * s));
      const ty = Math.min(0, Math.max(h - h * s, h / 2 - cy * s));
      root.style.transition = `transform ${ms}ms cubic-bezier(.65,0,.35,1)`;
      // Inside the zoomed root a translate is multiplied by the zoom. The origin is the root box, so on a scrolled page
      // it sits above the viewport: put the origin at the viewport top, in the root's unzoomed units.
      root.style.transformOrigin = `0 ${scrollY / z}px`;
      root.style.transform = `translate(${tx / z}px, ${ty / z}px) scale(${s})`;
      const cursor = document.getElementById("pitch-cursor");
      if (cursor) { cursor.style.transition = "opacity 200ms"; cursor.style.opacity = "0"; }
      return { tx, ty, s };
    },
    [cx, cy, scale, ms, VIEWPORT.width, VIEWPORT.height, ZOOM],
  );
  await page.waitForTimeout(ms + 50);
}

export async function zoomOut(page, ms = 900) {
  await page.evaluate((ms) => {
    const root = document.documentElement;
    root.style.transition = `transform ${ms}ms cubic-bezier(.65,0,.35,1)`;
    root.style.transform = "none";
    const cursor = document.getElementById("pitch-cursor");
    if (cursor) setTimeout(() => { cursor.style.opacity = "1"; }, ms);
  }, ms);
  page.__camera = null;
  await page.waitForTimeout(ms + 50);
}

/** Scrolls the window with an eased animation, so the recording shows motion instead of a jump. */
export async function smoothScroll(page, y, ms = 800) {
  await page.evaluate(
    ([target, ms]) =>
      new Promise((done) => {
        const from = scrollY;
        const start = performance.now();
        const step = (now) => {
          const t = Math.min(1, (now - start) / ms);
          const k = t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
          scrollTo(0, from + (target - from) * k);
          if (t < 1) requestAnimationFrame(step);
          else done();
        };
        requestAnimationFrame(step);
      }),
    [y, ms],
  );
}

/** Scrolls a scrollable ancestor (the acta drawer) so `locator` sits near the top, with the same easing. */
export async function smoothScrollInto(page, locator, offset = 120, ms = 800) {
  await locator.evaluate(
    (el, [offset, ms]) =>
      new Promise((done) => {
        let box = el.parentElement;
        while (box && !(box.scrollHeight > box.clientHeight && /(auto|scroll)/.test(getComputedStyle(box).overflowY))) {
          box = box.parentElement;
        }
        if (!box) return done();
        const from = box.scrollTop;
        const target = from + el.getBoundingClientRect().top - box.getBoundingClientRect().top - offset;
        const start = performance.now();
        const step = (now) => {
          const t = Math.min(1, (now - start) / ms);
          const k = t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
          box.scrollTop = from + (target - from) * k;
          if (t < 1) requestAnimationFrame(step);
          else done();
        };
        requestAnimationFrame(step);
      }),
    [offset, ms],
  );
}

/** Union of several boxes, for zooming on a group of cards. */
export function union(...boxes) {
  const x = Math.min(...boxes.map((b) => b.x));
  const y = Math.min(...boxes.map((b) => b.y));
  const right = Math.max(...boxes.map((b) => b.x + b.width));
  const bottom = Math.max(...boxes.map((b) => b.y + b.height));
  return { x, y, width: right - x, height: bottom - y };
}

// ── «Mouse real» mode: human pace, curved paths, a pause on hover before each click, key-by-key typing. ──

// Deterministic jitter, so a take re-recorded with the same script moves the same way.
let seed = 7;
function jitter() {
  seed = (seed * 16807) % 2147483647;
  return seed / 2147483647;
}

/** Moves along a cubic Bézier that bows to one side, slower for longer trips (roughly Fitts' law). */
export async function humanMove(page, x, y) {
  const from = { ...page.__cursor };
  const dx = x - from.x;
  const dy = y - from.y;
  const distance = Math.hypot(dx, dy);
  if (distance < 2) return;
  const ms = 380 + distance * 0.42;
  const bow = (jitter() - 0.5) * 0.35 * distance;
  const nx = -dy / distance;
  const ny = dx / distance;
  const c1 = { x: from.x + dx * 0.3 + nx * bow, y: from.y + dy * 0.3 + ny * bow };
  const c2 = { x: from.x + dx * 0.75 + nx * bow * 0.6, y: from.y + dy * 0.75 + ny * bow * 0.6 };
  const steps = Math.max(12, Math.round(ms / 16));
  for (let i = 1; i <= steps; i++) {
    const t = ease(i / steps);
    const u = 1 - t;
    const px = u ** 3 * from.x + 3 * u * u * t * c1.x + 3 * u * t * t * c2.x + t ** 3 * x;
    const py = u ** 3 * from.y + 3 * u * u * t * c1.y + 3 * u * t * t * c2.y + t ** 3 * y;
    await page.mouse.move(px, py);
    await page.evaluate(([a, b]) => window.__pitchMove?.(a, b), [px, py]);
    await page.waitForTimeout(16);
  }
  page.__cursor = { x, y };
}

/** A point inside the element, a little off its center the way a hand aims. */
async function aim(locator) {
  await locator.scrollIntoViewIfNeeded();
  const box = await locator.boundingBox();
  return {
    x: box.x + box.width * (0.42 + jitter() * 0.16),
    y: box.y + box.height * (0.4 + jitter() * 0.2),
  };
}

export async function humanHover(page, locator, ms = 700) {
  const point = await aim(locator);
  await humanMove(page, point.x, point.y);
  await page.waitForTimeout(ms);
}

export async function humanClick(page, locator, hover = 380) {
  const point = await aim(locator);
  await humanMove(page, point.x, point.y);
  await page.waitForTimeout(hover + jitter() * 200);
  await page.evaluate(([a, b]) => window.__pitchClick?.(a, b), [point.x, point.y]);
  await page.mouse.down();
  await page.waitForTimeout(70 + jitter() * 40);
  await page.mouse.up();
}

/** Types key by key at a typing pace, with a longer beat after spaces and punctuation. */
export async function humanType(page, text) {
  for (const char of text) {
    await page.keyboard.type(char);
    const pause = /[\s,.:;]/.test(char) ? 120 + jitter() * 90 : 55 + jitter() * 70;
    await page.waitForTimeout(pause);
  }
}

/** Scrolls with the wheel in small notches, so the motion reads as a hand on a mouse. */
export async function humanScroll(page, dy) {
  const notches = Math.max(1, Math.round(Math.abs(dy) / 60));
  const step = dy / notches;
  for (let i = 0; i < notches; i++) {
    await page.mouse.wheel(0, step);
    await page.waitForTimeout(28 + jitter() * 20);
  }
  await page.waitForTimeout(250);
}

/** Scrolls until the element sits about `top` px below the viewport top. */
export async function humanScrollTo(page, locator, top = 160) {
  const box = await locator.boundingBox();
  if (box) await humanScroll(page, box.y - top);
}

/** Holds still with a faint drift of the hand, for the idle tail every take ends with. */
export async function idle(page, ms) {
  const start = Date.now();
  while (Date.now() - start < ms) {
    const { x, y } = page.__cursor;
    await humanMove(page, x + (jitter() - 0.5) * 18, y + (jitter() - 0.5) * 12);
    await page.waitForTimeout(500 + jitter() * 400);
  }
}
