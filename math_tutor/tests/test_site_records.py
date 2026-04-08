from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from math_tutor.site_challenges import render_chapter_challenge_card
from math_tutor.site_models import DocumentRecord, PromptOutputRecord
from math_tutor.site_records import render_document_overview_card, render_document_page_content


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

    def test_render_document_page_content_staging_keeps_class_note_link_only_in_learn_area(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf_path = root / "4401267_note.pdf"
            summary_html_path = root / "4401267_study-guide.html"
            summary_pdf_path = root / "4401267_study-guide.pdf"
            pdf_path.write_text("note", encoding="utf-8")
            summary_html_path.write_text("<html><body>summary</body></html>", encoding="utf-8")
            summary_pdf_path.write_text("pdf", encoding="utf-8")

            record = DocumentRecord(
                file_id="4401267",
                display_name="Alg 2 Trig H Chp 5.1 Note.docx",
                pdf_path=pdf_path,
                download_url=None,
                fetched_at=None,
                prompt_outputs=[
                    PromptOutputRecord(
                        slug="study-guide",
                        title="Study Guide",
                        response_path=root / "4401267_study-guide.md",
                        response_html_path=summary_html_path,
                        response_pdf_path=summary_pdf_path,
                        metadata_path=None,
                        processed_at="2026-04-08T00:00:00Z",
                        response_markdown="## Short Summary\nRadians and arc length.\n",
                    )
                ],
            )

            html = render_document_page_content(
                record,
                output_dir=root,
                site_dir=root,
                base_path="/site/",
                include_guided_learning=False,
                site_page_href=site_page_href,
                experience_variant="staging",
            )

            chapter_focus_start = html.index('<section class="content-card chapter-hero-card"')
            learn_start = html.index('<section class="content-card section-card section-surface" id="learn">')
            practice_start = html.index('<section class="content-card section-card section-surface" id="practice">')

            chapter_focus_html = html[chapter_focus_start:learn_start]
            learn_html = html[learn_start:practice_start]

            self.assertNotIn("Class Note PDF", chapter_focus_html)
            self.assertNotIn('id="resources"', html)
            self.assertIn("Class Note PDF", learn_html)
            self.assertEqual(html.count("Class Note PDF"), 1)


if __name__ == "__main__":
    unittest.main()
