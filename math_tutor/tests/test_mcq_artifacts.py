from __future__ import annotations

import unittest
from pathlib import Path

from math_tutor.mcq_artifacts import build_mcq_html, build_mcq_output_paths


class MCQArtifactsTests(unittest.TestCase):
    def test_build_mcq_output_paths_uses_base_stem_and_slug(self) -> None:
        paths = build_mcq_output_paths(
            source_md=Path("4401267_alg-2trig-h-chp-5-1-note-docx__mental-math-gpt5.md"),
            mcq_slug="__mental-math-gpt5-mcq",
            responses_dir=Path("/tmp/responses"),
        )

        self.assertEqual(paths.output_stem, "4401267_alg-2trig-h-chp-5-1-note-docx__mental-math-gpt5-mcq")
        self.assertEqual(paths.markdown_path, Path("/tmp/responses/4401267_alg-2trig-h-chp-5-1-note-docx__mental-math-gpt5-mcq.md"))

    def test_build_mcq_html_renders_title_and_copy_button(self) -> None:
        html = build_mcq_html("4401267_alg-2trig-h-chp-5-1-note-docx__mental-math-gpt5-mcq", "1.\n(A) 1")

        self.assertIn("MCQ Options", html)
        self.assertIn("copy-q-btn", html)
        self.assertIn("mental-math-gpt5-mcq", html)


if __name__ == "__main__":
    unittest.main()
