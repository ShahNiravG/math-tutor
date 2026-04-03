from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from math_tutor.canvas_course import CanvasFile
from math_tutor.prompt_catalog import PROMPTS_BY_SLUG
from math_tutor.prompt_generation import PromptResponseResult
from math_tutor.prompt_output_store import persist_prompt_output
from math_tutor.state_store import GeneratedOutputState


class PromptOutputStoreTests(unittest.TestCase):
    def test_persist_prompt_output_writes_artifacts_and_updates_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            pdf_path = root / "source.pdf"
            pdf_path.write_bytes(b"pdf")
            response_path = root / "response.md"
            response_html_path = root / "response.html"
            response_pdf_path = root / "response.pdf"
            metadata_path = root / "metadata.json"
            state_path = root / "generated_output_state.json"
            generated_output_state = GeneratedOutputState(path=state_path, processed={})
            canvas_file = CanvasFile(
                file_id=1,
                display_name="Alg 2 Trig H Chp 5.1 Note.docx",
                download_url="https://example.com/file.pdf",
                content_type="application/pdf",
                size=None,
                updated_at=None,
            )

            with patch("math_tutor.prompt_output_store.build_response_pdf") as build_pdf:
                persist_prompt_output(
                    canvas_file=canvas_file,
                    prompt_spec=PROMPTS_BY_SLUG["study-guide"],
                    pdf_path=pdf_path,
                    response_path=response_path,
                    response_html_path=response_html_path,
                    response_pdf_path=response_pdf_path,
                    metadata_path=metadata_path,
                    result=PromptResponseResult(output_text="hello", response_id="resp_123"),
                    effective_model="gpt-5.4",
                    generated_output_state=generated_output_state,
                    pdf_browser=object(),
                )

            self.assertEqual(response_path.read_text(encoding="utf-8"), "hello")
            self.assertTrue(response_html_path.exists())
            self.assertTrue(metadata_path.exists())
            self.assertIn("1", generated_output_state.processed)
            self.assertEqual(
                generated_output_state.processed["1"]["study-guide"]["model"],
                "gpt-5.4",
            )
            saved_state = json.loads(state_path.read_text(encoding="utf-8"))
            self.assertIn("processed", saved_state)
            build_pdf.assert_called_once()


if __name__ == "__main__":
    unittest.main()
