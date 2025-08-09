
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple, Any
from lxml import etree
from rapidfuzz import fuzz, process

@dataclass
class IndexEntry:
    path: str               # hierarchical path of titles
    title: str              # current node title
    codes: List[str]        # codes found under this node
    uses: List[str]         # 'use' synonyms
    sees: List[str]         # 'see' references (raw text)

class IndexStore:
    def __init__(self, entries: List[IndexEntry]):
        self.entries = entries
        # Build searchable corpus of phrases
        self.corpus = [e.path for e in entries]

    @classmethod
    def from_bytes(cls, b: bytes) -> "IndexStore":
        root = etree.fromstring(b)
        entries: List[IndexEntry] = []

        def collect(node, path_parts):
            # Titles
            title_el = node.find("title")
            title = title_el.text if title_el is not None else ""
            path = " > ".join([*path_parts, title]).strip(" >")

            # Codes
            codes = [c.text for c in node.findall(".//code")] + [c.text for c in node.findall(".//codes")]
            codes = [c.strip() for c in codes if c is not None]

            # Uses
            uses = [u.text for u in node.findall(".//use") if u is not None and u.text]

            # See refs (store raw inner text)
            sees = []
            for sel in node.findall(".//see"):
                # Combine element text and any child text
                txt = "".join(sel.itertext())
                if txt:
                    sees.append(txt)

            if title:
                entries.append(IndexEntry(path=path, title=title, codes=codes, uses=uses, sees=sees))

            # Recurse into term children
            for child in node.findall("term"):
                collect(child, [*path_parts, title])

        # Walk all letters → mainTerm nodes
        for letter in root.findall("letter"):
            for main in letter.findall("mainTerm"):
                collect(main, [letter.findtext("title","")])

        return cls(entries)

    def search(self, phrase: str, topk: int = 25, score_cutoff: int = 75) -> List[Tuple[str, int, IndexEntry]]:
        if not phrase.strip():
            return []
        results = process.extract(
            query=phrase,
            choices=self.corpus,
            scorer=fuzz.token_set_ratio,
            limit=topk,
            score_cutoff=score_cutoff
        )
        # Map back to entries by path
        path_to_entry = {e.path: e for e in self.entries}
        hits: List[Tuple[str,int,IndexEntry]] = []
        for path, score, _ in results:
            entry = path_to_entry.get(path)
            if entry:
                hits.append((path, score, entry))
        return hits
