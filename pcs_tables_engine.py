
from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from lxml import etree
from collections import defaultdict, deque

# --------- Trie data structure ----------
@dataclass
class TrieNode:
    children: Dict[str, 'TrieNode'] = field(default_factory=dict)
    terminal: bool = False

class TablesTrie:
    def __init__(self):
        self.root = TrieNode()
        self.nodes = 1

    def add_code(self, code: str):
        node = self.root
        for ch in code:
            if ch not in node.children:
                node.children[ch] = TrieNode()
                self.nodes += 1
            node = node.children[ch]
        node.terminal = True

    def walk(self, token: str) -> Optional[TrieNode]:
        node = self.root
        for ch in token:
            if ch not in node.children:
                return None
            node = node.children[ch]
        return node

    def expand(self, prefix: str, limit: int = 100) -> List[str]:
        node = self.walk(prefix)
        if not node:
            return []
        out = []
        stack: List[Tuple[str, TrieNode]] = [(prefix, node)]
        while stack and len(out) < limit:
            cur, n = stack.pop()
            if n.terminal and len(cur) == 7:
                out.append(cur)
            for ch, child in n.children.items():
                stack.append((cur + ch, child))
        return sorted(out)

# ------------- Engine ------------------
class TablesEngine:
    def __init__(self, trie: TablesTrie, labels: Dict[int, Dict[str, str]]):
        self.trie = trie
        self.labels = labels  # pos -> code -> label

    @classmethod
    def from_bytes(cls, xml_bytes: bytes) -> 'TablesEngine':
        trie = TablesTrie()
        labels: Dict[int, Dict[str, str]] = defaultdict(dict)

        # Stream parse, picking codes from each pcsTable/pcsRow combination
        ctx = etree.iterparse(io.BytesIO(xml_bytes), events=("start","end"))
        # We will collect axes by pos for each pcsRow, then cartesian product
        import io as _io
        import itertools
        # re-init with BytesIO (above var shadowing)
        ctx = etree.iterparse(_io.BytesIO(xml_bytes), events=("start","end"))
        in_row = False
        axes: Dict[int, List[str]] = {}
        current_axis_pos = None

        for ev, el in ctx:
            tag = el.tag.split('}')[-1]
            if ev == "start" and tag == "pcsRow":
                in_row = True
                axes = {}
            elif ev == "end" and tag == "pcsRow":
                # build all legal 7-char codes from this row
                # pos 1..7 must exist in axes; if some missing, skip
                if all(p in axes for p in range(1,8)):
                    for combo in itertools.product(axes[1], axes[2], axes[3], axes[4], axes[5], axes[6], axes[7]):
                        code = "".join(combo)
                        if len(code) == 7:
                            trie.add_code(code)
                in_row = False
                axes = {}
                el.clear()
            elif in_row and ev == "end" and tag == "axis":
                # axis has @pos, and nested <label code="X">...</label>
                try:
                    pos = int(el.get("pos"))
                except Exception:
                    pos = None
                if pos is not None:
                    values = []
                    for lab in el.findall(".//label"):
                        c = lab.get("code")
                        if c is None:
                            continue
                        values.append(c)
                        # save human label
                        if lab.text:
                            labels[pos][c] = lab.text
                    if values:
                        axes[pos] = values
                el.clear()
            elif ev == "end":
                el.clear()

        return cls(trie, labels)

    def is_valid(self, code: str) -> bool:
        code = code.strip().upper()
        if len(code) != 7: return False
        node = self.trie.walk(code)
        return bool(node and node.terminal)

    def is_potential_prefix(self, token: str) -> bool:
        token = token.strip().upper()
        if not (1 <= len(token) <= 7): return False
        return self.trie.walk(token) is not None

    def expand(self, prefix: str, limit: int = 100) -> List[str]:
        prefix = prefix.strip().upper()
        return self.trie.expand(prefix, limit=limit)

    def stats(self):
        return {"nodes": self.trie.nodes}

    def _label(self, pos: int, ch: str) -> str:
        return self.labels.get(pos, {}).get(ch, ch)

    def explain(self, code: str) -> str:
        code = code.strip().upper()
        if not self.is_valid(code):
            return "Not a legal 2025 PCS code."
        parts = [f"1:{code[0]} = {self._label(1, code[0])}",
                 f"2:{code[1]} = {self._label(2, code[1])}",
                 f"3:{code[2]} = {self._label(3, code[2])}",
                 f"4:{code[3]} = {self._label(4, code[3])}",
                 f"5:{code[4]} = {self._label(5, code[4])}",
                 f"6:{code[5]} = {self._label(6, code[5])}",
                 f"7:{code[6]} = {self._label(7, code[6])}"]
        return " | ".join(parts)

    def nearest_explanations(self, token: str) -> str:
        token = token.strip().upper()
        node = self.trie.walk(token)
        if node is None:
            return "Prefix not in tables; try a shorter start."
        pos = len(token) + 1
        opts = sorted(node.children.keys())
        if not opts:
            return "Prefix is a dead end per tables."
        labels = [f"{pos}:{c}={self._label(pos, c)}" for c in opts]
        return "Next allowed chars → " + ", ".join(labels)
