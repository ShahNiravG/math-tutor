from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from math_tutor.prompt_saved_outputs import print_saved_prompt_pdfs


class PromptSavedOutputsTests(unittest.TestCase):
    def test_print_saved_prompt_pdfs_dry_run_reports_matching_targets(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            responses_dir = output_dir / "responses"
            responses_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = responses_dir / "study-guide.pdf"
            pdf_path.write_text("pdf", encoding="utf-8")

            (output_dir / "fetch_state.json").write_text(
                json.dumps(
                    {
                        "fetched": {
                            "1": {
                                "display_name": "Alg 2 Trig H Chp 5.1 Note.docx",
                                "pdf_path": str(output_dir / "downloads" / "note.pdf"),
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (output_dir / "generated_output_state.json").write_text(
                json.dumps(
                    {
                        "processed": {
                            "1": {
                                "study-guide": {
                                    "display_name": "Alg 2 Trig H Chp 5.1 Note.docx",
                                    "prompt_title": "Study Guide",
                                    "response_pdf_path": str(pdf_path),
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch("builtins.print") as print_mock:
                print_saved_prompt_pdfs(
                    output_dir=output_dir,
                    prompt_slugs=("study-guide",),
                    chapter_filters=["5.1"],
                    printer="Brother",
                    dry_run=True,
                )

        printed_text = "\n".join(
            " ".join(str(arg) for arg in call.args)
            for call in print_mock.call_args_list
        )
        self.assertIn("Dry run", printed_text)
        self.assertIn("study-guide.pdf", printed_text)


if __name__ == "__main__":
    unittest.main()
