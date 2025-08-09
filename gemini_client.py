
from __future__ import annotations
from typing import List
import os

try:
    import google.generativeai as genai
except Exception:
    genai = None

SYSTEM_HINT = (
    "You are a medical coding assistant. Given a procedure note, propose ICD-10-PCS codes. "
    "Return only a newline-separated list of 7-character codes (A–Z, 0–9), no commentary."
)

class GeminiHelper:
    def __init__(self, client, model: str, temperature: float):
        self.client = client
        self.model = model
        self.temperature = temperature
        self.available = client is not None

    @classmethod
    def build_from_secrets(cls, secrets, model_name: str = "gemini-2.0-flash", temperature: float = 0.2) -> "GeminiHelper":
        if genai is None:
            return cls(None, model_name, temperature)
        api_key = None
        try:
            api_key = secrets["GEMINI_API_KEY"]
        except Exception:
            api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return cls(None, model_name, temperature)
        genai.configure(api_key=api_key)
        return cls(genai, model_name, temperature)

    def propose_pcs_codes(self, text: str) -> List[str]:
        if not self.available:
            return []
        model = self.client.GenerativeModel(self.model)
        prompt = f"""{SYSTEM_HINT}

Procedure note:
{text}

Return:
- Newline-separated ICD-10-PCS codes only.
- If unsure, propose likely candidates (but avoid non-7-char outputs)."""
        resp = model.generate_content(prompt, generation_config={"temperature": self.temperature})
        content = resp.text if hasattr(resp, "text") else ""
        codes = []
        for line in content.splitlines():
            token = "".join(ch for ch in line.strip().upper() if ch.isalnum())
            if len(token) == 7:
                codes.append(token)
        return codes
