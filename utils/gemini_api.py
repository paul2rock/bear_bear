
from typing import List, Dict, Any
import os

# Uses the new google-genai client:
# pip install google-genai
from google import genai

BASE_SYS_MSG = """You are assisting with ICD-10-PCS coding.
- Never invent a PCS code; all codes come from the official Index/Tables.
- Your job: re-rank given candidate codes and write a short, coder-friendly rationale.
- If documentation is ambiguous, prefer multiple codes with clear notes about ambiguity.
"""

def gemini_rerank_and_explain(api_key: str, model: str, text: str, suggestions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not api_key:
        return suggestions

    client = genai.Client(api_key=api_key)

    # Build prompt with current candidates
    candidates_str = "\n".join([
        f"- {s.get('code','(partial)')} | conf={s.get('confidence',0):.2f} | why={s.get('why','')} | evidence={'; '.join(s.get('evidence',[])[:3])}"
        for s in suggestions
    ])

    prompt = f"""{BASE_SYS_MSG}

Procedure note:
{text[:4000]}

Candidates to re-rank and explain:
{candidates_str}

Return JSON list with keys: code, confidence, why (1–3 lines), evidence (<=3 short quotes).
"""

    res = client.models.generate_content(
        model=model,
        contents=prompt,
        config={
            "temperature": 0.2,
            "max_output_tokens": 800,
            "response_mime_type": "application/json"
        }
    )

    try:
        enriched = res.text
        import json
        parsed = json.loads(enriched)
        # Merge back into original list (keep only codes we already proposed)
        codes_set = {s.get("code") for s in suggestions}
        final = []
        for item in parsed:
            if item.get("code") in codes_set:
                final.append({
                    **next(s for s in suggestions if s.get("code")==item.get("code")),
                    "confidence": float(item.get("confidence", 0)),
                    "why": item.get("why", ""),
                    "evidence": item.get("evidence", [])
                })
        # Fallback if parse fails to preserve original order
        return final or suggestions
    except Exception:
        return suggestions
