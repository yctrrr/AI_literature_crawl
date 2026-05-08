from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime
from pathlib import Path


DEFAULT_ARCHIVE_ROOT = Path("./data/archive")
DEFAULT_GROUP = "AI_crawl"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare an EndNote import package for crawled PDFs.")
    parser.add_argument("--archive-root", type=Path, default=DEFAULT_ARCHIVE_ROOT)
    parser.add_argument("--group", default=DEFAULT_GROUP, help="Keyword/group label added to every imported record.")
    parser.add_argument("--output-dir", type=Path, default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    archive_root = args.archive_root.resolve()
    output_dir = (args.output_dir or archive_root / "_endnote_import").resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    records = load_records(archive_root)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ris_path = output_dir / f"{args.group}_{timestamp}.ris"
    enw_path = output_dir / f"{args.group}_{timestamp}.enw"
    manifest_path = output_dir / f"{args.group}_{timestamp}_manifest.csv"
    latest_ris = output_dir / f"{args.group}_latest.ris"
    latest_enw = output_dir / f"{args.group}_latest.enw"

    write_ris(ris_path, records, args.group)
    write_enw(enw_path, records, args.group)
    write_manifest(manifest_path, records, args.group)
    latest_ris.write_text(ris_path.read_text(encoding="utf-8"), encoding="utf-8")
    latest_enw.write_text(enw_path.read_text(encoding="utf-8"), encoding="utf-8")

    print(f"records: {len(records)}")
    print(f"ris: {ris_path}")
    print(f"enw: {enw_path}")
    print(f"latest_ris: {latest_ris}")
    print(f"latest_enw: {latest_enw}")
    print(f"manifest: {manifest_path}")
    return 0


def load_records(archive_root: Path) -> list[dict]:
    records: list[dict] = []
    seen: dict[str, dict] = {}
    for metadata_path in sorted(archive_root.rglob("*.metadata.json")):
        if any(part.startswith("_") for part in metadata_path.relative_to(archive_root).parts):
            continue
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        pdf_path = resolve_pdf_path(metadata, metadata_path)
        attachment_paths = resolve_attachment_paths(metadata, metadata_path)
        key = metadata.get("doi") or metadata.get("source_url") or str(pdf_path)
        if key in seen:
            merge_attachment_paths(seen[key], attachment_paths)
            continue
        if not pdf_path.is_file():
            continue
        metadata["_metadata_path"] = str(metadata_path)
        metadata["pdf_path"] = str(pdf_path)
        metadata["attachment_paths"] = [str(path) for path in attachment_paths]
        seen[key] = metadata
        records.append(metadata)
    return records


def resolve_pdf_path(metadata: dict, metadata_path: Path) -> Path:
    pdf_path = Path(metadata.get("pdf_path") or "")
    if pdf_path.is_file():
        return pdf_path
    if metadata_path.name.endswith(".metadata.json"):
        sibling_pdf = metadata_path.with_name(metadata_path.name[: -len(".metadata.json")] + ".pdf")
        if sibling_pdf.is_file():
            return sibling_pdf
    file_stem = metadata.get("file_stem")
    if file_stem:
        sibling_pdf = metadata_path.with_name(f"{file_stem}.pdf")
        if sibling_pdf.is_file():
            return sibling_pdf
    return pdf_path


def resolve_attachment_paths(metadata: dict, metadata_path: Path) -> list[Path]:
    candidates: list[Path] = []
    attachment_path = Path(metadata.get("attachment_path") or "")
    if attachment_path.is_file():
        candidates.append(attachment_path)

    stems = [metadata_path.name[: -len(".metadata.json")]]
    if metadata.get("file_stem"):
        stems.append(str(metadata["file_stem"]))
    for stem in dict.fromkeys(stems):
        candidates.extend(sorted(metadata_path.parent.glob(f"Supp-{stem}.*")))

    result: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate.is_file():
            continue
        key = str(candidate.resolve()).lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(candidate)
    return result


def merge_attachment_paths(record: dict, attachment_paths: list[Path]) -> None:
    existing = list(record.get("attachment_paths") or [])
    seen = {file_signature(Path(path)) for path in existing if Path(path).is_file()}
    for attachment_path in attachment_paths:
        key = file_signature(attachment_path)
        if key not in seen:
            existing.append(str(attachment_path))
            seen.add(key)
    record["attachment_paths"] = existing


def file_signature(path: Path) -> tuple[int, str]:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return path.stat().st_size, hasher.hexdigest()


def write_ris(path: Path, records: list[dict], group: str) -> None:
    chunks = []
    for record in records:
        chunks.extend(record_to_ris(record, group))
        chunks.append("")
    path.write_text("\n".join(chunks), encoding="utf-8")


def write_enw(path: Path, records: list[dict], group: str) -> None:
    chunks = []
    for record in records:
        chunks.extend(record_to_enw(record, group))
        chunks.append("")
    path.write_text("\n".join(chunks), encoding="utf-8")


def record_to_ris(record: dict, group: str) -> list[str]:
    lines = ["TY  - JOUR"]
    add(lines, "TI", record.get("title"))
    for author in record.get("authors") or []:
        add(lines, "AU", author)
    add(lines, "T2", record.get("journal"))
    add(lines, "PY", record.get("year"))
    add(lines, "DA", record.get("published"))
    add(lines, "DO", record.get("doi"))
    add(lines, "AB", clean_text(record.get("abstract")))
    add(lines, "UR", record.get("source_url") or record.get("pdf_url"))
    add(lines, "L1", record.get("pdf_path"))
    for attachment_path in record.get("attachment_paths") or []:
        add(lines, "L1", attachment_path)
    add(lines, "KW", group)
    if record.get("keyword"):
        add(lines, "KW", record.get("keyword"))
    if record.get("category"):
        add(lines, "N1", f"AI_web_crawl category: {record.get('category')}")
    add(lines, "N1", f"AI_web_crawl metadata: {record.get('_metadata_path')}")
    lines.append("ER  -")
    return lines


def record_to_enw(record: dict, group: str) -> list[str]:
    lines = ["%0 Journal Article"]
    add_endnote(lines, "%T", record.get("title"))
    for author in record.get("authors") or []:
        add_endnote(lines, "%A", author)
    add_endnote(lines, "%J", record.get("journal"))
    add_endnote(lines, "%D", record.get("year"))
    add_endnote(lines, "%8", record.get("published"))
    add_endnote(lines, "%R", record.get("doi"))
    add_endnote(lines, "%X", clean_text(record.get("abstract")))
    add_endnote(lines, "%U", record.get("source_url") or record.get("pdf_url"))
    add_endnote(lines, "%>", record.get("pdf_path"))
    for attachment_path in record.get("attachment_paths") or []:
        add_endnote(lines, "%>", attachment_path)
    add_endnote(lines, "%K", group)
    if record.get("keyword"):
        add_endnote(lines, "%K", record.get("keyword"))
    if record.get("category"):
        add_endnote(lines, "%Z", f"AI_web_crawl category: {record.get('category')}")
    add_endnote(lines, "%Z", f"AI_web_crawl metadata: {record.get('_metadata_path')}")
    return lines


def write_manifest(path: Path, records: list[dict], group: str) -> None:
    fields = [
        "group",
        "title",
        "authors",
        "year",
        "journal",
        "doi",
        "category",
        "pdf_path",
        "attachment_paths",
        "source_url",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow(
                {
                    "group": group,
                    "title": record.get("title", ""),
                    "authors": "; ".join(record.get("authors") or []),
                    "year": record.get("year", ""),
                    "journal": record.get("journal", ""),
                    "doi": record.get("doi", ""),
                    "category": record.get("category", ""),
                    "pdf_path": record.get("pdf_path", ""),
                    "attachment_paths": "; ".join(record.get("attachment_paths") or []),
                    "source_url": record.get("source_url", ""),
                }
            )


def add(lines: list[str], tag: str, value: object) -> None:
    text = clean_text(value)
    if text:
        lines.append(f"{tag}  - {text}")


def add_endnote(lines: list[str], tag: str, value: object) -> None:
    text = clean_text(value)
    if text:
        lines.append(f"{tag} {text}")


def clean_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).replace("\r", " ").replace("\n", " ").split())


if __name__ == "__main__":
    raise SystemExit(main())
