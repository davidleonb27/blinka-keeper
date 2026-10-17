"""Writes GUION.md from the timelines build.py leaves in build/: what is said, when, and over which shot.

Usage: python3 guion.py   (after `python3 build.py horizontal` and `python3 build.py vertical`)
"""

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = json.loads((HERE / "script.json").read_text())
MAX_WPS = 2.6

SHOTS = {
    "open": "Tarjeta: «Una maqueta lo dice» se tacha; «Custodio lo demuestra». En producción · pagos reales · bajo ataque.",
    "problem": "Tarjeta: 24.768 denuncias y US$ 3.046.598.558 (FBI IC3, Informe anual 2025, fuente en pantalla).",
    "demo": "Producto: inicio → «Probar con una empresa demo» → panel con 36 facturas recibidas → «Decidir las 36 facturas» (acelerado ×4).",
    "results": "Producto: zoom a «Pagos indebidos 0» y a Pagado / Retenido / Pendiente.",
    "pdf": "Tarjeta: el PDF real que se sube; un barrido destapa la línea en blanco y marca la cuenta cambiada.",
    "attack": "Producto: «Róbale a Custodio», se sube el PDF, «No pasó. Custodio no pagó», R2 + R4, la cita destapada y el contador.",
    "arena": "Producto: Arena, 3 rondas en vivo (acelerado ×6) y el marcador final.",
    "acta": "Producto: acta de Andrés Paredes: por qué, qué tendría que cambiar, R4 resaltada.",
    "paid": "Producto: acta de una factura pagada; zoom a «Stripe · modo prueba» y la transferencia tr_….",
    "approve": "Producto: Cumulus Hosting fuera de lo acordado; Ana Gómez aprueba; zoom a la transferencia tr_….",
    "ledger": "Producto: Registro → «Verificar la cadena» (verde) → «Alterar una copia» (rojo en el asiento exacto).",
    "rules": "Producto: Reglas: se escribe «Nada sobre 1.000 USD sin que lo apruebe Ana» → compilar y simular (acelerado ×3).",
    "proof": "Tarjeta: 1.000 empresas · 25.139 facturas · 8.136 pagos re-auditados · 0 pagos indebidos (README › Métricas).",
    "compare": "Tarjeta: «Una maqueta lo dice» frente a «Custodio lo demuestra, en producción», fila por fila.",
    "close": "Tarjeta: «Custodio decide; Blinka paga.», enlace de la demo, repo, MIT y el equipo.",
    "v-open": "Tarjeta vertical: «Una maqueta lo dice. Custodio lo demuestra.»",
    "v-pdf": "Tarjeta vertical: el PDF con la línea oculta destapada y la cuenta cambiada.",
    "v-attack": "Producto: resultado del reto, Retenida, con la cita destapada.",
    "v-paid": "Producto: acta pagada con la transferencia tr_… de Stripe en modo prueba.",
    "v-ledger": "Producto: la copia alterada rompe la cadena en el asiento exacto.",
    "v-proof": "Tarjeta vertical: 1.000 empresas, 25.139 facturas, 0 pagos indebidos.",
    "v-close": "Tarjeta vertical: «Custodio decide; Blinka paga.»",
}


def clock(t: float) -> str:
    return f"{int(t // 60)}:{t % 60:04.1f}"


def words(text: str) -> int:
    return len(re.findall(r"[\wáéíóúüñÁÉÍÓÚÜÑ$]+", text))


def section(cut: str, title: str) -> list[str]:
    timeline = json.loads((HERE / "build" / f"{cut}-timeline.json").read_text())
    out = [f"## {title} · {clock(timeline['total'])}", ""]
    for scene in timeline["scenes"]:
        end = scene["start"] + scene["duration"]
        said = " ".join(line["text"] for line in scene["lines"])
        rate = words(said) / scene["duration"]
        assert rate <= MAX_WPS, f"{scene['id']}: {rate:.2f} palabras por segundo"
        out += [f"### {clock(scene['start'])}–{clock(end)} · {scene['id']}", "", f"**Se ve:** {SHOTS[scene['id']]}", ""]
        out += [f"- `{clock(line['at'])}` ({line['seconds']:.1f} s) {line['text']}" for line in scene["lines"]]
        out += ["", f"{words(said)} palabras en {scene['duration']:.1f} s ({rate:.1f} por segundo).", ""]
    return out


def main() -> None:
    lines = [
        "# Guion final del video",
        "",
        "Generado por `guion.py` desde la línea de tiempo del último render. Cada línea marca cuándo empieza a sonar",
        "(minuto:segundo del video) y cuánto dura con la voz sintética; para regrabar con voz propia, empieza cada frase",
        "en su marca y no la pases de la siguiente. Máximo 2,6 palabras por segundo en cada escena (lo comprueba este",
        "script). Los subtítulos quemados en el video salen de este mismo texto.",
        "",
        *section("horizontal", "Pitch horizontal 1920×1080"),
        *section("vertical", "Corte vertical 1080×1920"),
    ]
    (HERE / "GUION.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
