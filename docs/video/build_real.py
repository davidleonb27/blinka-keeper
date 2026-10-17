"""Edits the «mouse real» demo (GUION-VOZ.md) from one take per block and one voice file per block.

Usage: python3 build_real.py [--placeholder-voice] [--takes=DIR]
- Takes: build/real/bNN.mp4 + bNN.marks.json (node record.mjs --real).
- Voice: docs/video/voz/01.* … 10.* (any audio format). With --placeholder-voice, missing blocks are spoken by the
  local piper voice so the edit can be checked before the real voice arrives.
Each block keeps its take at real speed. The voice is placed so that one anchor word lands on the moment the take
does what that word says (word times come from faster-whisper on the voice itself); the take waits, never speeds up.
Captions carry the script's exact words. Writes out/custodio-demo-horizontal.mp4, out/custodio-demo-vertical.mp4,
their .ass captions and build/real-timeline.json.
"""

from __future__ import annotations

import difflib
import json
import re
import subprocess
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import build
from build import BUILD, FPS, HERE, OUT, ffmpeg, run, stamp, two_lines

TAKES = Path(next((a.split("=", 1)[1] for a in sys.argv if a.startswith("--takes=")), BUILD / "real")).resolve()
VOICE_DIR = HERE / "voz"
WORK = BUILD / "real-edit"
FADE = 0.3
LEAD = 0.4  # before the voice when nothing has to sync
TAIL = 0.7  # after the voice
# The word of each block that has to land on a moment of its take.
ANCHORS = {
    1: ("esconde", "select_hidden"),
    3: ("Decidir", "decide_click"),
    4: ("Frenada", "result"),
    5: ("aquí", "hover_tr"),
    6: ("compila", "compiled"),
    7: ("calendario", "calendar_open"),
    8: ("rojo", "alerts_view"),
    9: ("Altero", "tamper_click"),
}
TITLE_BLOCKS = {2: "problem"}
CLOSING_WORD = (10, "Custodio")  # block 10 cuts to the closing card on this word
LABEL = "Producto real · en producción"
# Vertical cut: blocks 1, 5 and 10 with their own voice. Crops (x, y, width) of the 1920×1080 takes; the window keeps
# HOLE's aspect. Block 1 switches to the FRENADO verdict of block 4 on «Custodio».
VERTICAL = [
    {"block": 1, "parts": [("b01", "start", (0, 0, 1200)), ("b04", "result", (420, 0, 1200))], "switch": "Custodio",
     "headlines": ["Una factura trampa.", "Custodio la frena."]},
    {"block": 5, "parts": [("b05", "start", (720, 0, 1200))], "headlines": ["Pago real. Stripe, modo prueba."]},
    {"block": 10, "parts": [("b10", "start", (360, 0, 1200))], "headlines": ["Ahora tú: intenta robarnos."]},
]


@dataclass
class Block:
    number: int
    text: str  # caption text, the script's words without stage directions
    say: str  # what the placeholder voice reads
    audio: Path | None = None
    duration: float = 0.0
    words: list[dict] = field(default_factory=list)  # whisper words with start/end
    start: float = 0.0  # on the timeline
    length: float = 0.0
    voice_at: float = 0.0  # voice start inside the block
    clip: Path | None = None


def script_blocks() -> list[Block]:
    text = (HERE / "GUION-VOZ.md").read_text(encoding="utf-8")
    blocks = []
    for number, voice in re.findall(r"^\| (\d+) \| [^|]+ \| ([^|]+) \|", text, re.MULTILINE):
        clean = re.sub(r"\s*\[pausa\]\s*", " ", voice).strip()
        blocks.append(Block(int(number), clean, voice.replace("[pausa]", "…").strip()))
    assert [b.number for b in blocks] == list(range(1, 11)), "GUION-VOZ.md debe tener los bloques 1 a 10"
    return blocks


def probe_seconds(path: Path) -> float:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         check=True, capture_output=True, text=True).stdout
    return float(out)


