from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any
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

PROMPTS: tuple[PromptSpec, ...] = (
    STUDY_GUIDE_PROMPT,
    INSPIRING_VIDEOS_PROMPT,
    MENTAL_MATH_PROMPT,
    OLYMPIAD_PROBLEMS_PROMPT,
    OLYMPIAD_SOLUTIONS_PROMPT,
)
PROMPTS_BY_SLUG: dict[str, PromptSpec] = {prompt_spec.slug: prompt_spec for prompt_spec in PROMPTS}


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
    parser.add_argument("--username", required=True, help="Canvas login username or email.")
    parser.add_argument("--password", required=True, help="Canvas login password.")
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
        default="math_tutor/output",
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
    return parser.parse_args()


def main() -> None:
    load_dotenv_if_present()
    args = parse_args()
    try:
        output_dir = Path(args.output_dir).resolve()
        downloads_dir = output_dir / "downloads"
        responses_dir = output_dir / "responses"
        metadata_dir = output_dir / "metadata"
        fetch_state = load_fetch_state(output_dir / "fetch_state.json")
        openai_state = load_openai_state(output_dir / "openai_state.json")
        selected_prompts = resolve_selected_prompts(args.prompt_slugs)
        forced_prompt_slugs = resolve_prompt_slug_set(args.force_prompt_slugs)
        processed_file_ids: set[str] = set()

        downloads_dir.mkdir(parents=True, exist_ok=True)
        responses_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)

        api_key = None
        if not args.fetch_only:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                raise SystemExit("OPENAI_API_KEY must be set in the environment unless --fetch-only is used.")

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
                    username=args.username,
                    password=args.password,
                )

                with build_canvas_client(context, args.course_url) as canvas_client:
                    files = list_canvas_pdfs_from_ui(page, canvas_client, args.course_url)
                    if args.limit is not None:
                        files = files[: args.limit]

                    if not files:
                        raise RuntimeError(
                            "No PDF files were found on the course pages. Confirm that the account can access module attachments or course files."
                        )

                    print(f"Found {len(files)} PDF file(s).")
                    client = OpenAI(api_key=api_key) if not args.fetch_only else None

                    for index, canvas_file in enumerate(files, start=1):
                        process_file(
                            canvas_client=canvas_client,
                            openai_client=client,
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


def list_canvas_pdfs_from_ui(page: Page, client: httpx.Client, course_url: str) -> list[CanvasFile]:
    files = list_canvas_pdfs_from_files_page(page, course_url)
    if files:
        return files
    return list_canvas_pdfs_from_modules_page(page, client, course_url)


def list_canvas_pdfs_from_files_page(page: Page, course_url: str) -> list[CanvasFile]:
    files_page_url = urljoin(course_url.rstrip("/") + "/", "files")
    seen_page_urls: set[str] = set()
    seen_file_ids: set[int] = set()
    results: list[CanvasFile] = []
    next_page_url: str | None = files_page_url

    while next_page_url and next_page_url not in seen_page_urls:
        seen_page_urls.add(next_page_url)
        page.goto(next_page_url, wait_until="networkidle", timeout=FILES_PAGE_TIMEOUT_MS)
        page.wait_for_timeout(1000)

        for candidate in extract_pdf_links_from_page(page, course_url):
            if candidate.file_id in seen_file_ids:
                continue
            seen_file_ids.add(candidate.file_id)
            results.append(candidate)

        next_page_url = find_next_files_page(page, course_url)

    return results


def list_canvas_pdfs_from_modules_page(
    page: Page, client: httpx.Client, course_url: str
) -> list[CanvasFile]:
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
        if not href or not matches_target_pdf(display_name):
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


def extract_pdf_links_from_page(page: Page, course_url: str) -> list[CanvasFile]:
    anchors = page.locator("a")
    results: list[CanvasFile] = []
    for index in range(anchors.count()):
        anchor = anchors.nth(index)
        href = anchor.get_attribute("href")
        if not href:
            continue
        absolute_url = urljoin(course_url, href)
        display_name = (anchor.inner_text() or "").strip()
        if not matches_target_pdf(display_name) or not is_pdf(display_name, "", absolute_url):
            continue
        file_id = extract_file_id(absolute_url)
        if file_id is None:
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


def is_pdf(display_name: str, content_type: str, url: str) -> bool:
    return (
        display_name.lower().endswith(".pdf")
        or content_type.lower() == "application/pdf"
        or url.lower().endswith(".pdf")
        or ".pdf?" in url.lower()
    )


def matches_target_pdf(display_name: str) -> bool:
    lowered_name = display_name.lower()
    return any(substring in lowered_name for substring in TARGET_NAME_SUBSTRINGS)


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
    response = client.get(module_item_url)
    response.raise_for_status()
    resolved_url = str(response.url)
    if "/files/" not in resolved_url:
        return None
    return resolved_url


def process_file(
    *,
    canvas_client: httpx.Client,
    openai_client: OpenAI,
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

    print(f"[{index}/{total}] Sending {canvas_file.display_name} to OpenAI for {prompt_spec.title}...")
    result = generate_prompt_response(
        client=openai_client,
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
    response_id: str


def generate_tutor_response(client: OpenAI, pdf_path: Path, model: str, prompt_text: str) -> Any:
    with pdf_path.open("rb") as handle:
        uploaded_file = client.files.create(file=handle, purpose="user_data")

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt_text},
                    {
                        "type": "input_file",
                        "file_id": uploaded_file.id,
                    },
                ],
            }
        ],
    )
    return response


def generate_text_only_response(client: OpenAI, model: str, prompt_text: str) -> Any:
    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt_text},
                ],
            }
        ],
    )
    return response


def generate_prompt_response(
    *,
    client: OpenAI,
    pdf_path: Path,
    model: str,
    prompt_spec: PromptSpec,
    source_output: str | None,
) -> PromptResponseResult:
    if prompt_spec.source_prompt_slug is None:
        response = generate_tutor_response(client, pdf_path, model, prompt_spec.text)
    else:
        if source_output is None:
            raise RuntimeError(f"{prompt_spec.title} requires a source prompt output.")
        prompt_text = prompt_spec.text.replace(prompt_spec.source_placeholder, source_output)
        response = generate_text_only_response(client, model, prompt_text)

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
    pdf_name = html_escape(pretty_title(title))
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
