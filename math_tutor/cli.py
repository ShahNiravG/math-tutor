from __future__ import annotations

import argparse
import html as html_module
import json
import os
import re
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin, urlparse

import httpx
from openai import OpenAI
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError, sync_playwright

COURSE_URL = "https://mitty.instructure.com/courses/4187"
DEFAULT_MODEL = "gpt-4.1"
DEFAULT_TIMEOUT_SECONDS = 60
LOGIN_RENDER_TIMEOUT_MS = 20_000
FILES_PAGE_TIMEOUT_MS = 30_000
TARGET_NAME_SUBSTRINGS = ("note.docx", "note.pdf")
ASSIGNMENT_NAME_PATTERN = re.compile(r"^\d+\.\d+", re.IGNORECASE)
MATHJAX_SCRIPT = (
    "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"
)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


@dataclass(frozen=True)
class PromptSpec:
    slug: str
    title: str
    text: str
    source_prompt_slug: str | None = None
    source_placeholder: str = "{{previous_output}}"
    include_source_pdf_link: bool = True
    generate_response_pdf: bool = True
    model: str | None = None
    reasoning_effort: str | None = None


STUDY_GUIDE_PROMPT = PromptSpec(
    slug="study-guide",
    title="Study guide",
    text="""You are a careful math tutor.

Read the attached PDF and produce:
1. A short summary of the document.
2. A list of the core definitions, theorems, and formulas.
3. A worked study guide that explains the important ideas step by step.
4. Five practice problems with answers, based only on the document.
5. Any assumptions or ambiguities you had to resolve.

Keep the response self-contained and use clear section headings.
""",
)

INSPIRING_VIDEOS_PROMPT = PromptSpec(
    slug="inspiring-videos",
    title="Inspiring Videos",
    text="""I have a 14-year-old student studying the math topics in the attached PDF.

For the topics in the PDF, recommend 1-2 highly engaging and visually intuitive YouTube videos from reputable math creators that inspire curiosity rather than focus on procedural problem solving.

Requirements:
1. Prefer videos that build deep conceptual understanding, such as geometric or visual intuition.
2. Keep the recommendations appropriate for a motivated beginner.
3. Avoid overly technical, competition-focused, or Olympiad-level content.
4. Do not provide a direct YouTube watch URL, since those are often hallucinated or stale.
5. Instead, provide a Google search link that is likely to find the exact video, using the video title, creator name, and the word YouTube in the query.
6. Make the search query specific enough that a student can quickly find the intended video from the results.
7. For each recommendation, briefly explain why it is inspiring and why it matches the topics in the PDF.
8. If the PDF spans several distinct topics, choose the 1-2 videos that best cover the most central ideas.

Format the response as a short list with the video title, creator, Google search link, and a brief explanation.
""",
    include_source_pdf_link=False,
    generate_response_pdf=False,
)

MENTAL_MATH_PROMPT = PromptSpec(
    slug="mental-math",
    title="Mental Math",
    text=(
        "Generate 10 mental math questions based on this math pdf. "
        "These question should be answerable without paper and pencil. "
        "The questions should test the understanding of the core concepts. "
        "Give only the questions, with short titles if helpful."
    ),
)

OLYMPIAD_PROBLEMS_PROMPT = PromptSpec(
    slug="olympiad-problems",
    title="Olympiad Problems",
    text="""You are designing elegant Olympiad-style mental math problems from the attached PDF.

Generate 6 challenging problems inspired by the core ideas in the PDF.

Requirements:
1. The problems should be harder than the normal mental math set.
2. They should reward insight, pattern recognition, symmetry, invariants, estimation, or clever algebraic/trigonometric manipulation.
3. They should still be solvable mentally or with very light scratch work.
4. Do not provide solutions yet.
5. Keep the statements concise and polished.
6. Output only a numbered list of problems under the heading "Problems".
""",
)

OLYMPIAD_SOLUTIONS_PROMPT = PromptSpec(
    slug="olympiad-solutions",
    title="Olympiad Solutions",
    text="""You are writing elegant Olympiad-style solutions.

Use the exact problem list below and provide step-by-step solutions for each problem.

Requirements:
1. Preserve the original numbering and wording of the problems.
2. Give concise but rigorous reasoning.
3. Prefer elegant observations over brute force.
4. Make each solution self-contained.
5. Format the response under the heading "Solutions".

Problem list to solve:
{{previous_output}}
""",
    source_prompt_slug="olympiad-problems",
)

GPT5_MODEL = "gpt-5.4"

STUDY_GUIDE_GPT5_PROMPT = PromptSpec(slug="study-guide-gpt5", title="Study Guide (GPT-5.4)", text=STUDY_GUIDE_PROMPT.text, model=GPT5_MODEL)
INSPIRING_VIDEOS_GPT5_PROMPT = PromptSpec(slug="inspiring-videos-gpt5", title="Inspiring Videos (GPT-5.4)", text=INSPIRING_VIDEOS_PROMPT.text, include_source_pdf_link=False, generate_response_pdf=False, model=GPT5_MODEL)
MENTAL_MATH_GPT5_PROMPT = PromptSpec(slug="mental-math-gpt5", title="Mental Math (GPT-5.4)", text=MENTAL_MATH_PROMPT.text, model=GPT5_MODEL)
OLYMPIAD_PROBLEMS_GPT5_PROMPT = PromptSpec(slug="olympiad-problems-gpt5", title="Olympiad Problems (GPT-5.4)", text=OLYMPIAD_PROBLEMS_PROMPT.text, model=GPT5_MODEL)
OLYMPIAD_SOLUTIONS_GPT5_PROMPT = PromptSpec(slug="olympiad-solutions-gpt5", title="Olympiad Solutions (GPT-5.4)", text=OLYMPIAD_SOLUTIONS_PROMPT.text, source_prompt_slug="olympiad-problems-gpt5", source_placeholder=OLYMPIAD_SOLUTIONS_PROMPT.source_placeholder, model=GPT5_MODEL)

GEMINI_MODEL = "gemini-3.1-pro-preview"

STUDY_GUIDE_GEMINI_PROMPT = PromptSpec(slug="study-guide-gemini", title="Study Guide (Gemini)", text=STUDY_GUIDE_PROMPT.text, model=GEMINI_MODEL)
INSPIRING_VIDEOS_GEMINI_PROMPT = PromptSpec(slug="inspiring-videos-gemini", title="Inspiring Videos (Gemini)", text=INSPIRING_VIDEOS_PROMPT.text, include_source_pdf_link=False, generate_response_pdf=False, model=GEMINI_MODEL)
MENTAL_MATH_GEMINI_PROMPT = PromptSpec(slug="mental-math-gemini", title="Mental Math (Gemini)", text=MENTAL_MATH_PROMPT.text, model=GEMINI_MODEL)
OLYMPIAD_PROBLEMS_GEMINI_PROMPT = PromptSpec(slug="olympiad-problems-gemini", title="Olympiad Problems (Gemini)", text=OLYMPIAD_PROBLEMS_PROMPT.text, model=GEMINI_MODEL)
OLYMPIAD_SOLUTIONS_GEMINI_PROMPT = PromptSpec(slug="olympiad-solutions-gemini", title="Olympiad Solutions (Gemini)", text=OLYMPIAD_SOLUTIONS_PROMPT.text, source_prompt_slug="olympiad-problems-gemini", source_placeholder=OLYMPIAD_SOLUTIONS_PROMPT.source_placeholder, model=GEMINI_MODEL)

