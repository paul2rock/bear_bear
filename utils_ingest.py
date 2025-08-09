
from __future__ import annotations
import io
from typing import BinaryIO
from pypdf import PdfReader
from docx import Document

def extract_text_from_upload(uploaded) -> str:
    name = uploaded.name.lower()
    data = uploaded.read()
    if name.endswith(".txt"):
        try:
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return data.decode("latin-1", errors="ignore")
    if name.endswith(".pdf"):
        buf = io.BytesIO(data)
        reader = PdfReader(buf)
        texts = []
        for page in reader.pages:
            try:
                texts.append(page.extract_text() or "")
            except Exception:
                pass
        return "\n".join(texts)
    if name.endswith(".docx"):
        buf = io.BytesIO(data)
        doc = Document(buf)
        return "\n".join(p.text for p in doc.paragraphs)
    return ""
