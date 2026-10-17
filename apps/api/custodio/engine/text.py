"""Text folding shared by matching and instruction detection."""

from __future__ import annotations

import unicodedata


def fold(text: str) -> str:
    """Lowercase without accents, so «Procésala» and «procesala» compare equal."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(char for char in decomposed if not unicodedata.combining(char)).lower()
