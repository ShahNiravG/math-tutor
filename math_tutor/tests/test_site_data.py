from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from math_tutor.site_data import load_records


class SiteDataTests(unittest.TestCase):
    def test_load_records_skips_assignment_downloads_and_reads_prompt_markdown(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            responses_dir = output_dir / "responses"
            responses_dir.mkdir(parents=True, exist_ok=True)
            response_path = responses_dir / "study-guide.md"
            response_path.write_text("summary text", encoding="utf-8")

            (output_dir / "fetch_state.json").write_text(
                json.dumps(
                    {
                        "fetched": {
                            "1": {
                                "display_name": "Alg 2 Trig H Chp 5.1 Note.docx",
                                "pdf_path": str(output_dir / "downloads" / "note.pdf"),
                                "download_url": "https://example.com/1",
                            },
                            "2": {
                                "display_name": "Alg 2 Trig H Chp 5.2 Note.docx",
                                "pdf_path": str(output_dir / "downloads" / "assignments" / "5.2.pdf"),
                                "download_url": "https://example.com/2",
                            },
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
                                    "response_path": str(response_path),
                                    "response_html_path": str(responses_dir / "study-guide.html"),
                                    "response_pdf_path": "",
                                    "metadata_path": "",
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            records = load_records(output_dir)

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].file_id, "1")
            self.assertEqual(records[0].prompt_outputs[0].response_markdown, "summary text")


if __name__ == "__main__":
    unittest.main()
