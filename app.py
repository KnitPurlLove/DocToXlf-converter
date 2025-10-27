# app.py
import streamlit as st
import tempfile, os
from xlf_utils import build_mapping_from_csv, build_mapping_from_docx, apply_mapping_to_xlf

st.set_page_config(page_title="XLF target populator", layout="centered")
st.title("Populate XLF <target> from CSV or DOCX")

st.markdown("""
Upload:
- Source-only XLIFF (.xlf/.xliff)
- Either a bilingual CSV (Source,Target) **or** a bilingual DOCX (table with columns: ignore, Source, Target)
Options:
- Preserve source inline tags in `<target>` (keeps bold/italic/BR formatting)
- Fuzzy matching (for near-miss matches)
""")

uploaded_xlf = st.file_uploader("Upload XLIFF (.xlf/.xliff)", type=["xlf","xliff"])
use_csv = st.checkbox("Use CSV (otherwise use DOCX)", value=True)
uploaded_csv = None
uploaded_docx = None
if use_csv:
    uploaded_csv = st.file_uploader("Upload bilingual CSV (Source,Target)", type=["csv"])
else:
    uploaded_docx = st.file_uploader("Upload bilingual Word (.docx) (table: ignore, Source, Target)", type=["docx"])

preserve_tags = st.checkbox("Preserve inline tags (copy source formatting)", value=False)
fuzzy = st.checkbox("Try fuzzy matching", value=False)
fuzzy_cutoff = st.slider("Fuzzy similarity cutoff (%)", min_value=60, max_value=95, value=85) / 100.0

if st.button("Run"):
    if not uploaded_xlf:
        st.error("Please upload the XLIFF file.")
    elif use_csv and not uploaded_csv:
        st.error("Please upload the bilingual CSV.")
    elif (not use_csv) and not uploaded_docx:
        st.error("Please upload the bilingual DOCX.")
    else:
        with tempfile.TemporaryDirectory() as tmpdir:
            xlf_path = os.path.join(tmpdir, uploaded_xlf.name)
            with open(xlf_path, "wb") as f:
                f.write(uploaded_xlf.getbuffer())

            if use_csv:
                csv_path = os.path.join(tmpdir, uploaded_csv.name)
                with open(csv_path, "wb") as f:
                    f.write(uploaded_csv.getbuffer())
                mapping = build_mapping_from_csv(csv_path)
            else:
                docx_path = os.path.join(tmpdir, uploaded_docx.name)
                with open(docx_path, "wb") as f:
                    f.write(uploaded_docx.getbuffer())
                mapping = build_mapping_from_docx(docx_path)

            st.write(f"Mapping entries found: {len(mapping)}")
            out_name = os.path.splitext(uploaded_xlf.name)[0] + '.updated.xlf'
            out_path = os.path.join(tmpdir, out_name)

            inserted, unmatched = apply_mapping_to_xlf(xlf_path, mapping, out_path,
                                                     preserve_tags=preserve_tags,
                                                     fuzzy=fuzzy,
                                                     fuzzy_cutoff=fuzzy_cutoff,
                                                     preview=True)
            st.success(f"Inserted/updated {inserted} <target> elements.")
            if unmatched:
                st.info(f"{len(unmatched)} unmatched segments (first 10 shown).")
                for u in unmatched[:10]:
                    st.write("-", u[:300] + ("..." if len(u)>300 else ""))

            with open(out_path, "rb") as f:
                st.download_button("Download updated XLF", f.read(), file_name=out_name, mime="application/xml")
