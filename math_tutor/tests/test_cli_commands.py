from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from math_tutor.cli_commands import (
    CliCommandContext,
    handle_print_command,
    process_saved_files,
    run_assignment_fetch_workflow,
    run_class_note_workflow,
    should_use_saved_fetch_shortcut,
)
from math_tutor.cli_runtime import build_output_layout
from math_tutor.prompt_catalog import PROMPTS_BY_SLUG
from math_tutor.state_store import FetchState, GeneratedOutputState


class CliCommandTests(unittest.TestCase):
    def test_handle_print_command_returns_false_when_no_print_flags_are_set(self) -> None:
        result = handle_print_command(
            output_dir=Path("/tmp/output"),
            print_all=False,
            print_prompt_slugs=None,
            chapter_filters=None,
            printer="Brother",
            dry_run=False,
        )

        self.assertFalse(result)

    def test_handle_print_command_dispatches_print_request(self) -> None:
        print_saved_prompt_pdfs = Mock()

        result = handle_print_command(
            output_dir=Path("/tmp/output"),
            print_all=False,
            print_prompt_slugs=["study-guide"],
            chapter_filters=["5.1"],
            printer="Brother",
            dry_run=True,
            print_saved_prompt_pdfs_fn=print_saved_prompt_pdfs,
        )

        self.assertTrue(result)
        print_saved_prompt_pdfs.assert_called_once()

    def test_should_use_saved_fetch_shortcut_for_assignment_chapter_with_saved_file(self) -> None:
        output_layout = build_output_layout(Path("/tmp/output"))
        context = CliCommandContext(
            output_dir=Path("/tmp/output"),
            output_layout=output_layout,
            fetch_state=FetchState(
                path=Path("/tmp/output/fetch_state.json"),
                fetched={
                    "10": {
                        "display_name": "Chp 5.1 work.pdf",
                        "pdf_path": "/tmp/output/downloads/assignments/4435419_chp-5-1-work.pdf",
                        "download_url": "https://example.com/10",
                        "content_type": "application/pdf",
                    }
                },
            ),
            generated_output_state=GeneratedOutputState(
                path=Path("/tmp/output/generated_output_state.json"),
                processed={},
            ),
            default_model="gpt-5.4",
            selected_prompts=(PROMPTS_BY_SLUG["study-guide"],),
            forced_prompt_slugs=set(),
            normalized_chapter_filters=["5.1"],
            force=False,
            force_generation=False,
            fetch_only=True,
            fetch_assignments=True,
            list_files=False,
            headful=False,
            limit=None,
            assignment_limit=1,
            course_url="https://example.com/course",
            login_url=None,
            site_dir=None,
            site_base_path="/site/",
            build_site_guided_learning=False,
            openai_api_key=None,
            gemini_client=None,
        )

        self.assertTrue(should_use_saved_fetch_shortcut(context))

    def test_process_saved_files_skips_browser_in_fetch_only_mode(self) -> None:
        output_layout = build_output_layout(Path("/tmp/output"))
        context = CliCommandContext(
            output_dir=Path("/tmp/output"),
            output_layout=output_layout,
            fetch_state=FetchState(path=Path("/tmp/output/fetch_state.json"), fetched={}),
            generated_output_state=GeneratedOutputState(
                path=Path("/tmp/output/generated_output_state.json"),
                processed={},
            ),
            default_model="gpt-5.4",
            selected_prompts=(PROMPTS_BY_SLUG["study-guide"],),
            forced_prompt_slugs=set(),
            normalized_chapter_filters=["5.1"],
            force=False,
            force_generation=False,
            fetch_only=True,
            fetch_assignments=False,
            list_files=False,
            headful=False,
            limit=1,
            assignment_limit=None,
            course_url="https://example.com/course",
            login_url=None,
            site_dir=None,
            site_base_path="/site/",
            build_site_guided_learning=False,
            openai_api_key=None,
            gemini_client=None,
        )
        files = [Mock(file_id=1)]

        with patch("math_tutor.cli_commands.process_file_batch", return_value={"1"}) as process_file_batch:
            with patch("math_tutor.cli_commands.sync_playwright") as sync_playwright:
                result = process_saved_files(
                    command_context=context,
                    files=files,
                    downloads_dir=output_layout.downloads_dir,
                    openai_client=None,
                )

        self.assertEqual(result, {"1"})
        process_file_batch.assert_called_once()
        sync_playwright.assert_not_called()

    def test_run_assignment_fetch_workflow_uses_manifest_covered_saved_files(self) -> None:
        output_layout = build_output_layout(Path("/tmp/output"))
        context = CliCommandContext(
            output_dir=Path("/tmp/output"),
            output_layout=output_layout,
            fetch_state=FetchState(path=Path("/tmp/output/fetch_state.json"), fetched={}),
            generated_output_state=GeneratedOutputState(
                path=Path("/tmp/output/generated_output_state.json"),
                processed={},
            ),
            default_model="gpt-5.4",
            selected_prompts=(PROMPTS_BY_SLUG["study-guide"],),
            forced_prompt_slugs=set(),
            normalized_chapter_filters=[],
            force=False,
            force_generation=False,
            fetch_only=True,
            fetch_assignments=True,
            list_files=False,
            headful=False,
            limit=None,
            assignment_limit=2,
            course_url="https://example.com/courses/4187",
            login_url=None,
            site_dir=None,
            site_base_path="/site/",
            build_site_guided_learning=False,
            openai_api_key=None,
            gemini_client=None,
        )
        saved_files = [Mock(file_id=10)]

        with patch(
            "math_tutor.cli_commands.list_canvas_assignment_entries",
            return_value=[("Chp 5.1 work", "https://example.com/assignments/1")],
        ):
            with patch("math_tutor.cli_commands.build_saved_assignment_files_for_names", return_value=saved_files):
                with patch("math_tutor.cli_commands.list_canvas_pdfs_from_assignments") as list_canvas_pdfs_from_assignments:
                    with patch("math_tutor.cli_commands.process_file_batch", return_value={"10"}) as process_file_batch:
                        result = run_assignment_fetch_workflow(
                            page=Mock(),
                            canvas_client=Mock(),
                            browser=Mock(),
                            command_context=context,
                        )

        self.assertEqual(result, {"10"})
        process_file_batch.assert_called_once()
        list_canvas_pdfs_from_assignments.assert_not_called()

    def test_run_assignment_fetch_workflow_logs_assignment_fetch_summary(self) -> None:
        output_layout = build_output_layout(Path("/tmp/output"))
        context = CliCommandContext(
            output_dir=Path("/tmp/output"),
            output_layout=output_layout,
            fetch_state=FetchState(path=Path("/tmp/output/fetch_state.json"), fetched={}),
            generated_output_state=GeneratedOutputState(
                path=Path("/tmp/output/generated_output_state.json"),
                processed={},
            ),
            default_model="gpt-5.4",
            selected_prompts=(PROMPTS_BY_SLUG["study-guide"],),
            forced_prompt_slugs=set(),
            normalized_chapter_filters=[],
            force=False,
            force_generation=False,
            fetch_only=True,
            fetch_assignments=True,
            list_files=False,
            headful=False,
            limit=None,
            assignment_limit=1,
            course_url="https://example.com/courses/4187",
            login_url=None,
            site_dir=None,
            site_base_path="/site/",
            build_site_guided_learning=False,
            openai_api_key=None,
            gemini_client=None,
        )
        assignment_file = Mock(file_id=10)

        with patch("math_tutor.cli_commands.discover_assignment_files", return_value=[assignment_file]):
            with patch("math_tutor.cli_commands.summarize_discovered_files") as summarize_discovered_files:
                with patch("math_tutor.cli_commands.process_file_batch", return_value={"10"}):
                    run_assignment_fetch_workflow(
                        page=Mock(),
                        canvas_client=Mock(),
                        browser=Mock(),
                        command_context=context,
                    )

        summarize_discovered_files.assert_called_once_with(
            files=[assignment_file],
            fetch_state=context.fetch_state,
            force=False,
        )

    def test_run_assignment_fetch_workflow_fetches_only_missing_manifest_entries(self) -> None:
        output_layout = build_output_layout(Path("/tmp/output"))
        context = CliCommandContext(
            output_dir=Path("/tmp/output"),
            output_layout=output_layout,
            fetch_state=FetchState(path=Path("/tmp/output/fetch_state.json"), fetched={}),
            generated_output_state=GeneratedOutputState(
                path=Path("/tmp/output/generated_output_state.json"),
                processed={},
            ),
            default_model="gpt-5.4",
            selected_prompts=(PROMPTS_BY_SLUG["study-guide"],),
            forced_prompt_slugs=set(),
            normalized_chapter_filters=[],
            force=False,
            force_generation=False,
            fetch_only=True,
            fetch_assignments=True,
            list_files=False,
            headful=False,
            limit=None,
            assignment_limit=2,
            course_url="https://example.com/courses/4187",
            login_url=None,
            site_dir=None,
            site_base_path="/site/",
            build_site_guided_learning=False,
            openai_api_key=None,
            gemini_client=None,
        )
        saved_file = Mock(file_id=10, display_name="4435419_chp-5-1-work.pdf")
        fetched_missing = Mock(file_id=11)
        assignment_entries = [
            ("Chp 5.1 work", "https://example.com/assignments/1"),
            ("Chp 11.4 note", "https://example.com/assignments/2"),
        ]

        with patch("math_tutor.cli_commands.list_canvas_assignment_entries", return_value=assignment_entries):
            with patch("math_tutor.cli_commands.build_saved_assignment_files_for_names", return_value=[saved_file]):
                with patch(
                    "math_tutor.cli_commands.list_canvas_pdfs_from_assignments",
                    return_value=[fetched_missing],
                ) as list_canvas_pdfs_from_assignments:
                    with patch("math_tutor.cli_commands.process_file_batch", return_value={"10", "11"}) as process_file_batch:
                        result = run_assignment_fetch_workflow(
                            page=Mock(),
                            canvas_client=Mock(),
                            browser=Mock(),
                            command_context=context,
                        )

        self.assertEqual(result, {"10", "11"})
        list_canvas_pdfs_from_assignments.assert_called_once()
        self.assertEqual(
            list_canvas_pdfs_from_assignments.call_args.kwargs["assignment_entries"],
            [("Chp 11.4 note", "https://example.com/assignments/2")],
        )
        self.assertEqual(process_file_batch.call_args.kwargs["files"], [saved_file, fetched_missing])

    def test_run_class_note_workflow_reuses_optimized_assignment_discovery(self) -> None:
        output_layout = build_output_layout(Path("/tmp/output"))
        context = CliCommandContext(
            output_dir=Path("/tmp/output"),
            output_layout=output_layout,
            fetch_state=FetchState(path=Path("/tmp/output/fetch_state.json"), fetched={}),
            generated_output_state=GeneratedOutputState(
                path=Path("/tmp/output/generated_output_state.json"),
                processed={},
            ),
            default_model="gpt-5.4",
            selected_prompts=(PROMPTS_BY_SLUG["study-guide"],),
            forced_prompt_slugs=set(),
            normalized_chapter_filters=[],
            force=False,
            force_generation=False,
            fetch_only=True,
            fetch_assignments=False,
            list_files=False,
            headful=False,
            limit=None,
            assignment_limit=None,
            course_url="https://example.com/courses/4187",
            login_url=None,
            site_dir=None,
            site_base_path="/site/",
            build_site_guided_learning=False,
            openai_api_key=None,
            gemini_client=None,
        )
        class_note = Mock(file_id=1, display_name="Alg 2 Trig H Chp 5.1 Note.docx")
        assignment_file = Mock(file_id=10)

        with patch("math_tutor.cli_commands.list_canvas_pdfs_from_ui", return_value=[class_note]):
            with patch("math_tutor.cli_commands.discover_assignment_files", return_value=[assignment_file]) as discover_assignment_files:
                with patch(
                    "math_tutor.cli_commands.process_file_batch",
                    side_effect=[{"1"}, {"10"}],
                ) as process_file_batch:
                    result = run_class_note_workflow(
                        page=Mock(),
                        canvas_client=Mock(),
                        browser=Mock(),
                        command_context=context,
                    )

        self.assertEqual(result, {"1", "10"})
        discover_assignment_files.assert_called_once()
        self.assertEqual(process_file_batch.call_count, 2)


if __name__ == "__main__":
    unittest.main()
