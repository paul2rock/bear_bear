
from dataclasses import dataclass
from typing import List, Optional, Dict
from lxml import etree
import re

VALID_CODE_RE = re.compile(r"^[0-9A-Z]{7}$")

@dataclass
class TablesEngine:
    has_tables: bool
    meta: Dict

    @classmethod
    def none_engine(cls) -> "TablesEngine":
        return cls(has_tables=False, meta={})

    @classmethod
    def from_bytes(cls, b: Optional[bytes]) -> "TablesEngine":
        if not b:
            return cls.none_engine()
        try:
            # NOTE: Full PCS tables parsing is complex. This v1 stores the XML root and basic metadata.
            root = etree.fromstring(b)
            version = root.findtext("version") or "unknown"
            return cls(has_tables=True, meta={"version": version})
        except Exception:
            return cls.none_engine()

    def is_valid(self, code: str) -> bool:
        # If we don't have the tables, only do a superficial validation.
        if not VALID_CODE_RE.match(code or ""):
            return False
        if not self.has_tables:
            # Can't verify against combinational rules; treat as "format valid, tables unknown".
            return False
        # TODO: Implement full combinational validation from tables.
        return False

    def expand_from_prefix(self, prefix: str) -> List[str]:
        # Without full tables, we can't true-expand. Return common defaults when plausible.
        # If prefix length is 3–4, we can try to finish with device 'Z' and qualifier 'Z' and approaches [0,3,X].
        prefix = (prefix or "").strip().upper()
        results: List[str] = []
        if len(prefix) == 3:
            for body_part in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789":
                for approach in ["0","3","4","X"]:  # open, percutaneous, percutaneous endoscopic, external (best-effort)
                    code = prefix + body_part + approach + "Z" + "Z"
                    if VALID_CODE_RE.match(code):
                        results.append(code)
            return results[:200]  # cap
        if len(prefix) == 4:
            for approach in ["0","3","4","X"]:
                code = prefix + approach + "Z" + "Z"
                if VALID_CODE_RE.match(code):
                    results.append(code)
            return results
        return []
