import streamlit as st
import requests
import time
import os
from pathlib import Path

import PyPDF2
from docx import Document

# ================= CONFIG =================
API_URL = "http://192.168.1.252:11434"
MODEL = "deepseek-r1:70b"
UPLOAD_DIR = "uploads"

os.makedirs(UPLOAD_DIR, exist_ok=True)

st.set_page_config(
    page_title="DeepSeek R1 70B Document Simplifier",
    layout="wide"
)

# ================= CONNECTION =================
def test_connection():
    try:
        r = requests.get(f"{API_URL}/api/tags", timeout=10)
        if r.status_code == 200:
            models = [m["name"] for m in r.json().get("models", [])]
            return f"✅ Connected to {MODEL}" if MODEL in models else f"❌ {MODEL} not found"
        return f"❌ Ollama error {r.status_code}"
    except Exception as e:
        return f"❌ Cannot connect: {e}"

# ================= FILE EXTRACTION =================
def extract_text_from_file(file_path: str):
    ext = Path(file_path).suffix.lower()

    if ext == ".pdf":
        with open(file_path, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            return "\n\n".join(p.extract_text() or "" for p in reader.pages).strip()

    if ext == ".docx":
        doc = Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs).strip()

    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read().strip()

    return ""

# ================= SIMPLIFICATION =================
def deepseek_simplify(text, max_length=4000):
    prompt = f"""
Convert ONLY technical terms to simple business language.
Preserve formatting and structure.
Do NOT summarize or shorten.
Preserve bold, headings, bullet points
Preserve structure exactly
Do NOT change font sizes

TEXT:
{text[:max_length]}

SIMPLIFIED:
"""

    start = time.time()

    r = requests.post(
        f"{API_URL}/api/generate",
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 2048
            },
        },
        timeout=500,
    )

    simplified = r.json().get("response", "").strip()

    return {
        "original": text,
        "simplified": simplified,
        "time": time.time() - start,
        "original_length": len(text),
        "simplified_length": len(simplified),
    }

# ================= UI =================
st.title("📄 DeepSeek R1 70B – Technical to Business Document Simplifier")

status = test_connection()
st.info(status)

if not status.startswith("✅"):
    st.stop()

# ---------------- Input ----------------
col1, col2 = st.columns(2)

with col1:
    text_input = st.text_area(
        "✍️ Paste Technical Text",
        height=300,
        placeholder="Paste technical document here..."
    )

with col2:
    uploaded_file = st.file_uploader(
        "📂 Upload File (PDF / DOCX / TXT)",
        type=["pdf", "docx", "txt"]
    )

# ---------------- Action ----------------
if st.button("🚀 Simplify Document", use_container_width=True):

    if uploaded_file:
        file_path = os.path.join(UPLOAD_DIR, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.read())
        input_text = extract_text_from_file(file_path)
    else:
        input_text = text_input.strip()

    if not input_text or len(input_text) < 10:
        st.error("❌ Please provide valid text or upload a file")
        st.stop()

    with st.spinner("🧠 DeepSeek is simplifying..."):
        result = deepseek_simplify(input_text)

    # ---------------- Output ----------------
    st.success("✅ Simplification Complete")

    st.subheader("📘 Simplified Output")
    st.text_area(
        "Business-Friendly Version",
        value=result["simplified"],
        height=350
    )

    with st.expander("📊 Statistics"):
        st.write(f"⏱ Time Taken: {result['time']:.2f} seconds")
        st.write(f"📄 Original Length: {result['original_length']} characters")
        st.write(f"📝 Simplified Length: {result['simplified_length']} characters")

    with st.expander("🧾 Original Text (Preview)"):
        st.text_area(
            "Original",
            value=result["original"][:1500],
            height=300
        )
