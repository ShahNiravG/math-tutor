from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from math_tutor.artifact_name_migration import migrate_output_dir
from math_tutor.state_store import canonical_generated_output_state_path


class ArtifactNameMigrationTests(unittest.TestCase):
    def test_migrate_output_dir_renames_legacy_study_guide_files_and_updates_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            responses_dir = output_dir / "responses"
            metadata_dir = output_dir / "metadata"
            responses_dir.mkdir(parents=True)
            metadata_dir.mkdir(parents=True)

            old_stem = "4401267_alg-2trig-h-chp-5-1-note-docx"
            old_md = responses_dir / f"{old_stem}.md"
            old_html = responses_dir / f"{old_stem}.html"
            old_pdf = responses_dir / f"{old_stem}.pdf"
            old_meta = metadata_dir / f"{old_stem}.json"
            for path in (old_md, old_html, old_pdf):
                path.write_text(path.suffix, encoding="utf-8")

            old_meta.write_text(
                json.dumps(
                    {
                        "canvas_file_id": 4401267,
                        "display_name": "Alg 2 Trig H Chp 5.1 Note.docx",
                        "prompt_slug": "study-guide",
                        "prompt_title": "Study Guide",
                        "model": "gpt-4.1",
                        "response_path": str(old_md),
                        "response_html_path": str(old_html),
                        "response_pdf_path": str(old_pdf),
                    }
                ),
                encoding="utf-8",
            )

            state_path = canonical_generated_output_state_path(output_dir)
            state_path.write_text(
                json.dumps(
                    {
                        "processed": {
                            "4401267": {
                                "study-guide": {
                                    "display_name": "Alg 2 Trig H Chp 5.1 Note.docx",
                                    "prompt_slug": "study-guide",
                                    "prompt_title": "Study Guide",
                                    "response_path": str(old_md),
                                    "response_html_path": str(old_html),
                                    "response_pdf_path": str(old_pdf),
                                    "metadata_path": str(old_meta),
                                    "model": "gpt-4.1",
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            migrated = migrate_output_dir(output_dir)

            self.assertEqual(migrated, 1)
            new_stem = "4401267_alg-2-trig-h-chp-5-1-note__study-guide-gpt4"
            self.assertFalse(old_md.exists())
            self.assertTrue((responses_dir / f"{new_stem}.md").exists())
            self.assertTrue((responses_dir / f"{new_stem}.html").exists())
            self.assertTrue((responses_dir / f"{new_stem}.pdf").exists())
            self.assertTrue((metadata_dir / f"{new_stem}.json").exists())

            state = json.loads(state_path.read_text(encoding="utf-8"))
            entry = state["processed"]["4401267"]["study-guide"]
            self.assertTrue(entry["response_path"].endswith(f"{new_stem}.md"))
            self.assertEqual(entry["model"], "gpt-4.1")

    def test_migrate_output_dir_infers_gpt4_for_legacy_study_guide_without_model(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            responses_dir = output_dir / "responses"
            responses_dir.mkdir(parents=True)

            old_stem = "4401268_alg-2trig-h-chp-5-2-note-docx"
            old_md = responses_dir / f"{old_stem}.md"
            old_html = responses_dir / f"{old_stem}.html"
            old_pdf = responses_dir / f"{old_stem}.pdf"
            for path in (old_md, old_html, old_pdf):
                path.write_text(path.suffix, encoding="utf-8")

            state_path = canonical_generated_output_state_path(output_dir)
            state_path.write_text(
                json.dumps(
                    {
                        "processed": {
                            "4401268": {
                                "study-guide": {
                                    "display_name": "Alg 2 Trig H Chp 5.2 Note.docx",
                                    "prompt_slug": "study-guide",
                                    "prompt_title": "Study Guide",
                                    "response_path": str(old_md),
                                    "response_html_path": str(old_html),
                                    "response_pdf_path": str(old_pdf),
                                    "metadata_path": "",
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            migrated = migrate_output_dir(output_dir)

            self.assertEqual(migrated, 1)
            state = json.loads(state_path.read_text(encoding="utf-8"))
            entry = state["processed"]["4401268"]["study-guide"]
            self.assertEqual(entry["model"], "gpt-4.1")
            self.assertTrue(entry["response_path"].endswith("4401268_alg-2-trig-h-chp-5-2-note__study-guide-gpt4.md"))

    def test_migrate_output_dir_renames_double_suffixed_mcq_files_and_updates_state(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            responses_dir = output_dir / "responses"
            metadata_dir = output_dir / "metadata"
            responses_dir.mkdir(parents=True)
            metadata_dir.mkdir(parents=True)

            stem = "4697228_alg-2trig-h-chp-8-1-note-docx__mental-math-gpt5-mcq-gpt5"
            old_md = responses_dir / f"{stem}.md"
            old_html = responses_dir / f"{stem}.html"
            old_pdf = responses_dir / f"{stem}.pdf"
            old_meta = metadata_dir / f"{stem}.json"
            for path in (old_md, old_html, old_pdf):
                path.write_text(path.suffix, encoding="utf-8")
            old_meta.write_text(
                json.dumps(
                    {
                        "canvas_file_id": 4697228,
                        "display_name": "alg 2trig_h chp 8.1 note.docx.pdf",
                        "prompt_slug": "mental-math-gpt5-mcq",
                        "prompt_title": "Mental Math MCQ (GPT-5.4)",
                        "model": "gpt-5.4",
                        "response_path": str(old_md),
                        "response_html_path": str(old_html),
                        "response_pdf_path": str(old_pdf),
                    }
                ),
                encoding="utf-8",
            )

            state_path = canonical_generated_output_state_path(output_dir)
            state_path.write_text(
                json.dumps(
                    {
                        "processed": {
                            "4697228": {
                                "mental-math-gpt5-mcq": {
                                    "display_name": "alg 2trig_h chp 8.1 note.docx.pdf",
                                    "prompt_slug": "mental-math-gpt5-mcq",
                                    "prompt_title": "Mental Math MCQ (GPT-5.4)",
                                    "response_path": str(old_md),
                                    "response_html_path": str(old_html),
                                    "response_pdf_path": str(old_pdf),
                                    "metadata_path": str(old_meta),
                                    "model": "gpt-5.4",
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            migrated = migrate_output_dir(output_dir)

            self.assertEqual(migrated, 1)
            new_stem = "4697228_alg-2trig-h-chp-8-1-note-docx__mental-math-gpt5-mcq"
            self.assertFalse(old_md.exists())
            self.assertTrue((responses_dir / f"{new_stem}.md").exists())
            self.assertTrue((responses_dir / f"{new_stem}.html").exists())
            self.assertTrue((responses_dir / f"{new_stem}.pdf").exists())
            self.assertTrue((metadata_dir / f"{new_stem}.json").exists())

            state = json.loads(state_path.read_text(encoding="utf-8"))
            entry = state["processed"]["4697228"]["mental-math-gpt5-mcq"]
            self.assertTrue(entry["response_path"].endswith(f"{new_stem}.md"))
            self.assertEqual(entry["model"], "gpt-5.4")


if __name__ == "__main__":
    unittest.main()
