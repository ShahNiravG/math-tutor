"""Build interactive challenge exams from saved AI-generated question files."""
from __future__ import annotations

import json
import hashlib
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from math_tutor.challenge_catalog import (
    build_chapter_exam_sets,
    build_exam_sets,
    ensure_classic_bank_metadata,
    load_explicit_curated_exams,
    load_curated_question_sources,
    load_all_questions,
)
from math_tutor.challenge_config import generate_config_php
from math_tutor.challenge_config import write_experience_script
from math_tutor.experience_variants import CLI_EXPERIENCE_CHOICES
from math_tutor.experience_variants import PRIMARY_EXPERIENCE_VARIANT
from math_tutor.experience_variants import normalize_experience_variant
from math_tutor.challenge_outputs import (
    copy_static_challenge_assets,
    materialize_chapter_exam_outputs,
    materialize_exam_outputs,
    write_json,
    write_canonical_challenge_catalogs,
)
from math_tutor.env_config import load_dotenv_if_present

PACKAGE_DIR = Path(__file__).resolve().parent

CHALLENGES_SRC_DIR = PACKAGE_DIR / "challenges_src"
CURATED_EXAMS_DIR = PACKAGE_DIR / "exams"
CANONICAL_CURATED_EXAMS_JSON = CHALLENGES_SRC_DIR / "curated_exams.json"
DEFAULT_EXPERIENCE_VARIANT = PRIMARY_EXPERIENCE_VARIANT


def load_classic_exam_bundle(canonical_exams_json: Path) -> dict[str, Any]:
    bundle = json.loads(canonical_exams_json.read_text(encoding="utf-8"))
    bundle["exams"] = [
        exam
        for exam in ensure_classic_bank_metadata(bundle.get("exams", []))
        if exam.get("bank", "classic") == "classic"
    ]
    return bundle


def build_deploy_exam_bundle(*, classic_bundle: dict[str, Any], curated_exams: list[dict]) -> dict[str, Any]:
    return {
        "generated_at": classic_bundle.get("generated_at") or datetime.now(timezone.utc).isoformat(),
        "exams": [*classic_bundle.get("exams", []), *curated_exams],
    }


def sync_curated_exam_bundle(*, exams_dir: Path, canonical_curated_exams_json: Path) -> dict[str, Any]:
    now_iso = datetime.now(timezone.utc).isoformat()
    if canonical_curated_exams_json.exists():
        bundle = json.loads(canonical_curated_exams_json.read_text(encoding="utf-8"))
    else:
        bundle = {"generated_at": now_iso, "exams": []}

    normalized_bundle = _normalize_curated_bundle(bundle, generated_at=now_iso)
    merged_exams = [dict(exam) for exam in normalized_bundle.get("exams", [])]
    explicit_exam_indexes = {str(exam.get("id")): index for index, exam in enumerate(merged_exams)}
    for explicit_exam in load_explicit_curated_exams(exams_dir):
        exam_id = str(explicit_exam.get("id", "")).strip()
        if not exam_id:
            continue
        existing_index = explicit_exam_indexes.get(exam_id)
        if existing_index is None:
            merged_exams.append(explicit_exam)
            explicit_exam_indexes[exam_id] = len(merged_exams) - 1
        else:
            merged_exams[existing_index] = explicit_exam
    existing_checksums_by_bank: dict[str, set[str]] = {}
    next_exam_number_by_bank: dict[str, int] = {}
    next_question_number_by_bank: dict[str, int] = {}

    for exam in merged_exams:
        bank_id = str(exam.get("bank", "")).strip().lower()
        if not bank_id:
            continue
        next_exam_number_by_bank[bank_id] = max(
            next_exam_number_by_bank.get(bank_id, 0),
            _exam_sequence_number(str(exam.get("id", ""))),
        )
        bank_checksum_set = existing_checksums_by_bank.setdefault(bank_id, set())
        for question in exam.get("questions", []):
            next_question_number_by_bank[bank_id] = max(
                next_question_number_by_bank.get(bank_id, 0),
                _curated_question_sequence_number(str(question.get("id", ""))),
            )
            checksum = _curated_question_checksum(question)
            if checksum is not None:
                bank_checksum_set.add(checksum)

    for source in load_curated_question_sources(exams_dir):
        bank_id = source["bank"]
        bank_title = source["bank_title"]
        new_questions: list[dict[str, Any]] = []
        bank_checksum_set = existing_checksums_by_bank.setdefault(bank_id, set())
        next_exam_number = next_exam_number_by_bank.get(bank_id, 0) + 1
        next_question_number = next_question_number_by_bank.get(bank_id, 0)
        for question in source["questions"]:
            checksum = _curated_question_checksum(question)
            if checksum is not None and checksum in bank_checksum_set:
                continue
            next_question_number += 1
            canonical_question = _canonicalize_curated_question(
                question,
                bank_id=bank_id,
                question_index=next_question_number,
            )
            new_questions.append(canonical_question)
            if checksum is not None:
                bank_checksum_set.add(checksum)
        next_question_number_by_bank[bank_id] = next_question_number
        while new_questions:
            exam_questions = new_questions[:5]
            new_questions = new_questions[5:]
            new_exam = {
                "id": f"{bank_id}-{next_exam_number:02d}",
                "title": f"{bank_title} Exam {next_exam_number}",
                "bank": bank_id,
                "bank_title": bank_title,
                "questions": exam_questions,
            }
            merged_exams.append(new_exam)
            next_exam_number += 1
        next_exam_number_by_bank[bank_id] = next_exam_number - 1

    merged_bundle = {
        "generated_at": normalized_bundle.get("generated_at") or now_iso,
        "exams": merged_exams,
    }
    if (not canonical_curated_exams_json.exists()) or (merged_bundle != bundle):
        write_json(canonical_curated_exams_json, merged_bundle, indent=2)
    return merged_bundle


