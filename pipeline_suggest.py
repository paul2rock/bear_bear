
from __future__ import annotations
from typing import List, Set
import re

from pcs_index import PCSIndex
from pcs_tables_engine import TablesEngine

# Minimal clinical NLP: harvest candidate terms (lowercased, dedup), keep multi-word spans.
def _extract_terms(text: str) -> List[str]:
    text = re.sub(r"[^A-Za-z0-9\-/\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # keep longer n-grams as one query string
    # bias to words that often show in op notes
    keep = []
    for chunk in re.split(r"[.;\n]", text):
        c = chunk.strip()
        if len(c) >= 6 and any(w in c.lower() for w in [
            "arthro", "arthros", "debrid", "biopsy", "excision", "extraction", "resection",
            "fusion", "arthrodesis", "arthroplasty", "open", "percutaneous", "endoscopic",
            "arthroscopic", "laparosc", "insertion", "repair", "replacement", "supplement",
            "transfer", "bypass", "dilation", "drainage"
        ]):
            keep.append(c)
    # always include the whole text (bounded) as a fuzzy anchor
    keep.append(text[:4000])
    # dedup preserving order
    seen = set(); out = []
    for k in keep:
        if k not in seen:
            out.append(k); seen.add(k)
    return out

def suggest_codes_from_note(text: str, index: PCSIndex, engine: TablesEngine, topk: int = 50) -> List[str]:
    if not engine or not index:
        return []
    terms = _extract_terms(text)
    # search Index for each term; collect codes (full or prefixes) found on the path
    stems: Set[str] = set()
    for t in terms:
        hits = index.search(t, limit=topk) or []
        for h in hits:
            # codes field may contain a sequence like "0JH" or "0JH6"
            codes = (h.get("codes") or "").split()
            for c in codes:
                token = re.sub(r"[^0-9A-Z]", "", c.upper())
                if 1 <= len(token) <= 7:
                    stems.add(token)
    # Now expand + validate using the tables
    final: Set[str] = set()
    for s in stems:
        if len(s) == 7 and engine.is_valid(s):
            final.add(s)
        elif 1 <= len(s) < 7:
            # expand
            for e in engine.expand(s, limit=500):
                if engine.is_valid(e):
                    final.add(e)
    # return sorted list
    return sorted(final)