def voice_for(block: Block, placeholder: bool) -> None:
    found = sorted(VOICE_DIR.glob(f"{block.number:02d}.*"))
    wav = WORK / f"voz-{block.number:02d}.wav"
    if found:
        ffmpeg("-i", found[0], "-ac", "1", "-ar", "48000", wav)
    elif placeholder:
        piper = BUILD / "tts" / "venv" / "bin" / "piper"
        raw = WORK / f"piper-{block.number:02d}.wav"
        subprocess.run([str(piper), "-m", str(BUILD / "tts" / "es_ES-sharvard-medium.onnx"), "-s", "0", "--length-scale",
                        "1.12", "--sentence-silence", "0.35", "-f", str(raw)],
                       input=block.say.replace("regla", "reggla").replace("Blinka", "Blinca").encode(), check=True, capture_output=True)
        ffmpeg("-i", raw, "-ac", "1", "-ar", "48000", wav)
    else:
        raise SystemExit(f"falta el audio del bloque {block.number:02d} en {VOICE_DIR} (o usa --placeholder-voice)")
    block.audio = wav
    block.duration = probe_seconds(wav)


def word_times(blocks: list[Block]) -> None:
    """Word start/end times of every voice file, from faster-whisper (cached by file size and mtime)."""
    cache = WORK / "words.json"
    known = json.loads(cache.read_text()) if cache.exists() else {}
    todo = [b for b in blocks if known.get(str(b.audio), {}).get("key") != _key(b.audio)]
    if todo:
        script = WORK / "words.py"
        script.write_text(
            "import json, sys\nfrom faster_whisper import WhisperModel\n"
            "m = WhisperModel('small', device='cpu', compute_type='int8')\nout = {}\n"
            "for f in sys.argv[1:]:\n"
            "    segs, _ = m.transcribe(f, language='es', beam_size=5, word_timestamps=True)\n"
            "    out[f] = [{'w': w.word.strip(), 's': w.start, 'e': w.end} for s in segs for w in s.words]\n"
            "print(json.dumps(out))\n")
        python = BUILD / "tts" / "venv" / "bin" / "python"
        result = subprocess.run([str(python), str(script), *[str(b.audio) for b in todo]], check=True, capture_output=True, text=True)
        for name, words in json.loads(result.stdout).items():
            known[name] = {"key": _key(Path(name)), "words": words}
        cache.write_text(json.dumps(known, ensure_ascii=False))
    for b in blocks:
        b.words = known[str(b.audio)]["words"]


def _key(path: Path) -> str:
    stat = path.stat()
    return f"{stat.st_size}-{stat.st_mtime_ns}"


def norm(word: str) -> str:
    word = unicodedata.normalize("NFD", word.lower())
    return re.sub(r"[^a-z0-9ñ]", "", "".join(c for c in word if unicodedata.category(c) != "Mn"))


def aligned_times(block: Block) -> list[tuple[float, float] | None]:
    """For each word of the caption text, its (start, end) in the voice, matched against the transcription."""
    script = [norm(w) for w in block.text.split()]
    heard = [norm(w["w"]) for w in block.words]
    times: list[tuple[float, float] | None] = [None] * len(script)
    matcher = difflib.SequenceMatcher(a=script, b=heard, autojunk=False)
    for a, b, size in matcher.get_matching_blocks():
        for k in range(size):
            times[a + k] = (block.words[b + k]["s"], block.words[b + k]["e"])
    return times


def time_of(block: Block, word: str, occurrence: int = 1) -> float | None:
    target = norm(word)
    seen = 0
    for spoken, t in zip(block.text.split(), aligned_times(block), strict=True):
        if norm(spoken) == target and t:
            seen += 1
            if seen == occurrence:
                return t[0]
    return None


def marks(take: str) -> dict[str, float]:
    data = json.loads((TAKES / f"{take}.marks.json").read_text())
    return {m["name"]: m["t"] for m in data["marks"]} | {"__start": data["start"], "__end": data["end"]}


def last_mark(take: str) -> float:
    data = json.loads((TAKES / f"{take}.marks.json").read_text())
    return max(m["t"] for m in data["marks"])


