from __future__ import annotations

import unittest

from math_tutor.canvas_course import (
    extract_file_id,
    is_pdf,
    is_pdf_by_name,
    matches_assignment_pdf,
    matches_target_pdf,
    normalize_download_url,
    parse_link_next,
)


class CanvasCourseTests(unittest.TestCase):
    def test_matches_target_pdf_accepts_note_variants(self) -> None:
        self.assertTrue(matches_target_pdf("Alg 2 Trig H Chp 5.1 Note.docx"))
        self.assertTrue(matches_target_pdf("Alg 2 Trig H Chp 5.1 Note.pdf"))
        self.assertFalse(matches_target_pdf("Alg 2 Trig H Chp 5.1 Study Guide.pdf"))

    def test_matches_assignment_pdf_uses_leading_chapter_pattern(self) -> None:
        self.assertTrue(matches_assignment_pdf("5.1.pdf"))
        self.assertTrue(matches_assignment_pdf("7.4 and 7.5"))
        self.assertFalse(matches_assignment_pdf("Chapter 5 Review.pdf"))

    def test_is_pdf_helpers(self) -> None:
        self.assertTrue(is_pdf_by_name("chapter.pdf"))
        self.assertTrue(is_pdf("chapter", "application/pdf", "https://example.com/file"))
        self.assertTrue(is_pdf("chapter", "text/plain", "https://example.com/file.pdf?download=1"))
        self.assertFalse(is_pdf("chapter", "text/plain", "https://example.com/file.txt"))

    def test_extract_file_id_and_normalize_download_url(self) -> None:
        self.assertEqual(extract_file_id("https://host/files/12345/download"), 12345)
        self.assertIsNone(extract_file_id("https://host/modules/items/9"))
        self.assertEqual(
            normalize_download_url("https://host/files/12345"),
            "https://host/files/12345?download=1",
        )
        self.assertEqual(
            normalize_download_url("https://host/files/12345?wrap=1"),
            "https://host/files/12345?wrap=1&download=1",
        )

    def test_parse_link_next(self) -> None:
        self.assertEqual(
            parse_link_next(
                '<https://host/api/v1/courses/1/assignments?page=2>; rel="next", '
                '<https://host/api/v1/courses/1/assignments?page=4>; rel="last"'
            ),
            "https://host/api/v1/courses/1/assignments?page=2",
        )
        self.assertIsNone(parse_link_next('<https://host/api/v1/courses/1/assignments?page=4>; rel="last"'))


if __name__ == "__main__":
    unittest.main()
