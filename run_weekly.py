from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from src.archive_manager import ArchiveManager
from src.article_fetcher import ArticleFetcher
from src.config import load_config
from src.llm import LLMClient
from src.pdf_utils import extract_pdf_text
from src.source_discovery import SourceDiscovery
from src.state_manager import StateManager
from src.utils import JsonlLogger, now_iso


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Weekly Nature literature crawler")
    parser.add_argument("--config", default="config.yaml", help="Path to config.yaml")
    parser.add_argument("--dry-run", action="store_true", help="Discover only; do not download or call OpenAI")
    parser.add_argument("--limit", type=int, default=None, help="Maximum new candidate articles to process")
    parser.add_argument("--headless", choices=["true", "false"], default=None, help="Override browser headless mode")
    parser.add_argument("--delay-seconds", type=int, default=None, help="Override request delay for this run")
    parser.add_argument("--no-summarize", action="store_true", help="Download/classify only; skip summaries")
    parser.add_argument("--skip-search-fallback", action="store_true", help="Disable /search fallback for this run")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    config = load_config(Path(args.config))
    if args.headless is not None:
        config.browser.headless = args.headless == "true"
    if args.skip_search_fallback:
        config.nature.search_fallback = False
    if args.delay_seconds is not None:
        config.nature.delay_seconds = args.delay_seconds

    archive = ArchiveManager(config.paths.category_source, config.paths.archive_root)
    archive.ensure_layout()
    state = StateManager(config.paths.archive_root / "_state")
    run_logger = JsonlLogger(config.paths.archive_root / "_state" / "run_log.jsonl")

    run_id = now_iso().replace(":", "-")
    run_logger.write({"event": "run_start", "run_id": run_id, "dry_run": args.dry_run})

    discovery = SourceDiscovery(config.nature)
    summarize = config.llm.summarize_by_default and not args.no_summarize
    candidates = discovery.discover(config.keywords)
    new_candidates = [c for c in candidates if not state.is_processed(c.doi, c.url)]
    process_limit = args.limit or config.download.max_articles_per_run
    new_candidates = new_candidates[:process_limit]

    print(f"Discovered {len(candidates)} candidates; {len(new_candidates)} new candidates selected.")
    if args.dry_run:
        for idx, candidate in enumerate(new_candidates, 1):
            print(f"{idx}. [{candidate.keyword}] {candidate.title} - {candidate.url}")
        run_logger.write({"event": "run_complete", "run_id": run_id, "mode": "dry_run", "selected": len(new_candidates)})
        return 0

    if summarize and not os.environ.get(config.llm.api_key_env):
        message = f"Missing {config.llm.api_key_env}; aborting before downloads because summarization is enabled."
        run_logger.write({"event": "run_aborted", "run_id": run_id, "reason": "missing_openai_api_key"})
        print(message, file=sys.stderr)
        return 2

    fetcher = ArticleFetcher(config)
    llm = LLMClient(config.llm)

    try:
        with fetcher:
            for candidate in new_candidates:
                process_candidate(candidate, archive, state, fetcher, llm, summarize, run_id)
    finally:
        run_logger.write({"event": "run_complete", "run_id": run_id, "mode": "full"})

    return 0


def process_candidate(candidate, archive, state, fetcher, llm, summarize: bool, run_id: str) -> None:
    staging_dir = archive.staging_dir(run_id, "")
    staging_dir.mkdir(parents=True, exist_ok=True)
    try:
        fetched = fetcher.fetch(candidate, staging_dir)
    except Exception as exc:
        state.write_failure(candidate, "fetch_error", str(exc))
        print(f"FETCH FAILED: {candidate.url} ({exc})")
        return

    if not fetched.pdf_path:
        state.write_pending_no_pdf(candidate, fetched.metadata, fetched.error or "no_pdf")
        print(f"NO PDF: {candidate.url}")
        return

    text_excerpt = extract_pdf_text(fetched.pdf_path, max_chars=llm.max_pdf_chars)
    categories = archive.categories()
    classification = llm.classify(candidate, fetched.metadata, text_excerpt, categories)
    article_dir = archive.finalize_article(candidate, fetched, classification)

    summary_text = ""
    summary_status = "skipped"
    if summarize:
        try:
            summary_text = llm.summarize(candidate, fetched.metadata, text_excerpt, classification)
            archive.write_summary(fetched, summary_text)
            summary_status = "completed"
        except Exception as exc:
            summary_status = "failed"
            state.write_failure(candidate, "summary_error", str(exc))
            print(f"SUMMARY FAILED: {candidate.url} ({exc})")

    state.write_processed(candidate, fetched, classification, article_dir, summary_status)
    print(f"DONE: {classification.category} - {candidate.title}")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        raise SystemExit(130)
