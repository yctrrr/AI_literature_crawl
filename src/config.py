from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass(slots=True)
class NatureConfig:
    base_url: str
    journals: list[str] = field(default_factory=lambda: [""])
    feed_first: bool = True
    feed_urls: list[str] = field(default_factory=list)
    search_fallback: bool = True
    min_results_before_search_fallback: int = 5
    search_max_pages_per_keyword: int = 2
    delay_seconds: int = 8
    request_timeout_seconds: int = 30
    user_agent: str = "LiteratureCrawler/0.1"


@dataclass(slots=True)
class PathsConfig:
    category_source: Path
    archive_root: Path


@dataclass(slots=True)
class DownloadConfig:
    require_pdf: bool = True
    first_attachment_only: bool = True
    skip_if_no_pdf: bool = True
    max_articles_per_run: int = 20


@dataclass(slots=True)
class BrowserConfig:
    headless: bool = True
    use_chrome_profile: bool = True
    user_data_dir: str = ""


@dataclass(slots=True)
class LLMConfig:
    provider: str = "deepseek"
    model: str = "deepseek-v4-pro"
    api_key_env: str = "DEEPSEEK_API_KEY"
    base_url: str = "https://api.deepseek.com"
    summarize_by_default: bool = True
    max_pdf_chars: int = 60000


@dataclass(slots=True)
class AppConfig:
    keywords: list[str]
    nature: NatureConfig
    paths: PathsConfig
    download: DownloadConfig
    browser: BrowserConfig
    llm: LLMConfig
    project_root: Path


def load_config(path: Path) -> AppConfig:
    path = path.resolve()
    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}

    nature = NatureConfig(**(raw.get("nature") or {}))
    paths_raw = raw.get("paths") or {}
    config_dir = path.parent
    paths = PathsConfig(
        category_source=_resolve_path(config_dir, paths_raw["category_source"]),
        archive_root=_resolve_path(config_dir, paths_raw["archive_root"]),
    )
    download = DownloadConfig(**(raw.get("download") or {}))
    browser = BrowserConfig(**(raw.get("browser") or {}))
    llm = LLMConfig(**(raw.get("llm") or {}))
    keywords = list(raw.get("keywords") or [])
    if not keywords:
        raise ValueError("config.yaml must define at least one keyword")

    return AppConfig(
        keywords=keywords,
        nature=nature,
        paths=paths,
        download=download,
        browser=browser,
        llm=llm,
        project_root=path.parent,
    )


def _resolve_path(base_dir: Path, value: str) -> Path:
    path = Path(value)
    return path if path.is_absolute() else (base_dir / path).resolve()
