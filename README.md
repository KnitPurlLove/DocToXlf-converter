# DocToXlf-converter
This applet allows you create an xlf file with source and target translation units if you provide it with the source xlf and the bilingual Word document or a CSV file.

# XLF Target Populator

Simple Streamlit app that inserts <target> elements into XLIFF 1.2 files using translations provided in CSV or DOCX.

## Files
- app.py: Streamlit app
- xlf_utils.py: helper functions
- requirements.txt

## Local run (quick)
1. Clone repo:
   git clone <your-repo-url>
   cd <repo>

2. Create virtualenv & install:
   python -m venv venv
   source venv/bin/activate   # Windows: venv\Scripts\activate
   pip install -r requirements.txt

3. Run Streamlit locally:
   streamlit run app.py

Open the URL printed by Streamlit (usually http://localhost:8501).

## Deploy to Streamlit Community Cloud
1. Push this repo to GitHub.
2. Sign in to https://share.streamlit.io with your GitHub account.
3. Click "New app" and connect the repo + branch, set `app.py` as entrypoint.
4. Deploy. Share the public URL with users.

## Notes
- CSV must be UTF-8 encoded.
- DOCX must contain a table where Column2 = Source and Column3 = Target (Column1 ignored).
- The script matches text by normalized exact matching by default. Use fuzzy matching if needed.
- Always test on a copy of your XLF first.
