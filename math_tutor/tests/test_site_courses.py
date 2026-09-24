from __future__ import annotations

import unittest

from math_tutor.site_courses import (
    COURSE_REGISTRY,
    canvas_course_location,
    get_course,
    matches_course_document,
)


class SiteCoursesTests(unittest.TestCase):
    def test_registry_contains_the_two_approved_courses_in_portal_order(self) -> None:
        self.assertEqual(
            [course.course_id for course in COURSE_REGISTRY],
            ["algebra-2-trig", "ap-calculus-ab"],
        )
        self.assertEqual(
            [course.display_name for course in COURSE_REGISTRY],
            ["Algebra II / Trigonometry", "AP Calculus AB"],
        )
        self.assertEqual(len({course.course_id for course in COURSE_REGISTRY}), len(COURSE_REGISTRY))

    def test_calculus_is_registered_as_an_empty_course(self) -> None:
        calculus = get_course("ap-calculus-ab")

        self.assertFalse(calculus.content_ready)
        self.assertEqual(calculus.section_label, "Chapter")
        self.assertEqual(
            calculus.canvas_course_url,
            "https://mitty.instructure.com/courses/4446",
        )

    def test_calculus_document_matcher_uses_school_notetaker_names(self) -> None:
        self.assertTrue(
            matches_course_document("ap-calculus-ab", "Chapter 2 Notetakers.pdf")
        )
        self.assertTrue(
            matches_course_document("ap-calculus-ab", "  chapter   2   notetakers.PDF  ")
        )
        self.assertTrue(
            matches_course_document("ap-calculus-ab", "Chapter 20 Notetakers.pdf")
        )
        self.assertFalse(
            matches_course_document("ap-calculus-ab", "Chapter 2.1 Notetakers.pdf")
        )
        self.assertFalse(
            matches_course_document("ap-calculus-ab", "Chapter 2 Homework.pdf")
        )
        self.assertFalse(
            matches_course_document("ap-calculus-ab", "Alg 2 Trig H Chp 2 Note.pdf")
        )

    def test_algebra_document_matcher_preserves_existing_note_rules(self) -> None:
        self.assertTrue(
            matches_course_document("algebra-2-trig", "Alg 2 Trig H Chp 5.1 Note.docx")
        )
        self.assertFalse(
            matches_course_document("algebra-2-trig", "Chapter 2 Notetakers.pdf")
        )

    def test_canvas_course_location_is_derived_from_the_course_url(self) -> None:
        self.assertEqual(
            canvas_course_location("ap-calculus-ab"),
            ("mitty.instructure.com", "4446"),
        )
        self.assertEqual(
            canvas_course_location("algebra-2-trig"),
            ("mitty.instructure.com", "4187"),
        )

    def test_unknown_course_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown course: missing-course"):
            get_course("missing-course")


if __name__ == "__main__":
    unittest.main()
