from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from math_tutor.mcq_prompts import MCQSourceConfig
from math_tutor.mcq_workflow import process_mcq_file


class MCQWorkflowTests(unittest.TestCase):
    def test_process_mcq_file_writes_markdown_html_and_pdf_via_injected_helpers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_md = temp_path / "4401267_alg-2trig-h-chp-5-1-note-docx__mental-math-gpt5.md"
            source_md.write_text("1. 2+2", encoding="utf-8")
            pdf_calls: list[tuple[Path, Path]] = []

            process_mcq_file(
                source_md=source_md,
                source_config=MCQSourceConfig(
                    "__mental-math-gpt5.md",
                    "__mental-math-gpt5-mcq",
                    "gpt",
                    "mental_math",
                ),
                responses_dir=temp_path,
                openai_client=None,
                gemini_client=None,
                force=True,
                build_prompt_fn=lambda **kwargs: f"prompt::{kwargs['questions_text']}",
                generate_mcq_text_fn=lambda **kwargs: "1.\n(A) 4\n(B) 5\n(C) 6\n(D) 7\nAnswer: A",
                build_html_fn=lambda stem, markdown: f"<html><body>{stem}::{markdown}</body></html>",
                build_pdf_fn=lambda **kwargs: pdf_calls.append(
                    (kwargs["response_html_path"], kwargs["response_pdf_path"])
                ),
            )

            markdown_path = temp_path / "4401267_alg-2trig-h-chp-5-1-note-docx__mental-math-gpt5-mcq.md"
            html_path = temp_path / "4401267_alg-2trig-h-chp-5-1-note-docx__mental-math-gpt5-mcq.html"

            self.assertTrue(markdown_path.exists())
            self.assertTrue(html_path.exists())
            self.assertIn("Answer: A", markdown_path.read_text(encoding="utf-8"))
            self.assertIn("mental-math-gpt5-mcq", html_path.read_text(encoding="utf-8"))
            self.assertEqual(len(pdf_calls), 1)

    def test_process_mcq_file_skips_when_output_exists_and_not_forced(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            source_md = temp_path / "4401267_alg-2trig-h-chp-5-1-note-docx__mental-math-gpt5.md"
            source_md.write_text("1. 2+2", encoding="utf-8")
            existing_output = temp_path / "4401267_alg-2trig-h-chp-5-1-note-docx__mental-math-gpt5-mcq.md"
            existing_output.write_text("existing", encoding="utf-8")
            invoked = {"called": False}

            process_mcq_file(
                source_md=source_md,
                source_config=MCQSourceConfig(
                    "__mental-math-gpt5.md",
                    "__mental-math-gpt5-mcq",
                    "gpt",
                    "mental_math",
                ),
                responses_dir=temp_path,
                openai_client=None,
                gemini_client=None,
                force=False,
                generate_mcq_text_fn=lambda **kwargs: invoked.__setitem__("called", True),
            )

            self.assertFalse(invoked["called"])


if __name__ == "__main__":
    unittest.main()
