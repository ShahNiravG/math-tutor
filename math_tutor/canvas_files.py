"""Pure Canvas file metadata and matching helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from math_tutor.state_store import FetchState


TARGET_NAME_SUBSTRINGS = ("note.docx", "note.pdf")
TARGET_NOTE_PDF_PATTERN = re.compile(r"\bnote(?:\s*\([^)]*\))?(?:\.docx)?\.pdf$", re.IGNORECASE)
ASSIGNMENT_NAME_PATTERN = re.compile(r"^\d+\.\d+", re.IGNORECASE)


@dataclass(frozen=True)
class CanvasFile:
    file_id: int
    display_name: str
    download_url: str
    content_type: str
    size: int | None
    updated_at: str | None


def parse_link_next(link_header: str) -> str | None:
    for part in link_header.split(","):
        part = part.strip()
        if 'rel="next"' not in part:
            continue
        url_match = re.match(r"<([^>]+)>", part)
        if url_match:
            return url_match.group(1)
    return None


def is_pdf(display_name: str, content_type: str, url: str) -> bool:
    return (
        display_name.lower().endswith(".pdf")
        or content_type.lower() == "application/pdf"
        or url.lower().endswith(".pdf")
        or ".pdf?" in url.lower()
    )


def is_pdf_by_name(display_name: str) -> bool:
    return display_name.lower().endswith(".pdf")


def matches_target_pdf(display_name: str) -> bool:
    lowered_name = display_name.lower()
    return any(substring in lowered_name for substring in TARGET_NAME_SUBSTRINGS) or bool(
        TARGET_NOTE_PDF_PATTERN.search(display_name)
    )


def matches_assignment_pdf(display_name: str) -> bool:
    return bool(ASSIGNMENT_NAME_PATTERN.match(display_name))


def extract_file_id(url: str) -> int | None:
    match = re.search(r"/files/(\d+)", url)
    if not match:
        return None
    return int(match.group(1))


def normalize_download_url(url: str) -> str:
    if "download=1" in url:
        return url
    separator = "&" if "?" in url else "?"
    return f"{url}{separator}download=1"


def summarize_discovered_files(
    *,
    files: list[CanvasFile],
    fetch_state: FetchState,
    force: bool,
) -> None:
    existing_count = 0
    new_files: list[CanvasFile] = []
    for canvas_file in files:
        state_key = str(canvas_file.file_id)
        pdf_path_value = fetch_state.fetched.get(state_key, {}).get("pdf_path", "")
        if pdf_path_value and Path(pdf_path_value).exists() and not force:
            existing_count += 1
            continue
        new_files.append(canvas_file)

    print(
        f"Fetch check summary: {len(files)} matching file(s), "
        f"{existing_count} already fetched, {len(new_files)} new.",
        flush=True,
    )
    if new_files:
        print("New matching files:", flush=True)
        for canvas_file in new_files:
            print(f"  {canvas_file.display_name} (file id {canvas_file.file_id})", flush=True)
    else:
        print("No new matching files were found on Canvas.", flush=True)
