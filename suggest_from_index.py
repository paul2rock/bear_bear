
from __future__ import annotations
from typing import List, Dict, Tuple
import re
from rapidfuzz import fuzz
from pcs_tables_engine import TablesEngine
from pcs_index import PCSIndex

CODE_RE = re.compile(r'^[0-9A-Z]{3,7}$')

def _ngram_terms(text: str, n=(1,2,3)) -> List[str]:
    tokens = re.findall(r"[A-Za-z0-9]+", text.lower())
    grams = []
    for k in n:
        for i in range(len(tokens)-k+1):
            grams.append(" ".join(tokens[i:i+k]))
    # Dedup while preserving order
    seen = set(); out=[]
    for g in grams:
        if g not in seen:
            seen.add(g); out.append(g)
    return out[:500]

def suggest_from_index(note_text: str, index: PCSIndex, engine: TablesEngine, topk_hits=40, max_codes=100) -> List[str]:
    # Search index with a single combined query (top), plus some targeted n-grams.
    base_hits = index.search(note_text, limit=topk_hits)
    # Pull more signal from n-grams (short phrases like "arthroplasty knee", "arthroscopy", etc.)
    grams = _ngram_terms(note_text, n=(2,3))
    for g in grams[:50]:
        base_hits += index.search(g, limit=5)

    # Collect raw code tokens from hits
    raw = []
    for hit in base_hits:
        for c in (hit.get("codes") or []):
            # some nodes store multi-codes in a single string; split on non-alnum
            for tok in re.split(r'[^0-9A-Z]+', c.upper()):
                if CODE_RE.match(tok):
                    raw.append((tok, hit["path"], hit["score"]))

    # Expand using tables where needed; keep only legal 7-char codes
    scored: Dict[str, float] = {}
    for tok, path, score in raw:
        if len(tok) == 7 and engine.is_valid(tok):
            scored[tok] = max(scored.get(tok, 0), score/100.0 + 0.2)  # bonus for exact 7-char from index
        elif 3 <= len(tok) <= 6:
            # use strict table expansion; only legal completions returned
            for code in engine.expand(tok, limit=80):
                scored[code] = max(scored.get(code, 0), score/100.0)

    # Rank by score
    ranked = sorted(scored.items(), key=lambda x: (-x[1], x[0]))
    return [c for c,_ in ranked[:max_codes]]
