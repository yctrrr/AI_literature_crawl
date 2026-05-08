# AI Literature Crawl

<!-- README-I18N:START -->

**English** | [中文](./README.zh.md)

<!-- README-I18N:END -->

## Overview

AI Literature Crawl is an automated workflow for collecting Nature-platform literature. It discovers candidate articles from configurable feeds and searches, filters by journal title, downloads article PDFs and the first supplementary file when available, classifies papers into a local topic taxonomy with DeepSeek, and appends summaries to a cumulative Markdown file.

The default configuration is tuned for air quality, climate change, and energy transition literature.

## Features

- Discovers candidates from Nature feeds/article lists first.
- Uses Nature search as a controlled fallback when feed results are insufficient.
- Filters candidates before the run limit is applied, using `nature.journal_name_required_term`.
- Downloads only articles with accessible PDFs.
- Prioritizes the real Nature download button over fallback PDF metadata links.
- Downloads the first supplementary/additional file when it is a real downloadable file.
- Names PDFs as `Journal-FirstAuthor-Year-Title.pdf`.
- Names supplements as `Supp-Journal-FirstAuthor-Year-Title.<ext>`.
- Uses DeepSeek V4 Pro through an OpenAI-compatible API.
- Classifies each paper into folders.
- Avoids duplicate downloads using DOI/URL metadata.
- Skips unreadable PDF pages during text extraction instead of stopping the whole run.
- Generates EndNote import files where the main PDF and matching `Supp-*` files are attached to the same record.
- Supports Windows Task Scheduler for weekly runs.

## Paths

- Project: this repository root
- Category source: `./example_taxonomy` by default
- Archive root: `./data/archive` by default

These paths are configurable in `config.yaml`.

## Project Structure

```text
literature_crawl/
  config.yaml
  README.md
  prepare_endnote_import.py
  requirements.txt
  run_weekly.py
  scheduler.ps1
  src/
    archive_manager.py
    article_fetcher.py
    config.py
    llm.py
    models.py
    pdf_utils.py
    source_discovery.py
    state_manager.py
    utils.py
```

## Setup

```powershell
git clone https://github.com/yctrrr/AI_literature_crawl.git
cd AI_literature_crawl
pip install -r requirements.txt
playwright install chromium
$env:DEEPSEEK_API_KEY = "..."
```

For persistent scheduled runs:

```powershell
setx DEEPSEEK_API_KEY "your_key_here"
```

Restart PowerShell after using `setx`.

For institutional access, run once with a visible browser and complete login if needed:

```powershell
python .\run_weekly.py --config .\config.yaml --limit 1 --headless false
```

`--limit 1` is only for testing. Formal runs use `download.max_articles_per_run` from `config.yaml`; the current default is `20`.

## Configuration

Key settings live in `config.yaml`:

```yaml
keywords:
  - air pollution
  - climate change
  - energy transition

nature:
  journal_name_required_term: Nature

download:
  max_articles_per_run: 20

llm:
  provider: deepseek
  model: deepseek-v4-pro
  api_key_env: DEEPSEEK_API_KEY
  base_url: https://api.deepseek.com
```

Do not put API keys directly in `config.yaml`; use environment variables.

## Commands

Discovery only:

```powershell
python .\run_weekly.py --config .\config.yaml --dry-run
```

Download and summarize one paper:

```powershell
python .\run_weekly.py --config .\config.yaml --limit 1 --headless false
```

Download and summarize the top 10 journal-matched candidates:

```powershell
python .\run_weekly.py --config .\config.yaml --limit 10 --headless false
```

Formal run using `download.max_articles_per_run`:

```powershell
python .\run_weekly.py --config .\config.yaml --headless false
```

Download/classify without summary:

```powershell
python .\run_weekly.py --config .\config.yaml --limit 1 --headless false --no-summarize
```

Prepare an EndNote import package from downloaded papers:

```powershell
python .\prepare_endnote_import.py
```

The generated `.enw` file stores the main PDF and any matching `Supp-*` file on the same EndNote record, and adds the `AI_crawl` keyword for grouping.

## Weekly Scheduler

Register the default Monday 09:00 task:

```powershell
powershell -ExecutionPolicy Bypass -File .\scheduler.ps1
```

The task runs:

```powershell
python <repo>\run_weekly.py --config <repo>\config.yaml
```

## Outputs

- `_download\Journal-FirstAuthor-Year-Title.pdf`
- `_download\Supp-Journal-FirstAuthor-Year-Title.<ext>` before classification/move
- `<Category>\Journal-FirstAuthor-Year-Title.pdf`
- `<Category>\Supp-Journal-FirstAuthor-Year-Title.<ext>`
- `<Category>\Journal-FirstAuthor-Year-Title.metadata.json`
- `_state\processed_articles.jsonl`
- `_state\pending_no_pdf.jsonl`
- `_state\filtered_articles.jsonl`
- `_state\failed_downloads.jsonl`
- `_state\run_log.jsonl`
- `_summaries\summary.md`
- `_endnote_import\AI_crawl_latest.enw`

Each paper entry in `summary.md` uses the final PDF filename without `.pdf` as its Markdown title, so it can be matched directly to the downloaded file.

## Duplicate Handling

The crawler avoids repeat downloads using:

- `_state\processed_articles.jsonl`
- `_state\filtered_articles.jsonl`
- existing `<Category>\*.metadata.json`
- DOI first, source URL second

If a previous run downloaded or filtered a paper, later formal runs skip it. Missing summaries can be filled later with a separate repair workflow if needed.

## Notes

- Nature page structure can change, so selectors may need maintenance.
- `nature.journal_name_required_term` filters out articles whose journal title does not contain the configured text before the run applies `--limit` / `download.max_articles_per_run`.
- PDF text extraction skips unreadable pages and records extraction failures without stopping the whole run.
- Institution-protected PDFs may require a logged-in Chrome profile.
- Search fallback is intentionally rate-limited by `delay_seconds`.
