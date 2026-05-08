from __future__ import annotations

import zlib
from pathlib import Path

from pypdf import PdfReader
from pypdf.errors import PdfReadError


def extract_pdf_text(path: Path, max_chars: int = 60000) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    count = 0
    for page_index, page in enumerate(reader.pages, 1):
        try:
            text = page.extract_text() or ""
        except (PdfReadError, ValueError, RuntimeError, zlib.error) as exc:
            if count < max_chars:
                parts.append(f"[PDF text extraction skipped page {page_index}: {type(exc).__name__}]")
            continue
        if not text.strip():
            continue
        remaining = max_chars - count
        if remaining <= 0:
            break
        parts.append(text[:remaining])
        count += min(len(text), remaining)
    return "\n\n".join(parts)
