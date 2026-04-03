from __future__ import annotations

import unittest

from math_tutor.site_navigation import render_sidebar_item
from math_tutor.site_models import DocumentRecord
from math_tutor.site_shell import render_page_shell


def site_page_href(filename: str, base_path: str) -> str:
    return f"{base_path}{filename}" if base_path else filename


class SiteShellTests(unittest.TestCase):
    def test_render_sidebar_item_marks_active_record(self) -> None:
        record = DocumentRecord(
            file_id="4401267",
            display_name="Alg 2 Trig H Chp 5.1 Note.docx",
            pdf_path=None,
            download_url=None,
            fetched_at=None,
            prompt_outputs=[],
        )

        html = render_sidebar_item(record, record, "/site/", site_page_href)

        self.assertIn('class="active"', html)
        self.assertIn('/site/doc-4401267.html', html)
        self.assertIn("Chapter 5.1", html)

    def test_render_page_shell_renders_library_sidebar_and_shell_css(self) -> None:
        record = DocumentRecord(
            file_id="4401267",
            display_name="Alg 2 Trig H Chp 5.1 Note.docx",
            pdf_path=None,
            download_url=None,
            fetched_at=None,
            prompt_outputs=[],
        )

        html = render_page_shell(
            title="Library - Algebra II with Trigonometry Tutor",
            records=[record],
            active_record=None,
            body_html="<section>Library body</section>",
            total_prompt_outputs=12,
            generated_at="2026-04-02 12:00 UTC",
            base_path="/site/",
            site_page_href=site_page_href,
            page_kind="library",
        )

        self.assertIn('<aside class="sidebar sidebar-library">', html)
        self.assertIn(">Chapters<", html)
        self.assertIn("Library body", html)
        self.assertIn("window.MathJax", html)
        self.assertIn(".card-summary {", html)
        self.assertIn(".summary-card .card-summary", html)


if __name__ == "__main__":
    unittest.main()