PROMPTS: tuple[PromptSpec, ...] = (
    STUDY_GUIDE_PROMPT,
    STUDY_GUIDE_GPT5_PROMPT,
    STUDY_GUIDE_GEMINI_PROMPT,
    INSPIRING_VIDEOS_PROMPT,
    INSPIRING_VIDEOS_GPT5_PROMPT,
    INSPIRING_VIDEOS_GEMINI_PROMPT,
    MENTAL_MATH_PROMPT,
    MENTAL_MATH_GPT5_PROMPT,
    MENTAL_MATH_GEMINI_PROMPT,
    OLYMPIAD_PROBLEMS_PROMPT,
    OLYMPIAD_PROBLEMS_GPT5_PROMPT,
    OLYMPIAD_PROBLEMS_GEMINI_PROMPT,
    OLYMPIAD_SOLUTIONS_PROMPT,
    OLYMPIAD_SOLUTIONS_GPT5_PROMPT,
    OLYMPIAD_SOLUTIONS_GEMINI_PROMPT,
)
PROMPTS_BY_SLUG: dict[str, PromptSpec] = {prompt_spec.slug: prompt_spec for prompt_spec in PROMPTS}
CLASS_NOTE_PRINT_SLUG = "class-note"
ASSIGNMENT_PRINT_SLUG = "assignment"
PRINTABLE_PROMPT_SLUGS: tuple[str, ...] = (
    CLASS_NOTE_PRINT_SLUG,
    ASSIGNMENT_PRINT_SLUG,
    STUDY_GUIDE_PROMPT.slug,
    STUDY_GUIDE_GPT5_PROMPT.slug,
    STUDY_GUIDE_GEMINI_PROMPT.slug,
    MENTAL_MATH_PROMPT.slug,
    MENTAL_MATH_GPT5_PROMPT.slug,
    MENTAL_MATH_GEMINI_PROMPT.slug,
    OLYMPIAD_PROBLEMS_PROMPT.slug,
    OLYMPIAD_PROBLEMS_GPT5_PROMPT.slug,
    OLYMPIAD_PROBLEMS_GEMINI_PROMPT.slug,
    OLYMPIAD_SOLUTIONS_PROMPT.slug,
    OLYMPIAD_SOLUTIONS_GPT5_PROMPT.slug,
    OLYMPIAD_SOLUTIONS_GEMINI_PROMPT.slug,
)


@dataclass(frozen=True)
class CanvasFile:
    file_id: int
    display_name: str
    download_url: str
    content_type: str
    size: int | None
    updated_at: str | None


@dataclass
class FetchState:
    path: Path
    fetched: dict[str, dict[str, str]]


@dataclass
class OpenAIState:
    path: Path
    processed: dict[str, dict[str, dict[str, str]]]


@dataclass(frozen=True)
class PrintTarget:
    file_id: str
    chapter_label: str
    display_name: str
    prompt_slug: str
    prompt_title: str
    pdf_path: Path


def load_dotenv_if_present(path: Path = DEFAULT_ENV_PATH) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue

        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        os.environ[key] = value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download PDFs from a Canvas course and process them with OpenAI."
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
        default=str(PACKAGE_DIR / "output"),
        help="Directory for downloads, responses, and metadata.",
    )
    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
        help=f"OpenAI model to use. Defaults to {DEFAULT_MODEL}.",
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
        help="Only fetch matching PDFs and update fetch state; skip the OpenAI processing phase.",
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
        "--force-openai",
        action="store_true",
        help="Run the OpenAI processing step again even for files already marked as successfully processed.",
    )
    parser.add_argument(
        "--force-prompt",
        dest="force_prompt_slugs",
        action="append",
        choices=sorted(PROMPTS_BY_SLUG),
        help=(
            "Force the OpenAI step for a specific prompt slug. "
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
            "Limit OpenAI processing to a specific prompt slug. "
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
            "Print saved generated PDFs for a prompt without rerunning fetch or OpenAI. "
            "Repeat the flag to print multiple prompt types, for example "
            "--print-prompt class-note --print-prompt study-guide."
        ),
    )
    parser.add_argument(
        "--chapter",
        dest="chapter_filters",
        action="append",
        help=(
            "Optional chapter filter for --print-prompt, such as 6.3 or 7.4 & 7.5. "
            "Repeat the flag to print multiple chapters. If omitted, all chapters are printed."
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
        if args.print_all or args.print_prompt_slugs:
            slugs = PRINTABLE_PROMPT_SLUGS if args.print_all else tuple(args.print_prompt_slugs)
            print_saved_prompt_pdfs(
                output_dir=output_dir,
                prompt_slugs=slugs,
                chapter_filters=args.chapter_filters or [],
                printer=args.printer,
                dry_run=args.dry_run,
            )
            return

        username = args.username or os.environ.get("MATH_TUTOR_USERNAME")
        password = args.password or os.environ.get("MATH_TUTOR_PASSWORD")
        if not username or not password:
            raise SystemExit(
                "--username and --password are required (or set MATH_TUTOR_USERNAME / MATH_TUTOR_PASSWORD in .env)."
            )

        downloads_dir = output_dir / "downloads"
        assignments_dir = output_dir / "downloads" / "assignments"
        responses_dir = output_dir / "responses"
        metadata_dir = output_dir / "metadata"
        fetch_state = load_fetch_state(output_dir / "fetch_state.json")
        openai_state = load_openai_state(output_dir / "openai_state.json")
        selected_prompts = resolve_selected_prompts(args.prompt_slugs)
        forced_prompt_slugs = resolve_prompt_slug_set(args.force_prompt_slugs)
        processed_file_ids: set[str] = set()

        downloads_dir.mkdir(parents=True, exist_ok=True)
        assignments_dir.mkdir(parents=True, exist_ok=True)
        responses_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)

        api_key = None
        gemini_client = None
        if not args.fetch_only and not args.fetch_assignments:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise SystemExit("OPENAI_API_KEY must be set in the environment unless --fetch-only is used.")
            gemini_api_key = os.environ.get("GEMINI_API_KEY")
            if gemini_api_key:
                try:
                    from google import genai as google_genai
                    gemini_client = google_genai.Client(api_key=gemini_api_key)
                    print("Gemini client initialized.")
                except ImportError:
                    print("Warning: GEMINI_API_KEY is set but google-genai is not installed. Gemini prompts will be skipped.")

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not args.headful)
            try:
                context = browser.new_context(accept_downloads=False)
                page = context.new_page()

                login_entry_url = args.login_url or args.course_url
                print(f"Starting login flow at {login_entry_url}...")
                perform_login(
                    page=page,
                    login_url=login_entry_url,
                    course_url=args.course_url,
                    username=username,
                    password=password,
                )

                with build_canvas_client(context, args.course_url) as canvas_client:
                    if args.list_files:
                        all_files = list_canvas_pdfs_from_ui(
                            page, canvas_client, args.course_url, name_matcher=is_pdf_by_name
                        )
                        print(f"All PDF files found on course pages ({len(all_files)}):")
                        for f in all_files:
                            print(f"  {f.display_name!r}")
                        return

                    if args.fetch_assignments:
                        # Explicit assignment-only mode.
                        files = list_canvas_pdfs_from_assignments(
                            page, canvas_client, args.course_url, limit=args.assignment_limit
                        )
                        if not files:
                            raise RuntimeError(
                                "No assignment files were found on the course pages. Confirm that the account can access module attachments or course files."
                            )
                        print(f"Found {len(files)} assignment file(s).")
                        for index, canvas_file in enumerate(files, start=1):
                            process_file(
                                canvas_client=canvas_client,
                                openai_client=None,
                                gemini_client=None,
                                pdf_browser=browser,
                                canvas_file=canvas_file,
                                downloads_dir=assignments_dir,
                                responses_dir=responses_dir,
                                metadata_dir=metadata_dir,
                                fetch_state=fetch_state,
                                openai_state=openai_state,
                                model=args.model,
                                prompts=selected_prompts,
                                forced_prompt_slugs=forced_prompt_slugs,
                                force=args.force,
                                fetch_only=True,
                                force_openai=False,
                                index=index,
                                total=len(files),
                            )
                            processed_file_ids.add(str(canvas_file.file_id))
                    else:
                        # Normal mode: fetch class notes with OpenAI, then fetch assignments (no OpenAI).
                        files = list_canvas_pdfs_from_ui(
                            page, canvas_client, args.course_url, name_matcher=matches_target_pdf
                        )
                        if args.limit is not None:
                            files = files[:args.limit]
                        if not files:
                            raise RuntimeError(
                                "No PDF files were found on the course pages. Confirm that the account can access module attachments or course files."
                            )
                        print(f"Found {len(files)} class note file(s).")
                        client = OpenAI(api_key=api_key) if not args.fetch_only else None
                        for index, canvas_file in enumerate(files, start=1):
                            process_file(
                                canvas_client=canvas_client,
                                openai_client=client,
                                gemini_client=gemini_client,
                                pdf_browser=browser,
                                canvas_file=canvas_file,
                                downloads_dir=downloads_dir,
                                responses_dir=responses_dir,
                                metadata_dir=metadata_dir,
                                fetch_state=fetch_state,
                                openai_state=openai_state,
                                model=args.model,
                                prompts=selected_prompts,
                                forced_prompt_slugs=forced_prompt_slugs,
                                force=args.force,
                                fetch_only=args.fetch_only,
                                force_openai=args.force_openai,
                                index=index,
                                total=len(files),
                            )
                            processed_file_ids.add(str(canvas_file.file_id))

                        # Also fetch assignments (never sent to OpenAI).
                        assignment_files = list_canvas_pdfs_from_assignments(
                            page, canvas_client, args.course_url
                        )
                        if assignment_files:
                            print(f"Found {len(assignment_files)} assignment file(s).")
                            for index, canvas_file in enumerate(assignment_files, start=1):
                                process_file(
                                    canvas_client=canvas_client,
                                    openai_client=None,
                                    gemini_client=None,
                                    pdf_browser=browser,
                                    canvas_file=canvas_file,
                                    downloads_dir=assignments_dir,
                                    responses_dir=responses_dir,
                                    metadata_dir=metadata_dir,
                                    fetch_state=fetch_state,
                                    openai_state=openai_state,
                                    model=args.model,
                                    prompts=selected_prompts,
                                    forced_prompt_slugs=forced_prompt_slugs,
                                    force=args.force,
                                    fetch_only=True,
                                    force_openai=False,
                                    index=index,
                                    total=len(assignment_files),
                                )
                                processed_file_ids.add(str(canvas_file.file_id))
            finally:
                maybe_prompt_before_exit(args.headful)
                browser.close()

        if args.build_site_guided_learning:
            from math_tutor.site_builder import build_site

            index_path = build_site(
                output_dir=output_dir,
                site_dir=Path(args.site_dir).resolve() if args.site_dir else None,
                base_path=args.site_base_path,
                limit=args.limit,
                include_guided_learning=True,
                file_ids=processed_file_ids,
            )
            print(f"Built tutoring page with Guided Learning at {index_path}")
    except KeyboardInterrupt:
        raise SystemExit(130)


