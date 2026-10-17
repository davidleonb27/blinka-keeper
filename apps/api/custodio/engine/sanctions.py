"""Screening a name against the OFAC SDN list (R14): deterministic, explainable and never a decision on its own.

A name and every entry of the list (its name and aliases) become sorted tokens: folded, without accents, punctuation,
company-type suffixes (S.A.S., LLC, S.A. de C.V., LTDA, Inc.) or connecting words (de, la, y, of, the). Two names
are compared word by word: each word takes the Jaro-Winkler similarity of its best partner on the other side, and
the score is the lower of the two directions' averages, so every word on both sides needs a close partner. A score
of SIMILARITY_THRESHOLD or more is a hit; R14 then escalates and a person rules out the false positive.

The threshold was calibrated on the OFAC copy of 15 October 2026: every supplier name and alias of the demo company
scores 0.86 or less against it, while a one-letter typo of a listed name scores above 0.94. To stay fast on the
~40.000 names of the list, a name is only compared with entries that share a word with it up to one deleted letter.

The copy of the list ships with the code (custodio/dataset/ofac/sdn.json, dated and versioned) and is read once per
process; the same name and the same copy always give the same answer.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from functools import cache
from importlib.resources import files

from custodio.contracts import Model
from custodio.engine.text import name_tokens

SIMILARITY_THRESHOLD = 0.92
CONNECTING_WORDS = frozenset({"de", "del", "la", "las", "el", "los", "y", "e", "the", "of", "and"})
WINKLER_PREFIX = 4
WINKLER_SCALE = 0.1
SHORT_WORD = 3  # words this short are indexed as they are, without their one-letter deletions
BUNDLED_PACKAGE = "custodio.dataset.ofac"
BUNDLED_FILE = "sdn.json"


class SanctionsEntryFile(Model):
    uid: int
    name: str
    aliases: tuple[str, ...] = ()
    countries: tuple[str, ...] = ()
    programs: tuple[str, ...] = ()
    type: str | None = None


class SanctionsFile(Model):
    source: str
    published_on: date | None
    downloaded_on: date | None
    fictitious: bool = False
    entries: list[SanctionsEntryFile]


@dataclass(frozen=True)
class SanctionsEntry:
    uid: int
    name: str
    aliases: tuple[str, ...]
    countries: tuple[str, ...]
    programs: tuple[str, ...]


@dataclass(frozen=True)
class SanctionsHit:
    queried: str
    entry: SanctionsEntry
    matched_name: str  # the entry's name or the alias that matched
    score: float


@dataclass(frozen=True)
class _Variant:
    tokens: tuple[str, ...]
    written: str
    entry: SanctionsEntry


@dataclass(eq=False)  # one list is one copy: compared by identity, it carries its own index and cache
class SanctionsList:
    entries: tuple[SanctionsEntry, ...]
    source: str
    published_on: date | None
    fictitious: bool = False
    _variants: list[_Variant] = field(default_factory=list, init=False, repr=False)
    _by_key: defaultdict[str, set[int]] = field(default_factory=lambda: defaultdict(set), init=False, repr=False)
    _screened: dict[str, SanctionsHit | None] = field(default_factory=dict, init=False, repr=False)

    @classmethod
    def from_json(cls, text: str) -> SanctionsList:
        raw = SanctionsFile.model_validate_json(text)
        entries = tuple(SanctionsEntry(e.uid, e.name, e.aliases, e.countries, e.programs) for e in raw.entries)
        return cls(entries=entries, source=raw.source, published_on=raw.published_on, fictitious=raw.fictitious)

    @property
    def size(self) -> int:
        return len(self.entries)

    def screen(self, name: str) -> SanctionsHit | None:
        """The closest entry at or above the threshold, or None."""
        tokens = tuple(screening_tokens(name))
        key = " ".join(tokens)
        if key not in self._screened:
            self._screened[key] = self._closest(name, tokens) if tokens else None
        found = self._screened[key]
        return None if found is None else SanctionsHit(name, found.entry, found.matched_name, found.score)

    def _closest(self, name: str, tokens: tuple[str, ...]) -> SanctionsHit | None:
        best: SanctionsHit | None = None
        for index in sorted(self._candidates(tokens)):
            variant = self._variants[index]
            score = token_set_similarity(tokens, variant.tokens)
            if score >= SIMILARITY_THRESHOLD and (best is None or score > best.score):
                best = SanctionsHit(name, variant.entry, variant.written, score)
        return best

    def _candidates(self, tokens: tuple[str, ...]) -> set[int]:
        if not self._variants:
            self._index()
        return {index for token in tokens for key in _keys(token) for index in self._by_key.get(key, ())}

    def _index(self) -> None:
        for entry in self.entries:
            for written in (entry.name, *entry.aliases):
                variant_tokens = tuple(screening_tokens(written))
                if not variant_tokens:
                    continue
                self._variants.append(_Variant(variant_tokens, written, entry))
                for token in variant_tokens:
                    for key in _keys(token):
                        self._by_key[key].add(len(self._variants) - 1)


@cache
def bundled_sanctions() -> SanctionsList:
    """The dated OFAC copy that ships with the code."""
    return SanctionsList.from_json(files(BUNDLED_PACKAGE).joinpath(BUNDLED_FILE).read_text(encoding="utf-8"))


def screening_tokens(name: str) -> list[str]:
    return sorted(token for token in name_tokens(name) if token not in CONNECTING_WORDS)


def token_set_similarity(left: tuple[str, ...], right: tuple[str, ...]) -> float:
    if left == right or "".join(left) == "".join(right):
        return 1.0
    return min(_directed(left, right), _directed(right, left))


def jaro_winkler(left: str, right: str) -> float:
    similarity = _jaro(left, right)
    prefix = 0
    for a, b in zip(left[:WINKLER_PREFIX], right[:WINKLER_PREFIX], strict=False):
        if a != b:
            break
        prefix += 1
    return similarity + prefix * WINKLER_SCALE * (1 - similarity)


def _directed(words: tuple[str, ...], partners: tuple[str, ...]) -> float:
    return sum(max(jaro_winkler(word, partner) for partner in partners) for word in words) / len(words)


def _jaro(left: str, right: str) -> float:
    if left == right:
        return 1.0
    if not left or not right:
        return 0.0
    window = max(len(left), len(right)) // 2 - 1
    taken = [False] * len(right)
    matched_left = []
    for i, char in enumerate(left):
        for j in range(max(0, i - window), min(len(right), i + window + 1)):
            if not taken[j] and right[j] == char:
                taken[j] = True
                matched_left.append(char)
                break
    matches = len(matched_left)
    if matches == 0:
        return 0.0
    matched_right = [char for j, char in enumerate(right) if taken[j]]
    transpositions = sum(a != b for a, b in zip(matched_left, matched_right, strict=True)) / 2
    return (matches / len(left) + matches / len(right) + (matches - transpositions) / matches) / 3


def _keys(token: str) -> set[str]:
    """The word and the word with any one letter deleted: two words one edit apart share at least one key."""
    if len(token) <= SHORT_WORD:
        return {token}
    return {token, *(token[:i] + token[i + 1 :] for i in range(len(token)))}
