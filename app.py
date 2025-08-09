
import os
import io
import re
import json
import time
from typing import List, Dict, Optional, Tuple
import streamlit as st

from pcs_tables_engine import TablesEngine, TablesTrie
from pcs_index import PCSIndex
from suggest_from_index import suggest_from_index
from pcs_definitions import PCSDefinitions
from gemini_client import GeminiHelper
from utils_ingest import extract_text_from_upload

st.set_page_config(page_title="ICD-10-PCS Coder (2025)", layout="wide")

st.title("ICD-10-PCS Coder (2025)")
st.caption("Upload official XMLs in the sidebar, then analyze procedure notes and validate PCS codes.")

with st.sidebar:
    st.header("1) Load Official XMLs")
    tables_xml = st.file_uploader("icd10pcs_tables_2025.xml", type=["xml"])
    index_xml = st.file_uploader("icd10pcs_index_2025.xml", type=["xml"])
    defs_xml = st.file_uploader("icd10pcs_definitions_2025.xml", type=["xml"])

    st.markdown("---")
    st.header("Optional Knowledge")
    bp_key = st.file_uploader("Body Part Key.md", type=["md"], key="bpkey")
    dev_agg = st.file_uploader("Device Aggregation Table.md", type=["md"], key="devagg")
    dev_key = st.file_uploader("Device Key.md", type=["md"], key="devkey")
    sub_key = st.file_uploader("Substance Key.md", type=["md"], key="subkey")

    proc_checklist_files = st.file_uploader("Procedure Checklist (.md, multiple)", type=["md"], accept_multiple_files=True)

    st.markdown("---")
    st.header("Gemini Settings (optional)")
    model_name = st.text_input("Model", value="gemini-2.0-flash", help="Adjust if your account uses a different name.")
    use_llm = st.toggle("Use Gemini to propose codes", value=False)
    temperature = st.slider("Temperature", 0.0, 1.0, 0.2, 0.05)

    st.caption("Set GEMINI_API_KEY in Streamlit Secrets. App still works without the LLM.")

@st.cache_resource(show_spinner=True)
def build_tables_engine(xml_bytes: bytes) -> TablesEngine:
    return TablesEngine.from_bytes(xml_bytes)

@st.cache_resource(show_spinner=True)
def load_index(xml_bytes: Optional[bytes]) -> Optional[PCSIndex]:
    if not xml_bytes:
        return None
    return PCSIndex.from_bytes(xml_bytes)

@st.cache_resource(show_spinner=True)
def load_definitions(xml_bytes: Optional[bytes]) -> Optional[PCSDefinitions]:
    if not xml_bytes:
        return None
    return PCSDefinitions.from_bytes(xml_bytes)

engine = None
pcs_index = None
pcs_defs = None
if tables_xml:
    with st.spinner("Building Tables trie (first load may take ~30–90s)..."):
        engine = build_tables_engine(tables_xml.read())
        st.success(f"Loaded {engine.stats()['nodes']} trie nodes from Tables.")
if index_xml:
    pcs_index = load_index(index_xml.read())
if defs_xml:
    pcs_defs = load_definitions(defs_xml.read())

colA, colB = st.columns([3,2], gap="large")

with colA:
    st.header("2) Upload Procedure Notes")
    note_file = st.file_uploader("Upload PDF / DOCX / TXT", type=["pdf","docx","txt"])
    note_text = ""
    if note_file is not None:
        with st.spinner("Extracting text..."):
            note_text = extract_text_from_upload(note_file)
        st.text_area("Extracted Text", value=note_text[:10000], height=280)

    st.header("3) Candidate Codes")
    sug_col1, sug_col2 = st.columns([1,1])
    with sug_col1:
        suggest_from_xml = st.button("Suggest from XMLs (Index→Tables)", use_container_width=True)
    with sug_col2:
        suggest_with_gemini = st.button("Suggest with Gemini (constrained)", use_container_width=True)

    suggest_btn = st.button("Suggest from Index (no AI)", help="Use Index + Tables to auto-propose legal codes from the note text.")
    manual_codes = st.text_area("Paste candidate codes (one per line)", placeholder="0JH60MZ\n0JH80MZ")
    candidates = []
    if manual_codes.strip():
        for line in manual_codes.strip().splitlines():
            token = re.sub(r'[^0-9A-Z]', '', line.strip().upper())
            if token:
                candidates.append(token)

    llm_codes = []

    auto_codes = []
    if suggest_btn and note_text and engine and pcs_index:
        with st.spinner("Mining Index and expanding via Tables..."):
            auto_codes = suggest_from_index(note_text, pcs_index, engine, topk_hits=60, max_codes=150)
        if not auto_codes:
            st.info("No legal codes could be generated from the Index search. Try adding more clinical detail.")
        else:
            st.success(f"Found {len(auto_codes)} candidate code(s) from Index.")

    if use_llm and note_text and engine:
        with st.spinner("Asking Gemini..."):
            helper = GeminiHelper.build_from_secrets(st.secrets, model_name=model_name, temperature=temperature)
            if helper.available:
                llm_codes = helper.propose_pcs_codes(note_text)
            else:
                st.warning("Gemini not configured. Add GEMINI_API_KEY to Secrets.")
    unique = []
    for c in candidates + auto_codes + llm_codes:
        if c not in unique:
            unique.append(c)

    st.header("4) Validation")
    if not engine:
        st.info("Load the Tables XML to enable strict validation.")
    else:
        if unique:
            rows = []
            for code in unique:
                ok = engine.is_valid(code)
                expl = engine.explain(code) if ok else engine.nearest_explanations(code)
                rows.append((code, "✅ Valid" if ok else "❌ Invalid", expl))
            st.dataframe({"Code":[r[0] for r in rows], "Validity":[r[1] for r in rows], "Explanation":[r[2] for r in rows]})
        else:
            st.caption("No candidate codes yet. Paste them or enable Gemini with a note.")

with colB:
    st.header("5) Explore the Tables")
    if engine:
        prefix = st.text_input("Expand from prefix (1–7 chars)", value="0")
        maxn = st.slider("Max expansions", 10, 500, 50, 10)
        if st.button("Expand"):
            with st.spinner("Walking trie..."):
                expansions = engine.expand(prefix, limit=maxn)
            st.write(f"{len(expansions)} result(s):")
            st.code("\n".join(expansions[:maxn]))
    else:
        st.info("Load the Tables XML to explore expansions.")

    st.header("6) Lookups (Index / Definitions)")
    if pcs_index:
        term = st.text_input("Index search term", value="arthroplasty")
        if term:
            matches = pcs_index.search(term, limit=25)
            if matches:
                for m in matches:
                    st.write(f"- **{m['path']}** → {m.get('codes','')} {m.get('code','')}")
            else:
                st.caption("No hits in Index.")
    else:
        st.caption("Upload the Index XML to enable this.")

    if pcs_defs and engine:
        code_for_def = st.text_input("Explain a code")
        if code_for_def:
            if engine.is_potential_prefix(code_for_def):
                st.warning("That looks like a prefix. Enter a full 7-character code.")
            elif engine.is_valid(code_for_def):
                st.write(pcs_defs.describe_code(code_for_def, engine))
            else:
                st.error("Not a legal code in the tables.")

st.markdown("---")
st.caption("Placeholders present for: Body Part Key / Device Aggregation Table / Device Key / Substance Key / Procedure Checklists. Drop them into the repo later — the app will surface them in the sidebar and can be integrated into prompting.")