def maybe_prompt_before_exit(headful: bool) -> None:
    if not headful:
        return
    try:
        input("Press Enter to exit...")
    except EOFError:
        pass


def perform_login(
    *,
    page: Page,
    login_url: str,
    course_url: str,
    username: str,
    password: str,
) -> None:
    page.goto(login_url, wait_until="networkidle", timeout=DEFAULT_TIMEOUT_SECONDS * 1000)

    if "onelogin.com" in page.url:
        perform_onelogin(page=page, username=username, password=password)
    else:
        perform_canvas_login(page=page, username=username, password=password)

    if not wait_for_login_completion(page):
        current_url = page.url
        if "/login" in current_url or "onelogin.com" in current_url:
            raise RuntimeError(
                f"Login did not complete successfully. Current page remained at {current_url}. "
                "Re-run with --headful to inspect the auth flow or finish any extra verification step."
            )
        page.goto(course_url, wait_until="domcontentloaded", timeout=DEFAULT_TIMEOUT_SECONDS * 1000)
        page.wait_for_load_state("networkidle", timeout=DEFAULT_TIMEOUT_SECONDS * 1000)

    current_url = page.url
    if "/login" in current_url or "onelogin.com" in current_url:
        login_error = extract_login_error(page)
        if login_error:
            raise RuntimeError(f"Canvas login failed: {login_error}")
        raise RuntimeError(
            "Login did not complete successfully. Re-run with --headful to inspect the flow."
        )

    page.goto(course_url, wait_until="networkidle", timeout=DEFAULT_TIMEOUT_SECONDS * 1000)


def perform_canvas_login(*, page: Page, username: str, password: str) -> None:
    fill_first(
        page,
        [
            'input[name="pseudonym_session[unique_id]"]',
            'input[name="username"]',
            'input[type="email"]',
            'input[autocomplete="username"]',
            'input[placeholder*="Email" i]',
            'input[placeholder*="Username" i]',
            'input[aria-label*="Email" i]',
            'input[aria-label*="Username" i]',
            'input[type="text"]',
        ],
        username,
    )
    fill_first(
        page,
        [
            'input[name="pseudonym_session[password]"]',
            'input[name="password"]',
            'input[type="password"]',
            'input[autocomplete="current-password"]',
            'input[placeholder*="Password" i]',
            'input[aria-label*="Password" i]',
        ],
        password,
    )
    tick_checkbox_if_present(page)
    click_first(
        page,
        [
            'button[type="submit"]',
            'input[type="submit"]',
            'button:has-text("Log In")',
            'button:has-text("Login")',
            'button:has-text("Sign In")',
            'button:has-text("Next")',
        ],
    )

def perform_onelogin(*, page: Page, username: str, password: str) -> None:
    fill_first(
        page,
        [
            'input[name="username"]',
            'input[autocomplete="username"]',
            'input[type="email"]',
            'input[type="text"]',
        ],
        username,
    )
    click_first(
        page,
        [
            'button:has-text("Continue")',
            'button[type="submit"]',
            'input[type="submit"]',
        ],
    )

    password_locator = wait_for_any_locator(
        page,
        [
            'input[name="password"]',
            'input[autocomplete="current-password"]',
            'input[type="password"]',
        ],
        timeout_ms=LOGIN_RENDER_TIMEOUT_MS,
    )
    if password_locator is None:
        raise RuntimeError("OneLogin password field did not appear after submitting the username.")

    password_locator.fill(password)
    tick_checkbox_if_present(page)
    click_first(
        page,
        [
            'button:has-text("Continue")',
            'button[type="submit"]',
            'input[type="submit"]',
        ],
    )


def fill_first(page: Page, selectors: list[str], value: str) -> None:
    locator = wait_for_any_locator(page, selectors, timeout_ms=LOGIN_RENDER_TIMEOUT_MS)
    if locator is not None:
        locator.fill(value)
        return
    raise RuntimeError(f"Unable to find a login field matching selectors: {selectors}")


def click_first(page: Page, selectors: list[str]) -> None:
    locator = wait_for_any_locator(page, selectors, timeout_ms=LOGIN_RENDER_TIMEOUT_MS)
    if locator is not None:
        locator.click()
        return
    raise RuntimeError(f"Unable to find a submit control matching selectors: {selectors}")


def tick_checkbox_if_present(page: Page) -> None:
    locator = wait_for_locator_with_timeout(page, 'input[type="checkbox"]', timeout_ms=2_000)
    if locator is None:
        return
    if not locator.is_checked():
        locator.set_checked(True, force=True)


def extract_login_error(page: Page) -> str | None:
    error_patterns = [
        "Please verify your login or password and try again.",
        "Invalid login",
        "Incorrect password",
        "Unable to log in",
        "The email or password you entered is incorrect",
        "Your account is locked",
        "MFA required",
    ]
    for pattern in error_patterns:
        locator = page.get_by_text(pattern, exact=False)
        if locator.count() > 0:
            return locator.first.inner_text().strip()
    return None


def wait_for_login_completion(page: Page) -> bool:
    deadline = time.monotonic() + DEFAULT_TIMEOUT_SECONDS
    course_pattern = re.compile(r".*/courses/\d+.*")
    while time.monotonic() < deadline:
        if course_pattern.match(page.url):
            return True
        login_error = extract_login_error(page)
        if login_error:
            raise RuntimeError(f"Canvas login failed: {login_error}")
        page.wait_for_timeout(250)
    return False


