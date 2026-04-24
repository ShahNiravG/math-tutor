from __future__ import annotations

import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from math_tutor.cli_context import build_command_context


class CliContextTests(unittest.TestCase):
    def test_build_command_context_populates_expected_fields(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            args = Namespace(
                prompt_slugs=["study-guide"],
                force_prompt_slugs=["study-guide"],
                chapter_filters=["5.1"],
                fetch_only=True,
                fetch_assignments=False,
                default_model="gpt-5.4",
                force=False,
                force_generation=False,
                list_files=False,
                headful=False,
                limit=3,
                assignment_limit=2,
                course_url="https://example.com/course",
                login_url=None,
                site_dir=None,
                site_base_path="/site/",
                build_site_guided_learning=False,
                dry_run=False,
            )

            with patch("math_tutor.cli_context.initialize_gemini_client", return_value="gemini-client") as initialize_gemini_client:
                context = build_command_context(
                    args=args,
                    output_dir=output_dir,
                    log=lambda message: None,
                )

            self.assertEqual(context.output_dir, output_dir)
            self.assertEqual(context.default_model, "gpt-5.4")
            self.assertEqual(context.limit, 3)
            self.assertEqual(context.selected_prompts[0].slug, "study-guide")
            self.assertEqual(context.forced_prompt_slugs, {"study-guide"})
            self.assertEqual(context.normalized_chapter_filters, ["5.1"])
            self.assertIsNone(context.gemini_client)
            initialize_gemini_client.assert_not_called()
            self.assertTrue(context.output_layout.downloads_dir.is_dir())


if __name__ == "__main__":
    unittest.main()
