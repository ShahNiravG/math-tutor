"""Generate multiple-choice options for existing mental-math and olympiad question files."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from math_tutor.env_config import load_dotenv_if_present
from math_tutor.mcq_artifacts import build_mcq_output_paths
from math_tutor.mcq_clients import build_mcq_clients
from math_tutor.mcq_prompts import SOURCE_CONFIGS
from math_tutor.mcq_workflow import process_mcq_file

PACKAGE_DIR = Path(__file__).resolve().parent
RESPONSES_DIR = PACKAGE_DIR / "output" / "responses"


def main() -> None:
    load_dotenv_if_present()

    parser = argparse.ArgumentParser(
        description="Generate MCQ options for existing mental-math and olympiad question files."
    )
    parser.add_argument("--responses-dir", default=str(RESPONSES_DIR),
                        help="Directory containing *__mental-math-*.md and *__olympiad-*.md files.")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate even if MCQ output already exists.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be processed without making API calls.")
    parser.add_argument("--limit", type=int, default=0,
                        help="Stop after processing this many files (0 = no limit).")
    args = parser.parse_args()

    responses_dir = Path(args.responses_dir).resolve()

    openai_client, gemini_client = build_mcq_clients(
        openai_api_key=os.environ.get("OPENAI_API_KEY"),
        gemini_api_key=os.environ.get("GEMINI_API_KEY"),
    )

    total = 0
    skipped = 0
    processed = 0

    for source_config in SOURCE_CONFIGS:
        source_files = sorted(responses_dir.glob(f"*{source_config.source_suffix}"))
        for source_md in source_files:
            total += 1
            output_paths = build_mcq_output_paths(
                source_md=source_md,
                mcq_slug=source_config.mcq_suffix,
                responses_dir=responses_dir,
            )

            if not args.force and output_paths.markdown_path.exists():
                skipped += 1
                if args.dry_run:
                    print(f"  [skip] {output_paths.markdown_path.name}")
                continue

            if args.dry_run:
                print(f"  [would process] {source_md.name} → {output_paths.markdown_path.name}")
                processed += 1
                continue

            process_mcq_file(
                source_md=source_md,
                source_config=source_config,
                responses_dir=responses_dir,
                openai_client=openai_client,
                gemini_client=gemini_client,
                force=args.force,
            )
            processed += 1
            if args.limit and processed >= args.limit:
                print(f"\nReached --limit {args.limit}, stopping.")
                break
        if args.limit and processed >= args.limit:
            break

    print(f"\nDone. {processed} processed, {skipped} skipped, {total} total.")
