from __future__ import annotations

import unittest
from pathlib import Path

from math_tutor.chaptering import (
    chapter_slug,
    chapter_sort_key,
    format_assignment_display_name,
    parse_assignment_chapters,
    parse_display_name_chapter,
    parse_response_stem_chapter,
)


class ChapteringTests(unittest.TestCase):
    def test_parse_display_name_chapter_single(self) -> None:
        self.assertEqual(
            parse_display_name_chapter("Alg 2 Trig H Chp 5.1 Note.docx"),
            "5.1",
        )

    def test_parse_display_name_chapter_multi(self) -> None:
        self.assertEqual(
            parse_display_name_chapter("Alg 2 Trig H Chp 7.4 & 7.5 Note.docx"),
            "7.4 & 7.5",
        )

    def test_parse_response_stem_chapter(self) -> None:
        self.assertEqual(
            parse_response_stem_chapter("4506904_alg-2trig-h-chp-6-1-note-docx__mental-math-gpt5"),
            "6.1",
        )

    def test_parse_assignment_chapters(self) -> None:
        self.assertEqual(
            parse_assignment_chapters("4517747_chp-6-1-6-2-work.pdf"),
            {"6.1", "6.2"},
        )

    def test_format_assignment_display_name(self) -> None:
        self.assertEqual(
            format_assignment_display_name(Path("4517747_chp-6-1-6-2-work.pdf")),
            "Chapter 6.1 6.2 Work",
        )

    def test_chapter_sort_key_and_slug(self) -> None:
        self.assertEqual(chapter_sort_key("5.1"), 5.1)
        self.assertEqual(chapter_slug("7.4 & 7.5"), "7475")


if __name__ == "__main__":
    unittest.main()
