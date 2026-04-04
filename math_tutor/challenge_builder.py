"""Build interactive challenge exams from saved AI-generated question files."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from math_tutor.challenge_catalog import (
    build_chapter_exam_sets,
    build_exam_sets,
    load_all_questions,
)
from math_tutor.challenge_config import generate_config_php
from math_tutor.challenge_config import write_experience_script
from math_tutor.challenge_outputs import (
    copy_static_challenge_assets,
    materialize_chapter_exam_outputs,
    materialize_exam_outputs,
    write_canonical_challenge_catalogs,
)
from math_tutor.env_config import load_dotenv_if_present

PACKAGE_DIR = Path(__file__).resolve().parent

CHALLENGES_SRC_DIR = PACKAGE_DIR / "challenges_src"

def build_challenges(
    output_dir: Path,
    site_dir: Path,
    force: bool = False,
    experience_variant: str = "default",
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

    # Always copy static PHP + HTML source files (picks up UI changes)
    # Skip exams.json — it's only needed to generate individual exam files, not served directly.
    copy_static_challenge_assets(source_dir=CHALLENGES_SRC_DIR, challenges_dir=challenges_dir)
    for source_path in CHALLENGES_SRC_DIR.glob("*"):
        if source_path.name in ("exams.json", "master_questions.json", "chapter_exams.json"):
            continue
        suffix = "/" if source_path.is_dir() else ""
        print(f"  Copied {source_path.name}{suffix}")

    # Always generate a lightweight exams-index.json for the picker page (no question text)
    # and individual per-exam JSON files so exam.html only fetches ~4KB instead of 194KB.
    full = json.loads(canonical_exams_json.read_text(encoding="utf-8"))
    exam_output_stats = materialize_exam_outputs(
        challenges_dir=challenges_dir,
        bundle=full,
        full_bundle_size=canonical_exams_json.stat().st_size,
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
        choices=("default", "staging"),
        default="default",
        help="Choose which challenge experience variant to build. Defaults to default.",
    )
    args = parser.parse_args()
    build_challenges(
        output_dir=Path(args.output_dir).resolve(),
        site_dir=Path(args.site_dir).resolve(),
        force=args.force,
        experience_variant=args.experience,
    )
