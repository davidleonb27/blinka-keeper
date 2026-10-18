"""Verifica la cadena del registro de Blinka Keeper sin instalar nada.

Uso: python3 verificar_registro.py registro.json

Es el mismo algoritmo del verificador público (GET /api/v1/ledger/verify, custodio.engine.ledger.verify):
hash = sha256(hash anterior + JSON canónico de {seq, at, kind, subject_id, payload}); el primer asiento parte de 64
ceros. JSON canónico: claves ordenadas, sin espacios, sin escapar acentos. Sale con 0 si la cadena está íntegra y con
1 si se rompe, diciendo en qué asiento. Sólo usa la biblioteca estándar de Python.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

GENESIS_HASH = "0" * 64
HASHED_FIELDS = ("seq", "at", "kind", "subject_id", "payload")
BROKEN = 1


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def first_broken_seq(entries: list[dict[str, Any]]) -> int | None:
    previous = GENESIS_HASH
    for position, entry in enumerate(entries, start=1):
        body = canonical_json({field: entry[field] for field in HASHED_FIELDS})
        recomputed = hashlib.sha256((entry["prev_hash"] + body).encode()).hexdigest()
        if entry["seq"] != position or entry["prev_hash"] != previous or entry["hash"] != recomputed:
            return position
        previous = entry["hash"]
    return None


def main(arguments: list[str]) -> int:
    entries = json.loads(Path(arguments[0]).read_text(encoding="utf-8"))
    broken = first_broken_seq(entries)
    if broken is None:
        head = entries[-1]["hash"] if entries else GENESIS_HASH
        print(f"Cadena íntegra: {len(entries)} asientos. Último hash: {head}")
        return 0
    print(f"La cadena se rompe en el asiento #{broken}: su hash ya no corresponde a su contenido o a su anterior.")
    return BROKEN


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
