"""Shared chapter-parsing utilities used across fetch, build, and deploy flows.

This module centralizes chapter-identification logic so that the same chapter
labels, sort keys, and slugs are used consistently throughout the project.
The functions are intentionally pure and small so they can be unit-tested
without requiring network access, filesystem writes, or generated artifacts.
"""

from __future__ import annotations

import re
from pathlib import Path


def chapter_sort_key(chapter: str) -> float:
    """Return a numeric sort key for chapter labels such as ``"5.1"``.

    Unknown or malformed chapter labels sort last.
    """

    match = re.match(r"^(\d+(?:\.\d+)?)", chapter)
    return float(match.group(1)) if match else 9999.0


def chapter_slug(chapter: str) -> str:
    """Return the compact chapter slug used by generated challenge assets."""

    return re.sub(r"[^0-9]+", "", chapter)


def parse_display_name_chapter(display_name: str) -> str | None:
    """Extract a human-readable chapter label from a display name.

    Examples:
    - ``"Alg 2 Trig H Chp 5.1 Note.docx"`` -> ``"5.1"``
    - ``"Alg 2 Trig H Chp 7.4 & 7.5 Note.docx"`` -> ``"7.4 & 7.5"``
    """

    match = re.search(r"chp[.\s]+(\d+(?:\.\d+)?(?:\s*&\s*\d+(?:\.\d+)?)*)", display_name.lower())
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1).strip())


def parse_response_stem_chapter(stem: str) -> str:
    """Extract a chapter label from a generated response filename stem."""

    base = stem.split("__")[0]
    match = re.search(r"chp-(\d+(?:-\d+)*)", base)
    if not match:
        return "?"
    parts = match.group(1).split("-")
    chapters: list[str] = []
    index = 0
    while index + 1 < len(parts):
        chapters.append(f"{parts[index]}.{parts[index + 1]}")
        index += 2
    return " & ".join(chapters) if chapters else "?"


def parse_assignment_chapters(filename: str) -> set[str]:
    """Extract chapter labels from assignment filenames.

    Example: ``"4517747_chp-6-1-6-2-work.pdf"`` -> ``{"6.1", "6.2"}``
    """

    stem = re.sub(r"^\d+_", "", Path(filename).stem)
    match = re.match(r"chp-([\d][\d-]*)", stem)
    if not match:
        return set()
    chapter_part = match.group(1).rstrip("-")
    digits = chapter_part.split("-")
    chapters: set[str] = set()
    index = 0
    while index + 1 < len(digits):
        chapters.add(f"{digits[index]}.{digits[index + 1]}")
        index += 2
    return chapters


def format_assignment_display_name(path: Path) -> str:
    """Format an assignment filename into a readable chapter label."""

    stem = re.sub(r"^\d+_", "", path.stem)
    parts = stem.split("-")
    words: list[str] = []
    index = 0
    if parts and parts[0].lower() == "chp":
        words.append("Chp")
        index = 1
        while index + 1 < len(parts) and parts[index].isdigit() and parts[index + 1].isdigit():
            words.append(f"{parts[index]}.{parts[index + 1]}")
            index += 2
    while index < len(parts):
        words.append(parts[index].capitalize())
        index += 1
    return " ".join(words)
