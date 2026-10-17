"""Refresh the OFAC SDN copy that R14 screens against: download, normalize to compact JSON, write it dated.

Usage: uv run python scripts/update_ofac.py

Downloads sdn.csv (names and programs), alt.csv (aliases) and add.csv (countries) from the Treasury's public list
(https://www.treasury.gov/ofac/downloads/) and writes custodio/dataset/ofac/sdn.json with one entry per SDN uid:
name, aliases, countries, programs and type. `published_on` is the list's Last-Modified date; commit the new file so
the copy in use is always versioned. Nothing here is a decision: R14 only escalates a hit to a person.
"""

from __future__ import annotations

import csv
import io
import json
import sys
from collections import defaultdict
from datetime import UTC, date, datetime
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx

DOWNLOADS = "https://www.treasury.gov/ofac/downloads/"
FILES = ("sdn.csv", "alt.csv", "add.csv")
TARGET = Path(__file__).resolve().parents[1] / "custodio" / "dataset" / "ofac" / "sdn.json"
NULL = "-0-"
ENCODING = "latin-1"  # the Treasury publishes plain ASCII; latin-1 reads any stray byte without failing
TIMEOUT_SECONDS = 120.0
SDN_UID, SDN_NAME, SDN_TYPE, SDN_PROGRAM = 0, 1, 2, 3
ALT_UID, ALT_NAME = 0, 3
ADD_UID, ADD_COUNTRY = 0, 4
MIN_COLUMNS = 5


def parse_entries(sdn: str, alt: str, add: str) -> list[dict[str, object]]:
    aliases: defaultdict[str, list[str]] = defaultdict(list)
    for row in _rows(alt):
        if (name := _value(row[ALT_NAME])) is not None:
            aliases[row[ALT_UID]].append(name)
    countries: defaultdict[str, list[str]] = defaultdict(list)
    for row in _rows(add):
        country = _value(row[ADD_COUNTRY])
        if country is not None and country not in countries[row[ADD_UID]]:
            countries[row[ADD_UID]].append(country)
    return [
        {
            "uid": int(row[SDN_UID]),
            "name": row[SDN_NAME],
            "aliases": aliases[row[SDN_UID]],
            "countries": countries[row[SDN_UID]],
            "programs": _programs(row[SDN_PROGRAM]),
            "type": _value(row[SDN_TYPE]),
        }
        for row in _rows(sdn)
    ]


def build_copy(
    entries: list[dict[str, object]], *, published_on: date | None, downloaded_on: date, source: str
) -> dict[str, object]:
    return {
        "source": source,
        "published_on": published_on.isoformat() if published_on else None,
        "downloaded_on": downloaded_on.isoformat(),
        "entries": entries,
    }


def to_json(copy: dict[str, object]) -> str:
    """Compact, with one entry per line, so a refresh reads as a reviewable diff."""
    header = {key: value for key, value in copy.items() if key != "entries"}
    entries = copy["entries"]
    assert isinstance(entries, list)
    lines = ",\n".join(json.dumps(entry, ensure_ascii=False, separators=(",", ":")) for entry in entries)
    head = json.dumps(header, ensure_ascii=False, separators=(",", ":"))[:-1]
    return f'{head},"entries":[\n{lines}\n]}}\n'


def main() -> int:
    texts, published_on = {}, None
    with httpx.Client(follow_redirects=True, timeout=TIMEOUT_SECONDS) as client:
        for name in FILES:
            response = client.get(DOWNLOADS + name)
            response.raise_for_status()
            texts[name] = response.content.decode(ENCODING)
            if name == "sdn.csv" and "last-modified" in response.headers:
                published_on = parsedate_to_datetime(response.headers["last-modified"]).date()
    entries = parse_entries(texts["sdn.csv"], texts["alt.csv"], texts["add.csv"])
    copy = build_copy(entries, published_on=published_on, downloaded_on=datetime.now(UTC).date(), source=DOWNLOADS)
    TARGET.write_text(to_json(copy), encoding="utf-8")
    print(json.dumps({"entries": len(entries), "published_on": copy["published_on"], "file": str(TARGET)}))
    return 0


def _rows(text: str) -> list[list[str]]:
    return [[cell.strip() for cell in row] for row in csv.reader(io.StringIO(text)) if len(row) >= MIN_COLUMNS]


def _value(cell: str) -> str | None:
    return None if cell in ("", NULL) else cell


def _programs(cell: str) -> list[str]:
    value = _value(cell)
    return [part.strip("[] ") for part in value.split("] [")] if value else []


if __name__ == "__main__":
    sys.exit(main())
