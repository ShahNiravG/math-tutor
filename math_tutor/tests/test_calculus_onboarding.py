from __future__ import annotations

import unittest
from unittest.mock import Mock

from math_tutor.calculus_onboarding import (
    CanvasAssignmentCandidate,
    build_candidate_payload,
    extract_chapter_assignment_candidates,
    fetch_canvas_assignment_items,
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
        )

        self.assertEqual(payload["course_id"], "ap-calculus-ab")
        self.assertEqual(payload["chapter"], "3")
        self.assertEqual(payload["assignments"][0]["assignment_id"], "310002")
        serialized = repr(payload).lower()
        for forbidden in ("cookie", "token", "password", "oidc", "gateway.cengage.com"):
            self.assertNotIn(forbidden, serialized)

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


if __name__ == "__main__":
    unittest.main()
