"""Build interactive challenge exams from saved AI-generated question files."""
from __future__ import annotations

import json
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from math_tutor.challenge_catalog import (
    build_chapter_exam_sets,
    build_exam_sets,
    load_all_questions,
)
from math_tutor.chaptering import chapter_slug, chapter_sort_key
from math_tutor.env_config import load_dotenv_if_present

PACKAGE_DIR = Path(__file__).resolve().parent

CHALLENGES_SRC_DIR = PACKAGE_DIR / "challenges_src"
# ---------------------------------------------------------------------------
# Config PHP generation
# ---------------------------------------------------------------------------

def _php_str(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def generate_config_php(output_path: Path) -> None:
    load_dotenv_if_present()
    host = os.environ.get("MYSQL_HOST") or os.environ.get("MySQL_HOST") or "localhost"
    dbname = os.environ.get("DBNAME", "")
    user = os.environ.get("DBUSER", "")
    password = os.environ.get("DBPASSWORD", "")
    output_path.write_text(
        f"<?php\n"
        f"define('DB_HOST', {_php_str(host)});\n"
        f"define('DB_NAME', {_php_str(dbname)});\n"
        f"define('DB_USER', {_php_str(user)});\n"
        f"define('DB_PASS', {_php_str(password)});\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build_challenges(
    output_dir: Path,
    site_dir: Path,
    force: bool = False,
) -> None:
    challenges_dir = site_dir / "challenges"
    challenges_dir.mkdir(parents=True, exist_ok=True)

    # Canonical files live in challenges_src/ so they are tracked in git
    canonical_exams_json = CHALLENGES_SRC_DIR / "exams.json"
    canonical_master_json = CHALLENGES_SRC_DIR / "master_questions.json"
    canonical_chapter_exams_json = CHALLENGES_SRC_DIR / "chapter_exams.json"

    if (
        not force
        and canonical_exams_json.exists()
        and canonical_master_json.exists()
        and canonical_chapter_exams_json.exists()
    ):
        existing = json.loads(canonical_exams_json.read_text(encoding="utf-8"))
        generated_at = existing.get("generated_at", "unknown")
        exam_count = len(existing.get("exams", []))
        print(f"Challenge exams already generated ({exam_count} exams, bundle: {generated_at}). "
              f"Skipping regeneration. Use --force-challenges to regenerate.")
    else:
        if force and canonical_exams_json.exists():
            print("Force flag set — regenerating challenge exams...")
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

        canonical_exams_json.write_text(
            json.dumps({"generated_at": generated_at, "exams": exams}, indent=2),
            encoding="utf-8",
        )
        print(f"  Wrote {canonical_exams_json}")

        # Master questions catalog: flat list of all MCQ-equipped questions (uber artifact)
        all_with_mcq = [q for q in questions if "correct" in q]
        master_data = {
            "generated_at": generated_at,
            "total": len(all_with_mcq),
            "mental_math": sum(1 for q in all_with_mcq if q["type"] == "mm"),
            "olympiad": sum(1 for q in all_with_mcq if q["type"] == "op"),
            "questions": all_with_mcq,
        }
        canonical_master_json.write_text(
            json.dumps(master_data, indent=2), encoding="utf-8"
        )
        print(f"  Wrote {canonical_master_json.name} ({len(all_with_mcq)} questions)")
        canonical_chapter_exams_json.write_text(
            json.dumps({"generated_at": generated_at, "exams": chapter_exams}, indent=2),
            encoding="utf-8",
        )
        print(f"  Wrote {canonical_chapter_exams_json.name} ({len(chapter_exams)} chapter exams)")

    # Always copy static PHP + HTML source files (picks up UI changes)
    # Skip exams.json — it's only needed to generate individual exam files, not served directly.
    for src_file in CHALLENGES_SRC_DIR.glob("*"):
        if src_file.name in ("exams.json", "master_questions.json", "chapter_exams.json"):
            continue
        dest = challenges_dir / src_file.name
        if src_file.is_dir():
            if dest.exists():
                shutil.rmtree(dest)
            shutil.copytree(src_file, dest)
            print(f"  Copied {src_file.name}/")
        else:
            shutil.copy2(src_file, dest)
            print(f"  Copied {src_file.name}")

    # Always generate a lightweight exams-index.json for the picker page (no question text)
    # and individual per-exam JSON files so exam.html only fetches ~4KB instead of 194KB.
    full = json.loads(canonical_exams_json.read_text(encoding="utf-8"))
    generated_at = full.get("generated_at")
    index_entries = []
    exams_subdir = challenges_dir / "exams"
    exams_subdir.mkdir(exist_ok=True)
    total_individual_kb = 0
    for exam in full.get("exams", []):
        mm = sum(1 for q in exam["questions"] if q["type"] == "mm")
        op = sum(1 for q in exam["questions"] if q["type"] == "op")
        chapters = sorted(
            {q["chapter"] for q in exam["questions"]},
            key=lambda c: float(re.match(r"^[\d.]+", c).group()) if re.match(r"^[\d.]+", c) else 9999,
        )
        index_entries.append({
            "id": exam["id"],
            "title": exam["title"],
            "mm": mm,
            "op": op,
            "chapters": chapters,
        })
        # Write individual exam file: exams/{exam-id}.json
        individual_path = exams_subdir / f"{exam['id']}.json"
        individual_path.write_text(
            json.dumps({"generated_at": generated_at, **exam}),
            encoding="utf-8",
        )
        total_individual_kb += individual_path.stat().st_size
    index_json_path = challenges_dir / "exams-index.json"
    index_json_path.write_text(
        json.dumps({"generated_at": generated_at, "exams": index_entries}),
        encoding="utf-8",
    )
    full_kb = canonical_exams_json.stat().st_size // 1024
    avg_kb = (total_individual_kb // len(index_entries)) if index_entries else 0
    print(f"  Wrote exams-index.json ({len(index_entries)} exams, "
          f"{index_json_path.stat().st_size // 1024}KB vs {full_kb}KB full)")
    print(f"  Wrote {len(index_entries)} individual exam files to exams/ "
          f"(avg {avg_kb // 1024 if avg_kb >= 1024 else avg_kb}{'KB' if avg_kb >= 1024 else 'B'} each, "
          f"vs {full_kb}KB full bundle)")

    chapter_full = json.loads(canonical_chapter_exams_json.read_text(encoding="utf-8"))
    chapter_index_entries = []
    chapter_subdir = challenges_dir / "chapter-exams"
    chapter_subdir.mkdir(exist_ok=True)
    for exam in chapter_full.get("exams", []):
        mm = sum(1 for q in exam["questions"] if q["type"] == "mm")
        op = sum(1 for q in exam["questions"] if q["type"] == "op")
        models = sorted({q["model_label"] for q in exam["questions"]})
        chapter_index_entries.append({
            "id": exam["id"],
            "title": exam["title"],
            "chapter": exam["chapter"],
            "challenge_type": exam.get("challenge_type", ""),
            "mm": mm,
            "op": op,
            "question_count": len(exam["questions"]),
            "models": models,
        })
        (exams_subdir / f"{exam['id']}.json").write_text(
            json.dumps({"generated_at": chapter_full.get("generated_at"), **exam}),
            encoding="utf-8",
        )
    (chapter_subdir / "index.json").write_text(
        json.dumps({"generated_at": chapter_full.get("generated_at"), "exams": chapter_index_entries}, indent=2),
        encoding="utf-8",
    )
    for chapter in sorted({e["chapter"] for e in chapter_index_entries}, key=chapter_sort_key):
        chapter_exams = [e for e in chapter_index_entries if e["chapter"] == chapter]
        chapter_key = chapter_slug(chapter)
        (chapter_subdir / f"chp{chapter_key}.json").write_text(
            json.dumps({
                "generated_at": chapter_full.get("generated_at"),
                "chapter": chapter,
                "exams": chapter_exams,
            }, indent=2),
            encoding="utf-8",
        )
    print(f"  Wrote chapter challenge index ({len(chapter_index_entries)} exams)")

    # Always regenerate config.php from current env vars
    config_path = challenges_dir / "config.php"
    generate_config_php(config_path)
    print(f"  Generated {config_path}")

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
    args = parser.parse_args()
    build_challenges(
        output_dir=Path(args.output_dir).resolve(),
        site_dir=Path(args.site_dir).resolve(),
        force=args.force,
    )
