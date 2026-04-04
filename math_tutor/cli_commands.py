"""High-level command orchestration helpers for the operator CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright

from math_tutor.canvas_course import (
    build_canvas_client,
    is_pdf_by_name,
    list_canvas_pdfs_from_assignments,
    list_canvas_pdfs_from_ui,
    matches_target_pdf,
    perform_login,
    summarize_discovered_files,
)
from math_tutor.cli_generation import build_openai_generation_client
from math_tutor.cli_runtime import (
    OutputLayout,
    build_saved_assignment_files,
    build_saved_class_note_files,
    display_name_matches_chapter_filters,
    needs_pdf_browser,
)
from math_tutor.cli_workflows import FileBatchContext, process_file_batch
from math_tutor.prompt_catalog import PRINTABLE_PROMPT_SLUGS, PromptSpec
from math_tutor.prompt_saved_outputs import print_saved_prompt_pdfs
from math_tutor.state_store import FetchState, GeneratedOutputState


@dataclass(frozen=True)
class CliCommandContext:
    output_dir: Path
    output_layout: OutputLayout
    fetch_state: FetchState
    generated_output_state: GeneratedOutputState
    default_model: str
    selected_prompts: tuple[PromptSpec, ...]
    forced_prompt_slugs: set[str]
    normalized_chapter_filters: list[str]
    force: bool
    force_generation: bool
    fetch_only: bool
    fetch_assignments: bool
    list_files: bool
    headful: bool
    limit: int | None
    assignment_limit: int | None
    course_url: str
    login_url: str | None
    site_dir: str | None
    site_base_path: str
    build_site_guided_learning: bool
    openai_api_key: str | None
    gemini_client: Any


def handle_print_command(
    *,
    output_dir: Path,
    print_all: bool,
    print_prompt_slugs: list[str] | None,
    chapter_filters: list[str] | None,
    printer: str,
    dry_run: bool,
    print_saved_prompt_pdfs_fn: Any = print_saved_prompt_pdfs,
) -> bool:
    if not (print_all or print_prompt_slugs):
        return False

    prompt_slugs = PRINTABLE_PROMPT_SLUGS if print_all else tuple(print_prompt_slugs or [])
    print_saved_prompt_pdfs_fn(
        output_dir=output_dir,
        prompt_slugs=prompt_slugs,
        chapter_filters=chapter_filters or [],
        printer=printer,
        dry_run=dry_run,
    )
    return True


def run_skip_fetch_workflow(command_context: CliCommandContext) -> set[str]:
    if command_context.fetch_assignments:
        skip_fetch_files = build_saved_assignment_files(
            fetch_state=command_context.fetch_state,
            assignments_dir=command_context.output_layout.assignments_dir,
            normalized_chapter_filters=command_context.normalized_chapter_filters,
            limit=command_context.assignment_limit or command_context.limit,
        )
        print(f"Found {len(skip_fetch_files)} already-fetched assignment file(s).", flush=True)
        downloads_dir = command_context.output_layout.assignments_dir
    else:
        skip_fetch_files = build_saved_class_note_files(
            fetch_state=command_context.fetch_state,
            assignments_dir=command_context.output_layout.assignments_dir,
            normalized_chapter_filters=command_context.normalized_chapter_filters,
            limit=command_context.limit,
        )
        print(f"Found {len(skip_fetch_files)} already-fetched class note file(s).", flush=True)
        downloads_dir = command_context.output_layout.downloads_dir
    openai_client = build_openai_generation_client(command_context.openai_api_key)

    if needs_pdf_browser(command_context.selected_prompts):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=not command_context.headful)
            try:
                return process_file_batch(
                    files=skip_fetch_files,
                    batch_context=FileBatchContext(
                        canvas_client=None,
                        openai_client=openai_client,
                        gemini_client=command_context.gemini_client,
                        pdf_browser=browser,
                        downloads_dir=downloads_dir,
                        responses_dir=command_context.output_layout.responses_dir,
                        metadata_dir=command_context.output_layout.metadata_dir,
                        fetch_state=command_context.fetch_state,
                        generated_output_state=command_context.generated_output_state,
                        default_model=command_context.default_model,
                        prompts=command_context.selected_prompts,
                        forced_prompt_slugs=command_context.forced_prompt_slugs,
                        force=command_context.force,
                        fetch_only=False,
                        force_generation=command_context.force_generation,
                    ),
                )
            finally:
                browser.close()

    return process_file_batch(
        files=skip_fetch_files,
        batch_context=FileBatchContext(
            canvas_client=None,
            openai_client=openai_client,
            gemini_client=command_context.gemini_client,
            pdf_browser=None,
            downloads_dir=downloads_dir,
            responses_dir=command_context.output_layout.responses_dir,
            metadata_dir=command_context.output_layout.metadata_dir,
            fetch_state=command_context.fetch_state,
            generated_output_state=command_context.generated_output_state,
            default_model=command_context.default_model,
            prompts=command_context.selected_prompts,
            forced_prompt_slugs=command_context.forced_prompt_slugs,
            force=command_context.force,
            fetch_only=False,
            force_generation=command_context.force_generation,
        ),
    )


def run_canvas_workflow(
    *,
    command_context: CliCommandContext,
    canvas_credentials: tuple[str, str],
    maybe_prompt_before_exit: Any,
) -> set[str]:
    processed_file_ids: set[str] = set()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=not command_context.headful)
        try:
            context = browser.new_context(accept_downloads=False)
            page = context.new_page()

            login_entry_url = command_context.login_url or command_context.course_url
            print(f"Starting login flow at {login_entry_url}...", flush=True)
            perform_login(
                page=page,
                login_url=login_entry_url,
                course_url=command_context.course_url,
                username=canvas_credentials[0],
                password=canvas_credentials[1],
            )

            with build_canvas_client(context, command_context.course_url) as canvas_client:
                if command_context.fetch_assignments:
                    return run_assignment_fetch_workflow(
                        page=page,
                        canvas_client=canvas_client,
                        browser=browser,
                        command_context=command_context,
                    )

                if _handle_list_files_request(
                    page=page,
                    canvas_client=canvas_client,
                    course_url=command_context.course_url,
                    list_files=command_context.list_files,
                ):
                    return processed_file_ids

                return run_class_note_workflow(
                    page=page,
                    canvas_client=canvas_client,
                    browser=browser,
                    command_context=command_context,
                )
        finally:
            maybe_prompt_before_exit(command_context.headful)
            browser.close()


def _handle_list_files_request(
    *,
    page: Any,
    canvas_client: Any,
    course_url: str,
    list_files: bool,
) -> bool:
    if not list_files:
        return False
    all_files = list_canvas_pdfs_from_ui(page, canvas_client, course_url, name_matcher=is_pdf_by_name)
    print(f"All PDF files found on course pages ({len(all_files)}):", flush=True)
    for canvas_file in all_files:
        print(f"  {canvas_file.display_name!r}", flush=True)
    return True


def run_assignment_fetch_workflow(
    *,
    page: Any,
    canvas_client: Any,
    browser: Any,
    command_context: CliCommandContext,
) -> set[str]:
    files = list_canvas_pdfs_from_assignments(
        page,
        canvas_client,
        command_context.course_url,
        limit=command_context.assignment_limit,
    )
    if not files:
        raise RuntimeError(
            "No assignment files were found on the course pages. Confirm that the account can access module attachments or course files."
        )
    print(f"Found {len(files)} assignment file(s).", flush=True)
    return process_file_batch(
        files=files,
        batch_context=FileBatchContext(
            canvas_client=canvas_client,
            openai_client=None,
            gemini_client=None,
            pdf_browser=browser,
            downloads_dir=command_context.output_layout.assignments_dir,
            responses_dir=command_context.output_layout.responses_dir,
            metadata_dir=command_context.output_layout.metadata_dir,
            fetch_state=command_context.fetch_state,
            generated_output_state=command_context.generated_output_state,
            default_model=command_context.default_model,
            prompts=command_context.selected_prompts,
            forced_prompt_slugs=command_context.forced_prompt_slugs,
            force=command_context.force,
            fetch_only=True,
            force_generation=False,
        ),
    )


def run_class_note_workflow(
    *,
    page: Any,
    canvas_client: Any,
    browser: Any,
    command_context: CliCommandContext,
) -> set[str]:
    files = list_canvas_pdfs_from_ui(
        page,
        canvas_client,
        command_context.course_url,
        name_matcher=matches_target_pdf,
    )
    if command_context.normalized_chapter_filters:
        files = [
            file
            for file in files
            if display_name_matches_chapter_filters(
                file.display_name,
                command_context.normalized_chapter_filters,
            )
        ]
    summarize_discovered_files(files=files, fetch_state=command_context.fetch_state, force=command_context.force)
    if command_context.limit is not None:
        files = files[:command_context.limit]
    if not files:
        raise RuntimeError(
            "No PDF files were found on the course pages. Confirm that the account can access module attachments or course files."
        )
    print(f"Found {len(files)} class note file(s).", flush=True)

    processed_file_ids = process_file_batch(
        files=files,
        batch_context=FileBatchContext(
            canvas_client=canvas_client,
            openai_client=None if command_context.fetch_only else build_openai_generation_client(command_context.openai_api_key),
            gemini_client=command_context.gemini_client,
            pdf_browser=browser,
            downloads_dir=command_context.output_layout.downloads_dir,
            responses_dir=command_context.output_layout.responses_dir,
            metadata_dir=command_context.output_layout.metadata_dir,
            fetch_state=command_context.fetch_state,
            generated_output_state=command_context.generated_output_state,
            default_model=command_context.default_model,
            prompts=command_context.selected_prompts,
            forced_prompt_slugs=command_context.forced_prompt_slugs,
            force=command_context.force,
            fetch_only=command_context.fetch_only,
            force_generation=command_context.force_generation,
        ),
    )

    assignment_files = list_canvas_pdfs_from_assignments(page, canvas_client, command_context.course_url)
    if assignment_files:
        print(f"Found {len(assignment_files)} assignment file(s).", flush=True)
        processed_file_ids.update(
            process_file_batch(
                files=assignment_files,
                batch_context=FileBatchContext(
                    canvas_client=canvas_client,
                    openai_client=None,
                    gemini_client=None,
                    pdf_browser=browser,
                    downloads_dir=command_context.output_layout.assignments_dir,
                    responses_dir=command_context.output_layout.responses_dir,
                    metadata_dir=command_context.output_layout.metadata_dir,
                    fetch_state=command_context.fetch_state,
                    generated_output_state=command_context.generated_output_state,
                    default_model=command_context.default_model,
                    prompts=command_context.selected_prompts,
                    forced_prompt_slugs=command_context.forced_prompt_slugs,
                    force=command_context.force,
                    fetch_only=True,
                    force_generation=False,
                ),
            )
        )
    return processed_file_ids


def build_guided_learning_site(
    *,
    output_dir: Path,
    site_dir: str | None,
    base_path: str,
    limit: int | None,
    processed_file_ids: set[str],
) -> Path:
    from math_tutor.site_builder import build_site

    return build_site(
        output_dir=output_dir,
        site_dir=Path(site_dir).resolve() if site_dir else None,
        base_path=base_path,
        limit=limit,
        include_guided_learning=True,
        file_ids=processed_file_ids,
    )
