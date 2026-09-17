from __future__ import annotations

from pathlib import Path


def read_transcript(uploaded_file) -> str:
    suffix = Path(uploaded_file.name).suffix.lower()
    if suffix in {".txt", ".md", ".csv"}:
        return uploaded_file.getvalue().decode("utf-8", errors="replace")
    if suffix == ".docx":
        from docx import Document
        doc = Document(uploaded_file)
        return "\n".join(p.text for p in doc.paragraphs)
    if suffix == ".pdf":
        from pypdf import PdfReader
        reader = PdfReader(uploaded_file)
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    raise ValueError("Supported transcript files: TXT, MD, CSV, DOCX, PDF.")
