"""Challenge catalog writing and deploy materialization helpers."""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any

from math_tutor.chaptering import chapter_slug, chapter_sort_key


def build_master_question_payload(*, generated_at: str, questions: list[dict]) -> dict[str, Any]:
    all_with_mcq = [question for question in questions if "correct" in question]
    return {
        "generated_at": generated_at,
        "total": len(all_with_mcq),
        "mental_math": sum(1 for question in all_with_mcq if question["type"] == "mm"),
        "olympiad": sum(1 for question in all_with_mcq if question["type"] == "op"),
        "questions": all_with_mcq,
    }


def write_json(path: Path, payload: dict[str, Any], *, indent: int | None = None) -> None:
    path.write_text(json.dumps(payload, indent=indent), encoding="utf-8")


def write_canonical_challenge_catalogs(
    *,
    canonical_exams_json: Path,
    canonical_master_json: Path,
    canonical_chapter_exams_json: Path,
    generated_at: str,
    exams: list[dict],
    chapter_exams: list[dict],
    questions: list[dict],
) -> dict[str, int]:
    write_json(
        canonical_exams_json,
        {"generated_at": generated_at, "exams": exams},
        indent=2,
    )
    master_payload = build_master_question_payload(generated_at=generated_at, questions=questions)
    write_json(canonical_master_json, master_payload, indent=2)
    write_json(
        canonical_chapter_exams_json,
        {"generated_at": generated_at, "exams": chapter_exams},
        indent=2,
    )
    return {
        "exam_count": len(exams),
        "chapter_exam_count": len(chapter_exams),
        "question_count": master_payload["total"],
    }


def copy_static_challenge_assets(*, source_dir: Path, challenges_dir: Path) -> None:
    for source_path in source_dir.glob("*"):
        if source_path.name in ("exams.json", "master_questions.json", "chapter_exams.json"):
            continue
        destination = challenges_dir / source_path.name
        if source_path.is_dir():
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(source_path, destination)
        else:
            shutil.copy2(source_path, destination)


def materialize_exam_outputs(*, challenges_dir: Path, bundle: dict[str, Any], full_bundle_size: int) -> dict[str, int]:
    generated_at = bundle.get("generated_at")
    index_entries: list[dict[str, Any]] = []
    exams_subdir = challenges_dir / "exams"
    exams_subdir.mkdir(exist_ok=True)
    total_individual_bytes = 0
    for exam in bundle.get("exams", []):
        mm_count = sum(1 for question in exam["questions"] if question["type"] == "mm")
        op_count = sum(1 for question in exam["questions"] if question["type"] == "op")
        chapters = sorted(
            {question["chapter"] for question in exam["questions"]},
            key=_chapter_numeric_sort_key,
        )
        index_entries.append(
            {
                "id": exam["id"],
                "title": exam["title"],
                "mm": mm_count,
                "op": op_count,
                "chapters": chapters,
            }
        )
        individual_path = exams_subdir / f"{exam['id']}.json"
        write_json(individual_path, {"generated_at": generated_at, **exam})
        total_individual_bytes += individual_path.stat().st_size

    index_json_path = challenges_dir / "exams-index.json"
    write_json(index_json_path, {"generated_at": generated_at, "exams": index_entries})
    average_individual_size = (total_individual_bytes // len(index_entries)) if index_entries else 0
    return {
        "exam_count": len(index_entries),
        "index_size_kb": index_json_path.stat().st_size // 1024,
        "full_bundle_size_kb": full_bundle_size // 1024,
        "avg_individual_size_bytes": average_individual_size,
    }


def materialize_chapter_exam_outputs(*, challenges_dir: Path, bundle: dict[str, Any]) -> dict[str, int]:
    chapter_index_entries: list[dict[str, Any]] = []
    exams_subdir = challenges_dir / "exams"
    exams_subdir.mkdir(exist_ok=True)
    chapter_subdir = challenges_dir / "chapter-exams"
    chapter_subdir.mkdir(exist_ok=True)
    generated_at = bundle.get("generated_at")

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
    return {"chapter_exam_count": len(chapter_index_entries)}


def _chapter_numeric_sort_key(chapter: str) -> float:
    match = re.match(r"^[\d.]+", chapter)
    if not match:
        return 9999
    return float(match.group())
