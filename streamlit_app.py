
import os
import io
import json
import streamlit as st

from utils.text_extract import extract_text_from_file
from utils.index_parser import IndexStore
from utils.definitions import DefinitionsStore
from utils.tables_engine import TablesEngine
from utils.coder import suggest_codes
from utils.gemini_api import gemini_rerank_and_explain

st.set_page_config(page_title="ICD-10-PCS Assistant", layout="wide")

st.title("ICD-10-PCS Coding Assistant (Index + Tables + Definitions + Gemini)")

with st.sidebar:
    st.header("Reference Files")
    idx_file = st.file_uploader("Upload icd10pcs_index_2025.xml", type=["xml"], key="idx")
    tbl_file = st.file_uploader("Upload icd10pcs_tables_2025.xml", type=["xml"], key="tbl")
    def_file = st.file_uploader("Upload icd10pcs_definitions_2025.xml", type=["xml"], key="def")

    st.markdown("---")
    st.header("Future Integrations (placeholders)")
    st.file_uploader("Body Part Key.md", type=["md"], key="bpkey")
    st.file_uploader("Device Aggregation Table.md", type=["md"], key="devagg")
    st.file_uploader("Device Key.md", type=["md"], key="devkey")
    st.file_uploader("Substance Key.md", type=["md"], key="substkey")
    st.file_uploader(".DS_Store (ignored)", type=[], key="dsstore")
    st.file_uploader("Procedure Checklist Folder (.md files)", type=["md"], accept_multiple_files=True, key="checklists")

    st.markdown("---")
    st.header("Gemini Settings")
    use_gemini = st.checkbox("Use Gemini 2.0 Flash for re-ranking and explanations", value=True)
    api_key = st.text_input("GEMINI_API_KEY", value=os.getenv("GEMINI_API_KEY", ""), type="password")
    gemini_model = st.text_input("Model", value="gemini-2.0-flash")

# Load reference stores (allow defaults from /mnt/data if user didn't upload)
def resolve_default(path_hint):
    if os.path.exists(path_hint):
        return open(path_hint, "rb").read()
    return None

idx_bytes = idx_file.read() if idx_file else resolve_default("/mnt/data/icd10pcs_index_2025.xml")
tbl_bytes = tbl_file.read() if tbl_file else resolve_default("/mnt/data/icd10pcs_tables_2025.xml")
def_bytes = def_file.read() if def_file else resolve_default("/mnt/data/icd10pcs_definitions_2025.xml")

index_store = None
defs_store = None
tables_engine = None

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Index XML", "Loaded" if idx_bytes else "Missing")
with col2:
    st.metric("Tables XML", "Loaded" if tbl_bytes else "Missing")
with col3:
    st.metric("Definitions XML", "Loaded" if def_bytes else "Missing")

if idx_bytes:
    index_store = IndexStore.from_bytes(idx_bytes)

if def_bytes:
    defs_store = DefinitionsStore.from_bytes(def_bytes)

tables_engine = TablesEngine.from_bytes(tbl_bytes) if tbl_bytes else TablesEngine.none_engine()

st.markdown("---")

st.header("Upload Procedure Note")
note_file = st.file_uploader("PDF / DOCX / TXT", type=["pdf", "docx", "txt"])

default_text = st.text_area("...or paste text directly", height=200, value="")

if st.button("Analyze & Suggest PCS Codes", type="primary"):
    if not (note_file or default_text.strip()):
        st.warning("Please upload a note or paste text.")
        st.stop()

    # Extract text
    try:
        if note_file:
            text = extract_text_from_file(note_file)
        else:
            text = default_text
    except Exception as e:
        st.error(f"Failed to extract text: {e}")
        st.stop()

    # Suggest codes
    suggestions = suggest_codes(
        text=text,
        index_store=index_store,
        tables_engine=tables_engine,
        defs_store=defs_store,
    )

    # Optional: rerank/explain with Gemini
    if use_gemini and api_key and suggestions:
        try:
            suggestions = gemini_rerank_and_explain(
                api_key=api_key,
                model=gemini_model,
                text=text,
                suggestions=suggestions
            )
        except Exception as e:
            st.warning(f"Gemini step skipped: {e}")

    if not suggestions:
        st.info("No codes suggested. Try lowering the match threshold or adding more clinical detail.")
    else:
        st.subheader("Suggested PCS Codes")
        # Results table
        import pandas as pd
        df = pd.DataFrame([{
            "Code": s.get("code"),
            "Confidence": round(s.get("confidence", 0), 3),
            "Validated": s.get("validated", False),
            "Reason": s.get("why",""),
            "Evidence": "; ".join(s.get("evidence", [])[:3])
        } for s in suggestions])
        st.dataframe(df, use_container_width=True)

        # Detail expander per code
        for s in suggestions:
            with st.expander(f"Details for {s.get('code','(partial)')}"):
                st.json(s, expanded=False)

        # Download
        st.download_button(
            "Download results (JSON)",
            data=json.dumps(suggestions, indent=2),
            file_name="pcs_results.json",
            mime="application/json"
        )

st.markdown("""
---
**Notes**
- This is an offline-first assistant. It prefers the official XML files (Index/Tables/Definitions) for code generation & validation.
- Gemini is used only for *ranking* and *human-readable explanations*, not for creating codes outside the official tables.
""")
