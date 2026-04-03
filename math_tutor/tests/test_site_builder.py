from __future__ import annotations

import unittest
from pathlib import Path

from math_tutor.site_content import render_record_summary
from math_tutor.site_models import DocumentRecord, PromptOutputRecord


class SiteBuilderTests(unittest.TestCase):
    def test_render_record_summary_wraps_summary_content_in_prominent_container(self) -> None:
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
                    response_markdown="## Short Summary\nThis chapter introduces radians.\n",
                )
            ],
        )

        html = render_record_summary(record)

        self.assertIn('class="guided-card summary-card"', html)
        self.assertIn('class="card-summary"', html)
        self.assertIn("This chapter introduces radians.", html)


if __name__ == "__main__":
    unittest.main()
