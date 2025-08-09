
from typing import Union
from io import BytesIO
import fitz  # PyMuPDF
import docx

def extract_text_from_file(uploaded_file: Union[BytesIO, "UploadedFile"]) -> str:
    name = uploaded_file.name.lower()
    data = uploaded_file.read()
    if name.endswith(".pdf"):
        return _extract_pdf(data)
    if name.endswith(".docx"):
        return _extract_docx(data)
    if name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")
    raise ValueError("Unsupported file type. Use PDF, DOCX, or TXT.")

def _extract_pdf(b: bytes) -> str:
    text = []
    with fitz.open(stream=b, filetype="pdf") as doc:
        for page in doc:
            text.append(page.get_text())
    return "\n".join(text)

def _extract_docx(b: bytes) -> str:
    bio = BytesIO(b)
    d = docx.Document(bio)
    return "\n".join(p.text for p in d.paragraphs)
