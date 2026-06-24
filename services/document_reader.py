"""
Извлечение текста из документов для передачи в AI.
Поддерживает PDF и DOCX.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MAX_CHARS = 30000


def extract_text(filepath: str) -> str | None:
    """Извлекает текст из файла. Возвращает None если формат не поддерживается."""
    path = Path(filepath)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _extract_pdf(filepath)
    if suffix in (".docx", ".doc"):
        return _extract_docx(filepath)

    return None


def _extract_pdf(filepath: str) -> str:
    try:
        import fitz  # pymupdf
        doc = fitz.open(filepath)
        pages = []
        for page in doc:
            pages.append(page.get_text())
        doc.close()
        text = "\n".join(pages).strip()
        return text[:MAX_CHARS] + "\n\n[...текст обрезан, документ слишком большой]" if len(text) > MAX_CHARS else text
    except Exception as e:
        logger.error(f"Ошибка чтения PDF: {e}")
        raise


def _extract_docx(filepath: str) -> str:
    try:
        from docx import Document
        doc = Document(filepath)
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n".join(paragraphs).strip()
        return text[:MAX_CHARS] + "\n\n[...текст обрезан, документ слишком большой]" if len(text) > MAX_CHARS else text
    except Exception as e:
        logger.error(f"Ошибка чтения DOCX: {e}")
        raise


def is_supported(filename: str) -> bool:
    return Path(filename).suffix.lower() in (".pdf", ".docx", ".doc")
