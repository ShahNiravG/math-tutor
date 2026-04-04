from __future__ import annotations

import argparse
import re
from pathlib import Path

from math_tutor.cli_auth import resolve_canvas_credentials
from math_tutor.cli_commands import (
    build_guided_learning_site,
    handle_print_command,
    run_canvas_workflow,
    run_skip_fetch_workflow,
    should_use_saved_fetch_shortcut,
)
from math_tutor.cli_context import build_command_context
from math_tutor.env_config import load_dotenv_if_present
from math_tutor.prompt_catalog import DEFAULT_MODEL, PRINTABLE_PROMPT_SLUGS, PROMPTS_BY_SLUG

COURSE_URL = "https://mitty.instructure.com/courses/4187"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download PDFs from a Canvas course and generate tutoring artifacts."
    )
    parser.add_argument("--username", required=False, help="Canvas login username or email.")
    parser.add_argument("--password", required=False, help="Canvas login password.")
    parser.add_argument(
        "--course-url",
        default=COURSE_URL,
        help=f"Canvas course URL to scan. Defaults to {COURSE_URL}.",
    )
    parser.add_argument(
        "--login-url",
        default=None,
        help="Optional login entry URL. If omitted, the CLI starts from the course URL and follows the site's redirect chain.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parent / "output"),
        help="Directory for downloads, responses, and metadata.",
    )
    parser.add_argument(
        "--default-model",
        default=DEFAULT_MODEL,
        help=f"Default model for prompts that do not specify one. Defaults to {DEFAULT_MODEL}.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of PDFs to process.",
    )
    parser.add_argument(
        "--headful",
        action="store_true",
        help="Run the login browser in headed mode for debugging.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Reprocess files even if an output already exists.",
    )
    parser.add_argument(
        "--fetch-only",
        action="store_true",
        help="Only fetch matching PDFs and update fetch state; skip the generation phase.",
    )
    parser.add_argument(
        "--skip-fetch",
        action="store_true",
        help="Skip Canvas login and fetching entirely; use already-downloaded PDFs from fetch_state.json.",
    )
    parser.add_argument(
        "--list-files",
        action="store_true",
        help="List all PDF file names found on the course pages and exit (useful for debugging name patterns).",
    )
    parser.add_argument(
        "--fetch-assignments",
        action="store_true",
        help=(
            "Fetch assignment PDFs (chapter-numbered files like '5.1.pdf' or '7.4 and 7.5.pdf') "
            "instead of class notes."
        ),
    )
    parser.add_argument(
        "--assignment-limit",
        type=int,
        default=None,
        help="Maximum number of assignment PDFs to fetch when --fetch-assignments is used.",
    )
    parser.add_argument(
        "--force-generation",
        action="store_true",
        help="Run the generation step again even for files that already have saved outputs.",
    )
    parser.add_argument(
        "--force-prompt",
        dest="force_prompt_slugs",
        action="append",
        choices=sorted(PROMPTS_BY_SLUG),
        help=(
            "Force generation for a specific prompt slug. "
            "Repeat the flag to force multiple prompts, for example "
            "--force-prompt study-guide --force-prompt inspiring-videos."
        ),
    )
    parser.add_argument(
        "--prompt",
        dest="prompt_slugs",
        action="append",
        choices=sorted(PROMPTS_BY_SLUG),
        help=(
            "Limit generation to a specific prompt slug. "
            "Repeat the flag to run multiple prompts, for example "
            "--prompt study-guide --prompt mental-math. Defaults to all prompts."
        ),
    )
    parser.add_argument(
        "--build-site-guided-learning",
        action="store_true",
        help=(
            "After processing, build the tutoring page and add a Guided Learning section for each PDF processed in this run."
        ),
    )
    parser.add_argument(
        "--site-dir",
        default=None,
        help="Optional output directory for the generated tutoring page when --build-site-guided-learning is used.",
    )
    parser.add_argument(
        "--site-base-path",
        default="",
        help=(
            "Optional deployed site prefix such as /math_tutor/ when --build-site-guided-learning is used."
        ),
    )
    parser.add_argument(
        "--print-prompt",
        dest="print_prompt_slugs",
        action="append",
        choices=sorted(PRINTABLE_PROMPT_SLUGS),
        help=(
            "Print saved generated PDFs for a prompt without rerunning fetch or generation. "
            "Repeat the flag to print multiple prompt types, for example "
            "--print-prompt class-note --print-prompt study-guide."
        ),
    )
    parser.add_argument(
        "--chapter",
        dest="chapter_filters",
        action="append",
        help=(
            "Optional chapter filter, such as 6.3 or 7.4 & 7.5. "
            "Repeat the flag to include multiple chapters. "
            "Applies to both --print-prompt and the main processing pipeline. "
            "If omitted, all chapters are processed."
        ),
    )
    parser.add_argument(
        "--printer",
        default="Brother",
        help="Printer name to use with --print-prompt. Defaults to Brother.",
    )
    parser.add_argument(
        "--print-all",
        action="store_true",
        help="Print all prompt types (class note, assignments, and all generated PDFs) for the given --chapter.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="With --print-prompt or --print-all, list what would be printed without sending to the printer.",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv_if_present()
    args = parse_args()
    try:
        output_dir = Path(args.output_dir).resolve()
        if handle_print_command(
            output_dir=output_dir,
            print_all=args.print_all,
            print_prompt_slugs=args.print_prompt_slugs,
            chapter_filters=args.chapter_filters,
            printer=args.printer,
            dry_run=args.dry_run,
        ):
            return

        command_context = build_command_context(
            args=args,
            output_dir=output_dir,
            log=lambda message: print(message, flush=True),
        )

        canvas_credentials = resolve_canvas_credentials(
            username=args.username,
            password=args.password,
            skip_fetch=args.skip_fetch or should_use_saved_fetch_shortcut(command_context),
        )

        if args.skip_fetch:
            processed_file_ids = run_skip_fetch_workflow(command_context)
        else:
            processed_file_ids = run_canvas_workflow(
                command_context=command_context,
                canvas_credentials=canvas_credentials,
                maybe_prompt_before_exit=maybe_prompt_before_exit,
            )

        if args.build_site_guided_learning:
            index_path = build_guided_learning_site(
                output_dir=output_dir,
                site_dir=args.site_dir,
                base_path=args.site_base_path,
                limit=args.limit,
                processed_file_ids=processed_file_ids,
            )
            print(f"Built tutoring page with Guided Learning at {index_path}", flush=True)
    except KeyboardInterrupt:
        raise SystemExit(130)


def maybe_prompt_before_exit(headful: bool) -> None:
    if not headful:
        return
    try:
        input("Press Enter to exit...")
    except EOFError:
        pass


if __name__ == "__main__":
    main()