def _source_stem_from_exam_id(exam_id: str) -> str:
    if len(exam_id) < 4 or exam_id[-3] != "-":
        return ""
    suffix = exam_id[-2:]
    if not suffix.isdigit():
        return ""
    return exam_id[:-3]


def _exam_sequence_number(exam_id: str) -> int:
    suffix = exam_id[-2:] if len(exam_id) >= 2 else ""
    return int(suffix) if suffix.isdigit() else 0


def _curated_question_sequence_number(question_id: str) -> int:
    match = question_id.rsplit("-q", 1)
    if len(match) != 2 or not match[1].isdigit():
        return 0
    return int(match[1])


def _normalize_curated_bundle(bundle: dict[str, Any], *, generated_at: str) -> dict[str, Any]:
    normalized_exams: list[dict[str, Any]] = []
    exam_counts: dict[str, int] = {}
    question_counts: dict[str, int] = {}
    for exam in bundle.get("exams", []):
        if exam.get("source_type") == "explicit_curated_exam":
            normalized_exams.append(_normalize_explicit_curated_exam_record(exam))
            continue
        bank_id = str(exam.get("bank", "")).strip().lower() or "curated"
        bank_title = _canonical_curated_bank_title(
            bank_id,
            fallback_title=str(exam.get("bank_title", "")).strip() or bank_id.upper(),
        )
        exam_counts[bank_id] = exam_counts.get(bank_id, 0) + 1
        exam_number = exam_counts[bank_id]
        normalized_questions: list[dict[str, Any]] = []
        for question in exam.get("questions", []):
            question_counts[bank_id] = question_counts.get(bank_id, 0) + 1
            question_number = question_counts[bank_id]
            normalized_questions.append(
                _canonicalize_curated_question(
                    question,
                    bank_id=bank_id,
                    question_index=question_number,
                )
            )
        normalized_exams.append(
            {
                "id": f"{bank_id}-{exam_number:02d}",
                "title": f"{bank_title} Exam {exam_number}",
                "bank": bank_id,
                "bank_title": bank_title,
                "questions": normalized_questions,
            }
        )
    return {
        "generated_at": bundle.get("generated_at") or generated_at,
        "exams": normalized_exams,
    }