def wait_for_locator(page: Page, selector: str) -> Any | None:
    return wait_for_locator_with_timeout(page, selector, timeout_ms=LOGIN_RENDER_TIMEOUT_MS)


def wait_for_any_locator(page: Page, selectors: list[str], timeout_ms: int) -> Any | None:
    deadline = time.monotonic() + (timeout_ms / 1000)
    while time.monotonic() < deadline:
        for selector in selectors:
            locator = page.locator(selector).first
            try:
                if locator.count() > 0 and locator.is_visible():
                    return locator
            except PlaywrightTimeoutError:
                continue
        page.wait_for_timeout(250)
    return None


def wait_for_locator_with_timeout(page: Page, selector: str, timeout_ms: int) -> Any | None:
    locator = page.locator(selector).first
    try:
        locator.wait_for(state="visible", timeout=timeout_ms)
        return locator
    except PlaywrightTimeoutError:
        return None


def build_canvas_client(context: Any, course_url: str) -> httpx.Client:
    parsed = urlparse(course_url)
    cookies = context.cookies()
    jar = httpx.Cookies()
    for cookie in cookies:
        domain = cookie.get("domain") or parsed.hostname
        jar.set(
            cookie["name"],
            cookie["value"],
            domain=domain.lstrip(".") if isinstance(domain, str) else domain,
            path=cookie.get("path", "/"),
        )
    return httpx.Client(
        base_url=f"{parsed.scheme}://{parsed.netloc}",
        cookies=jar,
        follow_redirects=True,
        timeout=DEFAULT_TIMEOUT_SECONDS,
    )


def list_canvas_pdfs_from_ui(
    page: Page,
    client: httpx.Client,
    course_url: str,
    name_matcher: Callable[[str], bool] | None = None,
) -> list[CanvasFile]:
    matcher = name_matcher or matches_target_pdf
    files = list_canvas_pdfs_from_files_page(page, course_url, name_matcher=matcher)
    if files:
        return files
    return list_canvas_pdfs_from_modules_page(page, client, course_url, name_matcher=matcher)


def list_canvas_pdfs_from_files_page(
    page: Page,
    course_url: str,
    name_matcher: Callable[[str], bool] | None = None,
) -> list[CanvasFile]:
    matcher = name_matcher or matches_target_pdf
    files_page_url = urljoin(course_url.rstrip("/") + "/", "files")
    seen_page_urls: set[str] = set()
    seen_file_ids: set[int] = set()
    results: list[CanvasFile] = []
    queue: list[str] = [files_page_url]

    while queue:
        current_url = queue.pop(0)
        if current_url in seen_page_urls:
            continue
        seen_page_urls.add(current_url)
        page.goto(current_url, wait_until="networkidle", timeout=FILES_PAGE_TIMEOUT_MS)
        page.wait_for_timeout(1000)

        for candidate in extract_pdf_links_from_page(page, course_url, name_matcher=matcher):
            if candidate.file_id in seen_file_ids:
                continue
            seen_file_ids.add(candidate.file_id)
            results.append(candidate)

        for folder_url in find_subfolder_urls(page, course_url):
            if folder_url not in seen_page_urls:
                queue.append(folder_url)

        next_page_url = find_next_files_page(page, course_url)
        if next_page_url and next_page_url not in seen_page_urls:
            queue.insert(0, next_page_url)

    return results


def list_canvas_pdfs_from_modules_page(
    page: Page,
    client: httpx.Client,
    course_url: str,
    name_matcher: Callable[[str], bool] | None = None,
) -> list[CanvasFile]:
    matcher = name_matcher or matches_target_pdf
    modules_url = urljoin(course_url.rstrip("/") + "/", "modules")
    page.goto(modules_url, wait_until="networkidle", timeout=FILES_PAGE_TIMEOUT_MS)
    page.wait_for_timeout(1000)

    anchors = page.locator("a")
    seen_file_ids: set[int] = set()
    results: list[CanvasFile] = []
    for index in range(anchors.count()):
        anchor = anchors.nth(index)
        href = anchor.get_attribute("href")
        display_name = (anchor.inner_text() or "").strip()
        if not href or not matcher(display_name):
            continue
        if "/modules/items/" not in href:
            continue
        resolved_url = resolve_module_attachment_url(client, urljoin(course_url, href))
        if resolved_url is None:
            continue
        file_id = extract_file_id(resolved_url)
        if file_id is None or file_id in seen_file_ids:
            continue
        seen_file_ids.add(file_id)
        results.append(
            CanvasFile(
                file_id=file_id,
                display_name=display_name,
                download_url=normalize_download_url(resolved_url),
                content_type="application/pdf",
                size=None,
                updated_at=None,
            )
        )
    return results


def extract_pdf_links_from_page(
    page: Page,
    course_url: str,
    name_matcher: Callable[[str], bool] | None = None,
) -> list[CanvasFile]:
    matcher = name_matcher or matches_target_pdf
    anchors = page.locator("a")
    results: list[CanvasFile] = []
    for index in range(anchors.count()):
        anchor = anchors.nth(index)
        href = anchor.get_attribute("href")
        if not href:
            continue
        absolute_url = urljoin(course_url, href)
        display_name = (anchor.inner_text() or "").strip()
        file_id = extract_file_id(absolute_url)
        if file_id is None:
            continue
        if not matcher(display_name):
            continue
        results.append(
            CanvasFile(
                file_id=file_id,
                display_name=display_name or f"file-{file_id}.pdf",
                download_url=normalize_download_url(absolute_url),
                content_type="application/pdf",
                size=None,
                updated_at=None,
            )
        )
    return results


def find_subfolder_urls(page: Page, course_url: str) -> list[str]:
    """Return URLs for subfolders visible on the current Canvas files page."""
    anchors = page.locator("a")
    results: list[str] = []
    for index in range(anchors.count()):
        anchor = anchors.nth(index)
        href = anchor.get_attribute("href") or ""
        if "/files/folder/" in href or re.search(r"/files\?folder_id=\d+", href):
            absolute = urljoin(course_url, href)
            results.append(absolute)
    return results


def find_next_files_page(page: Page, course_url: str) -> str | None:
    selectors = [
        'a[rel="next"]',
        'a[aria-label*="Next" i]',
        'a:has-text("Next")',
    ]
    for selector in selectors:
        locator = page.locator(selector).first
        if locator.count() == 0 or not locator.is_visible():
            continue
        href = locator.get_attribute("href")
        if href:
            return urljoin(course_url, href)
    return None


def _parse_link_next(link_header: str) -> str | None:
    """Extract the 'next' URL from an RFC 5988 Link header."""
    for part in link_header.split(","):
        part = part.strip()
        if 'rel="next"' in part:
            url_match = re.match(r"<([^>]+)>", part)
            if url_match:
                return url_match.group(1)
    return None


def list_canvas_pdfs_from_assignments(
    page: Page,
    client: httpx.Client,
    course_url: str,
    limit: int | None = None,
) -> list[CanvasFile]:
    """Navigate each assignment page with Playwright and extract PDF download links."""
    course_id_match = re.search(r"/courses/(\d+)", course_url)
    if not course_id_match:
        return []
    course_id = course_id_match.group(1)

    # Collect all assignment HTML URLs from the API.
    assignment_entries: list[tuple[str, str]] = []  # (name, html_url)
    next_url: str | None = f"/api/v1/courses/{course_id}/assignments?per_page=100"
    while next_url:
        try:
            response = client.get(next_url)
            response.raise_for_status()
        except httpx.HTTPStatusError:
            break
        data = response.json()
        if not isinstance(data, list):
            break
        for assignment in data:
            name = assignment.get("name") or f"assignment-{assignment.get('id', 'unknown')}"
            html_url = assignment.get("html_url") or ""
            if html_url:
                assignment_entries.append((name, html_url))
        next_url = _parse_link_next(response.headers.get("link", ""))

    results: list[CanvasFile] = []
    seen_file_ids: set[int] = set()

    for assignment_name, assignment_url in assignment_entries:
        if limit is not None and len(results) >= limit:
            break
        page.goto(assignment_url, wait_until="networkidle", timeout=FILES_PAGE_TIMEOUT_MS)
        page.wait_for_timeout(500)

        anchors = page.locator("a")
        for i in range(anchors.count()):
            href = anchors.nth(i).get_attribute("href") or ""
            if "/files/" not in href or "/download" not in href:
                continue
            file_id = extract_file_id(href)
            if file_id is None or file_id in seen_file_ids:
                continue
            seen_file_ids.add(file_id)
            absolute_url = urljoin(course_url, href)
            safe_name = assignment_name if assignment_name.lower().endswith(".pdf") else f"{assignment_name}.pdf"
            results.append(
                CanvasFile(
                    file_id=file_id,
                    display_name=safe_name,
                    download_url=absolute_url,
                    content_type="application/pdf",
                    size=None,
                    updated_at=None,
                )
            )

    return results


