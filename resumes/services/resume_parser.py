import os
import pdfplumber
import docx


def extract_text_from_resume(file_path):
    """
    Extracts raw text from a PDF or DOCX file.
    Returns empty string if extraction fails, rather than raising -
    a bad resume shouldn't crash the analysis flow (Section 27: graceful error handling).
    """
    ext = os.path.splitext(file_path)[1].lower()

    try:
        if ext == '.pdf':
            return _extract_pdf(file_path)
        elif ext == '.docx':
            return _extract_docx(file_path)
    except Exception:
        return ''

    return ''


def _extract_pdf(file_path):
    text_parts = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return '\n'.join(text_parts)


def _extract_docx(file_path):
    document = docx.Document(file_path)
    return '\n'.join(paragraph.text for paragraph in document.paragraphs)