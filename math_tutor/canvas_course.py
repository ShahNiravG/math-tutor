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

import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
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
    print("Checking Canvas modules page for matching PDFs...", flush=True)
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
    module_links: list[tuple[str, str]] = []
    for index in range(anchors.count()):
        anchor = anchors.nth(index)
        href = anchor.get_attribute("href")
        display_name = (anchor.inner_text() or "").strip()
        if not href or not matcher(display_name):
            continue
        if "/modules/items/" not in href:
            continue
        module_links.append((display_name, urljoin(course_url, href)))

    resolved_pairs = resolve_module_attachment_urls(client, module_links)
    seen_file_ids: set[int] = set()
    results: list[CanvasFile] = []
    for display_name, resolved_url in resolved_pairs:
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
    assignment_entries: list[tuple[str, str]] | None = None,
) -> list[CanvasFile]:
    assignment_entries = assignment_entries or list_canvas_assignment_entries(
        client,
        course_url,
        limit=limit,
    )

    if limit is not None:
        assignment_entries = assignment_entries[:limit]

    results: list[CanvasFile] = []
    seen_file_ids: set[int] = set()
    assignment_downloads = fetch_assignment_download_links(client, assignment_entries, course_url)
    for assignment_name, download_urls in assignment_downloads:
        if not download_urls:
            download_urls = scan_assignment_download_links_from_page(
                page,
                assignment_url_for_name(assignment_entries, assignment_name),
                course_url=course_url,
            )
        safe_name = assignment_name if assignment_name.lower().endswith(".pdf") else f"{assignment_name}.pdf"
        for absolute_url in download_urls:
            file_id = extract_file_id(absolute_url)
            if file_id is None or file_id in seen_file_ids:
                continue
            seen_file_ids.add(file_id)
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


def list_canvas_assignment_entries(
    client: httpx.Client,
    course_url: str,
    limit: int | None = None,
) -> list[tuple[str, str]]:
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
        assignment_entries.extend(extract_assignment_entries_from_api_items(data))
        next_url = parse_link_next(response.headers.get("link", ""))

    if limit is not None:
        return assignment_entries[:limit]
    return assignment_entries


def extract_assignment_entries_from_api_items(items: list[dict[str, Any]]) -> list[tuple[str, str]]:
    results: list[tuple[str, str]] = []
    for assignment in items:
        html_url = assignment.get("html_url") or ""
        submission_types = assignment.get("submission_types") or []
        if html_url and "online_upload" in submission_types:
            name = assignment.get("name") or f"assignment-{assignment.get('id', 'unknown')}"
            results.append((name, html_url))
    return results


def assignment_url_for_name(assignment_entries: list[tuple[str, str]], assignment_name: str) -> str:
    for name, url in assignment_entries:
        if name == assignment_name:
            return url
    return ""


def fetch_assignment_download_links(
    client: httpx.Client,
    assignment_entries: list[tuple[str, str]],
    course_url: str,
) -> list[tuple[str, list[str]]]:
    def fetch_one(entry: tuple[str, str]) -> tuple[str, list[str]]:
        assignment_name, assignment_url = entry
        try:
            response = client.get(assignment_url)
            response.raise_for_status()
        except httpx.HTTPError:
            return (assignment_name, [])
        return (
            assignment_name,
            extract_assignment_downloads_from_html(html_text=response.text, course_url=course_url),
        )

    max_workers = min(8, max(1, len(assignment_entries)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(fetch_one, assignment_entries))


def extract_assignment_downloads_from_html(*, html_text: str, course_url: str) -> list[str]:
    hrefs = re.findall(r'href=["\']([^"\']+)["\']', html_text, flags=re.IGNORECASE)
    results: list[str] = []
    seen: set[str] = set()
    for href in hrefs:
        if "/files/" not in href or "/download" not in href:
            continue
        absolute_url = urljoin(course_url, href)
        if absolute_url in seen:
            continue
        seen.add(absolute_url)
        results.append(absolute_url)
    return results


def scan_assignment_download_links_from_page(page: Page, assignment_url: str, *, course_url: str) -> list[str]:
    if not assignment_url:
        return []
    page.goto(assignment_url, wait_until="networkidle", timeout=FILES_PAGE_TIMEOUT_MS)
    page.wait_for_timeout(500)

    anchors = page.locator("a")
    results: list[str] = []
    seen: set[str] = set()
    for index in range(anchors.count()):
        href = anchors.nth(index).get_attribute("href") or ""
        if "/files/" not in href or "/download" not in href:
            continue
        if href in seen:
            continue
        seen.add(href)
        results.append(urljoin(course_url, href))
    return results


def resolve_module_attachment_urls(
    client: httpx.Client,
    module_links: list[tuple[str, str]],
) -> list[tuple[str, str | None]]:
    def resolve_one(entry: tuple[str, str]) -> tuple[str, str | None]:
        display_name, module_item_url = entry
        return (display_name, resolve_module_attachment_url(client, module_item_url))

    max_workers = min(8, max(1, len(module_links)))
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        return list(executor.map(resolve_one, module_links))


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
    saved_pdf_path_value = fetch_state.fetched.get(state_key, {}).get("pdf_path", "")
    saved_pdf_path = Path(saved_pdf_path_value) if saved_pdf_path_value else None
    previously_fetched = (
        state_key in fetch_state.fetched
        and (
            destination.exists()
            or (saved_pdf_path is not None and saved_pdf_path.exists())
        )
    )
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
    """Stream a PDF from ``url`` into ``destination`` atomically.

    The download writes to a sibling ``.part`` file first and only renames it
    into ``destination`` on successful completion. If the stream fails
    partway (network drop, HTTP error, disk full), the partial file is
    removed and any pre-existing file at ``destination`` is preserved.

    Args:
        client: Authenticated ``httpx.Client`` used for streaming.
        url: PDF URL to fetch.
        destination: Final on-disk path for the fetched PDF.

    Raises:
        httpx.HTTPError: Propagated from ``raise_for_status``.
        OSError: Propagated from underlying file I/O.
        Exception: Any exception raised mid-stream is re-raised after the
            partial file is cleaned up.
    """
    destination.parent.mkdir(parents=True, exist_ok=True)
    part_path = destination.with_name(f".{destination.name}.part")
    try:
        with client.stream("GET", url) as response:
            response.raise_for_status()
            with part_path.open("wb") as handle:
                for chunk in response.iter_bytes():
                    handle.write(chunk)
        os.replace(part_path, destination)
    except BaseException:
        try:
            part_path.unlink()
        except FileNotFoundError:
            pass
        raise
