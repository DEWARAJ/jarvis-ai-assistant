"""JARVIS v6.0 — Word/Excel/PowerPoint/PDF reading and editing."""
from __future__ import annotations
from pathlib import Path

try: from docx import Document; _DOCX = True
except ImportError: _DOCX = False

try: import openpyxl; _XLSX = True
except ImportError: _XLSX = False

try: from pptx import Presentation; _PPTX = True
except ImportError: _PPTX = False

try: import PyPDF2; _PDF = True
except ImportError: _PDF = False

try: from reportlab.pdfgen import canvas; _REPORTLAB = True
except ImportError: _REPORTLAB = False


# ── Word ─────────────────────────────────────────────────────────────────────

def read_docx(path: str) -> str:
    if not _DOCX: return "python-docx not installed."
    try:
        doc = Document(path)
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    except Exception as e: return f"Read error: {e}"


def add_paragraph_to_docx(path: str, text: str, confirmed: bool = False) -> str:
    if not _DOCX: return "python-docx not installed."
    try:
        doc = Document(path) if Path(path).exists() else Document()
        doc.add_paragraph(text)
        doc.save(path)
        return f"Paragraph added to {path}"
    except Exception as e: return f"Write error: {e}"


def find_replace_docx(path: str, find: str, replace: str,
                      confirmed: bool = False) -> str:
    if not _DOCX: return "python-docx not installed."
    try:
        doc = Document(path)
        for p in doc.paragraphs:
            if find in p.text:
                for run in p.runs:
                    if find in run.text:
                        run.text = run.text.replace(find, replace)
        doc.save(path)
        return f"Replaced '{find}' → '{replace}' in {path}"
    except Exception as e: return f"Replace error: {e}"


# ── Excel ─────────────────────────────────────────────────────────────────────

def read_xlsx(path: str, sheet: str | None = None) -> str:
    if not _XLSX: return "openpyxl not installed."
    try:
        wb = openpyxl.load_workbook(path, data_only=True)
        ws = wb[sheet] if sheet else wb.active
        rows = []
        for row in ws.iter_rows(values_only=True):
            rows.append("\t".join(str(c) if c is not None else "" for c in row))
        return "\n".join(rows[:100])
    except Exception as e: return f"Read error: {e}"


def write_xlsx_cell(path: str, cell: str, value: str,
                    sheet: str | None = None, confirmed: bool = False) -> str:
    if not _XLSX: return "openpyxl not installed."
    try:
        wb = openpyxl.load_workbook(path) if Path(path).exists() else openpyxl.Workbook()
        ws = wb[sheet] if sheet else wb.active
        ws[cell] = value
        wb.save(path)
        return f"Wrote '{value}' to {cell} in {path}"
    except Exception as e: return f"Write error: {e}"


# ── PDF ───────────────────────────────────────────────────────────────────────

def read_pdf(path: str) -> str:
    if not _PDF: return "PyPDF2 not installed."
    try:
        with open(path,"rb") as f:
            reader = PyPDF2.PdfReader(f)
            return "\n".join(p.extract_text() or "" for p in reader.pages)
    except Exception as e: return f"PDF read error: {e}"


def create_pdf(path: str, text: str, confirmed: bool = False) -> str:
    if not _REPORTLAB: return "reportlab not installed."
    try:
        c = canvas.Canvas(path)
        y = 750
        for line in text.split("\n"):
            c.drawString(50, y, line[:100])
            y -= 15
            if y < 50: c.showPage(); y = 750
        c.save()
        return f"PDF created: {path}"
    except Exception as e: return f"PDF create error: {e}"


# ── PowerPoint ────────────────────────────────────────────────────────────────

def read_pptx(path: str) -> str:
    if not _PPTX: return "python-pptx not installed."
    try:
        prs = Presentation(path)
        slides = []
        for i, slide in enumerate(prs.slides, 1):
            texts = [s.text for shape in slide.shapes
                     if shape.has_text_frame
                     for s in shape.text_frame.paragraphs if s.text.strip()]
            slides.append(f"Slide {i}: " + " | ".join(texts))
        return "\n".join(slides)
    except Exception as e: return f"PPTX read error: {e}"