def is_pdf(display_name: str, content_type: str, url: str) -> bool:
    return (
        display_name.lower().endswith(".pdf")
        or content_type.lower() == "application/pdf"
        or url.lower().endswith(".pdf")
        or ".pdf?" in url.lower()
    )


def is_pdf_by_name(display_name: str) -> bool:
    """Match any file with a .pdf extension (used for --list-files discovery)."""
    return display_name.lower().endswith(".pdf")


def matches_target_pdf(display_name: str) -> bool:
    lowered_name = display_name.lower()
    return any(substring in lowered_name for substring in TARGET_NAME_SUBSTRINGS)


def matches_assignment_pdf(display_name: str) -> bool:
    """Return True for chapter-numbered assignment PDFs.

    Matches names like '5.1', '5.1.pdf', '7.4 & 7.5.pdf', or '7.4 and 7.5.pdf'.
    Only the leading chapter number pattern is required; Canvas sometimes strips
    the .pdf extension from anchor text, so we don't require it here.
    """
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


def resolve_module_attachment_url(client: httpx.Client, module_item_url: str) -> str | None:
    try:
        response = client.get(module_item_url)
        response.raise_for_status()
    except httpx.HTTPStatusError:
        return None
    resolved_url = str(response.url)
    if "/files/" not in resolved_url:
        return None
    return resolved_url


def process_file(
    *,
    canvas_client: httpx.Client,
    openai_client: OpenAI,
    gemini_client: Any,
    pdf_browser: Any,
    canvas_file: CanvasFile,
    downloads_dir: Path,
    responses_dir: Path,
    metadata_dir: Path,
    fetch_state: FetchState,
    openai_state: OpenAIState,
    model: str,
    prompts: tuple[PromptSpec, ...],
    forced_prompt_slugs: set[str],
    force: bool,
    fetch_only: bool,
    force_openai: bool,
    index: int,
    total: int,
) -> None:
    stem = f"{canvas_file.file_id}_{slugify(Path(canvas_file.display_name).stem)}"
    extension = Path(canvas_file.display_name).suffix or ".pdf"
    pdf_path = downloads_dir / f"{stem}{extension}"
    prompt_outputs_cache: dict[str, str] = {}

    ensure_pdf_fetched(
        client=canvas_client,
        canvas_file=canvas_file,
        destination=pdf_path,
        fetch_state=fetch_state,
        force=force,
        index=index,
        total=total,
    )

    if fetch_only:
        print(f"[{index}/{total}] Fetch-only mode; skipping OpenAI for {canvas_file.display_name}.")
        return

    for prompt_spec in prompts:
        run_prompt(
            canvas_file=canvas_file,
            openai_client=openai_client,
            gemini_client=gemini_client,
            pdf_browser=pdf_browser,
            pdf_path=pdf_path,
            responses_dir=responses_dir,
            metadata_dir=metadata_dir,
            openai_state=openai_state,
            model=model,
            stem=stem,
            prompt_spec=prompt_spec,
            prompt_outputs_cache=prompt_outputs_cache,
            force=force,
            force_openai=force_openai or prompt_spec.slug in forced_prompt_slugs,
            index=index,
            total=total,
        )


