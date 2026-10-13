import os
import re
import pdfplumber
import docx


def extract_text_from_resume(file_path):
    """
    Extracts raw text from a PDF or DOCX file.
    Returns empty string if extraction fails, rather than raising -
    a bad or unreadable resume shouldn't crash the application.
    Extracts both paragraphs and table cells, with whitespace normalization.
    """
    if not file_path or not os.path.exists(file_path):
        return ''

    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == '.pdf':
            text = _extract_pdf(file_path)
        elif ext == '.docx':
            text = _extract_docx(file_path)
        else:
            return ''
        return _clean_extracted_text(text)
    except Exception:
        return ''


def _extract_pdf(file_path):
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text(layout=False)
            if page_text:
                text_parts.append(page_text)
            # Also extract text from any tables if not already captured
            tables = page.extract_tables() or []
            for table in tables:
                for row in table:
                    row_cells = [cell.strip() for cell in row if cell and cell.strip()]
                    if row_cells:
                        text_parts.append(" | ".join(row_cells))
    return '\n'.join(text_parts)


def _extract_docx(file_path):
    document = docx.Document(file_path)
    text_parts = []
    # Extract standard paragraphs
    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            text_parts.append(paragraph.text)

    # Extract tables (many resumes format skills and projects in tables)
    for table in document.tables:
        for row in table.rows:
            row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
            if row_cells:
                text_parts.append(" | ".join(dict.fromkeys(row_cells)))  # remove duplicate merged cells

    return '\n'.join(text_parts)


def _clean_extracted_text(raw_text):
    if not raw_text:
        return ''
    # Normalize bullet characters to uniform dashes
    cleaned = re.sub(r'[\u2022\u2023\u25E6\u2043\u2219\uf0b7]', '-', raw_text)
    # Remove excessive blank lines
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()