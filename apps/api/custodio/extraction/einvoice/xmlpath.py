"""Finding values in an element tree while keeping the readable path each one came from."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from xml.etree.ElementTree import Element

from custodio.extraction.einvoice.model import XmlValue


@dataclass(frozen=True)
class Node:
    element: Element
    path: str
    namespaces: Mapping[str, str]

    def find(self, path: str) -> Node | None:
        found = self.element.find(path, dict(self.namespaces))
        return None if found is None else Node(found, f"{self.path}/{path}", self.namespaces)

    def find_all(self, path: str) -> list[Node]:
        found = self.element.findall(path, dict(self.namespaces))
        return [Node(element, f"{self.path}/{path}", self.namespaces) for element in found]

    def text(self, path: str) -> XmlValue | None:
        node = self.find(path)
        return node.own_text() if node else None

    def own_text(self) -> XmlValue | None:
        text = (self.element.text or "").strip()
        return XmlValue(text, self.path) if text else None

    def attribute(self, name: str) -> XmlValue | None:
        text = (self.element.get(name) or "").strip()
        return XmlValue(text, f"{self.path}/@{name}") if text else None


def all_text(root: Element) -> str:
    """Every text node and attribute value of the tree, one per line."""
    pieces: list[str] = []
    for element in root.iter():
        pieces.extend(value for value in element.attrib.values() if value.strip())
        pieces.extend(text.strip() for text in (element.text, element.tail) if text and text.strip())
    return "\n".join(pieces)
