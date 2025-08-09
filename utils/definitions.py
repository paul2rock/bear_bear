
from dataclasses import dataclass
from typing import Dict, Optional, List
from lxml import etree

@dataclass
class Definition:
    key: str
    text: str

class DefinitionsStore:
    def __init__(self, defs: Dict[str, str]):
        self.defs = defs

    @classmethod
    def from_bytes(cls, b: bytes) -> "DefinitionsStore":
        # The exact schema varies; we try to harvest readable definitions for root operations and terms.
        root = etree.fromstring(b)
        defs: Dict[str, str] = {}

        # Generic harvest: capture <definition> under various nodes with a <title> or name
        for node in root.xpath("//*[definition]"):
            title_el = node.find("title")
            key = title_el.text.strip() if title_el is not None and title_el.text else node.tag
            def_el = node.find("definition")
            if def_el is not None:
                text = " ".join("".join(def_el.itertext()).split())
                if text:
                    defs[key] = text

        return cls(defs)

    def find(self, key: str) -> Optional[str]:
        # Simple lookups (exact or case-insensitive)
        if key in self.defs:
            return self.defs[key]
        # Try case-insensitive
        for k, v in self.defs.items():
            if k.lower() == key.lower():
                return v
        return None
