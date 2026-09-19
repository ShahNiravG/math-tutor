from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from math_tutor.canvas_course import CanvasFile
from math_tutor.prompt_catalog import PROMPTS_BY_SLUG, resolve_selected_prompts
from math_tutor.prompt_generation import PromptResponseResult
from math_tutor.prompt_pipeline import prompt_applies_to_file, run_prompt
from math_tutor.prompt_saved_outputs import should_skip_generation
from math_tutor.state_store import GeneratedOutputState


class PromptPipelineTests(unittest.TestCase):
    def test_invalid_calculus_output_is_rejected_before_persistence(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf_path = root / "chapter-2.pdf"
            pdf_path.write_bytes(b"%PDF-1.7")
            responses_dir = root / "responses"
            metadata_dir = root / "metadata"
            responses_dir.mkdir()
            metadata_dir.mkdir()
            canvas_file = CanvasFile(
                file_id=4839635,
                display_name="Chapter 2 Notetakers.pdf",
                download_url="https://example.com/file.pdf",
                content_type="application/pdf",
                size=None,
                updated_at=None,
            )
            prompt = resolve_selected_prompts(
                ["study-guide"], course_id="ap-calculus-ab"
            )[0]
            state = GeneratedOutputState(path=root / "state.json", processed={})

            with (
                patch(
                    "math_tutor.prompt_pipeline.generate_prompt_response",
                    return_value=PromptResponseResult(
                        output_text="Provider error: unavailable", response_id="response-1"
                    ),
                ),
                patch("math_tutor.prompt_pipeline.persist_prompt_output") as persist,
                self.assertRaisesRegex(ValueError, "provider error"),
            ):
                run_prompt(
                    canvas_file=canvas_file,
                    openai_client=None,
                    gemini_client=None,
                    pdf_browser=None,
                    pdf_path=pdf_path,
                    responses_dir=responses_dir,
                    metadata_dir=metadata_dir,
                    generated_output_state=state,
                    default_model="gpt-5.4",
                    stem="4839635_chapter-2-notetakers",
                    prompt_spec=prompt,
                    prompt_outputs_cache={},
                    force=False,
                    force_generation=False,
                    index=1,
                    total=1,
                )

            persist.assert_not_called()
            self.assertEqual(list(responses_dir.iterdir()), [])
            self.assertEqual(list(metadata_dir.iterdir()), [])
            self.assertEqual(state.processed, {})

    def test_auto_grading_assignment_only_applies_to_work_assignments(self) -> None:
        prompt_spec = PROMPTS_BY_SLUG["auto-grading-assignment"]
        assignment_file = CanvasFile(
            file_id=1,
            display_name="4517747_chp-6-1-6-2-work.pdf",
            download_url="https://example.com/file.pdf",
            content_type="application/pdf",
            size=None,
            updated_at=None,
        )
        class_note_file = CanvasFile(
            file_id=2,
            display_name="Alg 2 Trig H Chp 5.1 Note.docx",
            download_url="https://example.com/file.pdf",
            content_type="application/pdf",
            size=None,
            updated_at=None,
        )

        self.assertTrue(
            prompt_applies_to_file(
                prompt_spec=prompt_spec,
                canvas_file=assignment_file,
                pdf_path=Path("/tmp/output/downloads/assignments/4517747_chp-6-1-6-2-work.pdf"),
            )
        )
        self.assertFalse(
            prompt_applies_to_file(
                prompt_spec=prompt_spec,
                canvas_file=class_note_file,
                pdf_path=Path("/tmp/output/downloads/4401267_note.pdf"),
            )
        )

    def test_should_skip_generation_uses_artifact_existence(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            response_path = root / "response.md"
            html_path = root / "response.html"
            pdf_path = root / "response.pdf"
            response_path.write_text("body", encoding="utf-8")
            html_path.write_text("<html></html>", encoding="utf-8")
            pdf_path.write_text("pdf", encoding="utf-8")

            canvas_file = CanvasFile(
                file_id=1,
                display_name="Alg 2 Trig H Chp 5.1 Note.docx",
                download_url="https://example.com/file.pdf",
                content_type="application/pdf",
                size=None,
                updated_at=None,
            )
            should_skip = should_skip_generation(
                canvas_file=canvas_file,
                prompt_spec=PROMPTS_BY_SLUG["study-guide"],
                response_path=response_path,
                response_html_path=html_path,
                response_pdf_path=pdf_path,
                generated_output_state=GeneratedOutputState(
                    path=root / "generated_output_state.json", processed={}
                ),
                force=False,
                force_generation=False,
                index=1,
                total=1,
            )
            self.assertTrue(should_skip)


if __name__ == "__main__":
    unittest.main()
