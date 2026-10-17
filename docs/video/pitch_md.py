"""Rewrites the «Versión de 3:00» of docs/PITCH.md, and its vertical cut, from the last render's timelines."""

import json
from pathlib import Path

import guion

HERE = Path(__file__).resolve().parent
PITCH = HERE.parent / "PITCH.md"
TITLES = {
    "open": "Una maqueta lo dice; Custodio lo demuestra", "problem": "El problema", "demo": "Una empresa demo nueva, 38 facturas",
    "results": "Las cifras del panel", "pdf": "Un ataque de verdad", "attack": "El reto público lo frena",
    "arena": "La Arena cambia de técnica", "acta": "Cada decisión, con su acta", "paid": "Pago real en Stripe",
    "approve": "Una persona aprueba; el pago sale por Stripe", "stage": "Jurado: intenten robarnos ahora", "docs": "Código abierto, autoalojable", "ledger": "El registro detecta la alteración", "rules": "Reglas en tus palabras",
    "proof": "Medido a escala", "paid": "Pago real en Stripe", "calendar": "Se paga el día que vence", "autonomy": "Autonomía ganada", "reconcile": "Conciliación y cierre de mes", "compare": "Maqueta contra producto", "close": "Cierre",
}
TAKE = {
    "open": "Tarjeta animada, sin producto.",
    "problem": "Tarjeta animada; las cifras cuentan hasta su valor y la fuente queda fija al pie.",
    "demo": "Grabación continua con cursor visible; la espera de la decisión va acelerada ×4 y lo dice en pantalla.",
    "results": "Zoom suave a «Pagos indebidos» y a los tres totales, en la misma toma.",
    "pdf": "Tarjeta animada sobre el PDF real; un barrido destapa la línea oculta.",
    "attack": "Grabación continua: se sube el PDF, la lectura va ×3 y el resultado a velocidad normal con zoom.",
    "arena": "Encuadre fijo bajo el título de la página; las rondas ×6 y el marcador final a velocidad normal.",
    "acta": "Zoom a «Por qué» y «Qué tendría que cambiar», luego a R14 (OFAC) y R15 (fuera de banda).",
    "paid": "Zoom al identificador `tr_…` en el acta; no se abre el dashboard de Stripe.",
    "approve": "El clic en «Aprobar pago» se ve completo; zoom a la transferencia que sale después.",
    "paid": "Zoom al identificador `tr_…` en el acta; no se abre el dashboard de Stripe.",
    "calendar": "Zoom a «Valor capturado este mes» y a los próximos pagos.",
    "autonomy": "Clic en «Simular 30 días» (×2) y zoom al resultado y a una tarjeta en supervisión.",
    "reconcile": "Encuadre bajo la ayuda de carga; la conciliación ×3 y zoom al resumen y a «Sin factura».",
    "stage": "Plano fijo del modo escenario y zoom al contador; el número se lee de la pantalla.",
    "docs": "Zoom al bloque de comandos de Docker.",
    "ledger": "Zoom al verde de la verificación y al rojo de la copia alterada.",
    "rules": "Se teclea la regla en cámara; la compilación va ×3 y la simulación con zoom.",
    "proof": "Tarjeta animada.",
    "compare": "Tarjeta animada, fila por fila.",
    "close": "Plano fijo.",
}
BACKUP = {
    "open": "Tarjeta `open` de `docs/video/titles.html`.",
    "problem": "Tarjeta `problem`, con la fuente del FBI IC3 en pantalla.",
    "demo": "Toma `landing` de `docs/video/record.mjs` (espacio demo nuevo en producción).",
    "results": "Toma `landing`, marcas `zoom_zero` y `zoom_counts`.",
    "pdf": "Tarjeta `pdf` con el PDF real que genera `docs/video/make_attack_pdf.py`.",
    "attack": "Toma `attack`: el mismo PDF subido a «Róbale a Custodio».",
    "arena": "Toma `arena`: 3 rondas en vivo.",
    "acta": "Toma `held`: acta de Joaquín Méndez (F-038).",
    "paid": "Toma `paid`: acta con la transferencia `tr_…`.",
    "approve": "Toma `approve`: Cumulus Hosting aprobada por Ana Gómez; toma `paid` como respaldo del `tr_…`.",
    "stage": "Toma `stage`: `/reto?escenario=1`.",
    "paid": "Toma `paid_stripe`: acta con la transferencia `tr_…` (grabada antes del tope diario de Stripe).",
    "calendar": "Toma `calendar`: `/calendario`.",
    "autonomy": "Toma `autonomy`: `/autonomia` con «Simular 30 días».",
    "reconcile": "Toma `reconcile`: `/conciliacion` con el extracto de demo.",
    "docs": "Toma `docs`: `/docs/inicio-rapido`.",
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
    bounds = slots(scenes, h["total"])
    out = ["## Versión de 3:00", "",
           f"Es el guion de `docs/video/out/custodio-pitch-horizontal.mp4` ({guion.clock(h['total'])}). Los tiempos de abajo son",
           "los del corte en segundos enteros sobre 3:00; los exactos, frase por frase, están en",
           "[`video/GUION.md`](video/GUION.md).", ""]
    for i, s in enumerate(scenes):
        a, b = bounds[i], bounds[i + 1]
        said = " ".join(line["text"] for line in s["lines"])
        assert guion.words(said) <= guion.MAX_WPS * (b - a), (s["id"], guion.words(said), b - a)
        out += [f"### {a // 60}:{a % 60:02d}–{b // 60}:{b % 60:02d} · {TITLES[s['id']]}", "", f"**Se oye:** {said}", "",
                f"**Se ve:** {guion.SHOTS[s['id']]}", "", f"**Toma:** {TAKE[s['id']]}", "",
                f"**Respaldo:** {BACKUP[s['id']]}", ""]
    out += [f"## Corte vertical de {round(v['total'])} s", "",
            "Para redes y Build in Public, en el formato vertical de la competencia pero con producto real:",
            f"`docs/video/out/custodio-pitch-vertical.mp4` (1080×1920, {guion.clock(v['total'])}).", ""]
    out += [f"- **{guion.clock(s['start'])}** " + " ".join(line["text"] for line in s["lines"]) + f" {guion.SHOTS[s['id']]}"
            for s in v["scenes"]]
    text = PITCH.read_text()
    start = text.index("## Versión de 3:00")
    end = text.index("## Versión de 60 s")
    PITCH.write_text(text[:start] + "\n".join(out) + "\n\n" + text[end:])


def slots(scenes: list[dict], total: float) -> list[int]:
    """Whole-second slots that fill the 3:00 the delivery documents use: each scene gets its share of the cut
    (stretched to 180 s), never less than its words need at 2,6 per second."""
    import math

    starts = [s["start"] for s in scenes] + [total]
    share = [(b - a) * 180 / total for a, b in zip(starts, starts[1:])]
    need = [math.ceil(guion.words(" ".join(line["text"] for line in s["lines"])) / guion.MAX_WPS) for s in scenes]
    size = [max(n, math.floor(x)) for n, x in zip(need, share)]
    by_remainder = sorted(range(len(scenes)), key=lambda i: share[i] - math.floor(share[i]), reverse=True)
    while sum(size) < 180:
        size[by_remainder.pop(0) if by_remainder else -1] += 1
    while sum(size) > 180:
        i = max(range(len(scenes)), key=lambda k: size[k] - need[k])
        size[i] -= 1
    bounds = [0]
    for n in size:
        bounds.append(bounds[-1] + n)
    return bounds


if __name__ == "__main__":
    main()
