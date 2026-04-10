"""Challenge catalog writing and deploy materialization helpers."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from math_tutor.atomic_io import atomic_write_text
from math_tutor.chaptering import chapter_slug, chapter_sort_key
from math_tutor.challenge_catalog import CLASSIC_BANK_ID, CLASSIC_BANK_TITLE


def write_json(path: Path, payload: dict[str, Any], *, indent: int | None = None) -> None:
    new_content = json.dumps(payload, indent=indent)
    if path.exists() and path.read_text(encoding="utf-8") == new_content:
        return
    atomic_write_text(path, new_content)


def write_canonical_challenge_catalogs(
    *,
    canonical_exams_json: Path,
    canonical_chapter_exams_json: Path,
    generated_at: str,
    exams: list[dict],
    chapter_exams: list[dict],
) -> dict[str, int]:
    write_json(
        canonical_exams_json,
        {"generated_at": generated_at, "exams": exams},
        indent=2,
    )
    write_json(
        canonical_chapter_exams_json,
        {"generated_at": generated_at, "exams": chapter_exams},
        indent=2,
    )
    return {
        "exam_count": len(exams),
        "chapter_exam_count": len(chapter_exams),
    }


def _sync_dir(source: Path, dest: Path) -> None:
    """Recursively sync source into dest, skipping unchanged files."""
    dest.mkdir(exist_ok=True)
    source_names = {p.name for p in source.iterdir()}
    for child in list(dest.iterdir()):
        if child.name not in source_names:
            if child.is_dir():
                shutil.rmtree(child)
            else:
                child.unlink()
    for src_child in source.iterdir():
        dst_child = dest / src_child.name
        if src_child.is_dir():
            _sync_dir(src_child, dst_child)
        else:
            new_bytes = src_child.read_bytes()
            if dst_child.exists() and dst_child.read_bytes() == new_bytes:
                continue
            dst_child.write_bytes(new_bytes)


def copy_static_challenge_assets(*, source_dir: Path, challenges_dir: Path) -> None:
    for source_path in source_dir.glob("*"):
        if source_path.name in ("exams.json", "chapter_exams.json", "curated_exams.json"):
            continue
        destination = challenges_dir / source_path.name
        if source_path.is_dir():
            _sync_dir(source_path, destination)
        else:
            new_bytes = source_path.read_bytes()
            if destination.exists() and destination.read_bytes() == new_bytes:
                continue
            destination.write_bytes(new_bytes)


def materialize_exam_outputs(*, challenges_dir: Path, bundle: dict[str, Any], full_bundle_size: int) -> dict[str, Any]:
    generated_at = bundle.get("generated_at")
    index_entries: list[dict[str, Any]] = []
    exams_subdir = challenges_dir / "exams"
    exams_subdir.mkdir(exist_ok=True)
    written_ids: list[str] = []
    total_individual_bytes = 0
    for exam in bundle.get("exams", []):
        mm_count = sum(1 for question in exam["questions"] if question["type"] == "mm")
        op_count = sum(1 for question in exam["questions"] if question["type"] == "op")
        chapters = sorted(
            {question["chapter"] for question in exam["questions"] if question.get("chapter")},
            key=_chapter_numeric_sort_key,
        )
        index_entries.append(
            {
                "id": exam["id"],
                "title": exam["title"],
                "bank": exam.get("bank", CLASSIC_BANK_ID),
                "bank_id": exam.get("bank", CLASSIC_BANK_ID),
                "bank_title": exam.get("bank_title", CLASSIC_BANK_TITLE),
                "bank_label": exam.get("bank_title", CLASSIC_BANK_TITLE),
                "question_count": len(exam["questions"]),
                "mm": mm_count,
                "op": op_count,
                "chapters": chapters,
            }
        )
        individual_path = exams_subdir / f"{exam['id']}.json"
        write_json(individual_path, {"generated_at": generated_at, **exam})
        written_ids.append(exam["id"])
        total_individual_bytes += individual_path.stat().st_size

    index_json_path = challenges_dir / "exams-index.json"
    write_json(index_json_path, {"generated_at": generated_at, "exams": index_entries})
    average_individual_size = (total_individual_bytes // len(index_entries)) if index_entries else 0
    return {
        "exam_count": len(index_entries),
        "index_size_kb": index_json_path.stat().st_size // 1024,
        "full_bundle_size_kb": full_bundle_size // 1024,
        "avg_individual_size_bytes": average_individual_size,
        "written_exam_ids": written_ids,
    }


def materialize_chapter_exam_outputs(*, challenges_dir: Path, bundle: dict[str, Any]) -> dict[str, Any]:
    chapter_index_entries: list[dict[str, Any]] = []
    exams_subdir = challenges_dir / "exams"
    exams_subdir.mkdir(exist_ok=True)
    chapter_subdir = challenges_dir / "chapter-exams"
    chapter_subdir.mkdir(exist_ok=True)
    generated_at = bundle.get("generated_at")
    written_exam_ids: list[str] = []

    for exam in bundle.get("exams", []):
        mm_count = sum(1 for question in exam["questions"] if question["type"] == "mm")
        op_count = sum(1 for question in exam["questions"] if question["type"] == "op")
        models = sorted({question["model_label"] for question in exam["questions"]})
        chapter_index_entries.append(
            {
                "id": exam["id"],
                "title": exam["title"],
                "chapter": exam["chapter"],
                "challenge_type": exam.get("challenge_type", ""),
                "mm": mm_count,
                "op": op_count,
                "question_count": len(exam["questions"]),
                "models": models,
            }
        )
        write_json(exams_subdir / f"{exam['id']}.json", {"generated_at": generated_at, **exam})
        written_exam_ids.append(exam["id"])

    write_json(
        chapter_subdir / "index.json",
        {"generated_at": generated_at, "exams": chapter_index_entries},
        indent=2,
    )
    for chapter in sorted({entry["chapter"] for entry in chapter_index_entries}, key=chapter_sort_key):
        chapter_exams = [entry for entry in chapter_index_entries if entry["chapter"] == chapter]
        write_json(
            chapter_subdir / f"chp{chapter_slug(chapter)}.json",
            {
                "generated_at": generated_at,
                "chapter": chapter,
                "exams": chapter_exams,
            },
            indent=2,
        )
    return {"chapter_exam_count": len(chapter_index_entries), "written_exam_ids": written_exam_ids}


def _chapter_numeric_sort_key(chapter: str) -> float:
    match = re.match(r"^[\d.]+", chapter)
    if not match:
        return 9999
    return float(match.group())