def ensure_pdf_fetched(
    *,
    client: httpx.Client,
    canvas_file: CanvasFile,
    destination: Path,
    fetch_state: FetchState,
    force: bool,
    index: int,
    total: int,
) -> None:
    state_key = str(canvas_file.file_id)
    previously_fetched = state_key in fetch_state.fetched and destination.exists()
    if previously_fetched and not force:
        print(f"[{index}/{total}] Skipping download for {canvas_file.display_name}; already fetched.")
        return

    print(f"[{index}/{total}] Downloading {canvas_file.display_name}...")
    download_pdf(client, canvas_file.download_url, destination)
    fetch_state.fetched[state_key] = {
        "display_name": canvas_file.display_name,
        "download_url": canvas_file.download_url,
        "pdf_path": str(destination),
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    save_fetch_state(fetch_state)


def build_prompt_paths(
    *, responses_dir: Path, metadata_dir: Path, stem: str, prompt_spec: PromptSpec
) -> tuple[Path, Path, Path, Path]:
    if prompt_spec.slug == STUDY_GUIDE_PROMPT.slug:
        response_base = responses_dir / stem
        metadata_path = metadata_dir / f"{stem}.json"
    else:
        response_base = responses_dir / f"{stem}__{prompt_spec.slug}"
        metadata_path = metadata_dir / f"{stem}__{prompt_spec.slug}.json"
    return (
        response_base.with_suffix(".md"),
        response_base.with_suffix(".html"),
        response_base.with_suffix(".pdf"),
        metadata_path,
    )


def run_prompt(
    *,
    canvas_file: CanvasFile,
    openai_client: OpenAI,
    gemini_client: Any,
    pdf_browser: Any,
    pdf_path: Path,
    responses_dir: Path,
    metadata_dir: Path,
    openai_state: OpenAIState,
    model: str,
    stem: str,
    prompt_spec: PromptSpec,
    prompt_outputs_cache: dict[str, str],
    force: bool,
    force_openai: bool,
    index: int,
    total: int,
) -> str:
    response_path, response_html_path, response_pdf_path, metadata_path = build_prompt_paths(
        responses_dir=responses_dir,
        metadata_dir=metadata_dir,
        stem=stem,
        prompt_spec=prompt_spec,
    )

    if should_skip_openai(
        canvas_file=canvas_file,
        prompt_spec=prompt_spec,
        response_path=response_path,
        response_html_path=response_html_path,
        response_pdf_path=response_pdf_path,
        openai_state=openai_state,
        force=force,
        force_openai=force_openai,
        index=index,
        total=total,
    ):
        if response_path.exists():
            cached_output = response_path.read_text(encoding="utf-8")
            prompt_outputs_cache[prompt_spec.slug] = cached_output
            return cached_output
        return ""

    source_output = resolve_source_output(
        canvas_file=canvas_file,
        openai_client=openai_client,
        gemini_client=gemini_client,
        pdf_browser=pdf_browser,
        pdf_path=pdf_path,
        responses_dir=responses_dir,
        metadata_dir=metadata_dir,
        openai_state=openai_state,
        model=model,
        stem=stem,
        prompt_spec=prompt_spec,
        prompt_outputs_cache=prompt_outputs_cache,
        index=index,
        total=total,
    )

    effective_model = prompt_spec.model or model
    print(f"[{index}/{total}] Sending {canvas_file.display_name} to {effective_model} for {prompt_spec.title}...")
    result = generate_prompt_response(
        client=openai_client,
        gemini_client=gemini_client,
        pdf_path=pdf_path,
        model=model,
        prompt_spec=prompt_spec,
        source_output=source_output,
    )

    response_path.write_text(result.output_text, encoding="utf-8")
    response_html_path.write_text(
        build_response_html(
            title=canvas_file.display_name,
            prompt_title=prompt_spec.title,
            markdown_text=result.output_text,
            pdf_label=pdf_path.name if prompt_spec.include_source_pdf_link else None,
            pdf_href=(
                Path(os.path.relpath(pdf_path, start=response_html_path.parent)).as_posix()
                if prompt_spec.include_source_pdf_link
                else None
            ),
        ),
        encoding="utf-8",
    )
    if prompt_spec.generate_response_pdf:
        build_response_pdf(
            response_html_path=response_html_path,
            response_pdf_path=response_pdf_path,
            browser=pdf_browser,
        )
    metadata = {
        "canvas_file_id": canvas_file.file_id,
        "display_name": canvas_file.display_name,
        "download_url": canvas_file.download_url,
        "content_type": canvas_file.content_type,
        "size": canvas_file.size,
        "updated_at": canvas_file.updated_at,
        "openai_model": model,
        "openai_response_id": result.response_id,
        "prompt_slug": prompt_spec.slug,
        "prompt_title": prompt_spec.title,
        "source_prompt_slug": prompt_spec.source_prompt_slug,
        "pdf_path": str(pdf_path),
        "response_path": str(response_path),
        "response_html_path": str(response_html_path),
        "response_pdf_path": str(response_pdf_path) if prompt_spec.generate_response_pdf else "",
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    file_state = openai_state.processed.setdefault(str(canvas_file.file_id), {})
    file_state[prompt_spec.slug] = {
        "display_name": canvas_file.display_name,
        "prompt_slug": prompt_spec.slug,
        "prompt_title": prompt_spec.title,
        "response_path": str(response_path),
        "response_html_path": str(response_html_path),
        "response_pdf_path": str(response_pdf_path) if prompt_spec.generate_response_pdf else "",
        "metadata_path": str(metadata_path),
        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "openai_response_id": result.response_id,
        "source_prompt_slug": prompt_spec.source_prompt_slug or "",
        "model": model,
    }
    save_openai_state(openai_state)
    prompt_outputs_cache[prompt_spec.slug] = result.output_text
    print(f"[{index}/{total}] Saved {prompt_spec.title} output to {response_path}.")
    return result.output_text


def resolve_source_output(
    *,
    canvas_file: CanvasFile,
    openai_client: OpenAI,
    gemini_client: Any,
    pdf_browser: Any,
    pdf_path: Path,
    responses_dir: Path,
    metadata_dir: Path,
    openai_state: OpenAIState,
    model: str,
    stem: str,
    prompt_spec: PromptSpec,
    prompt_outputs_cache: dict[str, str],
    index: int,
    total: int,
) -> str | None:
    if prompt_spec.source_prompt_slug is None:
        return None

    if prompt_spec.source_prompt_slug in prompt_outputs_cache:
        return prompt_outputs_cache[prompt_spec.source_prompt_slug]

    source_prompt = PROMPTS_BY_SLUG[prompt_spec.source_prompt_slug]
    source_response_path, _, _, _ = build_prompt_paths(
        responses_dir=responses_dir,
        metadata_dir=metadata_dir,
        stem=stem,
        prompt_spec=source_prompt,
    )
    if source_response_path.exists():
        source_output = source_response_path.read_text(encoding="utf-8")
        prompt_outputs_cache[source_prompt.slug] = source_output
        return source_output

    print(
        f"[{index}/{total}] {prompt_spec.title} needs {source_prompt.title} first; generating the prerequisite output."
    )
    return run_prompt(
        canvas_file=canvas_file,
        openai_client=openai_client,
        gemini_client=gemini_client,
        pdf_browser=pdf_browser,
        pdf_path=pdf_path,
        responses_dir=responses_dir,
        metadata_dir=metadata_dir,
        openai_state=openai_state,
        model=model,
        stem=stem,
        prompt_spec=source_prompt,
        prompt_outputs_cache=prompt_outputs_cache,
        force=False,
        force_openai=False,
        index=index,
        total=total,
    )


def download_pdf(client: httpx.Client, url: str, destination: Path) -> None:
    with client.stream("GET", url) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)


@dataclass(frozen=True)
class PromptResponseResult:
    output_text: str
    response_id: str | None


def generate_tutor_response(
    client: OpenAI, pdf_path: Path, model: str, prompt_text: str, reasoning_effort: str | None = None
) -> Any:
    with pdf_path.open("rb") as handle:
        uploaded_file = client.files.create(file=handle, purpose="user_data")

    kwargs: dict[str, Any] = dict(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt_text},
                    {"type": "input_file", "file_id": uploaded_file.id},
                ],
            }
        ],
    )
    if reasoning_effort:
        kwargs["reasoning"] = {"effort": reasoning_effort}
    return client.responses.create(**kwargs)


def generate_text_only_response(
    client: OpenAI, model: str, prompt_text: str, reasoning_effort: str | None = None
) -> Any:
    kwargs: dict[str, Any] = dict(
        model=model,
        input=[{"role": "user", "content": [{"type": "input_text", "text": prompt_text}]}],
    )
    if reasoning_effort:
        kwargs["reasoning"] = {"effort": reasoning_effort}
    return client.responses.create(**kwargs)


def generate_gemini_tutor_response(
    client: Any, pdf_path: Path, model: str, prompt_text: str
) -> PromptResponseResult:
    from google.genai import types as genai_types
    with pdf_path.open("rb") as handle:
        uploaded_file = client.files.upload(
            file=handle,
            config=genai_types.UploadFileConfig(
                mime_type="application/pdf",
                display_name=pdf_path.name,
            ),
        )
    response = client.models.generate_content(
        model=model,
        contents=[
            genai_types.Content(
                role="user",
                parts=[
                    genai_types.Part(text=prompt_text),
                    genai_types.Part(
                        file_data=genai_types.FileData(
                            mime_type="application/pdf",
                            file_uri=uploaded_file.uri,
                        )
                    ),
                ],
            )
        ],
    )
    return PromptResponseResult(output_text=response.text, response_id=None)


def generate_gemini_text_only_response(
    client: Any, model: str, prompt_text: str
) -> PromptResponseResult:
    from google.genai import types as genai_types
    response = client.models.generate_content(
        model=model,
        contents=[genai_types.Content(role="user", parts=[genai_types.Part(text=prompt_text)])],
    )
    return PromptResponseResult(output_text=response.text, response_id=None)


def generate_prompt_response(
    *,
    client: OpenAI,
    gemini_client: Any,
    pdf_path: Path,
    model: str,
    prompt_spec: PromptSpec,
    source_output: str | None,
) -> PromptResponseResult:
    effective_model = prompt_spec.model or model
    if effective_model.startswith("gemini"):
        if gemini_client is None:
            raise RuntimeError("GEMINI_API_KEY must be set to run Gemini prompts.")
        if prompt_spec.source_prompt_slug is None:
            return generate_gemini_tutor_response(gemini_client, pdf_path, effective_model, prompt_spec.text)
        if source_output is None:
            raise RuntimeError(f"{prompt_spec.title} requires a source prompt output.")
        prompt_text = prompt_spec.text.replace(prompt_spec.source_placeholder, source_output)
        return generate_gemini_text_only_response(gemini_client, effective_model, prompt_text)

    reasoning_effort = prompt_spec.reasoning_effort
    if prompt_spec.source_prompt_slug is None:
        response = generate_tutor_response(client, pdf_path, effective_model, prompt_spec.text, reasoning_effort)
    else:
        if source_output is None:
            raise RuntimeError(f"{prompt_spec.title} requires a source prompt output.")
        prompt_text = prompt_spec.text.replace(prompt_spec.source_placeholder, source_output)
        response = generate_text_only_response(client, effective_model, prompt_text, reasoning_effort)
    return PromptResponseResult(output_text=response.output_text, response_id=response.id)


def load_fetch_state(path: Path) -> FetchState:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        fetched = payload.get("fetched", {})
        if isinstance(fetched, dict):
            return FetchState(path=path, fetched=fetched)
    return FetchState(path=path, fetched={})


def save_fetch_state(fetch_state: FetchState) -> None:
    payload = {"fetched": fetch_state.fetched}
    fetch_state.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_openai_state(path: Path) -> OpenAIState:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        processed = payload.get("processed", {})
        if isinstance(processed, dict):
            return OpenAIState(path=path, processed=normalize_openai_state(processed))
    return OpenAIState(path=path, processed={})