def _normalize_explicit_curated_exam_record(exam: dict[str, Any]) -> dict[str, Any]:
    normalized_exam = dict(exam)
    normalized_exam["source_type"] = "explicit_curated_exam"
    normalized_questions: list[dict[str, Any]] = []
    for index, question in enumerate(normalized_exam.get("questions", []), 1):
        normalized_question = dict(question)
        normalized_question.setdefault("question_number", index)
        normalized_question.setdefault("curated_problem_number", index)
        normalized_question.setdefault("curated_problem_link", "")
        normalized_question.setdefault("question_images", [])
        normalized_questions.append(normalized_question)
    normalized_exam["questions"] = normalized_questions
    normalized_exam["question_count"] = len(normalized_questions)
    return normalized_exam


def _canonical_curated_bank_title(bank_id: str, *, fallback_title: str) -> str:
    if bank_id == "amc":
        return "AMC & AIME"
    return fallback_title


def _canonicalize_curated_question(question: dict[str, Any], *, bank_id: str, question_index: int) -> dict[str, Any]:
    normalized_question = dict(question)
    normalized_question["id"] = f"{bank_id}-q{question_index:03d}"
    normalized_question["type"] = bank_id
    normalized_question["curated_problem_number"] = int(
        normalized_question.get("curated_problem_number", normalized_question.get("question_number", question_index))
    )
    checksum = _curated_question_checksum(normalized_question)
    if checksum is not None:
        normalized_question["curated_question_checksum"] = checksum
    normalized_question.pop("curated_fingerprint", None)
    return normalized_question


def _curated_question_checksum(question: dict[str, Any]) -> str | None:
    text = _normalize_curated_text(str(question.get("text", "")).strip())
    if not text:
        return None
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _normalize_curated_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()

