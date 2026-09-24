from __future__ import annotations

import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from math_tutor.cli_context import build_command_context


class CliContextTests(unittest.TestCase):
    def test_calculus_fetch_only_does_not_require_a_generation_prompt(self) -> None:
        with TemporaryDirectory() as temp_dir:
            args = Namespace(
                course_id="ap-calculus-ab",
                prompt_slugs=None,
                force_prompt_slugs=None,
                chapter_filters=None,
                fetch_only=True,
                fetch_assignments=False,
                default_model="gpt-5.4",
                force=False,
                force_generation=False,
                list_files=False,
                headful=False,
                limit=None,
                assignment_limit=None,
                course_url=None,
                login_url=None,
                site_dir=None,
                site_base_path="/site/",
                build_site_guided_learning=False,
                dry_run=False,
            )

            context = build_command_context(
                args=args,
                output_dir=Path(temp_dir) / "output",
                log=lambda message: None,
            )

            self.assertEqual(context.selected_prompts, ())
            self.assertEqual(context.normalized_chapter_filters, [])
            self.assertIsNone(context.openai_api_key)
            self.assertIsNone(context.gemini_client)

    def test_dry_run_does_not_resolve_model_credentials_or_clients(self) -> None:
        with TemporaryDirectory() as temp_dir:
            args = Namespace(
                course_id="ap-calculus-ab",
                prompt_slugs=["study-guide"],
                force_prompt_slugs=None,
                chapter_filters=["2"],
                fetch_only=False,
                fetch_assignments=False,
                default_model="gpt-5.4",
                force=False,
                force_generation=False,
                list_files=False,
                headful=False,
                limit=None,
                assignment_limit=None,
                course_url=None,
                login_url=None,
                site_dir=None,
                site_base_path="/site/",
                build_site_guided_learning=False,
                dry_run=True,
            )

            with (
                patch("math_tutor.cli_context.resolve_openai_api_key") as resolve_key,
                patch("math_tutor.cli_context.initialize_gemini_client") as initialize_gemini,
            ):
                context = build_command_context(
                    args=args,
                    output_dir=Path(temp_dir) / "output",
                    log=lambda message: None,
                )

            self.assertIsNone(context.openai_api_key)
            self.assertIsNone(context.gemini_client)
            resolve_key.assert_not_called()
            initialize_gemini.assert_not_called()

    def test_build_command_context_populates_expected_fields(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "output"
            args = Namespace(
                course_id="ap-calculus-ab",
                prompt_slugs=["study-guide"],
                force_prompt_slugs=["study-guide"],
                chapter_filters=["3"],
                fetch_only=True,
                fetch_assignments=False,
                default_model="gpt-5.4",
                force=False,
                force_generation=False,
                list_files=False,
                headful=False,
                limit=3,
                assignment_limit=2,
                course_url=None,
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

            calculus_output = output_dir / "courses" / "ap-calculus-ab"
            self.assertEqual(context.output_dir, calculus_output)
            self.assertEqual(context.course_id, "ap-calculus-ab")
            self.assertEqual(
                context.course_url,
                "https://mitty.instructure.com/courses/4446",
            )
            self.assertEqual(context.fetch_state.path, calculus_output / "fetch_state.json")
            self.assertEqual(context.default_model, "gpt-5.4")
            self.assertEqual(context.limit, 3)
            self.assertEqual(context.selected_prompts[0].slug, "study-guide")
            self.assertEqual(context.forced_prompt_slugs, {"study-guide"})
            self.assertEqual(context.normalized_chapter_filters, ["3"])
            self.assertIsNone(context.gemini_client)
            initialize_gemini_client.assert_not_called()
            self.assertTrue(context.output_layout.downloads_dir.is_dir())


if __name__ == "__main__":
    unittest.main()
