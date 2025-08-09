
from __future__ import annotations
from typing import Dict
from dataclasses import dataclass
from lxml import etree
import io

@dataclass
class PCSDefinitions:
    # Minimal placeholder; real file can include operation definitions, etc.
    ops: Dict[str, str]

    @classmethod
    def from_bytes(cls, xml_bytes: bytes) -> 'PCSDefinitions':
        # Parse <axis pos="3"> Operation labels/definitions for tooltips.
        ops = {}
        ctx = etree.iterparse(io.BytesIO(xml_bytes), events=("end",))
        current_pos = None
        for ev, el in ctx:
            tag = el.tag.split('}')[-1]
            if tag == "axis":
                try:
                    current_pos = int(el.get("pos"))
                except Exception:
                    current_pos = None
            elif tag == "label" and current_pos == 3:
                code = el.get("code")
                text = (el.text or "").strip()
                if code and text:
                    ops[code] = text
            el.clear()
        return cls(ops)

    def describe_code(self, code: str, engine) -> str:
        # Decompose by axis and show labels; include op text if known
        code = code.strip().upper()
        if len(code) != 7:
            return "Needs 7 characters."
        parts = []
        parts.append(f"Section {code[0]}: {engine._label(1, code[0])}")
        parts.append(f"Body System {code[1]}: {engine._label(2, code[1])}")
        op = engine._label(3, code[2])
        op_more = self.ops.get(code[2])
        if op_more and op_more != op:
            parts.append(f"Operation {code[2]}: {op} — {op_more}")
        else:
            parts.append(f"Operation {code[2]}: {op}")
        parts.append(f"Body Part {code[3]}: {engine._label(4, code[3])}")
        parts.append(f"Approach {code[4]}: {engine._label(5, code[4])}")
        parts.append(f"Device {code[5]}: {engine._label(6, code[5])}")
        parts.append(f"Qualifier {code[6]}: {engine._label(7, code[6])}")
        return "\n".join(parts)
