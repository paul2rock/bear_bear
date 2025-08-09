
from typing import List, Dict, Any
import re
from rapidfuzz import fuzz
from .index_parser import IndexStore
from .tables_engine import TablesEngine
from .definitions import DefinitionsStore

# Simple keyword hints for approach & diagnostic qualifier
APPROACH_HINTS = {
    "open": "0",
    "percutaneous": "3",
    "percutaneous endoscopic": "4",
    "endoscopic": "4",
    "arthroscopic": "4",
    "laparoscopic": "4",
    "external": "X"
}

def detect_approach(text: str) -> str:
    t = text.lower()
    for k, v in APPROACH_HINTS.items():
        if k in t:
            return v
    return ""  # unknown

def is_biopsy(text: str) -> bool:
    t = text.lower()
    return any(w in t for w in ["biopsy", "bx", "diagnostic sample", "diagnostic excision"])

def suggest_codes(text: str, index_store: IndexStore, tables_engine: TablesEngine, defs_store: DefinitionsStore) -> List[Dict[str, Any]]:
    if not index_store:
        return []

    # Extract key phrases (very light v1)
    phrases = re.findall(r"[A-Za-z][A-Za-z \-/]{3,}", text)
    query = " ".join(phrases[:60])  # cap length

    hits = index_store.search(query, topk=30, score_cutoff=72)

    approach_ch = detect_approach(text)
    biopsy = is_biopsy(text)

    suggestions: List[Dict[str, Any]] = []
    seen = set()

    for path, score, entry in hits:
        # Prefer codes present in the entry
        for code in entry.codes:
            c = code.strip().upper()
            if len(c) == 7 and c not in seen:
                validated = tables_engine.is_valid(c)
                why = f"Matched Index path: {path} (score {score})."
                if biopsy and c.endswith("Z"):
                    # some tables use qualifier X for diagnostic biopsies (not universal)
                    c = c[:-1] + "X"
                suggestions.append({
                    "code": c,
                    "confidence": min(0.99, score/100.0),
                    "validated": validated,
                    "why": why,
                    "evidence": [path] + entry.uses[:2] + entry.sees[:1]
                })
                seen.add(c)

        # If partial codes exist (e.g., 3-4 chars), try to complete with defaults
        for code in entry.codes:
            c = code.strip().upper()
            if c in seen:
                continue
            if len(c) in (3,4):
                expanded = tables_engine.expand_from_prefix(c)
                if approach_ch:
                    expanded = [e for e in expanded if len(e)==7 and e[4]==approach_ch] or expanded
                # take a few
                for e in expanded[:5]:
                    if e not in seen:
                        suggestions.append({
                            "code": e,
                            "confidence": min(0.85, score/100.0 - 0.05),
                            "validated": tables_engine.is_valid(e),
                            "why": f"Index partial code {c} expanded to plausible codes (tables-lite).",
                            "evidence": [path] + entry.uses[:2] + entry.sees[:1]
                        })
                        seen.add(e)

    # De-dup and sort
    suggestions.sort(key=lambda x: (-x["confidence"], x["code"]))
    return suggestions[:30]
