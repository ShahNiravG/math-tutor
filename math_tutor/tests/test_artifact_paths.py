from __future__ import annotations

import unittest
from pathlib import Path

from math_tutor.artifact_paths import build_prompt_paths
from math_tutor.prompt_catalog import PROMPTS_BY_SLUG


class ArtifactPathsTests(unittest.TestCase):
    def test_build_prompt_paths_for_study_guide(self) -> None:
        md_path, html_path, pdf_path, metadata_path = build_prompt_paths(
            responses_dir=Path("output/responses"),
            metadata_dir=Path("output/metadata"),
            stem="4401267_alg-2trig-h-chp-5-1-note-docx",
            prompt_spec=PROMPTS_BY_SLUG["study-guide"],
        )
        self.assertEqual(md_path, Path("output/responses/4401267_alg-2trig-h-chp-5-1-note-docx.md"))
        self.assertEqual(html_path, Path("output/responses/4401267_alg-2trig-h-chp-5-1-note-docx.html"))
        self.assertEqual(pdf_path, Path("output/responses/4401267_alg-2trig-h-chp-5-1-note-docx.pdf"))
        self.assertEqual(metadata_path, Path("output/metadata/4401267_alg-2trig-h-chp-5-1-note-docx.json"))

    def test_build_prompt_paths_for_non_study_guide(self) -> None:
        md_path, html_path, pdf_path, metadata_path = build_prompt_paths(
            responses_dir=Path("output/responses"),
            metadata_dir=Path("output/metadata"),
            stem="4401267_alg-2trig-h-chp-5-1-note-docx",
            prompt_spec=PROMPTS_BY_SLUG["mental-math-gpt5"],
        )
        self.assertEqual(md_path, Path("output/responses/4401267_alg-2trig-h-chp-5-1-note-docx__mental-math-gpt5.md"))
        self.assertEqual(html_path, Path("output/responses/4401267_alg-2trig-h-chp-5-1-note-docx__mental-math-gpt5.html"))
        self.assertEqual(pdf_path, Path("output/responses/4401267_alg-2trig-h-chp-5-1-note-docx__mental-math-gpt5.pdf"))
        self.assertEqual(metadata_path, Path("output/metadata/4401267_alg-2trig-h-chp-5-1-note-docx__mental-math-gpt5.json"))


if __name__ == "__main__":
    unittest.main()