def build_challenges(
    output_dir: Path,
    site_dir: Path,
    force: bool = False,
    experience_variant: str = DEFAULT_EXPERIENCE_VARIANT,
) -> None:
    experience_variant = normalize_experience_variant(experience_variant)
    challenges_dir = site_dir / "challenges"
    challenges_dir.mkdir(parents=True, exist_ok=True)

    # Canonical files live in challenges_src/ so they are tracked in git
    canonical_exams_json = CHALLENGES_SRC_DIR / "exams.json"
    canonical_master_json = CHALLENGES_SRC_DIR / "master_questions.json"
    canonical_chapter_exams_json = CHALLENGES_SRC_DIR / "chapter_exams.json"
    canonical_curated_exams_json = CANONICAL_CURATED_EXAMS_JSON

    if canonical_exams_json.exists() and canonical_master_json.exists() and canonical_chapter_exams_json.exists():
        existing = json.loads(canonical_exams_json.read_text(encoding="utf-8"))
        generated_at = existing.get("generated_at", "unknown")
        exam_count = len(existing.get("exams", []))
        action_label = "Preserving existing classic challenge mappings"
        if force:
            action_label += " (force keeps canonical classic catalogs unchanged)"
        print(f"{action_label} ({exam_count} exams, bundle: {generated_at}).")
    else:
        print("Generating challenge exams for the first time...")
        questions = load_all_questions(output_dir)
        mcq_mm = sum(1 for q in questions if q["type"] == "mm" and "correct" in q)
        mcq_op = sum(1 for q in questions if q["type"] == "op" and "correct" in q)
        print(f"  Found {len(questions)} questions total; "
              f"{mcq_mm} mental math + {mcq_op} olympiad have MCQ data")

        exams = build_exam_sets(questions)
        chapter_exams = build_chapter_exam_sets(questions)
        generated_at = datetime.now(timezone.utc).isoformat()
        print(f"  Generated {len(exams)} challenge exams (bundle: {generated_at})")
        catalog_stats = write_canonical_challenge_catalogs(
            canonical_exams_json=canonical_exams_json,
            canonical_master_json=canonical_master_json,
            canonical_chapter_exams_json=canonical_chapter_exams_json,
            generated_at=generated_at,
            exams=exams,
            chapter_exams=chapter_exams,
            questions=questions,
        )
        print(f"  Wrote {canonical_exams_json}")
        print(f"  Wrote {canonical_master_json.name} ({catalog_stats['question_count']} questions)")
        print(f"  Wrote {canonical_chapter_exams_json.name} ({catalog_stats['chapter_exam_count']} chapter exams)")

    curated_bundle = sync_curated_exam_bundle(
        exams_dir=CURATED_EXAMS_DIR,
        canonical_curated_exams_json=canonical_curated_exams_json,
    )
    curated_exams = curated_bundle.get("exams", [])
    classic_bundle = load_classic_exam_bundle(canonical_exams_json)
    full = build_deploy_exam_bundle(classic_bundle=classic_bundle, curated_exams=curated_exams)
    if curated_exams:
        print(
            f"  Loaded {len(curated_exams)} curated bank exam(s) from "
            f"{canonical_curated_exams_json.name}"
        )

    # Always copy static PHP + HTML source files (picks up UI changes)
    # Skip exams.json — it's only needed to generate individual exam files, not served directly.
    copy_static_challenge_assets(source_dir=CHALLENGES_SRC_DIR, challenges_dir=challenges_dir)
    for source_path in CHALLENGES_SRC_DIR.glob("*"):
        if source_path.name in ("exams.json", "master_questions.json", "chapter_exams.json", "curated_exams.json"):
            continue
        suffix = "/" if source_path.is_dir() else ""
        print(f"  Copied {source_path.name}{suffix}")

    # Always generate a lightweight exams-index.json for the picker page (no question text)
    # and individual per-exam JSON files so exam.html only fetches ~4KB instead of 194KB.
    exam_output_stats = materialize_exam_outputs(
        challenges_dir=challenges_dir,
        bundle=full,
        full_bundle_size=len(json.dumps(full).encode("utf-8")),
    )
    average_size = exam_output_stats["avg_individual_size_bytes"]
    average_label = (
        f"{average_size // 1024}KB" if average_size >= 1024 else f"{average_size}B"
    )
    print(
        f"  Wrote exams-index.json ({exam_output_stats['exam_count']} exams, "
        f"{exam_output_stats['index_size_kb']}KB vs {exam_output_stats['full_bundle_size_kb']}KB full)"
    )
    print(
        f"  Wrote {exam_output_stats['exam_count']} individual exam files to exams/ "
        f"(avg {average_label} each, vs {exam_output_stats['full_bundle_size_kb']}KB full bundle)"
    )

    chapter_full = json.loads(canonical_chapter_exams_json.read_text(encoding="utf-8"))
    chapter_output_stats = materialize_chapter_exam_outputs(
        challenges_dir=challenges_dir,
        bundle=chapter_full,
    )
    print(f"  Wrote chapter challenge index ({chapter_output_stats['chapter_exam_count']} exams)")

    # Always regenerate config.php from current env vars
    config_path = challenges_dir / "config.php"
    generate_config_php(config_path, experience_variant=experience_variant)
    print(f"  Generated {config_path}")

    experience_script_path = challenges_dir / "experience.js"
    write_experience_script(experience_script_path, experience_variant=experience_variant)
    print(f"  Generated {experience_script_path}")

    print(f"\nChallenge exams at: {challenges_dir}")


def main() -> None:
    load_dotenv_if_present()
    import argparse
    parser = argparse.ArgumentParser(description="Build challenge exam files from saved AI responses.")
    parser.add_argument("--output-dir", default=str(PACKAGE_DIR / "output"),
                        help="Directory containing responses/ and other outputs.")
    parser.add_argument("--site-dir", default=str(PACKAGE_DIR / "output" / "deploy" / "math_tutor" / "site"),
                        help="Site directory where challenges/ will be written.")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate exams.json even if it already exists.")
    parser.add_argument(
        "--experience",
        choices=CLI_EXPERIENCE_CHOICES,
        default=DEFAULT_EXPERIENCE_VARIANT,
        help=(
            f"Choose which challenge experience variant to build. Defaults to {DEFAULT_EXPERIENCE_VARIANT}. "
            "Use archived for the older pre-refresh styling."
        ),
    )
    args = parser.parse_args()
    build_challenges(
        output_dir=Path(args.output_dir).resolve(),
        site_dir=Path(args.site_dir).resolve(),
        force=args.force,
        experience_variant=normalize_experience_variant(args.experience),
    )
