
from __future__ import annotations
from typing import List, Dict, Optional, Tuple
from lxml import etree
from rapidfuzz import process, fuzz
import io

class PCSIndex:
    def __init__(self, items: List[Dict]):
        # items: [{path, titles:[...], codes:[...]}]
        self.items = items
        self._keys = [" > ".join(it["titles"]) for it in items]

    @classmethod
    def from_bytes(cls, xml_bytes: bytes) -> 'PCSIndex':
        # Walk the XML preserving hierarchy and capturing codes under each node
        root = etree.fromstring(xml_bytes)
        items: List[Dict] = []

        def walk(node, titles):
            # capture this node if it has a title
            title_el = node.find("title")
            my_title = title_el.text.strip() if title_el is not None and title_el.text else None
            cur_titles = titles + ([my_title] if my_title else [])

            # gather codes anywhere under this node's immediate level
            codes = []
            for el in node.findall("./code"):
                if el.text: codes.append(el.text.strip())
            for el in node.findall("./codes"):
                if el.text: codes.append(el.text.strip())

            # Only store if we have a title
            if my_title:
                items.append({
                    "titles": cur_titles,
                    "codes": list(dict.fromkeys(codes)),  # unique
                })

            # Recurse into child <term> nodes
            for child in node.findall("term"):
                walk(child, cur_titles)

        for letter in root.findall("letter"):
            letter_title = letter.findtext("title","").strip()
            for main in letter.findall("mainTerm"):
                walk(main, [letter_title])

        return cls(items)

    def search(self, query: str, limit: int = 25, score_cutoff: int = 70) -> List[Dict]:
        if not self.items or not query.strip():
            return []
        keys = [" > ".join(it["titles"]) for it in self.items]
        results = process.extract(query, keys, scorer=fuzz.token_set_ratio, limit=limit, score_cutoff=score_cutoff)
        out = []
        for text, score, idx in results:
            it = dict(self.items[idx])
            it["path"] = text
            it["score"] = int(score)
            out.append(it)
        return out