def lay_out(blocks: list[Block]) -> None:
    """Block length and where its voice starts: synced on the anchor, never faster, waiting when it must."""
    for b in blocks:
        if b.number in TITLE_BLOCKS:
            b.voice_at, b.length = LEAD, LEAD + b.duration + TAIL
            continue
        take = f"b{b.number:02d}"
        m = marks(take)
        anchor = ANCHORS.get(b.number)
        word_at = time_of(b, anchor[0]) if anchor else None
        if anchor and word_at is not None:
            b.voice_at = m[anchor[1]] - word_at  # may be negative: the take then waits on its first frame
        else:
            b.voice_at = LEAD
        lead_pad = max(0.0, -b.voice_at)
        b.voice_at += lead_pad
        b.length = max(b.voice_at + b.duration + TAIL, lead_pad + last_mark(take) + 1.2)
        b.__dict__["lead_pad"] = lead_pad
    t = 0.0
    for b in blocks:
        b.start = t
        t += b.length - FADE


def render_cards(blocks: list[Block]) -> dict[str, Path]:
    jobs, cards = [], {}
    data = build.title_data(TAKES / "factura-AC-2026-14.pdf")
    for b in blocks:
        if b.number in TITLE_BLOCKS:
            b.clip = WORK / f"card-{b.number:02d}.mp4"
            jobs.append({"scene": TITLE_BLOCKS[b.number], "w": 1920, "h": 1080, "d": round(b.length, 3), "data": data, "out": str(b.clip)})
    closing = blocks[-1]
    word_at = time_of(closing, CLOSING_WORD[1]) or closing.duration * 0.7
    cards["close_at"] = closing.voice_at + word_at - 0.25
    close_len = closing.length - cards["close_at"]
    cards["close"] = WORK / "card-close.mp4"
    jobs.append({"scene": "close", "w": 1920, "h": 1080, "d": round(close_len, 3), "data": data, "out": str(cards["close"])})
    jobs.append({"scene": "label", "w": 1920, "h": 1080, "d": 0, "data": {"text": LABEL}, "out": str(WORK / "label.png")})
    (WORK / "titles.json").write_text(json.dumps(jobs))
    run("node", HERE / "titles.mjs", WORK / "titles.json")
    return cards


