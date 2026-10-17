#!/usr/bin/env bash
# Reproduces both cuts of the pitch from scratch: tools, fonts, voice, recording on the deployed demo, edit.
#   ./render.sh            records new takes (a brand-new demo workspace) and renders both cuts
#   ./render.sh --no-record  renders again from the takes already in build/raw
# Needs node 22, python 3, ffmpeg with libass, poppler-utils (pdftotext, pdftoppm) and uv (for the attack PDF).
set -euo pipefail
cd "$(dirname "$0")"

VOICE=es_ES-sharvard-medium
VOICE_URL=https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/$VOICE.onnx

npm ci --silent
mkdir -p build/fonts build/tts build/assets out

# Fonts of the web (Source Serif 4 for titles, Inter for text), as TTF for the cards and libass.
if [ ! -f build/fonts/Inter-600.ttf ]; then
  for family in "Inter:wght@400;500;600;700" "Source+Serif+4:opsz,wght@8..60,600;8..60,700"; do
    curl -fsS -A "Mozilla/4.0" "https://fonts.googleapis.com/css2?family=$family"
  done > build/fonts/fonts.css
  python3 - <<'EOF'
import re, subprocess
css = open("build/fonts/fonts.css").read()
for block in re.findall(r"@font-face \{(.*?)\}", css, re.S):
    family = re.search(r"font-family: '([^']+)'", block).group(1).replace(" ", "")
    weight = re.search(r"font-weight: (\d+)", block).group(1)
    url = re.search(r"url\(([^)]+)\)", block).group(1)
    subprocess.run(["curl", "-fsS", "-o", f"build/fonts/{family}-{weight}.ttf", url], check=True)
EOF
fi

# Local Spanish voice: piper with the es_ES «sharvard» voice (male speaker), the most intelligible one we measured.
if [ ! -x build/tts/venv/bin/piper ]; then
  python3 -m venv build/tts/venv
  build/tts/venv/bin/pip install -q piper-tts
fi
[ -f build/tts/$VOICE.onnx ] || curl -fsSL -o build/tts/$VOICE.onnx "$VOICE_URL"
[ -f build/tts/$VOICE.onnx.json ] || curl -fsSL -o build/tts/$VOICE.onnx.json "$VOICE_URL.json"

if [ "${1:-}" != "--no-record" ]; then
  node record.mjs build/raw
fi
pdftoppm -r 200 -png -singlefile build/raw/factura-AC-2026-14.pdf build/assets/attack

python3 build.py horizontal
python3 build.py vertical
python3 guion.py
ls -l out/*.mp4
