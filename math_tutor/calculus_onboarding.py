"""Safe, review-first metadata discovery for AP Calculus AB chapters."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

from math_tutor.atomic_io import atomic_write_json
from math_tutor.canvas_files import parse_link_next
from math_tutor.canvas_course import build_canvas_client
from math_tutor.canvas_login import perform_login
from math_tutor.cli_auth import resolve_canvas_credentials
from math_tutor.env_config import load_dotenv_if_present


COURSE_URL = "https://mitty.instructure.com/courses/4446"


@dataclass(frozen=True)
class CanvasAssignmentCandidate:
    assignment_id: str
    name: str
    html_url: str
    section_id: str


def extract_chapter_assignment_candidates(
    items: list[dict[str, Any]],
    *,
    chapter: str,
) -> tuple[CanvasAssignmentCandidate, ...]:
    section_pattern = re.compile(rf"(?<!\d)({re.escape(chapter)}\.\d+)(?!\d)")
    candidates: list[CanvasAssignmentCandidate] = []
    for item in items:
        if "external_tool" not in (item.get("submission_types") or []):
            continue
        name = str(item.get("name") or "").strip()
        section_match = section_pattern.search(name)
        if section_match is None:
            continue
        assignment_id = str(item.get("id") or "")
        html_url = str(item.get("html_url") or "")
        _validate_canvas_assignment_url(html_url, assignment_id=assignment_id)
        candidates.append(
            CanvasAssignmentCandidate(
                assignment_id=assignment_id,
                name=name,
                html_url=html_url,
                section_id=section_match.group(1),
            )
        )
    return tuple(sorted(candidates, key=lambda candidate: _section_sort_key(candidate.section_id)))


def fetch_canvas_assignment_items(client: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    next_url: str | None = "/api/v1/courses/4446/assignments?per_page=100"
    while next_url:
        response = client.get(next_url)
        response.raise_for_status()
        page_items = response.json()
        if not isinstance(page_items, list) or any(not isinstance(item, dict) for item in page_items):
            raise ValueError("Canvas assignments API returned an invalid payload.")
        items.extend(page_items)
        next_url = parse_link_next(response.headers.get("link", ""))
    return items


def build_candidate_payload(
    *,
    chapter: str,
    assignments: tuple[CanvasAssignmentCandidate, ...],
) -> dict[str, Any]:
    if not chapter.isdigit():
        raise ValueError("Calculus chapter must be a positive integer.")
    return {
        "schema_version": 1,
        "status": "review-required",
        "course_id": "ap-calculus-ab",
        "chapter": chapter,
        "assignments": [
            {
                "section_id": assignment.section_id,
                "assignment_id": assignment.assignment_id,
                "name": assignment.name,
                "html_url": assignment.html_url,
            }
            for assignment in assignments
        ],
    }


def _validate_canvas_assignment_url(url: str, *, assignment_id: str) -> None:
    parsed = urlsplit(url)
    expected_path = f"/courses/4446/assignments/{assignment_id}"
    if (
        not assignment_id.isdigit()
        or parsed.scheme != "https"
        or parsed.hostname != "mitty.instructure.com"
        or parsed.path != expected_path
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        raise ValueError("Candidate must use a safe Canvas assignment URL.")


def _section_sort_key(section_id: str) -> tuple[int, ...]:
    return tuple(int(part) for part in section_id.split("."))


def _default_candidate_path(chapter: str) -> Path:
    return (
        Path(__file__).resolve().parent
        / "output"
        / "courses"
        / "ap-calculus-ab"
        / "metadata"
        / f"chapter-{chapter}-onboarding-candidate.json"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover safe, review-only Canvas metadata for an AP Calculus AB chapter."
    )
    parser.add_argument("--chapter", required=True)
    parser.add_argument("--candidate-output", type=Path)
    parser.add_argument("--headful", action="store_true")
    args = parser.parse_args()
    if not args.chapter.isdigit():
        parser.error("--chapter must be a positive integer")

    load_dotenv_if_present()
    credentials = resolve_canvas_credentials(
        username=None,
        password=None,
        skip_fetch=False,
        env=os.environ,
    )
    assert credentials is not None
    candidate_path = args.candidate_output or _default_candidate_path(args.chapter)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not args.headful)
        try:
            context = browser.new_context(accept_downloads=False)
            page = context.new_page()
            perform_login(
                page=page,
                login_url=COURSE_URL,
                course_url=COURSE_URL,
                username=credentials[0],
                password=credentials[1],
            )
            with build_canvas_client(context, COURSE_URL) as client:
                items = fetch_canvas_assignment_items(client)
            assignments = extract_chapter_assignment_candidates(items, chapter=args.chapter)
            payload = build_candidate_payload(chapter=args.chapter, assignments=assignments)
            atomic_write_json(candidate_path, payload, indent=2)
        finally:
            browser.close()

    print(f"Wrote review-required candidate: {candidate_path}")
    print(f"Found {len(assignments)} safe Chapter {args.chapter} Canvas assignment(s).")
    for assignment in assignments:
        print(f"  {assignment.section_id}: {assignment.name} (assignment {assignment.assignment_id})")


if __name__ == "__main__":
    main()
