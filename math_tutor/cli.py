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
PROMPT = """You are a careful math tutor.

Read the attached PDF and produce:
1. A short summary of the document.
2. A list of the core definitions, theorems, and formulas.
3. A worked study guide that explains the important ideas step by step.
4. Five practice problems with answers, based only on the document.
5. Any assumptions or ambiguities you had to resolve.

Keep the response self-contained and use clear section headings.
"""


@dataclass(frozen=True)
class CanvasFile:
    file_id: int
    display_name: str
    download_url: str
    content_type: str
    size: int | None
    updated_at: str | None


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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    try:
        output_dir = Path(args.output_dir).resolve()
        downloads_dir = output_dir / "downloads"
        responses_dir = output_dir / "responses"
        metadata_dir = output_dir / "metadata"

        downloads_dir.mkdir(parents=True, exist_ok=True)
        responses_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise SystemExit("OPENAI_API_KEY must be set in the environment.")

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

                    client = OpenAI(api_key=api_key)
                    print(f"Found {len(files)} PDF file(s).")

                    for index, canvas_file in enumerate(files, start=1):
                        process_file(
                            canvas_client=canvas_client,
                            openai_client=client,
                            canvas_file=canvas_file,
                            downloads_dir=downloads_dir,
                            responses_dir=responses_dir,
                            metadata_dir=metadata_dir,
                            model=args.model,
                            force=args.force,
                            index=index,
                            total=len(files),
                        )
            finally:
                maybe_prompt_before_exit(args.headful)
                browser.close()
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
        if not href or not display_name.lower().endswith(".pdf"):
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
        if not is_pdf(display_name, "", absolute_url):
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
    canvas_file: CanvasFile,
    downloads_dir: Path,
    responses_dir: Path,
    metadata_dir: Path,
    model: str,
    force: bool,
    index: int,
    total: int,
) -> None:
    stem = f"{canvas_file.file_id}_{slugify(Path(canvas_file.display_name).stem)}"
    extension = Path(canvas_file.display_name).suffix or ".pdf"
    pdf_path = downloads_dir / f"{stem}{extension}"
    response_path = responses_dir / f"{stem}.md"
    metadata_path = metadata_dir / f"{stem}.json"

    if response_path.exists() and not force:
        print(f"[{index}/{total}] Skipping {canvas_file.display_name}; output already exists.")
        return

    print(f"[{index}/{total}] Downloading {canvas_file.display_name}...")
    download_pdf(canvas_client, canvas_file.download_url, pdf_path)
    print(f"[{index}/{total}] Sending {canvas_file.display_name} to OpenAI...")
    result = generate_tutor_response(openai_client, pdf_path, model)

    response_path.write_text(result.output_text, encoding="utf-8")
    metadata = {
        "canvas_file_id": canvas_file.file_id,
        "display_name": canvas_file.display_name,
        "download_url": canvas_file.download_url,
        "content_type": canvas_file.content_type,
        "size": canvas_file.size,
        "updated_at": canvas_file.updated_at,
        "openai_model": model,
        "openai_response_id": result.id,
        "pdf_path": str(pdf_path),
        "response_path": str(response_path),
    }
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(f"[{index}/{total}] Saved output to {response_path}.")


def download_pdf(client: httpx.Client, url: str, destination: Path) -> None:
    with client.stream("GET", url) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)


def generate_tutor_response(client: OpenAI, pdf_path: Path, model: str) -> Any:
    with pdf_path.open("rb") as handle:
        uploaded_file = client.files.create(file=handle, purpose="user_data")

    response = client.responses.create(
        model=model,
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": PROMPT},
                    {
                        "type": "input_file",
                        "file_id": uploaded_file.id,
                    },
                ],
            }
        ],
    )
    return response


def slugify(value: str) -> str:
    lowered = value.lower().strip()
    return re.sub(r"[^a-z0-9]+", "-", lowered).strip("-") or "document"


if __name__ == "__main__":
    main()
