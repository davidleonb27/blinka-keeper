"""Verifica un recibo firmado de Custodio sin instalar nada y sin acceso a Custodio.

Uso: python3 verificar_recibo.py recibo.json clave_publica.json [--exportar CARPETA]

clave_publica.json es lo que publica Custodio en /api/v1/.well-known/custodio-receipt-key. El recibo trae dos firmas
Ed25519 de esa clave: una sobre el JSON canónico de `body` (claves ordenadas, sin espacios, sin escapar acentos) y otra
sobre el SHA-256 de cada campo de `body`, que es como se sabe qué campo se alteró. Sale con 0 si el recibo es válido y
con 1 si no, diciendo por qué. La verificación Ed25519 sigue el RFC 8032 con la biblioteca estándar de Python.

Con --exportar se escriben cuerpo.json, firma.bin y clave.pem para comprobar la misma firma con OpenSSL 3:
    openssl pkeyutl -verify -pubin -inkey clave.pem -rawin -in cuerpo.json -sigfile firma.bin
"""

from __future__ import annotations

import base64
import hashlib
import json
import sys
from collections.abc import Iterator
from pathlib import Path
from typing import Any

INVALID = 1
Point = tuple[int, int, int, int]

_P = 2**255 - 19
_L = 2**252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_SQRT_M1 = pow(2, (_P - 1) // 4, _P)
_IDENTITY: Point = (0, 1, 1, 0)


def canonical_json(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def ed25519_verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    if len(public_key) != 32 or len(signature) != 64:
        return False
    a, r = _decompress(public_key), _decompress(signature[:32])
    s = int.from_bytes(signature[32:], "little")
    if a is None or r is None or s >= _L:
        return False
    h = int.from_bytes(hashlib.sha512(signature[:32] + public_key + message).digest(), "little") % _L
    return _equal(_multiply(s, _BASE), _add(r, _multiply(h, a)))


def field_digests(body: dict[str, Any]) -> dict[str, str]:
    return {path: hashlib.sha256(canonical_json(value)).hexdigest() for path, value in _leaves(body, "")}


def check(receipt: dict[str, Any], key: dict[str, Any]) -> tuple[bool, str]:
    public_key = base64.b64decode(key["public_key"])
    if receipt.get("key_id") != key["key_id"]:
        return False, f"el recibo dice estar firmado con la clave {receipt.get('key_id')}, no con {key['key_id']}"
    body = receipt["body"]
    if ed25519_verify(public_key, canonical_json(body), base64.b64decode(receipt["signature"])):
        if body.get("key_id") == key["key_id"]:
            return True, f"firmado por Custodio; la decisión fue «{body['decision']['verdict']}»"
    digests = receipt["field_digests"]
    if not ed25519_verify(public_key, canonical_json(digests), base64.b64decode(receipt["digests_signature"])):
        return False, "la firma no corresponde a este contenido ni a esta clave"
    now = field_digests(body)
    altered = sorted(path for path in set(now) | set(digests) if now.get(path) != digests.get(path))
    return False, "se alteró " + ", ".join(altered)


def export_for_openssl(receipt: dict[str, Any], key: dict[str, Any], folder: Path) -> None:
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "cuerpo.json").write_bytes(canonical_json(receipt["body"]))
    (folder / "firma.bin").write_bytes(base64.b64decode(receipt["signature"]))
    (folder / "clave.pem").write_text(key["public_key_pem"])


def main(arguments: list[str]) -> int:
    receipt = json.loads(Path(arguments[0]).read_text(encoding="utf-8"))
    key = json.loads(Path(arguments[1]).read_text(encoding="utf-8"))
    if len(arguments) > 3 and arguments[2] == "--exportar":
        export_for_openssl(receipt, key, Path(arguments[3]))
    valid, reason = check(receipt, key)
    print(("VÁLIDO: " if valid else "INVÁLIDO: ") + reason)
    return 0 if valid else INVALID


def _leaves(value: object, prefix: str) -> Iterator[tuple[str, object]]:
    if isinstance(value, dict) and value:
        for name, item in value.items():
            yield from _leaves(item, f"{prefix}.{name}" if prefix else str(name))
    elif isinstance(value, list) and value:
        for index, item in enumerate(value):
            yield from _leaves(item, f"{prefix}.{index}")
    else:
        yield prefix, value


def _add(p: Point, q: Point) -> Point:
    a = (p[1] - p[0]) * (q[1] - q[0]) % _P
    b = (p[1] + p[0]) * (q[1] + q[0]) % _P
    c = p[3] * 2 * _D * q[3] % _P
    d = p[2] * 2 * q[2] % _P
    e, f, g, h = b - a, d - c, d + c, b + a
    return (e * f % _P, g * h % _P, f * g % _P, e * h % _P)


def _multiply(scalar: int, point: Point) -> Point:
    result = _IDENTITY
    while scalar:
        if scalar & 1:
            result = _add(result, point)
        point = _add(point, point)
        scalar >>= 1
    return result


def _equal(p: Point, q: Point) -> bool:
    return (p[0] * q[2] - q[0] * p[2]) % _P == 0 and (p[1] * q[2] - q[1] * p[2]) % _P == 0


def _recover_x(y: int, sign: int) -> int | None:
    if y >= _P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P) % _P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (_P + 3) // 8, _P)
    if (x * x - x2) % _P:
        x = x * _SQRT_M1 % _P
    if (x * x - x2) % _P:
        return None
    return _P - x if (x & 1) != sign else x


def _decompress(encoded: bytes) -> Point | None:
    y = int.from_bytes(encoded, "little")
    sign, y = y >> 255, y & ((1 << 255) - 1)
    x = _recover_x(y, sign)
    return None if x is None else (x, y, 1, x * y % _P)


def _base_point() -> Point:
    y = 4 * pow(5, _P - 2, _P) % _P
    x = _recover_x(y, 0)
    assert x is not None
    return (x, y, 1, x * y % _P)


_BASE = _base_point()

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
