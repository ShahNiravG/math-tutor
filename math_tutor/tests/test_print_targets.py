from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from math_tutor.print_targets import collect_print_targets
from math_tutor.state_store import FetchState, GeneratedOutputState


class PrintTargetsTests(unittest.TestCase):
    def test_collect_print_targets_filters_by_chapter_and_prompt(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            response_pdf = root / "response.pdf"
            response_pdf.write_text("pdf", encoding="utf-8")

            fetch_state = FetchState(
                path=root / "fetch_state.json",
                fetched={
                    "4401267": {
                        "display_name": "Alg 2 Trig H Chp 5.1 Note.docx",
                        "pdf_path": str(root / "class-note.pdf"),
                    }
                },
            )
            generated_output_state = GeneratedOutputState(
                path=root / "generated_output_state.json",
                processed={
                    "4401267": {
                        "mental-math-gpt5": {
                            "display_name": "Alg 2 Trig H Chp 5.1 Note.docx",
                            "prompt_title": "Mental Math (GPT-5.4)",
                            "response_pdf_path": str(response_pdf),
                        }
                    }
                },
            )

            targets = collect_print_targets(
                fetch_state=fetch_state,
                generated_output_state=generated_output_state,
                prompt_slugs=("mental-math-gpt5",),
                chapter_filters=["5"],
                pretty_title=lambda name: name,
            )

            self.assertEqual(len(targets), 1)
            self.assertEqual(targets[0].chapter_label, "Chapter 5.1")
            self.assertEqual(targets[0].prompt_title, "Mental Math (GPT-5.4)")


if __name__ == "__main__":
    unittest.main()
