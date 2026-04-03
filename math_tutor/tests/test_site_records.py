from __future__ import annotations

import unittest
from pathlib import Path

from math_tutor.site_challenges import render_chapter_challenge_card
from math_tutor.site_models import DocumentRecord
from math_tutor.site_records import render_document_overview_card


def site_page_href(filename: str, base_path: str) -> str:
    return f"{base_path}{filename}" if base_path else filename


class SiteRecordsTests(unittest.TestCase):
    def test_render_document_overview_card_uses_summary_when_present(self) -> None:
        record = DocumentRecord(
            file_id="4401267",
            display_name="Alg 2 Trig H Chp 5.1 Note.docx",
            pdf_path=None,
            download_url=None,
            fetched_at=None,
            prompt_outputs=[],
        )

        html = render_document_overview_card(
            record,
            output_dir=Path("."),
            site_dir=Path("."),
            base_path="/site/",
            include_guided_learning=False,
            site_page_href=site_page_href,
        )

        self.assertIn("Chapter 5.1", html)
        self.assertIn("/site/doc-4401267.html", html)

    def test_render_chapter_challenge_card_uses_expected_labels(self) -> None:
        record = DocumentRecord(
            file_id="4401267",
            display_name="Alg 2 Trig H Chp 5.1 Note.docx",
            pdf_path=None,
            download_url=None,
            fetched_at=None,
            prompt_outputs=[],
        )

        html = render_chapter_challenge_card(record, "/site/", site_page_href)

        self.assertIn("Challenge Exams", html)
        self.assertIn("Mental Math Challenge", html)
        self.assertIn("Olympiad Challenge", html)
        self.assertIn("Resume Challenge", html)
        self.assertIn("/site/challenges/exam.html?id=", html)


if __name__ == "__main__":
    unittest.main()
