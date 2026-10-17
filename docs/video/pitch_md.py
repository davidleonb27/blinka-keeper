"""Rewrites the «Versión de 3:00» of docs/PITCH.md, and its vertical cut, from the last render's timelines."""

import json
from pathlib import Path

import guion

HERE = Path(__file__).resolve().parent
PITCH = HERE.parent / "PITCH.md"
TITLES = {
    "open": "Una maqueta lo dice; Custodio lo demuestra", "problem": "El problema", "demo": "Una empresa demo nueva, 36 facturas",
    "results": "Las cifras del panel", "pdf": "Un ataque de verdad", "attack": "El reto público lo retiene",
    "arena": "La Arena cambia de técnica", "acta": "Cada decisión, con su acta", "paid": "Pago real en Stripe",
    "approve": "Una persona aprueba", "ledger": "El registro detecta la alteración", "rules": "Reglas en tus palabras",
    "proof": "Medido a escala", "compare": "Maqueta contra producto", "close": "Cierre",
}
BACKUP = {
    "open": "Tarjeta `open` de `docs/video/titles.html`.",
    "problem": "Tarjeta `problem`, con la fuente del FBI IC3 en pantalla.",
    "demo": "Toma `landing` de `docs/video/record.mjs` (espacio demo nuevo en producción).",
    "results": "Toma `landing`, marcas `zoom_zero` y `zoom_counts`.",
    "pdf": "Tarjeta `pdf` con el PDF real que genera `docs/video/make_attack_pdf.py`.",
    "attack": "Toma `attack`: el mismo PDF subido a «Róbale a Custodio».",
    "arena": "Toma `arena`: 3 rondas en vivo.",
    "acta": "Toma `held`: acta de Andrés Paredes.",
    "paid": "Toma `paid`: acta con la transferencia `tr_…`.",
    "approve": "Toma `approve`: Cumulus Hosting aprobada por Ana Gómez.",
    "ledger": "Toma `ledger`: verificar y alterar una copia.",
    "rules": "Toma `rules`: compilar y simular sin aplicar.",
    "proof": "Tarjeta `proof` con las cifras del README › Métricas.",
    "compare": "Tarjeta `compare`.",
    "close": "Tarjeta `close`.",
}


def main() -> None:
    h = json.loads((HERE / "build" / "horizontal-timeline.json").read_text())
    v = json.loads((HERE / "build" / "vertical-timeline.json").read_text())
    scenes = h["scenes"]
    # The cut runs a little under 3:00; its scene starts are stretched to the 3:00 slot the delivery documents use.
    stretch = 180 / h["total"]
    bounds = [0] + [round((s["start"] + guion_fade()) * stretch) for s in scenes[1:]] + [180]
    out = ["## Versión de 3:00", "",
           f"Es el guion de `docs/video/out/custodio-pitch-horizontal.mp4` ({guion.clock(h['total'])}). Los tiempos de abajo son",
           "los del corte repartidos sobre 3:00 y redondeados al segundo; los exactos, frase por frase, están en",
           "[`video/GUION.md`](video/GUION.md).", ""]
    for i, s in enumerate(scenes):
        a, b = bounds[i], bounds[i + 1]
        said = " ".join(line["text"] for line in s["lines"])
        assert guion.words(said) <= guion.MAX_WPS * (b - a), (s["id"], guion.words(said), b - a)
        out += [f"### {a // 60}:{a % 60:02d}–{b // 60}:{b % 60:02d} · {TITLES[s['id']]}", "", f"**Se oye:** {said}", "",
                f"**Se ve:** {guion.SHOTS[s['id']]}", "", f"**Respaldo:** {BACKUP[s['id']]}", ""]
    out += [f"## Corte vertical de {round(v['total'])} s", "",
            "Para redes y Build in Public, en el formato vertical de la competencia pero con producto real:",
            f"`docs/video/out/custodio-pitch-vertical.mp4` (1080×1920, {guion.clock(v['total'])}).", ""]
    out += [f"- **{guion.clock(s['start'])}** " + " ".join(line["text"] for line in s["lines"]) + f" {guion.SHOTS[s['id']]}"
            for s in v["scenes"]]
    text = PITCH.read_text()
    start = text.index("## Versión de 3:00")
    end = text.index("## Versión de 60 s")
    PITCH.write_text(text[:start] + "\n".join(out) + "\n\n" + text[end:])


def guion_fade() -> float:
    return 0.2  # half the cross-fade: a scene owns the screen once its fade-in is halfway


if __name__ == "__main__":
    main()
