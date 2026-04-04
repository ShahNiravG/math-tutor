"""Command-context assembly for the operator CLI."""

from __future__ import annotations

from argparse import Namespace
from collections.abc import Callable
from pathlib import Path

from math_tutor.cli_commands import CliCommandContext
from math_tutor.cli_generation import initialize_gemini_client, resolve_openai_api_key
from math_tutor.cli_runtime import build_output_layout, ensure_output_layout, normalize_cli_chapter_filters
from math_tutor.prompt_catalog import resolve_prompt_slug_set, resolve_selected_prompts
from math_tutor.state_store import (
    canonical_generated_output_state_path,
    load_fetch_state,
    load_generated_output_state,
)


def build_command_context(
    *,
    args: Namespace,
    output_dir: Path,
    log: Callable[[str], None],
) -> CliCommandContext:
    output_layout = build_output_layout(output_dir)
    fetch_state = load_fetch_state(output_dir / "fetch_state.json")
    generated_output_state = load_generated_output_state(
        canonical_generated_output_state_path(output_dir)
    )
    selected_prompts = resolve_selected_prompts(args.prompt_slugs)
    forced_prompt_slugs = resolve_prompt_slug_set(args.force_prompt_slugs)
    normalized_chapter_filters = normalize_cli_chapter_filters(args.chapter_filters)

    ensure_output_layout(output_layout)

    openai_api_key = resolve_openai_api_key(
        prompts=selected_prompts,
        fetch_only=args.fetch_only,
        fetch_assignments=args.fetch_assignments,
    )
    gemini_client = None
    if not args.fetch_only and any((prompt.model or "").startswith("gemini") for prompt in selected_prompts):
        gemini_client = initialize_gemini_client(log=log)

    return CliCommandContext(
        output_dir=output_dir,
        output_layout=output_layout,
        fetch_state=fetch_state,
        generated_output_state=generated_output_state,
        default_model=args.default_model,
        selected_prompts=selected_prompts,
        forced_prompt_slugs=forced_prompt_slugs,
        normalized_chapter_filters=normalized_chapter_filters,
        force=args.force,
        force_generation=args.force_generation,
        fetch_only=args.fetch_only,
        fetch_assignments=args.fetch_assignments,
        list_files=args.list_files,
        headful=args.headful,
        limit=args.limit,
        assignment_limit=args.assignment_limit,
        course_url=args.course_url,
        login_url=args.login_url,
        site_dir=args.site_dir,
        site_base_path=args.site_base_path,
        build_site_guided_learning=args.build_site_guided_learning,
        openai_api_key=openai_api_key,
        gemini_client=gemini_client,
    )
