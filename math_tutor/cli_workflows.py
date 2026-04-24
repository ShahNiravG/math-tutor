"""Workflow helpers for repeated CLI processing patterns."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from openai import OpenAI

from math_tutor.canvas_course import CanvasFile
from math_tutor.prompt_catalog import PromptSpec
from math_tutor.prompt_pipeline import process_file
from math_tutor.state_store import FetchState, GeneratedOutputState


@dataclass(frozen=True)
class FileBatchContext:
    canvas_client: Any
    openai_client: OpenAI | None
    gemini_client: Any
    pdf_browser: Any
    downloads_dir: Path
    responses_dir: Path
    metadata_dir: Path
    fetch_state: FetchState
    generated_output_state: GeneratedOutputState
    default_model: str
    prompts: tuple[PromptSpec, ...]
    forced_prompt_slugs: set[str]
    requested_prompt_slugs: set[str]
    force: bool
    fetch_only: bool
    force_generation: bool
    dry_run: bool


def process_file_batch(
    *,
    files: list[CanvasFile],
    batch_context: FileBatchContext,
    process_file_fn: Callable[..., None] = process_file,
) -> set[str]:
    processed_file_ids: set[str] = set()
    for index, canvas_file in enumerate(files, start=1):
        process_file_fn(
            canvas_client=batch_context.canvas_client,
            openai_client=batch_context.openai_client,
            gemini_client=batch_context.gemini_client,
            pdf_browser=batch_context.pdf_browser,
            canvas_file=canvas_file,
            downloads_dir=batch_context.downloads_dir,
            responses_dir=batch_context.responses_dir,
            metadata_dir=batch_context.metadata_dir,
            fetch_state=batch_context.fetch_state,
            generated_output_state=batch_context.generated_output_state,
            default_model=batch_context.default_model,
            prompts=batch_context.prompts,
            forced_prompt_slugs=batch_context.forced_prompt_slugs,
            requested_prompt_slugs=batch_context.requested_prompt_slugs,
            force=batch_context.force,
            fetch_only=batch_context.fetch_only,
            force_generation=batch_context.force_generation,
            dry_run=batch_context.dry_run,
            index=index,
            total=len(files),
        )
        processed_file_ids.add(str(canvas_file.file_id))
    return processed_file_ids
