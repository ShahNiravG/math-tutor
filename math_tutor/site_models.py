"""Data models shared by site-generation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class PromptOutputRecord:
    slug: str
    title: str
    response_path: Path | None
    response_html_path: Path | None
    response_pdf_path: Path | None
    metadata_path: Path | None
    processed_at: str | None
    response_markdown: str | None


@dataclass
class DocumentRecord:
    file_id: str
    display_name: str
    pdf_path: Path | None
    download_url: str | None
    fetched_at: str | None
    prompt_outputs: list[PromptOutputRecord]
