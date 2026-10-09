import base64, io, json, os
import pandas as pd
import streamlit as st
import anthropic

st.set_page_config(page_title="Invoice to Excel", page_icon="🧾", layout="wide")

def secret(name):
    try:
        return st.secrets[name]
    except Exception:
        return os.getenv(name, "")

# Optional access code so only your paying clients can use it
APP_PASSWORD = secret("APP_PASSWORD")
if APP_PASSWORD:
    if st.text_input("Access code", type="password") != APP_PASSWORD:
        st.info("Enter your access code to continue.")
        st.stop()

client = anthropic.Anthropic(api_key=secret("ANTHROPIC_API_KEY"))
MODEL = "claude-sonnet-5-5"

PROMPT = """Extract data from this Indian GST invoice. Reply with ONLY a JSON object, no other text:
{"invoice_no": "", "invoice_date": "DD-MM-YYYY", "seller_name": "", "seller_gstin": "",
 "buyer_name": "", "buyer_gstin": "", "taxable_value": 0, "cgst": 0, "sgst": 0, "igst": 0, "total_amount": 0}
Use null if a field is missing. Numbers must be plain numbers without commas or currency symbols."""

def extract(file):
    data = base64.standard_b64encode(file.getvalue()).decode()
    name = file.name.lower()
    if name.endswith(".pdf"):
        block = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}}
    else:
        mt = "image/png" if name.endswith(".png") else "image/jpeg"
        block = {"type": "image", "source": {"type": "base64", "media_type": mt, "data": data}}
    resp = client.messages.create(
        model=MODEL, max_tokens=1000,
        messages=[{"role": "user", "content": [block, {"type": "text", "text": PROMPT}]}],
    )
    text = resp.content[0].text.replace("```json", "").replace("```", "").strip()
    return json.loads(text)

st.title("🧾 Invoice to Excel")
st.caption("Upload invoices (PDF, JPG, PNG). Get a ready Excel sheet. Please check the numbers before filing.")

files = st.file_uploader("Upload invoices", type=["pdf", "jpg", "jpeg", "png"], accept_multiple_files=True)

if files and st.button("Extract data", type="primary"):
    rows, bar = [], st.progress(0)
    for i, f in enumerate(files):
        try:
            row = extract(f)
        except Exception as e:
            row = {"error": str(e)[:80]}
        row["file"] = f.name
        rows.append(row)
        bar.progress((i + 1) / len(files))
    st.session_state["df"] = pd.DataFrame(rows)

if "df" in st.session_state:
    st.subheader("Review and edit")
    df = st.data_editor(st.session_state["df"], num_rows="dynamic", use_container_width=True)
    buf = io.BytesIO()
    df.to_excel(buf, index=False)
    st.download_button("⬇️ Download Excel", buf.getvalue(), "invoices.xlsx",
                       "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
