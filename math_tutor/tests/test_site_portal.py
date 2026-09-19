from __future__ import annotations

import unittest

from math_tutor.site_courses import COURSE_REGISTRY, get_course
from math_tutor.site_portal import build_empty_course_html, build_portal_html


class SitePortalTests(unittest.TestCase):
    def test_portal_lists_both_courses_with_course_scoped_links(self) -> None:
        html = build_portal_html(courses=COURSE_REGISTRY, base_path="/site/")

        self.assertIn("Choose your course", html)
        self.assertIn("Algebra II / Trigonometry", html)
        self.assertIn("AP Calculus AB", html)
        self.assertIn('href="/site/courses/algebra-2-trig/index.html"', html)
        self.assertIn('href="/site/courses/ap-calculus-ab/index.html"', html)
        self.assertIn('aria-label="Available courses"', html)

    def test_portal_uses_relative_links_for_a_local_build(self) -> None:
        html = build_portal_html(courses=COURSE_REGISTRY, base_path="")

        self.assertIn('href="courses/algebra-2-trig/index.html"', html)
        self.assertIn('href="courses/ap-calculus-ab/index.html"', html)

    def test_calculus_page_is_an_intentional_empty_state(self) -> None:
        html = build_empty_course_html(
            course=get_course("ap-calculus-ab"),
            portal_href="../../index.html",
        )

        self.assertIn("AP Calculus AB", html)
        self.assertIn("Course setup in progress", html)
        self.assertIn("No chapters have been published yet", html)
        self.assertIn('href="../../index.html"', html)
        self.assertIn("Switch Course", html)
        self.assertNotIn("Algebra II", html)
        self.assertNotIn("Challenge Exams", html)
        self.assertNotIn("library.html", html)


if __name__ == "__main__":
    unittest.main()
