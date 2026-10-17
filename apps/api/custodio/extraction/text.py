"""Text normalization shared by the checks: comparisons ignore case, accents and spacing; quotes do not."""

from __future__ import annotations

import unicodedata


def fold(text: str) -> str:
    """Lowercase, without accents and with single spaces: "Compañía  ANDINA" -> "compania andina"."""
    decomposed = unicodedata.normalize("NFKD", text)
    bare = "".join(char for char in decomposed if not unicodedata.combining(char))
    return squash(bare.casefold())


def squash(text: str) -> str:
    """Collapse every run of whitespace into one space and trim the ends."""
    return " ".join(text.split())
