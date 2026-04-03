from __future__ import annotations

import unittest
from pathlib import Path

from math_tutor.site_content import (
    build_guided_learning_prompt,
    extract_record_summary_html,
    extract_study_guide_summary_lines,
    normalize_summary_text,
)
from math_tutor.site_models import DocumentRecord, PromptOutputRecord


class SiteContentTests(unittest.TestCase):
    def test_normalize_summary_text_rewrites_document_to_chapter(self) -> None:
        self.assertEqual(
            normalize_summary_text("This document introduces radians."),
            "This chapter introduces radians.",
        )

    def test_extract_study_guide_summary_lines_stops_before_next_section(self) -> None:
        lines = extract_study_guide_summary_lines(
            "## Short Summary\nThis chapter introduces radians.\n\n## Definitions\nTerm\n"
        )
        self.assertEqual(lines, ["This chapter introduces radians."])

    def test_build_guided_learning_prompt_uses_markdown_summary_fallback(self) -> None:
        record = DocumentRecord(
            file_id="4401267",
            display_name="Alg 2 Trig H Chp 5.1 Note.docx",
            pdf_path=None,
            download_url=None,
            fetched_at=None,
            prompt_outputs=[
                PromptOutputRecord(
                    slug="study-guide",
                    title="Study Guide",
                    response_path=Path("output/responses/example.md"),
                    response_html_path=None,
                    response_pdf_path=None,
                    metadata_path=None,
                    processed_at="2026-04-02T00:00:00Z",
                    response_markdown="## Short Summary\nThis document introduces radians.\n",
                )
            ],
        )
        self.assertEqual(
            build_guided_learning_prompt(record),
            "This chapter introduces radians.",
        )

    def test_extract_record_summary_html_falls_back_to_markdown(self) -> None:
        record = DocumentRecord(
            file_id="4401267",
            display_name="Alg 2 Trig H Chp 5.1 Note.docx",
            pdf_path=None,
            download_url=None,
            fetched_at=None,
            prompt_outputs=[
                PromptOutputRecord(
                    slug="study-guide",
                    title="Study Guide",
                    response_path=Path("output/responses/example.md"),
                    response_html_path=None,
                    response_pdf_path=None,
                    metadata_path=None,
                    processed_at="2026-04-02T00:00:00Z",
                    response_markdown="## Short Summary\nThis document introduces radians.\n",
                )
            ],
        )
        html = extract_record_summary_html(record)
        self.assertIn("This chapter introduces radians.", html)


if __name__ == "__main__":
    unittest.main()
