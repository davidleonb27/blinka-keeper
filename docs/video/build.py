"""Cuts the pitch from the recorded takes, the title cards and the narration.

Usage: python3 build.py horizontal|vertical
Reads script.json and build/raw/<take>.mp4 + <take>.marks.json (record.mjs), renders the cards with titles.mjs,
speaks every line with piper, and writes out/custodio-pitch-<cut>.mp4, its .ass captions and build/<cut>-timeline.json.
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
import wave
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
BUILD = HERE / "build"
OUT = HERE / "out"
FPS = 30
FADE = 0.4  # cross-fade between scenes
LEAD = 0.35  # silence before a scene's first line
GAP = 0.25  # silence between lines
TAIL = 0.5  # silence after a scene's last line
WORDS_PER_SECOND = 2.5  # under the 2,6 the delivery documents allow
MAX_FIT_SPEED = 1.35  # a product scene may play this much faster to fit its narration
LENGTH_SCALE = "1.1"  # piper, a little slower than its own pace
BG = "0xEDF2F2"
SIZES = {"horizontal": (1920, 1080), "vertical": (1080, 1920)}
TITLE_MIN = {"open": 7.2, "pdf": 7.0, "problem": 8.0, "proof": 6.5, "compare": 7.5, "close": 4.5}
# Vertical footage window: the take is cropped to HOLE's aspect, scaled into it, and framed by titles' vframe.
HOLE = {"x": 40, "y": 600, "w": 1000, "h": 900}


@dataclass
class Line:
    text: str
    say: str
    wav: Path
    duration: float
    start: float = 0.0  # within the scene


@dataclass
class Scene:
    spec: dict
    lines: list[Line]
    duration: float = 0.0
    start: float = 0.0  # on the timeline
    clip: Path | None = None
    fit: float = 1.0
    segments: list[dict] = field(default_factory=list)

    @property
    def id(self) -> str:
        return self.spec["id"]


def run(*args: str | Path) -> None:
    subprocess.run([str(a) for a in args], check=True)


def ffmpeg(*args: str | Path) -> None:
    run("ffmpeg", "-v", "error", "-y", *args)


def wav_seconds(path: Path) -> float:
    with wave.open(str(path)) as w:
        return w.getnframes() / w.getframerate()


def speak(script: dict, scene: dict) -> list[Line]:
    voice = BUILD / "tts" / f"{script['voice']}.onnx"
    piper = BUILD / "tts" / "venv" / "bin" / "piper"
    lines = []
    for i, raw in enumerate(scene["lines"]):
        text, say = (raw["text"], raw.get("say", raw["text"])) if isinstance(raw, dict) else (raw, raw)
        say = say.replace("regla", "reggla")  # the voice swallows the g of «regla»; doubled, it says it
        wav = BUILD / "tts" / f"{scene['id']}-{i}.wav"
        subprocess.run([str(piper), "-m", str(voice), "-s", script.get("speaker", "0"), "--length-scale", LENGTH_SCALE, "--sentence-silence", "0.25",
                        "-f", str(wav)], input=say.encode(), check=True, capture_output=True)
        lines.append(Line(text, say, wav, wav_seconds(wav)))
    return lines


def spoken_words(text: str) -> int:
    return len(re.findall(r"[\wáéíóúüñÁÉÍÓÚÜÑ$]+", text))


def narration_length(lines: list[Line]) -> float:
    return LEAD + sum(line.duration for line in lines) + GAP * (len(lines) - 1) + TAIL


def take_file(take: str) -> str:
    """paid_stripe is a paid take kept from a run before the deployment's daily cap of Stripe test transfers. Without
    it, the paid take of the current run is the same shot."""
    if take == "paid_stripe" and (BUILD / "raw" / "paid.mp4").exists() and not (BUILD / "raw" / "paid_stripe.mp4").exists():
        return "paid"
    return take


def marks(take: str) -> dict[str, float]:
    data = json.loads((BUILD / "raw" / f"{take}.marks.json").read_text())
    return {m["name"]: m["t"] for m in data["marks"]} | {"__end": data["end"]}


def resolve(segment: dict) -> dict:
    segment = {**segment, "take": take_file(segment["take"])}
    m = marks(segment["take"])
    start = m[segment["from"]] + segment.get("fromOffset", 0)
    end = min(m[segment["to"]] + segment.get("toOffset", 0), m["__end"])
    return {**segment, "start": max(0.0, start), "length": end - max(0.0, start), "speed": segment.get("speed", 1)}


def title_data(pdf: Path = BUILD / "raw" / "factura-AC-2026-14.pdf") -> dict:
    """Boxes of the hidden line and the changed account in the attack PDF, from pdftotext (points, top-left)."""
    xml = subprocess.run(["pdftotext", "-bbox", str(pdf), "-"], check=True, capture_output=True, text=True).stdout
    words = [(float(a), float(b), float(c), float(d), w) for a, b, c, d, w in
             re.findall(r'xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">([^<]*)<', xml)]

    def span(first: str, last: str) -> tuple[dict, str]:
        i = next(k for k, w in enumerate(words) if w[4] == first)
        j = next(k for k in range(i, len(words)) if words[k][4] == last)
        chosen = words[i:j + 1]
        box = {"x0": min(w[0] for w in chosen), "y0": min(w[1] for w in chosen),
               "x1": max(w[2] for w in chosen), "y1": max(w[3] for w in chosen)}
        return box, " ".join(w[4] for w in chosen)

    hidden, hidden_text = span("Nota", "revisión.")
    account, _ = span("Banco:", "0450-9902")
    number = next(w[4] for w in words if re.fullmatch(r"\d{4}-\d{4}", w[4]))
    return {"hidden": hidden, "hiddenText": hidden_text, "account": account, "accountText": f"Banco Popular {number}"}


def plan(script: dict, cut: str) -> list[Scene]:
    scenes = []
    for spec in script[cut]:
        lines = speak(script, spec)
        scene = Scene(spec, lines)
        voice = narration_length(lines)
        if "segments" in spec:
            scene.segments = [resolve(s) for s in spec["segments"]]
            visual = sum(s["length"] / s["speed"] for s in scene.segments)
            scene.duration = max(voice, visual / MAX_FIT_SPEED)
            scene.fit = max(1.0, visual / scene.duration)
        else:
            scene.duration = max(voice + 0.3, TITLE_MIN.get(spec["title"].removeprefix("v-"), 4.0))
        # The voice can outrun the script's own limit; never give a scene less time than its words need at 2,5 per second.
        scene.duration = max(scene.duration, sum(spoken_words(line.text) for line in lines) / WORDS_PER_SECOND)
        if scene.segments:
            scene.fit = max(1.0, sum(s["length"] / s["speed"] for s in scene.segments) / scene.duration)
        at = LEAD
        for line in lines:
            line.start = at
            at += line.duration + GAP
        scenes.append(scene)
    t = 0.0
    for scene in scenes:
        scene.start = t
        t += scene.duration - FADE
    return scenes


def render_cards(scenes: list[Scene], cut: str) -> None:
    w, h = SIZES[cut]
    data = title_data()
    jobs = []
    for scene in scenes:
        if "title" in scene.spec:
            scene.clip = BUILD / cut / f"{scene.id}.mp4"
            jobs.append({"scene": scene.spec["title"].removeprefix("v-"), "w": w, "h": h, "d": round(scene.duration, 3),
                         "data": data, "out": str(scene.clip)})
            continue
        if "label" in scene.spec:
            jobs.append({"scene": "label", "w": w, "h": h, "d": 0, "data": {"text": scene.spec["label"]},
                         "out": str(BUILD / cut / f"{scene.id}-label.png")})
        if "headline" in scene.spec:
            jobs.append({"scene": "vframe", "w": w, "h": h, "d": 0, "data": {"headline": scene.spec["headline"], "hole": HOLE},
                         "out": str(BUILD / cut / f"{scene.id}-frame.png")})
        for speed in {s["speed"] for s in scene.segments if s["speed"] > 1}:
            jobs.append({"scene": "badge", "w": w, "h": h, "d": 0, "data": {"speed": speed},
                         "out": str(BUILD / cut / f"badge-{speed}.png")})
    (BUILD / cut).mkdir(parents=True, exist_ok=True)
    jobs_file = BUILD / cut / "titles.json"
    jobs_file.write_text(json.dumps(jobs))
    run("node", HERE / "titles.mjs", jobs_file)


def cut_product(scene: Scene, cut: str) -> None:
    """One clip per segment (speed, label, badge), joined, then frozen on its last frame to the scene's length."""
    parts = []
    for i, seg in enumerate(scene.segments):
        part = BUILD / cut / f"{scene.id}-{i}.mp4"
        rate = seg["speed"] * scene.fit
        inputs: list[str | Path] = ["-ss", f"{seg['start']:.3f}", "-t", f"{seg['length']:.3f}", "-i", BUILD / "raw" / f"{seg['take']}.mp4"]
        chain = f"[0:v]setpts=PTS/{rate:.4f},fps={FPS}"
        if cut == "vertical":
            crop = scene.spec["crop"]
            ch = round(crop["w"] * HOLE["h"] / HOLE["w"])
            chain += (f",crop={crop['w']}:{ch}:{crop['x']}:{crop.get('y', 0)},scale={HOLE['w']}:{HOLE['h']}:flags=lanczos[fg];"
                      f"color=c={BG}:s=1080x1920:r={FPS}[bg];[bg][fg]overlay={HOLE['x']}:{HOLE['y']}:shortest=1")
            inputs += ["-i", BUILD / cut / f"{scene.id}-frame.png"]
            chain += "[v0];[v0][1:v]overlay=0:0"
        else:
            inputs += ["-i", BUILD / cut / f"{scene.id}-label.png"]
            chain += "[v0];[v0][1:v]overlay=0:0"
        if seg["speed"] > 1:
            inputs += ["-i", BUILD / cut / f"badge-{seg['speed']}.png"]
            chain += f"[v1];[v1][{2}:v]overlay=0:0"
        ffmpeg(*inputs, "-filter_complex", chain + ",format=yuv420p", "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "14", part)
        parts.append(part)
    listing = BUILD / cut / f"{scene.id}-parts.txt"
    listing.write_text("".join(f"file '{p}'\n" for p in parts))
    scene.clip = BUILD / cut / f"{scene.id}.mp4"
    ffmpeg("-f", "concat", "-safe", "0", "-i", listing, "-vf", f"tpad=stop_mode=clone:stop_duration={scene.duration:.3f},"
           f"trim=duration={scene.duration:.3f},setpts=PTS-STARTPTS,fps={FPS},format=yuv420p",
           "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "14", scene.clip)


def join(scenes: list[Scene], cut: str) -> Path:
    inputs: list[str | Path] = []
    for scene in scenes:
        inputs += ["-i", scene.clip]
    graph, last, offset = [], "0:v", 0.0
    for i, scene in enumerate(scenes[1:], start=1):
        offset += scenes[i - 1].duration - FADE
        graph.append(f"[{last}][{i}:v]xfade=transition=fade:duration={FADE}:offset={offset:.3f}[x{i}]")
        last = f"x{i}"
    video = BUILD / cut / "video.mp4"
    ffmpeg(*inputs, "-filter_complex", ";".join(graph), "-map", f"[{last}]", "-c:v", "libx264", "-preset", "fast",
           "-crf", "14", "-pix_fmt", "yuv420p", video)
    return video


def narration(scenes: list[Scene], cut: str, total: float) -> Path:
    inputs: list[str | Path] = []
    pieces = []
    for scene in scenes:
        for line in scene.lines:
            k = len(pieces)
            inputs += ["-i", line.wav]
            delay = round((scene.start + line.start) * 1000)
            pieces.append(f"[{k}:a]aresample=48000,adelay={delay}|{delay}[a{k}]")
    mix = "".join(f"[a{k}]" for k in range(len(pieces)))
    graph = ";".join(pieces) + f";{mix}amix=inputs={len(pieces)}:normalize=0,apad,atrim=0:{total:.3f},loudnorm=I=-16:TP=-1.5:LRA=11[out]"
    audio = BUILD / cut / "voice.wav"
    ffmpeg(*inputs, "-filter_complex", graph, "-map", "[out]", "-ar", "48000", "-ac", "2", audio)
    return audio


def chunks(text: str, limit: int) -> list[str]:
    """Caption cards of at most two lines: split at sentence and clause ends, then by words."""
    phrases = [p.strip() for p in re.split(r"(?<=[.;:?!])\s+", text) if p.strip()]
    out: list[str] = []
    for phrase in phrases:
        if out and len(out[-1]) + 1 + len(phrase) <= 2 * limit:
            out[-1] += " " + phrase
            continue
        words, cur = phrase.split(), ""
        for word in words:
            if cur and len(cur) + 1 + len(word) > 2 * limit:
                out.append(cur)
                cur = word
            else:
                cur = f"{cur} {word}".strip()
        out.append(cur)
    return out


def two_lines(card: str, limit: int) -> str:
    """Breaks a card into two balanced lines when it does not fit in one."""
    if len(card) <= limit:
        return card
    words = card.split()
    best = min(range(1, len(words)), key=lambda i: abs(len(" ".join(words[:i])) - len(" ".join(words[i:]))))
    return " ".join(words[:best]) + r"\N" + " ".join(words[best:])


def stamp(t: float) -> str:
    cs = round(t * 100)
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def captions(scenes: list[Scene], cut: str) -> Path:
    w, h = SIZES[cut]
    vertical = cut == "vertical"
    size, margin, limit = (52, 250, 32) if vertical else (46, 50, 52)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter SemiBold,{size},&H00FFFFFF,&H00FFFFFF,&H28181610,&H28181610,0,0,0,0,100,100,0,0,3,14,0,2,80,80,{margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    for scene in scenes:
        for line in scene.lines:
            pieces = chunks(line.text, limit)
            weights = [len(p) for p in pieces]
            t = scene.start + line.start
            for piece, weight in zip(pieces, weights, strict=True):
                span = line.duration * weight / sum(weights)
                wrapped = two_lines(piece, limit)
                events.append(f"Dialogue: 0,{stamp(t)},{stamp(t + span + 0.15)},Cap,,0,0,0,,{wrapped}")
                t += span
    path = OUT / f"custodio-pitch-{cut}.ass"
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return path


def main(cut: str) -> None:
    script = json.loads((HERE / "script.json").read_text())
    OUT.mkdir(exist_ok=True)
    scenes = plan(script, cut)
    total = scenes[-1].start + scenes[-1].duration
    print(f"{cut}: {len(scenes)} escenas, {total:.1f} s")
    render_cards(scenes, cut)
    for scene in scenes:
        if scene.segments:
            cut_product(scene, cut)
    video = join(scenes, cut)
    audio = narration(scenes, cut, total)
    subs = captions(scenes, cut)
    final = OUT / f"custodio-pitch-{cut}.mp4"
    ffmpeg("-i", video, "-i", audio, "-vf", f"subtitles={subs}:fontsdir={BUILD / 'fonts'}", "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "slow", "-crf", "22" if cut == "horizontal" else "21", "-maxrate", "1.8M", "-bufsize", "3.6M",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-t", f"{total:.3f}", final)
    timeline = [{"id": s.id, "start": round(s.start, 2), "duration": round(s.duration, 2), "fit": round(s.fit, 2),
                 "lines": [{"at": round(s.start + line.start, 2), "seconds": round(line.duration, 2), "text": line.text} for line in s.lines]}
                for s in scenes]
    (BUILD / f"{cut}-timeline.json").write_text(json.dumps({"total": round(total, 2), "scenes": timeline}, ensure_ascii=False, indent=2))
    print(final, f"{final.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1])
