"""Canvas authentication, discovery, and download helpers.

This module owns the Canvas-facing operator workflow used by ``cli.py``:

- authenticate a Playwright page into Canvas or OneLogin
- build an authenticated ``httpx`` client from the browser session
- discover class-note and assignment PDFs across course pages
- download and record fetched PDFs in ``fetch_state.json``

The goal is to keep the CLI thin while preserving the current end-to-end
behavior and operator-visible logging.
"""

from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urljoin, urlparse

import httpx
from playwright.sync_api import Page

from math_tutor.canvas_files import (
    CanvasFile,
    extract_file_id,
    is_pdf,
    is_pdf_by_name,
    matches_assignment_pdf,
    matches_target_pdf,
    normalize_download_url,
    parse_link_next,
    summarize_discovered_files,
)
from math_tutor.canvas_login import perform_login, wait_for_locator
from math_tutor.state_store import FetchState, save_fetch_state


FILES_PAGE_TIMEOUT_MS = 30_000
DEFAULT_TIMEOUT_SECONDS = 30.0


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
    print("Checking Canvas files pages for matching PDFs...", flush=True)
    files = list_canvas_pdfs_from_files_page(page, course_url, name_matcher=matcher)
    if files:
        print(f"Found {len(files)} matching PDF(s) via Canvas files pages.", flush=True)
        return files
    print("No matching PDFs found via Canvas files pages; checking modules page...", flush=True)
    files = list_canvas_pdfs_from_modules_page(page, client, course_url, name_matcher=matcher)
    print(f"Found {len(files)} matching PDF(s) via Canvas modules page.", flush=True)
    return files


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
    anchors = page.locator("a")
    results: list[str] = []
    for index in range(anchors.count()):
        anchor = anchors.nth(index)
        href = anchor.get_attribute("href") or ""
        if "/files/folder/" in href or re.search(r"/files\?folder_id=\d+", href):
            results.append(urljoin(course_url, href))
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


def list_canvas_pdfs_from_assignments(
    page: Page,
    client: httpx.Client,
    course_url: str,
    limit: int | None = None,
) -> list[CanvasFile]:
    course_id_match = re.search(r"/courses/(\d+)", course_url)
    if not course_id_match:
        return []
    course_id = course_id_match.group(1)

    assignment_entries: list[tuple[str, str]] = []
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
        next_url = parse_link_next(response.headers.get("link", ""))

    results: list[CanvasFile] = []
    seen_file_ids: set[int] = set()
    for assignment_name, assignment_url in assignment_entries:
        if limit is not None and len(results) >= limit:
            break
        page.goto(assignment_url, wait_until="networkidle", timeout=FILES_PAGE_TIMEOUT_MS)
        page.wait_for_timeout(500)

        anchors = page.locator("a")
        for index in range(anchors.count()):
            href = anchors.nth(index).get_attribute("href") or ""
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
        print(f"[{index}/{total}] Skipping download for {canvas_file.display_name}; already fetched.", flush=True)
        return

    print(f"[{index}/{total}] Downloading {canvas_file.display_name}...", flush=True)
    download_pdf(client, canvas_file.download_url, destination)
    fetch_state.fetched[state_key] = {
        "display_name": canvas_file.display_name,
        "download_url": canvas_file.download_url,
        "pdf_path": str(destination),
        "fetched_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    save_fetch_state(fetch_state)


def download_pdf(client: httpx.Client, url: str, destination: Path) -> None:
    with client.stream("GET", url) as response:
        response.raise_for_status()
        with destination.open("wb") as handle:
            for chunk in response.iter_bytes():
                handle.write(chunk)
