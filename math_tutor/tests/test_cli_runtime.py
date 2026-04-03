from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from math_tutor.cli_runtime import (
    build_output_layout,
    build_saved_class_note_files,
    display_name_matches_chapter_filters,
    ensure_output_layout,
    needs_openai_generation_client,
    needs_pdf_browser,
    normalize_cli_chapter_filters,
)
from math_tutor.prompt_catalog import PROMPTS_BY_SLUG
from math_tutor.state_store import FetchState


class CliRuntimeTests(unittest.TestCase):
    def test_build_output_layout_uses_standard_directories(self) -> None:
        layout = build_output_layout(Path("/tmp/math-tutor-output"))

        self.assertEqual(layout.downloads_dir, Path("/tmp/math-tutor-output/downloads"))
        self.assertEqual(layout.assignments_dir, Path("/tmp/math-tutor-output/downloads/assignments"))
        self.assertEqual(layout.responses_dir, Path("/tmp/math-tutor-output/responses"))
        self.assertEqual(layout.metadata_dir, Path("/tmp/math-tutor-output/metadata"))

    def test_ensure_output_layout_creates_expected_directories(self) -> None:
        with TemporaryDirectory() as temp_dir:
            layout = build_output_layout(Path(temp_dir) / "output")

            ensure_output_layout(layout)

            self.assertTrue(layout.downloads_dir.is_dir())
            self.assertTrue(layout.assignments_dir.is_dir())
            self.assertTrue(layout.responses_dir.is_dir())
            self.assertTrue(layout.metadata_dir.is_dir())

    def test_display_name_matches_chapter_filters(self) -> None:
        filters = normalize_cli_chapter_filters(["7.4 & 7.5"])

        self.assertTrue(
            display_name_matches_chapter_filters(
                "Alg 2 Trig H Chp 7.4 & 7.5 Note.docx",
                filters,
            )
        )
        self.assertFalse(
            display_name_matches_chapter_filters(
                "Alg 2 Trig H Chp 5.1 Note.docx",
                filters,
            )
        )

    def test_build_saved_class_note_files_skips_assignments_and_filters_chapters(self) -> None:
        fetch_state = FetchState(
            path=Path("/tmp/fetch_state.json"),
            fetched={
                "1": {
                    "display_name": "Alg 2 Trig H Chp 5.1 Note.docx",
                    "pdf_path": "/tmp/output/downloads/4401267_note.pdf",
                    "download_url": "https://example.com/1",
                    "content_type": "application/pdf",
                },
                "2": {
                    "display_name": "Alg 2 Trig H Chp 5.2 Note.docx",
                    "pdf_path": "/tmp/output/downloads/assignments/5.2.pdf",
                    "download_url": "https://example.com/2",
                    "content_type": "application/pdf",
                },
            },
        )

        files = build_saved_class_note_files(
            fetch_state=fetch_state,
            assignments_dir=Path("/tmp/output/downloads/assignments"),
            normalized_chapter_filters=normalize_cli_chapter_filters(["5.1"]),
            limit=None,
        )

        self.assertEqual([file.file_id for file in files], [1])
        self.assertEqual(files[0].display_name, "Alg 2 Trig H Chp 5.1 Note.docx")

    def test_needs_openai_generation_client_only_for_non_gemini_prompts(self) -> None:
        self.assertTrue(
            needs_openai_generation_client((PROMPTS_BY_SLUG["study-guide"],))
        )
        self.assertFalse(
            needs_openai_generation_client((PROMPTS_BY_SLUG["mental-math-gemini"],))
        )

    def test_needs_pdf_browser_only_for_pdf_generating_prompts(self) -> None:
        self.assertTrue(needs_pdf_browser((PROMPTS_BY_SLUG["study-guide"],)))
        self.assertFalse(needs_pdf_browser((PROMPTS_BY_SLUG["study-guide-gemini"],)))


if __name__ == "__main__":
    unittest.main()