def save_openai_state(openai_state: OpenAIState) -> None:
    payload = {"processed": openai_state.processed}
    openai_state.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def normalize_openai_state(
    processed: dict[str, dict[str, Any]],
) -> dict[str, dict[str, dict[str, str]]]:
    normalized: dict[str, dict[str, dict[str, str]]] = {}
    for file_id, entry in processed.items():
        if not isinstance(entry, dict):
            continue
        if "response_path" in entry:
            prompt_entry = dict(entry)
            prompt_entry.setdefault("prompt_slug", STUDY_GUIDE_PROMPT.slug)
            prompt_entry.setdefault("prompt_title", STUDY_GUIDE_PROMPT.title)
            normalized[file_id] = {STUDY_GUIDE_PROMPT.slug: prompt_entry}
            continue

        prompt_map: dict[str, dict[str, str]] = {}
        for prompt_slug, prompt_entry in entry.items():
            if not isinstance(prompt_entry, dict):
                continue
            prompt_entry_copy = dict(prompt_entry)
            prompt_entry_copy.setdefault("prompt_slug", prompt_slug)
            prompt_entry_copy.setdefault("prompt_title", prompt_title_from_slug(prompt_slug))
            prompt_map[prompt_slug] = prompt_entry_copy
        if prompt_map:
            normalized[file_id] = prompt_map
    return normalized


def print_saved_prompt_pdfs(
    *,
    output_dir: Path,
    prompt_slugs: tuple[str, ...],
    chapter_filters: list[str],
    printer: str,
    dry_run: bool = False,
) -> None:
    fetch_state = load_fetch_state(output_dir / "fetch_state.json")
    openai_state = load_openai_state(output_dir / "openai_state.json")
    targets = collect_print_targets(
        fetch_state=fetch_state,
        openai_state=openai_state,
        prompt_slugs=prompt_slugs,
        chapter_filters=chapter_filters,
    )
    if not targets:
        chapter_text = f" for chapters {', '.join(chapter_filters)}" if chapter_filters else ""
        raise SystemExit(
            f"No printable PDFs were found for prompts {', '.join(prompt_slugs)}{chapter_text}."
        )

    if dry_run:
        print(f"Dry run — {len(targets)} PDF(s) would be sent to printer {printer}:")
        for target in targets:
            print(f"  {target.chapter_label} - {target.prompt_title}: {target.pdf_path.name}")
        return

    print(f"Sending {len(targets)} PDF(s) to printer {printer}...")
    for target in targets:
        try:
            subprocess.run(
                ["lp", "-d", printer, "-o", "sides=two-sided-long-edge", str(target.pdf_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise SystemExit("The 'lp' command is not available on this system.") from exc
        except subprocess.CalledProcessError as exc:
            details = (exc.stderr or exc.stdout or "").strip()
            if details:
                raise SystemExit(f"Printing failed for {target.pdf_path.name}: {details}") from exc
            raise SystemExit(f"Printing failed for {target.pdf_path.name}.") from exc

        print(
            f"Printed {target.chapter_label} - {target.prompt_title}: {target.pdf_path}"
        )


def collect_print_targets(
    *,
    fetch_state: FetchState,
    openai_state: OpenAIState,
    prompt_slugs: tuple[str, ...],
    chapter_filters: list[str],
) -> list[PrintTarget]:
    chapter_filters_normalized = [normalize_chapter_filter(value) for value in chapter_filters if value.strip()]
    file_ids = sorted(
        set(fetch_state.fetched) | set(openai_state.processed),
        key=sort_key_from_states(fetch_state.fetched, openai_state.processed),
    )
    targets: list[PrintTarget] = []
    for file_id in file_ids:
        fetched = fetch_state.fetched.get(file_id, {})
        processed = openai_state.processed.get(file_id, {})
        display_name = (
            first_processed_value(processed, "display_name")
            or fetched.get("display_name")
            or f"File {file_id}"
        )
        chapter_label = extract_chapter_label(display_name) or pretty_title(display_name)
        if chapter_filters_normalized and not chapter_matches_filters(chapter_label, display_name, chapter_filters_normalized):
            continue
        for prompt_slug in prompt_slugs:
            if prompt_slug == ASSIGNMENT_PRINT_SLUG:
                pdf_value = fetched.get("pdf_path", "")
                if not pdf_value or "/assignments/" not in pdf_value:
                    continue
                pdf_path = Path(pdf_value)
                if not pdf_path.exists():
                    continue
                targets.append(
                    PrintTarget(
                        file_id=file_id,
                        chapter_label=f"Chapter {chapter_label}" if extract_chapter_label(display_name) else chapter_label,
                        display_name=display_name,
                        prompt_slug=prompt_slug,
                        prompt_title="Assignment",
                        pdf_path=pdf_path,
                    )
                )
                continue
            if not processed:
                continue
            if prompt_slug == CLASS_NOTE_PRINT_SLUG:
                pdf_value = fetched.get("pdf_path", "")
                if not pdf_value:
                    continue
                pdf_path = Path(pdf_value)
                if not pdf_path.exists():
                    continue
                targets.append(
                    PrintTarget(
                        file_id=file_id,
                        chapter_label=f"Chapter {chapter_label}" if extract_chapter_label(display_name) else chapter_label,
                        display_name=display_name,
                        prompt_slug=prompt_slug,
                        prompt_title="Class Note",
                        pdf_path=pdf_path,
                    )
                )
                continue
            prompt_state = processed.get(prompt_slug, {})
            pdf_value = prompt_state.get("response_pdf_path", "")
            if not pdf_value:
                continue
            pdf_path = Path(pdf_value)
            if not pdf_path.exists():
                continue
            targets.append(
                PrintTarget(
                    file_id=file_id,
                    chapter_label=f"Chapter {chapter_label}" if extract_chapter_label(display_name) else chapter_label,
                    display_name=display_name,
                    prompt_slug=prompt_slug,
                    prompt_title=prompt_state.get("prompt_title") or prompt_title_from_slug(prompt_slug),
                    pdf_path=pdf_path,
                )
            )
    return targets


def first_processed_value(processed: dict[str, dict[str, str]], key: str) -> str | None:
    for prompt_slug in PROMPTS_BY_SLUG:
        prompt_entry = processed.get(prompt_slug, {})
        if isinstance(prompt_entry, dict):
            value = prompt_entry.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def extract_chapter_label(display_name: str) -> str | None:
    match = re.search(r"chp[.\s]+(\d+(?:\.\d+)?(?:\s*&\s*\d+(?:\.\d+)?)*)", display_name.lower())
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1).strip())


def normalize_chapter_filter(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def chapter_matches_filters(chapter_label: str, display_name: str, chapter_filters: list[str]) -> bool:
    chapter_text = normalize_chapter_filter(chapter_label)
    for chapter_filter in chapter_filters:
        if chapter_filter == chapter_text:
            return True
        # "5" matches sections "5.1", "5.2", etc.
        if chapter_text.startswith(chapter_filter + "."):
            return True
        # "7.4" matches compound "7.4 & 7.5"
        if chapter_text.startswith(chapter_filter + " "):
            return True
    return False


def sort_key_from_states(
    fetch_state: dict[str, dict[str, Any]],
    openai_state: dict[str, dict[str, Any]],
):
    def key(file_id: str) -> tuple[float, str]:
        display_name = (
            first_processed_value(openai_state.get(file_id, {}), "display_name")
            or fetch_state.get(file_id, {}).get("display_name")
            or ""
        )
        chapter_label = extract_chapter_label(display_name)
        chapter_value = parse_chapter_sort_value(chapter_label) if chapter_label else 10_000.0
        return (chapter_value, display_name.lower())

    return key


def parse_chapter_sort_value(chapter_label: str) -> float:
    first_part = chapter_label.split("&", 1)[0].strip()
    try:
        return float(first_part)
    except ValueError:
        return 10_000.0


def should_skip_openai(
    *,
    canvas_file: CanvasFile,
    prompt_spec: PromptSpec,
    response_path: Path,
    response_html_path: Path,
    response_pdf_path: Path,
    openai_state: OpenAIState,
    force: bool,
    force_openai: bool,
    index: int,
    total: int,
) -> bool:
    if force or force_openai:
        return False

    state_key = str(canvas_file.file_id)
    if state_key not in openai_state.processed:
        return False
    prompt_state = openai_state.processed[state_key].get(prompt_spec.slug)
    if prompt_state is None:
        return False

    has_all_artifacts = response_path.exists() and response_html_path.exists()
    if prompt_spec.generate_response_pdf:
        has_all_artifacts = has_all_artifacts and response_pdf_path.exists()

    if has_all_artifacts:
        print(
            f"[{index}/{total}] Skipping OpenAI for {canvas_file.display_name} ({prompt_spec.title}); already processed successfully."
        )
        return True

    print(
        f"[{index}/{total}] Prior OpenAI success recorded for {canvas_file.display_name} ({prompt_spec.title}), "
        "but a saved response artifact is missing; rerunning OpenAI."
    )
    return False


def prompt_title_from_slug(prompt_slug: str) -> str:
    prompt_spec = PROMPTS_BY_SLUG.get(prompt_slug)
    if prompt_spec is not None:
        return prompt_spec.title
    return prompt_slug.replace("-", " ").title()


def resolve_selected_prompts(prompt_slugs: list[str] | None) -> tuple[PromptSpec, ...]:
    if not prompt_slugs:
        return PROMPTS

    selected: list[PromptSpec] = []
    seen: set[str] = set()
    for prompt_slug in prompt_slugs:
        if prompt_slug in seen:
            continue
        prompt_spec = PROMPTS_BY_SLUG[prompt_slug]
        selected.append(prompt_spec)
        seen.add(prompt_slug)
    return tuple(selected)


def resolve_prompt_slug_set(prompt_slugs: list[str] | None) -> set[str]:
    if not prompt_slugs:
        return set()
    return set(prompt_slugs)


def build_response_html(
    *, title: str, prompt_title: str, markdown_text: str, pdf_label: str | None, pdf_href: str | None
) -> str:
    rendered = markdown_to_html(markdown_text)
    pdf_name = html_escape(response_document_title(title))
    prompt_name = html_escape(prompt_title)
    pdf_note = ""
    if pdf_label and pdf_href:
        pdf_rel = html_escape(pdf_href)
        pdf_link_label = html_escape(pdf_label)
        pdf_note = (
            f'<p>Saved tutoring response with MathJax rendering. Original PDF file: '
            f'<a href="{pdf_rel}">{pdf_link_label}</a></p>'
        )
    else:
        pdf_note = "<p>Saved tutoring response with MathJax rendering.</p>"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{pdf_name} - {prompt_name}</title>
  <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
      }}
    }};
  </script>
  <script defer src="{MATHJAX_SCRIPT}"></script>
  <style>
    :root {{
      --bg: #f6f1e8;
      --paper: #fffdf8;
      --ink: #1d2833;
      --muted: #667784;
      --line: #dfd5c8;
      --accent: #0f6a73;
      --code: #f1ebe2;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #f4d7c4 0, transparent 24%),
        linear-gradient(180deg, #f8f3eb 0%, var(--bg) 100%);
    }}
    .page {{
      width: min(920px, calc(100vw - 32px));
      margin: 24px auto 48px;
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: 0 16px 36px rgba(48, 36, 23, 0.08);
      overflow: hidden;
    }}
    header {{
      padding: 24px 28px 18px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, #fffaf3 0%, #fbf6ee 100%);
    }}
    header h1 {{
      margin: 0 0 8px;
      font-size: 2rem;
      line-height: 1.08;
    }}
    header p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
    }}
    main {{
      padding: 24px 28px 32px;
    }}
    a {{ color: var(--accent); }}
    h2, h3, h4 {{
      color: #213647;
      margin-top: 1.25em;
      margin-bottom: 0.45em;
    }}
    p, li {{
      line-height: 1.7;
    }}
    ul {{
      padding-left: 24px;
    }}
    hr {{
      border: 0;
      border-top: 1px solid var(--line);
      margin: 22px 0;
    }}
    code {{
      background: var(--code);
      padding: 0.1em 0.35em;
      border-radius: 6px;
      font-size: 0.95em;
    }}
  </style>
