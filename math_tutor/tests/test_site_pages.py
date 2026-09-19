from __future__ import annotations

import unittest
from pathlib import Path

from math_tutor.site_courses import get_course
from math_tutor.site_pages import build_index_html
from math_tutor.site_sections import render_surface_header


class SitePagesTests(unittest.TestCase):
    def test_course_header_identifies_course_and_links_back_to_portal(self) -> None:
        html = render_surface_header(
            active="home",
            base_path="/site/courses/algebra-2-trig/",
            eyebrow="Math Delight",
            title="Algebra II Trig Tutor",
            site_page_href=lambda filename, base_path: f"{base_path}{filename}",
            course=get_course("algebra-2-trig"),
            portal_href="/site/index.html",
        )

        self.assertIn("Algebra II / Trigonometry", html)
        self.assertIn('href="/site/index.html"', html)
        self.assertIn("Switch Course", html)
        self.assertIn('href="/site/courses/algebra-2-trig/library.html"', html)

    def test_build_index_html_includes_core_destinations(self) -> None:
        html = build_index_html(
            records=[],
            output_dir=Path("/tmp/output"),
            site_dir=Path("/tmp/site"),
            base_path="/site/",
            course=get_course("algebra-2-trig"),
            portal_href="/site/index.html",
            include_guided_learning=False,
            site_page_href=lambda filename, base_path: f"{base_path}{filename}",
        )

        self.assertIn("Challenge Exams", html)
        self.assertIn("Live Tutor", html)
        self.assertIn("Math Delight", html)

    def test_build_index_html_staging_includes_continue_card(self) -> None:
        html = build_index_html(
            records=[],
            output_dir=Path("/tmp/output"),
            site_dir=Path("/tmp/site"),
            base_path="/site/staging/",
            course=get_course("algebra-2-trig"),
            portal_href="/site/index.html",
            include_guided_learning=False,
            site_page_href=lambda filename, base_path: f"{base_path}{filename}",
            experience_variant="staging",
        )

        self.assertIn("data-continue-card", html)
        self.assertIn("data-challenge-link", html)
        self.assertIn("Start Practice", html)
        self.assertIn("experience-staging", html)
        self.assertIn('const LAST_RECORD_KEY = "math_tutor_last_record";', html)
        self.assertIn('const LEGACY_SESSION_KEY = "math_tutor_challenge_session";', html)
        self.assertIn('const SESSION_KEY_PREFIX = "math_tutor_challenge_session:";', html)
        self.assertIn("getMostRecentChallengeSession()", html)
        self.assertIn("Resume Chapter", html)


if __name__ == "__main__":
    unittest.main()
