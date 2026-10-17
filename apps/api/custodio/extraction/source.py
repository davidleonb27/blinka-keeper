"""The text a reading is checked against: what a person can see, page by page."""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from functools import cached_property

PAGE_SEPARATOR = "\n\n"


@dataclass(frozen=True)
class SourceText:
    pages: tuple[str, ...]

    @cached_property
    def text(self) -> str:
        return PAGE_SEPARATOR.join(self.pages)

    @cached_property
    def _page_starts(self) -> list[int]:
        starts, offset = [], 0
        for page in self.pages:
            starts.append(offset)
            offset += len(page) + len(PAGE_SEPARATOR)
        return starts

    def page_at(self, offset: int) -> int:
        """1-based page number holding the character at `offset` of `text`."""
        return bisect_right(self._page_starts, offset)