def cut_take(b: Block, cards: dict) -> None:
    take = TAKES / f"b{b.number:02d}.mp4"
    lead_pad = b.__dict__.get("lead_pad", 0.0)
    b.clip = WORK / f"block-{b.number:02d}.mp4"
    length = b.length
    if b.number == CLOSING_WORD[0]:
        length = cards["close_at"]
    chain = (f"[0:v]tpad=start_mode=clone:start_duration={lead_pad:.3f}:stop_mode=clone:stop_duration={length:.3f},"
             f"trim=duration={length:.3f},setpts=PTS-STARTPTS,fps={FPS}[v];[v][1:v]overlay=0:0,format=yuv420p")
    ffmpeg("-i", take, "-i", WORK / "label.png", "-filter_complex", chain, "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "15", b.clip)
    if b.number == CLOSING_WORD[0]:
        joined = WORK / "block-10-closed.mp4"
        ffmpeg("-i", b.clip, "-i", cards["close"], "-filter_complex",
               f"[0:v][1:v]xfade=transition=fade:duration=0.4:offset={length - 0.4:.3f},format=yuv420p",
               "-c:v", "libx264", "-preset", "fast", "-crf", "15", joined)
        b.clip = joined
        b.length = probe_seconds(joined)


def join(blocks: list[Block], name: str) -> Path:
    inputs: list = []
    for b in blocks:
        inputs += ["-i", b.clip]
    graph, last, offset = [], "0:v", 0.0
    for i in range(1, len(blocks)):
        offset += blocks[i - 1].length - FADE
        graph.append(f"[{last}][{i}:v]xfade=transition=fade:duration={FADE}:offset={offset:.3f}[x{i}]")
        last = f"x{i}"
    video = WORK / f"{name}-video.mp4"
    ffmpeg(*inputs, "-filter_complex", ";".join(graph), "-map", f"[{last}]", "-c:v", "libx264", "-preset", "fast",
           "-crf", "15", "-pix_fmt", "yuv420p", video)
    return video


def mix(blocks: list[Block], total: float, name: str) -> Path:
    inputs, pieces = [], []
    for k, b in enumerate(blocks):
        inputs += ["-i", b.audio]
        delay = round((b.start + b.voice_at) * 1000)
        pieces.append(f"[{k}:a]aresample=48000,adelay={delay}|{delay}[a{k}]")
    graph = (";".join(pieces) + ";" + "".join(f"[a{k}]" for k in range(len(blocks)))
             + f"amix=inputs={len(blocks)}:normalize=0,apad,atrim=0:{total:.3f},loudnorm=I=-16:TP=-1.5:LRA=11[out]")
    audio = WORK / f"{name}-voice.wav"
    ffmpeg(*inputs, "-filter_complex", graph, "-map", "[out]", "-ar", "48000", "-ac", "2", audio)
    return audio


def captions(blocks: list[Block], size: tuple[int, int], name: str) -> Path:
    w, h = size
    vertical = h > w
    font, margin, limit = (52, 250, 32) if vertical else (46, 50, 52)
    events = []
    for b in blocks:
        words = b.text.split()
        times = aligned_times(b)
        cards = build.chunks(b.text, limit)
        at = 0
        for card in cards:
            n = len(card.split())
            span = [t for t in times[at:at + n] if t]
            if span:
                start, end = span[0][0], span[-1][1]
            else:  # not heard: share the block's time by length
                start = b.duration * at / len(words)
                end = b.duration * (at + n) / len(words)
            events.append(f"Dialogue: 0,{stamp(b.start + b.voice_at + start)},{stamp(b.start + b.voice_at + end + 0.25)},Cap,,0,0,0,,"
                          f"{two_lines(card, limit)}")
            at += n
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {w}
PlayResY: {h}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap,Inter SemiBold,{font},&H00FFFFFF,&H00FFFFFF,&H28181610,&H28181610,0,0,0,0,100,100,0,0,3,14,0,2,80,80,{margin},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    path = OUT / f"custodio-demo-{name}.ass"
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")
    return path


def finish(video: Path, audio: Path, subs: Path, total: float, name: str) -> Path:
    final = OUT / f"custodio-demo-{name}.mp4"
    ffmpeg("-i", video, "-i", audio, "-vf", f"subtitles={subs}:fontsdir={BUILD / 'fonts'}", "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "slow", "-crf", "22", "-maxrate", "1.8M", "-bufsize", "3.6M", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", "-t", f"{total:.3f}", final)
    return final


def vertical(blocks: list[Block]) -> Path:
    """40–45 s: blocks 1, 5 and 10 with their own voice, the footage cropped into the vertical frame."""
    hole = build.HOLE
    chosen = []
    jobs = []
    for spec in VERTICAL:
        b = blocks[spec["block"] - 1]
        vb = Block(b.number, b.text, b.say, b.audio, b.duration, b.words)
        vb.voice_at, vb.length = LEAD, LEAD + b.duration + TAIL
        switch = time_of(b, spec["switch"]) if spec.get("switch") else None
        cuts = [0.0] + ([LEAD + switch - 0.2] if switch is not None else []) + [vb.length]
        parts = []
        for i, (take, mark, (x, y, cw)) in enumerate(spec["parts"]):
            frame = WORK / f"v{b.number:02d}-{i}-frame.png"
            jobs.append({"scene": "vframe", "w": 1080, "h": 1920, "d": 0, "data": {"headline": spec["headlines"][i], "hole": hole}, "out": str(frame)})
            parts.append((take, mark, x, y, cw, cuts[i], cuts[i + 1], frame))
        vb.__dict__["parts"] = parts
        chosen.append(vb)
    if blocks[-1].number == 10:
        jobs.append({"scene": "close", "w": 1080, "h": 1920, "d": 4.0, "data": build.title_data(TAKES / "factura-AC-2026-14.pdf"), "out": str(WORK / "v-close.mp4")})
    (WORK / "vtitles.json").write_text(json.dumps(jobs))
    run("node", HERE / "titles.mjs", WORK / "vtitles.json")
    for vb in chosen:
        pieces = []
        for k, (take, mark, x, y, cw, a, z, frame) in enumerate(vb.__dict__["parts"]):
            ch = round(cw * hole["h"] / hole["w"])
            start = marks(take)[mark] if mark != "start" else 0.0
            piece = WORK / f"v{vb.number:02d}-{k}.mp4"
            ffmpeg("-ss", f"{start:.3f}", "-i", TAKES / f"{take}.mp4", "-i", frame, "-filter_complex",
                   f"[0:v]tpad=stop_mode=clone:stop_duration={z - a:.3f},trim=duration={z - a:.3f},setpts=PTS-STARTPTS,fps={FPS},"
                   f"crop={cw}:{ch}:{x}:{y},scale={hole['w']}:{hole['h']}:flags=lanczos[fg];color=c={build.BG}:s=1080x1920:r={FPS}[bg];"
                   f"[bg][fg]overlay={hole['x']}:{hole['y']}:shortest=1[v];[v][1:v]overlay=0:0,format=yuv420p",
                   "-an", "-c:v", "libx264", "-preset", "fast", "-crf", "15", piece)
            pieces.append(piece)
        listing = WORK / f"v{vb.number:02d}.txt"
        listing.write_text("".join(f"file '{p}'\n" for p in pieces))
        vb.clip = WORK / f"v{vb.number:02d}.mp4"
        ffmpeg("-f", "concat", "-safe", "0", "-i", listing, "-c", "copy", vb.clip)
    t = 0.0
    for vb in chosen:
        vb.start = t
        t += vb.length - FADE
    video = join(chosen, "vertical")
    close = WORK / "v-close.mp4"
    total = t + FADE
    if close.exists():
        with_close = WORK / "vertical-closed.mp4"
        ffmpeg("-i", video, "-i", close, "-filter_complex", f"[0:v][1:v]xfade=transition=fade:duration=0.4:offset={total - 0.4:.3f},format=yuv420p",
               "-c:v", "libx264", "-preset", "fast", "-crf", "15", with_close)
        video, total = with_close, total + 3.6
    audio = mix(chosen, total, "vertical")
    subs = captions(chosen, (1080, 1920), "vertical")
    final = finish(video, audio, subs, total, "vertical")
    print(final, f"{total:.1f} s", f"{final.stat().st_size / 1e6:.1f} MB")
    if not 40 <= total <= 45:
        print(f"AVISO: el vertical dura {total:.1f} s (pedido: 40–45 s)")
    return final


def main(placeholder: bool) -> None:
    WORK.mkdir(parents=True, exist_ok=True)
    OUT.mkdir(exist_ok=True)
    blocks = script_blocks()
    for b in blocks:
        voice_for(b, placeholder)
    word_times(blocks)
    lay_out(blocks)
    cards = render_cards(blocks)
    for b in blocks:
        if b.number not in TITLE_BLOCKS:
            cut_take(b, cards)
    t = 0.0
    for b in blocks:
        b.start = t
        t += b.length - FADE
    total = t + FADE
    video = join(blocks, "horizontal")
    audio = mix(blocks, total, "horizontal")
    subs = captions(blocks, (1920, 1080), "horizontal")
    final = finish(video, audio, subs, total, "horizontal")
    timeline = {"total": round(total, 2), "blocks": [
        {"block": b.number, "start": round(b.start, 2), "length": round(b.length, 2), "voice_at": round(b.voice_at, 2),
         "voice": round(b.duration, 2), "audio": str(b.audio.name)} for b in blocks]}
    (BUILD / "real-timeline.json").write_text(json.dumps(timeline, indent=2))
    print(final, f"{total:.1f} s", f"{final.stat().st_size / 1e6:.1f} MB")
    if total > 180:
        print(f"AVISO: el horizontal dura {total:.1f} s (pedido: ≤ 180 s). Bloques más largos que su voz:")
        for b in blocks:
            if b.length > b.voice_at + b.duration + TAIL + 0.5:
                print(f"  bloque {b.number}: {b.length:.1f} s de imagen para {b.duration:.1f} s de voz")
    vertical(blocks)


if __name__ == "__main__":
    main("--placeholder-voice" in sys.argv)
