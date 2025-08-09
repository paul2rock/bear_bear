
# ICD-10-PCS Coder (2025) — Streamlit

A Streamlit app that extracts candidate ICD-10-PCS codes from procedure notes (PDF/DOCX/TXT) and **strictly validates** them against the official **2025 PCS Tables**. It also uses Gemini 2.0 Flash (if you provide an API key) to propose codes from free‑text notes, *then* enforces legality using the tables.

## Quick start (Streamlit Cloud via GitHub)

1. Push this folder to a public GitHub repo.
2. In Streamlit Cloud, set the app file to `app.py`.
3. Add a secret named `GEMINI_API_KEY` in **App Settings → Secrets** if you want LLM suggestions.
4. Run. In the sidebar, upload the three XMLs (**icd10pcs_tables_2025.xml**, **icd10pcs_index_2025.xml**, **icd10pcs_definitions_2025.xml**). They are *not* bundled to avoid licensing concerns.

> If you prefer local dev: `pip install -r requirements.txt && streamlit run app.py`

## What’s included

- **Real tables engine** (no stub): builds a prefix trie from the official tables; supports `is_valid(code)` and `expand(prefix)`.
- **Index/Definitions helpers** for UI lookups.
- **Document ingestion** with `pypdf` and `python-docx`.
- **Gemini** helper (optional; app still works without it).

## Why the app requires your XMLs at runtime
ICD-10-PCS content is copyrighted. To keep the repo clean, the app expects you to upload the official XMLs at runtime (see sidebar).

## Roadmap hooks (placeholders provided)
- Body Part Key.md, Device Aggregation Table.md, Device Key.md, Substance Key.md
- A **Procedure Checklist** folder with human-authored .md guides for specific procedures

Drop them into the repo later; the app will surface them in the sidebar and use them when present.
