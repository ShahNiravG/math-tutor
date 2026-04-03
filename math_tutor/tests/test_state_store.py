from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from math_tutor.state_store import load_generated_output_state, normalize_generated_output_state


class StateStoreTests(unittest.TestCase):
    def test_load_generated_output_state_only_reads_canonical_filename(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            legacy_path = root / "openai_state.json"
            legacy_path.write_text('{"processed": {"4401267": {"study-guide": {"response_path": "legacy.md"}}}}', encoding="utf-8")

            state = load_generated_output_state(root / "generated_output_state.json")

            self.assertEqual(state.path, root / "generated_output_state.json")
            self.assertEqual(state.processed, {})

    def test_normalize_generated_output_state_wraps_legacy_study_guide_shape(self) -> None:
        normalized = normalize_generated_output_state(
            {
                "4401267": {
                    "display_name": "Alg 2 Trig H Chp 5.1 Note.docx",
                    "response_path": "output/responses/example.md",
                }
            }
        )

        self.assertIn("4401267", normalized)
        self.assertIn("study-guide", normalized["4401267"])
        self.assertEqual(
            normalized["4401267"]["study-guide"]["prompt_title"],
            "Study Guide",
        )

    def test_normalize_generated_output_state_fills_prompt_metadata_for_nested_map(self) -> None:
        normalized = normalize_generated_output_state(
            {
                "4401267": {
                    "mental-math-gpt5": {
                        "response_path": "output/responses/mm.md",
                    }
                }
            }
        )

        entry = normalized["4401267"]["mental-math-gpt5"]
        self.assertEqual(entry["prompt_slug"], "mental-math-gpt5")
        self.assertEqual(entry["prompt_title"], "Mental Math (GPT-5.4)")

    def test_normalize_generated_output_state_infers_provider_from_model(self) -> None:
        normalized = normalize_generated_output_state(
            {
                "4401267": {
                    "mental-math-gpt5": {
                        "model": "gpt-5.4",
                        "response_id": "resp_123",
                    }
                }
            }
        )

        entry = normalized["4401267"]["mental-math-gpt5"]
        self.assertEqual(entry["model"], "gpt-5.4")
        self.assertEqual(entry["response_id"], "resp_123")


if __name__ == "__main__":
    unittest.main()
