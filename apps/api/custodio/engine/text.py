"""Spelling-insensitive comparisons shared by the engine and the auditor.

These are vocabulary, not decisions: how to compare two names, tax ids, account or invoice numbers. Who a supplier
is and whether a payment is proper is decided separately by the rules and, again, by the auditor.
"""

from __future__ import annotations

import re
import unicodedata

# Company-type suffixes that do not identify a supplier, written after dropping dots ("S.A.S." -> "sas").
COMPANY_SUFFIXES: tuple[tuple[str, ...], ...] = (
    ("s", "de", "rl", "de", "cv"),
    ("sa", "de", "cv"),
    ("s", "de", "rl"),
    ("sas",),
    ("sa",),
    ("sac",),
    ("srl",),
    ("spa",),
    ("ltda",),
    ("ltd",),
    ("llc",),
    ("inc",),
    ("corp",),
    ("gmbh",),
    ("eirl",),
    ("plc",),
)


def fold(text: str) -> str:
    """Lowercase without accents, so «Procésala» and «procesala» compare equal."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()


def normalize_name(name: str) -> str:
    tokens = re.sub(r"[^a-z0-9]+", " ", fold(name).replace(".", "")).split()
    return "".join(_strip_suffixes(tokens))


def normalize_code(code: str) -> str:
    """Tax ids, account numbers and invoice numbers: letters and digits only, uppercase."""
    return re.sub(r"[^A-Z0-9]", "", fold(code).upper())


def _strip_suffixes(tokens: list[str]) -> list[str]:
    for suffix in COMPANY_SUFFIXES:
        if len(tokens) > len(suffix) and tuple(tokens[-len(suffix) :]) == suffix:
            return _strip_suffixes(tokens[: -len(suffix)])
    return tokens
