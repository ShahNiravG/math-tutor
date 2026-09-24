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
from math_tutor.site_courses import canvas_course_location, get_course


COURSE_ID = "ap-calculus-ab"
COURSE_URL = get_course(COURSE_ID).canvas_course_url
CANVAS_HOST, CANVAS_COURSE_NUMBER = canvas_course_location(COURSE_ID)


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
    section_pattern = _leading_section_pattern(chapter)
    candidates: list[CanvasAssignmentCandidate] = []
    for item in items:
        if "external_tool" not in (item.get("submission_types") or []):
            continue
        name = str(item.get("name") or "").strip()
        section_match = section_pattern.match(name)
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


def _leading_section_pattern(chapter: str) -> re.Pattern[str]:
    # The section must lead the name (after an optional "Chp"/"Ch."/"Chapter" prefix) and must
    # not be a sub-section or the start of a range such as "3.1-3.3".
    return re.compile(
        rf"\s*(?:(?:chp|ch|chapter)\.?\s*)?({re.escape(chapter)}\.\d+)(?![\d.])(?!\s*[-–]\s*\d)",
        re.IGNORECASE,
    )


def find_unmatched_section_mentions(
    items: list[dict[str, Any]],
    *,
    chapter: str,
) -> tuple[dict[str, str], ...]:
    """Return external-tool assignments that mention a chapter section but were not matched."""
    leading_pattern = _leading_section_pattern(chapter)
    mention_pattern = re.compile(rf"(?<![\d.]){re.escape(chapter)}\.\d+(?!\d)")
    mentions: list[dict[str, str]] = []
    for item in items:
        if "external_tool" not in (item.get("submission_types") or []):
            continue
        name = str(item.get("name") or "").strip()
        if mention_pattern.search(name) and leading_pattern.match(name) is None:
            mentions.append({"assignment_id": str(item.get("id") or ""), "name": name})
    return tuple(mentions)


def fetch_canvas_assignment_items(client: Any) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    next_url: str | None = f"/api/v1/courses/{CANVAS_COURSE_NUMBER}/assignments?per_page=100"
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
    unmatched_mentions: tuple[dict[str, str], ...],
) -> dict[str, Any]:
    if not chapter.isdigit():
        raise ValueError("Calculus chapter must be a positive integer.")
    return {
        "schema_version": 2,
        "status": "review-required",
        "course_id": COURSE_ID,
        "chapter": chapter,
        "issues": _candidate_issues(assignments, unmatched_mentions),
        "assignments": [
            {
                "section_id": assignment.section_id,
                "assignment_id": assignment.assignment_id,
                "name": assignment.name,
                "html_url": assignment.html_url,
            }
            for assignment in assignments
        ],
        "unmatched_mentions": [dict(mention) for mention in unmatched_mentions],
    }


def candidate_exit_status(payload: dict[str, Any]) -> int:
    return 1 if payload["issues"] else 0


def _candidate_issues(
    assignments: tuple[CanvasAssignmentCandidate, ...],
    unmatched_mentions: tuple[dict[str, str], ...],
) -> list[dict[str, Any]]:
    if not assignments:
        issues: list[dict[str, Any]] = [{"code": "no-assignments"}]
    else:
        issues = []
    assignment_ids_by_section: dict[str, list[str]] = {}
    for assignment in assignments:
        assignment_ids_by_section.setdefault(assignment.section_id, []).append(
            assignment.assignment_id
        )
    for section_id, assignment_ids in assignment_ids_by_section.items():
        if len(assignment_ids) > 1:
            issues.append(
                {
                    "code": "duplicate-section",
                    "section_id": section_id,
                    "assignment_ids": assignment_ids,
                }
            )
    if unmatched_mentions:
        issues.append(
            {
                "code": "unmatched-section-mentions",
                "assignment_ids": [mention["assignment_id"] for mention in unmatched_mentions],
            }
        )
    return issues


def _validate_canvas_assignment_url(url: str, *, assignment_id: str) -> None:
    parsed = urlsplit(url)
    expected_path = f"/courses/{CANVAS_COURSE_NUMBER}/assignments/{assignment_id}"
    if (
        not assignment_id.isdigit()
        or parsed.scheme != "https"
        or parsed.hostname != CANVAS_HOST
        or parsed.path != expected_path
        or parsed.query
        or parsed.fragment
        or parsed.username
        or parsed.password
    ):
        # Name only the assignment ID: an unsafe URL may itself carry a token.
        raise ValueError(
            f"Candidate must use a safe Canvas assignment URL (assignment {assignment_id!s:.32})."
        )


def _section_sort_key(section_id: str) -> tuple[int, ...]:
    return tuple(int(part) for part in section_id.split("."))


def require_canvas_credentials(credentials: tuple[str, str] | None) -> tuple[str, str]:
    if credentials is None:
        raise SystemExit("Canvas credentials are required for Calculus onboarding discovery.")
    return credentials


def _default_candidate_path(chapter: str) -> Path:
    return (
        Path(__file__).resolve().parent
        / "output"
        / "courses"
        / COURSE_ID
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
    credentials = require_canvas_credentials(
        resolve_canvas_credentials(
            username=None,
            password=None,
            skip_fetch=False,
            env=os.environ,
        )
    )
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
            unmatched_mentions = find_unmatched_section_mentions(items, chapter=args.chapter)
            payload = build_candidate_payload(
                chapter=args.chapter,
                assignments=assignments,
                unmatched_mentions=unmatched_mentions,
            )
            atomic_write_json(candidate_path, payload, indent=2)
        finally:
            browser.close()

    print(f"Wrote review-required candidate: {candidate_path}")
    print(f"Found {len(assignments)} safe Chapter {args.chapter} Canvas assignment(s).")
    for assignment in assignments:
        print(f"  {assignment.section_id}: {assignment.name} (assignment {assignment.assignment_id})")
    for mention in unmatched_mentions:
        print(f"  UNMATCHED: {mention['name']} (assignment {mention['assignment_id']})")
    for issue in payload["issues"]:
        print(f"REVIEW ISSUE: {issue}")
    raise SystemExit(candidate_exit_status(payload))


if __name__ == "__main__":
    main()
