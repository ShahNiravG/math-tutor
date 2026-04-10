from __future__ import annotations

import tempfile
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


    def test_write_html_if_changed_skips_write_if_content_unchanged(self) -> None:
        from unittest.mock import patch
        from math_tutor.site_builder import _write_html_if_changed
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "test.html"
            _write_html_if_changed(path, "<html>content</html>")
            with patch.object(Path, "write_text") as mock_write:
                _write_html_if_changed(path, "<html>content</html>")
                mock_write.assert_not_called()

    def test_write_html_if_changed_writes_when_content_changed(self) -> None:
        from unittest.mock import patch
        from math_tutor.site_builder import _write_html_if_changed
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "test.html"
            _write_html_if_changed(path, "<html>old</html>")
            with patch.object(Path, "write_text") as mock_write:
                _write_html_if_changed(path, "<html>new</html>")
                mock_write.assert_called_once()


if __name__ == "__main__":
    unittest.main()
