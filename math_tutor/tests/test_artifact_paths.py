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
            model_name="gpt-4.1",
        )
        self.assertEqual(md_path, Path("output/responses/4401267_alg-2trig-h-chp-5-1-note-docx__study-guide-gpt4.md"))
        self.assertEqual(html_path, Path("output/responses/4401267_alg-2trig-h-chp-5-1-note-docx__study-guide-gpt4.html"))
        self.assertEqual(pdf_path, Path("output/responses/4401267_alg-2trig-h-chp-5-1-note-docx__study-guide-gpt4.pdf"))
        self.assertEqual(metadata_path, Path("output/metadata/4401267_alg-2trig-h-chp-5-1-note-docx__study-guide-gpt4.json"))

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

    def test_build_prompt_paths_for_default_gpt_prompt_uses_explicit_model_suffix(self) -> None:
        md_path, html_path, pdf_path, metadata_path = build_prompt_paths(
            responses_dir=Path("output/responses"),
            metadata_dir=Path("output/metadata"),
            stem="4401267_alg-2trig-h-chp-5-1-note-docx",
            prompt_spec=PROMPTS_BY_SLUG["inspiring-videos"],
            model_name="gpt-5.4",
        )
        self.assertEqual(md_path, Path("output/responses/4401267_alg-2trig-h-chp-5-1-note-docx__inspiring-videos-gpt5.md"))
        self.assertEqual(html_path, Path("output/responses/4401267_alg-2trig-h-chp-5-1-note-docx__inspiring-videos-gpt5.html"))
        self.assertEqual(pdf_path, Path("output/responses/4401267_alg-2trig-h-chp-5-1-note-docx__inspiring-videos-gpt5.pdf"))
        self.assertEqual(metadata_path, Path("output/metadata/4401267_alg-2trig-h-chp-5-1-note-docx__inspiring-videos-gpt5.json"))

    def test_build_prompt_paths_for_already_model_specific_prompt_keeps_existing_slug(self) -> None:
        md_path, html_path, pdf_path, metadata_path = build_prompt_paths(
            responses_dir=Path("output/responses"),
            metadata_dir=Path("output/metadata"),
            stem="4401267_alg-2trig-h-chp-5-1-note-docx",
            prompt_spec=PROMPTS_BY_SLUG["study-guide-gemini"],
            model_name="gpt-4.1",
        )
        self.assertEqual(md_path, Path("output/responses/4401267_alg-2trig-h-chp-5-1-note-docx__study-guide-gemini.md"))
        self.assertEqual(html_path, Path("output/responses/4401267_alg-2trig-h-chp-5-1-note-docx__study-guide-gemini.html"))
        self.assertEqual(pdf_path, Path("output/responses/4401267_alg-2trig-h-chp-5-1-note-docx__study-guide-gemini.pdf"))
        self.assertEqual(metadata_path, Path("output/metadata/4401267_alg-2trig-h-chp-5-1-note-docx__study-guide-gemini.json"))

    def test_build_prompt_paths_for_model_specific_mcq_prompt_does_not_duplicate_model_suffix(self) -> None:
        md_path, html_path, pdf_path, metadata_path = build_prompt_paths(
            responses_dir=Path("output/responses"),
            metadata_dir=Path("output/metadata"),
            stem="4697228_alg-2trig-h-chp-8-1-note-docx",
            prompt_spec=PROMPTS_BY_SLUG["mental-math-gpt5-mcq"],
            model_name="gpt-5.4",
        )
        self.assertEqual(md_path, Path("output/responses/4697228_alg-2trig-h-chp-8-1-note-docx__mental-math-gpt5-mcq.md"))
        self.assertEqual(html_path, Path("output/responses/4697228_alg-2trig-h-chp-8-1-note-docx__mental-math-gpt5-mcq.html"))
        self.assertEqual(pdf_path, Path("output/responses/4697228_alg-2trig-h-chp-8-1-note-docx__mental-math-gpt5-mcq.pdf"))
        self.assertEqual(metadata_path, Path("output/metadata/4697228_alg-2trig-h-chp-8-1-note-docx__mental-math-gpt5-mcq.json"))


if __name__ == "__main__":
    unittest.main()
