from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

from math_tutor.canvas_course import (
    CanvasFile,
    ensure_pdf_fetched,
    extract_assignment_entries_from_api_items,
    extract_file_id,
    extract_assignment_downloads_from_html,
    is_pdf,
    is_pdf_by_name,
    list_canvas_pdfs_from_assignments,
    list_canvas_pdfs_from_ui,
    matches_assignment_pdf,
    matches_target_pdf,
    normalize_download_url,
    parse_link_next,
)
from math_tutor.state_store import FetchState


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

    def test_ensure_pdf_fetched_reuses_saved_pdf_path_from_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            saved_pdf = root / "downloads" / "assignments" / "4435419_chp-5-1-work.pdf"
            saved_pdf.parent.mkdir(parents=True, exist_ok=True)
            saved_pdf.write_text("pdf", encoding="utf-8")
            alternate_destination = root / "downloads" / "assignments" / "4435419_other-name.pdf"

            fetch_state = FetchState(
                path=root / "fetch_state.json",
                fetched={
                    "4435419": {
                        "display_name": "Chp 5.1 work.pdf",
                        "download_url": "https://example.com/file.pdf",
                        "pdf_path": str(saved_pdf),
                    }
                },
            )
            canvas_file = CanvasFile(
                file_id=4435419,
                display_name="Chp 5.1 work.pdf",
                download_url="https://example.com/file.pdf",
                content_type="application/pdf",
                size=None,
                updated_at=None,
            )

            ensure_pdf_fetched(
                client=None,
                canvas_file=canvas_file,
                destination=alternate_destination,
                fetch_state=fetch_state,
                force=False,
                index=1,
                total=1,
            )

            self.assertFalse(alternate_destination.exists())

    def test_list_canvas_pdfs_from_ui_prefers_modules_without_files_probe(self) -> None:
        modules_result = [
            CanvasFile(
                file_id=1,
                display_name="Alg 2 Trig H Chp 5.1 Note.docx",
                download_url="https://example.com/file.pdf",
                content_type="application/pdf",
                size=None,
                updated_at=None,
            )
        ]
        with patch("math_tutor.canvas_course.list_canvas_pdfs_from_modules_page", return_value=modules_result) as modules_page:
            with patch("math_tutor.canvas_course.list_canvas_pdfs_from_files_page") as files_page:
                files = list_canvas_pdfs_from_ui(Mock(), Mock(), "https://example.com/course")

        self.assertEqual(files, modules_result)
        modules_page.assert_called_once()
        files_page.assert_not_called()

    def test_extract_assignment_downloads_from_html_finds_file_download_links(self) -> None:
        html_text = """
        <html><body>
          <a href="/courses/4187/files/4435419/download?download=1">Worksheet</a>
          <a href="/courses/4187/pages/other">Ignore</a>
        </body></html>
        """

        downloads = extract_assignment_downloads_from_html(
            html_text=html_text,
            course_url="https://mitty.instructure.com/courses/4187",
        )

        self.assertEqual(downloads, ["https://mitty.instructure.com/courses/4187/files/4435419/download?download=1"])

    def test_extract_assignment_entries_from_api_items_prefers_online_upload_assignments(self) -> None:
        entries = extract_assignment_entries_from_api_items(
            [
                {
                    "name": "Chp 5.1 work",
                    "html_url": "https://host/assignments/1",
                    "submission_types": ["online_upload"],
                },
                {
                    "name": "5.1 Hmwk-Angle Measure",
                    "html_url": "https://host/assignments/2",
                    "submission_types": ["external_tool"],
                },
            ]
        )

        self.assertEqual(entries, [("Chp 5.1 work", "https://host/assignments/1")])

    def test_list_canvas_pdfs_from_assignments_falls_back_to_page_scan_when_parallel_fetch_finds_nothing(self) -> None:
        client = Mock()
        response = Mock()
        response.json.return_value = [
            {
                "name": "Chp 5.1 work",
                "html_url": "https://host/assignments/1",
                "submission_types": ["online_upload"],
            }
        ]
        response.headers = {"link": ""}
        response.raise_for_status.return_value = None
        client.get.return_value = response

        anchor = Mock()
        anchor.get_attribute.return_value = "/courses/4187/files/4435419/download?download=1"
        anchors = Mock()
        anchors.count.return_value = 1
        anchors.nth.return_value = anchor
        page = Mock()
        page.locator.return_value = anchors

        with patch("math_tutor.canvas_course.fetch_assignment_download_links", return_value=[("Chp 5.1 work", [])]):
            files = list_canvas_pdfs_from_assignments(page, client, "https://host/courses/4187")

        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].file_id, 4435419)


if __name__ == "__main__":
    unittest.main()
