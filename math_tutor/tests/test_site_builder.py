from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        from math_tutor.site_builder import _write_html_if_changed
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "test.html"
            _write_html_if_changed(path, "<html>old</html>")
            with patch.object(Path, "write_text") as mock_write:
                _write_html_if_changed(path, "<html>new</html>")
                mock_write.assert_called_once()

    def test_build_site_creates_portal_and_isolated_course_directories(self) -> None:
        from math_tutor.site_builder import build_site

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "output"
            site_dir = root / "site"
            output_dir.mkdir()

            with patch("math_tutor.site_builder.build_challenges") as build_challenges:
                index_path = build_site(
                    output_dir=output_dir,
                    site_dir=site_dir,
                    base_path="/site/",
                )

            algebra_dir = site_dir / "courses" / "algebra-2-trig"
            calculus_dir = site_dir / "courses" / "ap-calculus-ab"
            self.assertEqual(index_path, site_dir / "index.html")
            self.assertTrue((site_dir / "index.html").is_file())
            self.assertTrue((algebra_dir / "index.html").is_file())
            self.assertTrue((algebra_dir / "library.html").is_file())
            self.assertTrue((algebra_dir / "live-tutor.html").is_file())
            self.assertTrue((algebra_dir / "privacy-policy.html").is_file())
            self.assertEqual([path.name for path in calculus_dir.iterdir()], ["index.html"])
            build_challenges.assert_called_once_with(
                output_dir=output_dir,
                site_dir=algebra_dir,
                experience_variant="staging",
            )

    def test_build_site_publishes_calculus_chapter_from_isolated_output(self) -> None:
        from math_tutor.site_builder import build_site

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "output"
            site_dir = root / "site"
            calculus_output_dir = output_dir / "courses" / "ap-calculus-ab"
            calculus_downloads_dir = calculus_output_dir / "downloads"
            calculus_downloads_dir.mkdir(parents=True)
            source_pdf = calculus_downloads_dir / "4839635_chapter-2-notetakers.pdf"
            source_pdf.write_bytes(b"%PDF-1.7\nchapter two")
            (calculus_output_dir / "fetch_state.json").write_text(
                json.dumps(
                    {
                        "fetched": {
                            "4839635": {
                                "display_name": "Chapter 2 Notetakers.pdf",
                                "pdf_path": str(source_pdf),
                                "download_url": "https://mitty.instructure.com/files/4839635/download",
                                "fetched_at": "2026-09-19T12:00:00Z",
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            responses_dir = calculus_output_dir / "responses"
            responses_dir.mkdir()
            response_md = responses_dir / "4839635_chapter-2-notetakers__study-guide-gpt5.md"
            response_html = responses_dir / "4839635_chapter-2-notetakers__study-guide-gpt5.html"
            response_pdf = responses_dir / "4839635_chapter-2-notetakers__study-guide-gpt5.pdf"
            response_md.write_text(
                "## Title\nLimits and Derivatives\n\n## Short Summary\nLimits become derivatives.\n",
                encoding="utf-8",
            )
            response_html.write_text("<html><body>Study Guide</body></html>", encoding="utf-8")
            response_pdf.write_bytes(b"%PDF-1.7\nstudy guide")
            (calculus_output_dir / "generated_output_state.json").write_text(
                json.dumps(
                    {
                        "processed": {
                            "4839635": {
                                "study-guide": {
                                    "display_name": "Chapter 2 Notetakers.pdf",
                                    "prompt_title": "Study Guide",
                                    "response_path": str(response_md),
                                    "response_html_path": str(response_html),
                                    "response_pdf_path": str(response_pdf),
                                    "processed_at": "2026-09-19T13:00:00Z",
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch("math_tutor.site_builder.build_challenges"):
                build_site(
                    output_dir=output_dir,
                    site_dir=site_dir,
                    base_path="/site/",
                )

            calculus_dir = site_dir / "courses" / "ap-calculus-ab"
            deployed_pdf = calculus_dir / "downloads" / source_pdf.name
            portal_html = (site_dir / "index.html").read_text(encoding="utf-8")
            course_html = (calculus_dir / "index.html").read_text(encoding="utf-8")
            record_html = (calculus_dir / "doc-4839635.html").read_text(encoding="utf-8")

            self.assertTrue((calculus_dir / "library.html").is_file())
            self.assertTrue((calculus_dir / "privacy-policy.html").is_file())
            self.assertFalse((calculus_dir / "live-tutor.html").exists())
            self.assertFalse((calculus_dir / "challenges").exists())
            self.assertEqual(deployed_pdf.read_bytes(), source_pdf.read_bytes())
            self.assertIn("AP Calculus AB", course_html)
            self.assertIn("Chapter 2: Limits and Derivatives", course_html)
            self.assertIn("doc-4839635.html", course_html)
            self.assertNotIn("Live Tutor", course_html)
            self.assertNotIn("Challenge Exams", course_html)
            self.assertIn("Class Note PDF", record_html)
            self.assertIn("Study guide", record_html)
            self.assertIn("Read Guide", record_html)
            self.assertIn("Chapter 2: Limits and Derivatives", record_html)
            self.assertNotIn("Chapter 2: Chapter 2 Notetakers", record_html)
            self.assertIn("Chapter 2 textbook", record_html)
            self.assertIn("Open Chapter 2 through Canvas", record_html)
            self.assertIn("Read It", record_html)
            self.assertNotIn("Open the textbook", record_html)
            self.assertNotIn("snapshotId=1529049", record_html)
            self.assertNotIn("gateway.cengage.com", record_html)
            self.assertNotIn("ltioidc", record_html)
            self.assertNotIn("token=", record_html)
            for unsupported in ("Challenge Exams", "Live Tutor", "Mental Math", "Olympiad"):
                self.assertNotIn(unsupported, course_html)
                self.assertNotIn(unsupported, record_html)
            library_html = (calculus_dir / "library.html").read_text(encoding="utf-8")
            self.assertIn("Choose a chapter, then pick your mode", library_html)
            self.assertIn(">Learn<", library_html)
            self.assertIn(">Challenge<", library_html)
            self.assertIn(
                'href="/site/courses/ap-calculus-ab/doc-4839635.html#ai-challenge"',
                library_html,
            )
            self.assertIn("Study guide and AI challenge ready", library_html)
            self.assertNotIn("1 study tools ready", library_html)
            self.assertNotIn(">Practice<", library_html)
            self.assertNotIn("#challenge", library_html)
            self.assertNotIn("#practice", library_html)
            self.assertNotIn("#practice", record_html)
            self.assertIn(
                '/site/courses/ap-calculus-ab/downloads/4839635_chapter-2-notetakers.pdf',
                record_html,
            )
            calculus_card = portal_html[portal_html.index("AP Calculus AB") - 250 :]
            self.assertIn("Ready", calculus_card)
            self.assertNotIn("Opening soon", calculus_card[:400])


if __name__ == "__main__":
    unittest.main()
