from __future__ import annotations

import unittest
from unittest.mock import Mock

from math_tutor.calculus_onboarding import (
    CanvasAssignmentCandidate,
    build_candidate_payload,
    candidate_exit_status,
    extract_chapter_assignment_candidates,
    fetch_canvas_assignment_items,
    find_unmatched_section_mentions,
    require_canvas_credentials,
)


class CalculusOnboardingTests(unittest.TestCase):
    def test_fetches_all_canvas_assignment_pages(self) -> None:
        first = Mock()
        first.json.return_value = [{"id": 1}]
        first.headers = {
            "link": '<https://mitty.instructure.com/api/v1/courses/4446/assignments?page=2>; rel="next"'
        }
        second = Mock()
        second.json.return_value = [{"id": 2}]
        second.headers = {}
        client = Mock()
        client.get.side_effect = [first, second]

        items = fetch_canvas_assignment_items(client)

        self.assertEqual(items, [{"id": 1}, {"id": 2}])
        self.assertEqual(client.get.call_count, 2)
        first.raise_for_status.assert_called_once_with()
        second.raise_for_status.assert_called_once_with()

    def test_candidate_payload_contains_only_reviewable_non_secret_fields(self) -> None:
        payload = build_candidate_payload(
            chapter="3",
            assignments=(
                CanvasAssignmentCandidate(
                    assignment_id="310002",
                    name="3.1 Derivatives",
                    html_url="https://mitty.instructure.com/courses/4446/assignments/310002",
                    section_id="3.1",
                ),
            ),
            unmatched_mentions=(),
        )

        self.assertEqual(payload["course_id"], "ap-calculus-ab")
        self.assertEqual(payload["chapter"], "3")
        self.assertEqual(payload["assignments"][0]["assignment_id"], "310002")
        serialized = repr(payload).lower()
        for forbidden in ("cookie", "token", "password", "oidc", "gateway.cengage.com"):
            self.assertNotIn(forbidden, serialized)

    def test_candidate_payload_reports_review_issues(self) -> None:
        def candidate(assignment_id: str, section_id: str) -> CanvasAssignmentCandidate:
            return CanvasAssignmentCandidate(
                assignment_id=assignment_id,
                name=f"Chp {section_id} Hmwk",
                html_url=f"https://mitty.instructure.com/courses/4446/assignments/{assignment_id}",
                section_id=section_id,
            )

        clean = build_candidate_payload(
            chapter="3",
            assignments=(candidate("1", "3.1"), candidate("2", "3.2")),
            unmatched_mentions=(),
        )
        duplicated = build_candidate_payload(
            chapter="3",
            assignments=(candidate("1", "3.1"), candidate("3", "3.1"), candidate("2", "3.2")),
            unmatched_mentions=({"assignment_id": "9", "name": "Quiz 3.1-3.3"},),
        )
        empty = build_candidate_payload(chapter="3", assignments=(), unmatched_mentions=())

        self.assertEqual(clean["schema_version"], 2)
        self.assertEqual(clean["issues"], [])
        self.assertEqual(clean["unmatched_mentions"], [])
        self.assertEqual(
            duplicated["issues"],
            [
                {"code": "duplicate-section", "section_id": "3.1", "assignment_ids": ["1", "3"]},
                {"code": "unmatched-section-mentions", "assignment_ids": ["9"]},
            ],
        )
        self.assertEqual(
            duplicated["unmatched_mentions"],
            [{"assignment_id": "9", "name": "Quiz 3.1-3.3"}],
        )
        self.assertEqual(empty["issues"], [{"code": "no-assignments"}])

    def test_missing_credentials_fail_explicitly_without_assert(self) -> None:
        with self.assertRaisesRegex(SystemExit, "Canvas credentials are required"):
            require_canvas_credentials(None)
        self.assertEqual(require_canvas_credentials(("user", "pass")), ("user", "pass"))

    def test_exit_status_is_nonzero_only_when_review_issues_exist(self) -> None:
        self.assertEqual(candidate_exit_status({"issues": []}), 0)
        self.assertEqual(candidate_exit_status({"issues": [{"code": "no-assignments"}]}), 1)

    def test_extracts_ordered_safe_external_tool_assignments_for_requested_chapter(self) -> None:
        items = [
            {
                "id": 310003,
                "name": "3.2 Product and Quotient Rules",
                "html_url": "https://mitty.instructure.com/courses/4446/assignments/310003",
                "submission_types": ["external_tool"],
            },
            {
                "id": 310002,
                "name": "3.1 Derivatives of Polynomials and Exponential Functions",
                "html_url": "https://mitty.instructure.com/courses/4446/assignments/310002",
                "submission_types": ["external_tool"],
            },
            {
                "id": 299777,
                "name": "2.1 The Tangent and Velocity Problems",
                "html_url": "https://mitty.instructure.com/courses/4446/assignments/299777",
                "submission_types": ["external_tool"],
            },
            {
                "id": 310004,
                "name": "3.3 worksheet",
                "html_url": "https://mitty.instructure.com/courses/4446/assignments/310004",
                "submission_types": ["online_upload"],
            },
        ]

        candidates = extract_chapter_assignment_candidates(items, chapter="3")

        self.assertEqual([candidate.section_id for candidate in candidates], ["3.1", "3.2"])
        self.assertEqual([candidate.assignment_id for candidate in candidates], ["310002", "310003"])

    def test_matches_real_canvas_names_and_rejects_ranges_and_later_chapters(self) -> None:
        def item(assignment_id: int, name: str) -> dict[str, object]:
            return {
                "id": assignment_id,
                "name": name,
                "html_url": f"https://mitty.instructure.com/courses/4446/assignments/{assignment_id}",
                "submission_types": ["external_tool"],
            }

        items = [
            item(299784, "Chp 3.1 Hmwk - Polynomials, Exponential Functions"),
            item(299793, "Chp 3.10 Hmwk - Linear Approximation,Differentials"),
            item(299786, "Ch. 3.3 Hmwk - Trigonometric Functions"),
            item(299787, "Chapter 3.4 Chain Rule"),
            item(310001, "4.1 due after 3.9 review"),
            item(310002, "Quiz 3.1-3.3"),
            item(310003, "Chp 3.1-3.3 Review"),
            item(310004, "Chp 3.1.2 Extra"),
        ]

        candidates = extract_chapter_assignment_candidates(items, chapter="3")

        self.assertEqual(
            [(candidate.section_id, candidate.assignment_id) for candidate in candidates],
            [("3.1", "299784"), ("3.3", "299786"), ("3.4", "299787"), ("3.10", "299793")],
        )

    def test_reports_section_mentions_that_did_not_match_for_review(self) -> None:
        url = "https://mitty.instructure.com/courses/4446/assignments/"
        items = [
            {"id": 1, "name": "Chp 3.1 Hmwk", "html_url": url + "1", "submission_types": ["external_tool"]},
            {"id": 2, "name": "Quiz 3.1-3.3", "html_url": url + "2", "submission_types": ["external_tool"]},
            {"id": 3, "name": "4.1 due after 3.9 review", "html_url": url + "3", "submission_types": ["external_tool"]},
            {"id": 4, "name": "3.2 worksheet", "html_url": url + "4", "submission_types": ["online_upload"]},
            {"id": 5, "name": "Chp 4.1 Hmwk", "html_url": url + "5", "submission_types": ["external_tool"]},
        ]

        mentions = find_unmatched_section_mentions(items, chapter="3")

        self.assertEqual(
            mentions,
            (
                {"assignment_id": "2", "name": "Quiz 3.1-3.3"},
                {"assignment_id": "3", "name": "4.1 due after 3.9 review"},
            ),
        )

    def test_rejects_off_course_or_parameterized_assignment_urls(self) -> None:
        unsafe_items = [
            {
                "id": 310002,
                "name": "3.1 Derivatives",
                "html_url": "https://example.com/courses/4446/assignments/310002",
                "submission_types": ["external_tool"],
            },
            {
                "id": 310003,
                "name": "3.2 Product Rule",
                "html_url": "https://mitty.instructure.com/courses/4446/assignments/310003?token=secret",
                "submission_types": ["external_tool"],
            },
        ]

        with self.assertRaisesRegex(ValueError, "safe Canvas assignment URL"):
            extract_chapter_assignment_candidates(unsafe_items, chapter="3")
        for unsafe_item in unsafe_items:
            with self.subTest(assignment_id=unsafe_item["id"]), self.assertRaisesRegex(
                ValueError, rf"assignment {unsafe_item['id']}\b"
            ):
                extract_chapter_assignment_candidates([unsafe_item], chapter="3")


if __name__ == "__main__":
    unittest.main()
