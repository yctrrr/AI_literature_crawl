from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Candidate:
    url: str
    title: str
    keyword: str
    source: str
    published: str = ""
    summary: str = ""
    doi: str = ""


@dataclass(slots=True)
class FetchResult:
    pdf_path: Path | None
    attachment_path: Path | None
    metadata: dict[str, Any] = field(default_factory=dict)
    error: str = ""


@dataclass(slots=True)
class Classification:
    category: str
    confidence: float
    rationale: str
    status: str = "completed"
