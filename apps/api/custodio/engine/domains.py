"""Whose domain is this email from? The same as the supplier's registered one, a lookalike of it, or another (R15).

A lookalike is the registered domain with a hyphen added or removed, another ending (.co, .com, .com.co), letters
that look alike (rn for m, 0 for o, 1 or I for l, vv for w) or at most MAX_LOOKALIKE_EDITS letters changed: the
usual disguises of a business-email-compromise attack. Vocabulary only: R15 and the auditor decide what it means.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum

EMAIL = re.compile(r"[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)+)")
MAX_LOOKALIKE_EDITS = 2
HOMOGLYPHS = (("rn", "m"), ("vv", "w"), ("0", "o"), ("1", "l"), ("I", "l"))  # (what is written, what it imitates)


class DomainLikeness(StrEnum):
    SAME = "same"
    LOOKALIKE = "lookalike"
    DIFFERENT = "different"


@dataclass(frozen=True)
class DomainComparison:
    likeness: DomainLikeness
    why: str | None = None  # Spanish, for a lookalike: what changed


def first_email(text: str) -> str | None:
    """The first email address in a document, as written: the sender's in an email or a signed invoice."""
    found = EMAIL.search(text)
    return found.group(0) if found else None


def email_domain(email: str) -> str:
    return email.rpartition("@")[2].lower()


def compare_domains(seen: str, registered: str) -> DomainComparison:
    """`seen` as written (case matters for I posing as l); `registered` as the company stored it."""
    lowered, wanted = seen.lower(), registered.lower()
    if lowered == wanted or lowered.endswith("." + wanted):
        return DomainComparison(DomainLikeness.SAME)
    why = _lookalike(seen, lowered, wanted)
    return DomainComparison(DomainLikeness.LOOKALIKE, why) if why else DomainComparison(DomainLikeness.DIFFERENT)


def edit_distance(left: str, right: str) -> int:
    """Insertions, deletions, substitutions and swaps of two adjacent letters (optimal string alignment)."""
    previous, current = list(range(len(right) + 1)), [0] * (len(right) + 1)
    before_previous: list[int] = []
    for i in range(1, len(left) + 1):
        current = [i] + [0] * len(right)
        for j in range(1, len(right) + 1):
            cost = 0 if left[i - 1] == right[j - 1] else 1
            current[j] = min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + cost)
            if i > 1 and j > 1 and left[i - 1] == right[j - 2] and left[i - 2] == right[j - 1]:
                current[j] = min(current[j], before_previous[j - 2] + 1)
        before_previous, previous = previous, current
    return previous[len(right)]


def _lookalike(written: str, seen: str, registered: str) -> str | None:
    if seen.replace("-", "") == registered.replace("-", ""):
        return "guion agregado" if seen.count("-") > registered.count("-") else "guion quitado"
    seen_name, _, seen_ending = seen.partition(".")
    name, _, ending = registered.partition(".")
    if seen_name == name:
        return f"otra terminación (.{seen_ending} en lugar de .{ending})"
    glyphs = [f"{glyph} por {letter}" for glyph, letter in HOMOGLYPHS if glyph in written and glyph not in registered]
    if glyphs and _skeleton(written) == _skeleton(registered):
        return f"homóglifos ({', '.join(glyphs)})"
    edits = edit_distance(seen, registered)
    if edits <= MAX_LOOKALIKE_EDITS:
        return f"a {edits} {'edición' if edits == 1 else 'ediciones'} de distancia"
    return None


def _skeleton(domain: str) -> str:
    """What a domain looks like: every look-alike glyph replaced by the letter it imitates."""
    text = domain.replace("I", "l").lower()
    for glyph, letter in HOMOGLYPHS:
        if glyph == glyph.lower():
            text = text.replace(glyph, letter)
    return text
