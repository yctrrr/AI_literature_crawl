from __future__ import annotations

from pathlib import Path

from pypdf import PdfReader


def extract_pdf_text(path: Path, max_chars: int = 60000) -> str:
    reader = PdfReader(str(path))
    parts: list[str] = []
    count = 0
    for page in reader.pages:
        text = page.extract_text() or ""
        if not text.strip():
            continue
        remaining = max_chars - count
        if remaining <= 0:
            break
        parts.append(text[:remaining])
        count += min(len(text), remaining)
    return "\n\n".join(parts)