</head>
<body>
  <article class="page">
    <header>
      <h1>{pdf_name}</h1>
      <p><strong>{prompt_name}</strong></p>
      {pdf_note}
    </header>
    <main>
      {rendered}
    </main>
  </article>
</body>
</html>
"""


def build_response_pdf(*, response_html_path: Path, response_pdf_path: Path, browser: Any | None = None) -> None:
    if browser is None:
        with sync_playwright() as playwright:
            owned_browser = playwright.chromium.launch(headless=True)
            try:
                render_response_pdf(
                    browser=owned_browser,
                    response_html_path=response_html_path,
                    response_pdf_path=response_pdf_path,
                )
            finally:
                owned_browser.close()
        return

    render_response_pdf(
        browser=browser,
        response_html_path=response_html_path,
        response_pdf_path=response_pdf_path,
    )


def render_response_pdf(*, browser: Any, response_html_path: Path, response_pdf_path: Path) -> None:
    page = browser.new_page()
    try:
        page.goto(response_html_path.resolve().as_uri(), wait_until="networkidle")
        try:
            page.wait_for_function("window.MathJax && window.MathJax.typesetPromise")
            page.evaluate("() => window.MathJax.typesetPromise()")
        except PlaywrightTimeoutError:
            pass
        page.pdf(
            path=str(response_pdf_path),
            format="Letter",
            print_background=True,
            margin={"top": "0.5in", "right": "0.5in", "bottom": "0.6in", "left": "0.5in"},
        )
    finally:
        page.close()


def markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    parts: list[str] = []
    paragraph: list[str] = []
    in_list = False

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            parts.append(f"<p>{render_inline(' '.join(paragraph).strip())}</p>")
            paragraph = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            parts.append("</ul>")
            in_list = False

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            flush_paragraph()
            close_list()
            continue
        if re.fullmatch(r"-{3,}", stripped):
            flush_paragraph()
            close_list()
            parts.append("<hr>")
            continue
        heading_match = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if heading_match:
            flush_paragraph()
            close_list()
            level = min(len(heading_match.group(1)) + 1, 4)
            parts.append(f"<h{level}>{render_inline(heading_match.group(2))}</h{level}>")
            continue
        if stripped.startswith(("- ", "* ")):
            flush_paragraph()
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{render_inline(stripped[2:].strip())}</li>")
            continue
        close_list()
        paragraph.append(stripped)

    flush_paragraph()
    close_list()
    return "\n".join(parts)


def render_inline(text: str) -> str:
    escaped = html_escape(text)
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
        r'<a href="\2">\1</a>',
        escaped,
    )
    escaped = re.sub(
        r"(?<![\"'=>])(https?://[^\s<]+)",
        r'<a href="\1">\1</a>',
        escaped,
    )
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
    return escaped


def pretty_title(display_name: str) -> str:
    cleaned = display_name.removesuffix(".pdf").replace(".docx", "")
    cleaned = re.sub(r"\s+\(\d+\)$", "", cleaned)
    cleaned = cleaned.replace("_", " ")
    return cleaned


def response_document_title(display_name: str) -> str:
    match = re.search(r"chp[.\s]+(\d+(?:\.\d+)?(?:\s*&\s*\d+(?:\.\d+)?)*)", display_name.lower())
    if match:
        chapter = re.sub(r"\s+", " ", match.group(1).strip())
        return f"Algebra II with Trigonometry Chapter {chapter}"
    return pretty_title(display_name)


def html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def slugify(value: str) -> str:
    lowered = value.lower().strip()
    return re.sub(r"[^a-z0-9]+", "-", lowered).strip("-") or "document"


if __name__ == "__main__":
    main()
