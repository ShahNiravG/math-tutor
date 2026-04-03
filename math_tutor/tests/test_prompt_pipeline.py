from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from math_tutor.canvas_course import CanvasFile
from math_tutor.prompt_catalog import PROMPTS_BY_SLUG
from math_tutor.prompt_saved_outputs import should_skip_generation
from math_tutor.state_store import GeneratedOutputState


class PromptPipelineTests(unittest.TestCase):
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
