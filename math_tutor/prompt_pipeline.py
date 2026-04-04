"""Prompt execution and saved-output orchestration for tutoring artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from openai import OpenAI

from math_tutor.artifact_paths import build_prompt_paths
from math_tutor.canvas_course import CanvasFile, ensure_pdf_fetched
from math_tutor.prompt_generation import PromptResponseResult, generate_prompt_response
from math_tutor.prompt_catalog import PROMPTS_BY_SLUG, PromptSpec
from math_tutor.prompt_output_store import persist_prompt_output
from math_tutor.prompt_saved_outputs import should_skip_generation
from math_tutor.response_artifacts import slugify
from math_tutor.state_store import (
    FetchState,
    GeneratedOutputState,
)


def prompt_applies_to_file(
    *,
    prompt_spec: PromptSpec,
    canvas_file: CanvasFile,
    pdf_path: Path,
) -> bool:
    if prompt_spec.assignment_only and "assignments" not in {part.lower() for part in pdf_path.parts}:
        return False

    if prompt_spec.required_filename_substrings:
        candidate_names = (canvas_file.display_name.lower(), pdf_path.name.lower())
        return all(any(substring.lower() in name for name in candidate_names) for substring in prompt_spec.required_filename_substrings)

    return True


def process_file(
    *,
    canvas_client: httpx.Client,
    openai_client: OpenAI,
    gemini_client: Any,
    pdf_browser: Any,
    canvas_file: CanvasFile,
    downloads_dir: Path,
    responses_dir: Path,
    metadata_dir: Path,
    fetch_state: FetchState,
    generated_output_state: GeneratedOutputState,
    default_model: str,
    prompts: tuple[PromptSpec, ...],
    forced_prompt_slugs: set[str],
    force: bool,
    fetch_only: bool,
    force_generation: bool,
    index: int,
    total: int,
) -> None:
    stem = f"{canvas_file.file_id}_{slugify(Path(canvas_file.display_name).stem)}"
    extension = Path(canvas_file.display_name).suffix or ".pdf"
    saved_pdf_path_value = fetch_state.fetched.get(str(canvas_file.file_id), {}).get("pdf_path", "")
    saved_pdf_path = Path(saved_pdf_path_value) if saved_pdf_path_value else None
    pdf_path = (
        saved_pdf_path
        if saved_pdf_path is not None and saved_pdf_path.exists() and not force
        else downloads_dir / f"{stem}{extension}"
    )
    prompt_outputs_cache: dict[str, str] = {}

    ensure_pdf_fetched(
        client=canvas_client,
        canvas_file=canvas_file,
        destination=pdf_path,
        fetch_state=fetch_state,
        force=force,
        index=index,
        total=total,
    )

    if fetch_only:
        print(f"[{index}/{total}] Fetch-only mode; skipping generation for {canvas_file.display_name}.", flush=True)
        return

    for prompt_spec in prompts:
        run_prompt(
            canvas_file=canvas_file,
            openai_client=openai_client,
            gemini_client=gemini_client,
            pdf_browser=pdf_browser,
            pdf_path=pdf_path,
            responses_dir=responses_dir,
            metadata_dir=metadata_dir,
            generated_output_state=generated_output_state,
            default_model=default_model,
            stem=stem,
            prompt_spec=prompt_spec,
            prompt_outputs_cache=prompt_outputs_cache,
            force=force,
            force_generation=force_generation or prompt_spec.slug in forced_prompt_slugs,
            index=index,
            total=total,
        )


def run_prompt(
    *,
    canvas_file: CanvasFile,
    openai_client: OpenAI,
    gemini_client: Any,
    pdf_browser: Any,
    pdf_path: Path,
    responses_dir: Path,
    metadata_dir: Path,
    generated_output_state: GeneratedOutputState,
    default_model: str,
    stem: str,
    prompt_spec: PromptSpec,
    prompt_outputs_cache: dict[str, str],
    force: bool,
    force_generation: bool,
    index: int,
    total: int,
) -> str:
    if not prompt_spec.generate:
        return ""
    if not prompt_applies_to_file(prompt_spec=prompt_spec, canvas_file=canvas_file, pdf_path=pdf_path):
        print(
            f"[{index}/{total}] Skipping {prompt_spec.title} for {canvas_file.display_name}; "
            "it only runs on assignment PDFs whose filenames include the required markers.",
            flush=True,
        )
        return ""

    response_path, response_html_path, response_pdf_path, metadata_path = build_prompt_paths(
        responses_dir=responses_dir,
        metadata_dir=metadata_dir,
        stem=stem,
        prompt_spec=prompt_spec,
        model_name=prompt_spec.model or default_model,
    )

    if should_skip_generation(
        canvas_file=canvas_file,
        prompt_spec=prompt_spec,
        response_path=response_path,
        response_html_path=response_html_path,
        response_pdf_path=response_pdf_path,
        generated_output_state=generated_output_state,
        force=force,
        force_generation=force_generation,
        index=index,
        total=total,
    ):
        if response_path.exists():
            cached_output = response_path.read_text(encoding="utf-8")
            prompt_outputs_cache[prompt_spec.slug] = cached_output
            return cached_output
        return ""

    source_output = resolve_source_output(
        canvas_file=canvas_file,
        openai_client=openai_client,
        gemini_client=gemini_client,
        pdf_browser=pdf_browser,
        pdf_path=pdf_path,
        responses_dir=responses_dir,
        metadata_dir=metadata_dir,
        generated_output_state=generated_output_state,
        default_model=default_model,
        stem=stem,
        prompt_spec=prompt_spec,
        prompt_outputs_cache=prompt_outputs_cache,
        index=index,
        total=total,
    )

    effective_model = prompt_spec.model or default_model
    print(f"[{index}/{total}] Sending {canvas_file.display_name} to {effective_model} for {prompt_spec.title}...", flush=True)
    result = generate_prompt_response(
        client=openai_client,
        gemini_client=gemini_client,
        pdf_path=pdf_path,
        default_model=default_model,
        prompt_spec=prompt_spec,
        source_output=source_output,
    )
    persist_prompt_output(
        canvas_file=canvas_file,
        prompt_spec=prompt_spec,
        pdf_path=pdf_path,
        response_path=response_path,
        response_html_path=response_html_path,
        response_pdf_path=response_pdf_path,
        metadata_path=metadata_path,
        result=result,
        effective_model=effective_model,
        generated_output_state=generated_output_state,
        pdf_browser=pdf_browser,
    )
    prompt_outputs_cache[prompt_spec.slug] = result.output_text
    print(f"[{index}/{total}] Saved {prompt_spec.title} output to {response_path}.", flush=True)
    return result.output_text


def resolve_source_output(
    *,
    canvas_file: CanvasFile,
    openai_client: OpenAI,
    gemini_client: Any,
    pdf_browser: Any,
    pdf_path: Path,
    responses_dir: Path,
    metadata_dir: Path,
    generated_output_state: GeneratedOutputState,
    default_model: str,
    stem: str,
    prompt_spec: PromptSpec,
    prompt_outputs_cache: dict[str, str],
    index: int,
    total: int,
) -> str | None:
    if prompt_spec.source_prompt_slug is None:
        return None

    if prompt_spec.source_prompt_slug in prompt_outputs_cache:
        return prompt_outputs_cache[prompt_spec.source_prompt_slug]

    source_prompt = PROMPTS_BY_SLUG[prompt_spec.source_prompt_slug]
    source_response_path, _, _, _ = build_prompt_paths(
        responses_dir=responses_dir,
        metadata_dir=metadata_dir,
        stem=stem,
        prompt_spec=source_prompt,
        model_name=source_prompt.model or default_model,
    )
    if source_response_path.exists():
        source_output = source_response_path.read_text(encoding="utf-8")
        prompt_outputs_cache[source_prompt.slug] = source_output
        return source_output

    print(
        f"[{index}/{total}] {prompt_spec.title} needs {source_prompt.title} first; generating the prerequisite output."
    )
    return run_prompt(
        canvas_file=canvas_file,
        openai_client=openai_client,
        gemini_client=gemini_client,
        pdf_browser=pdf_browser,
        pdf_path=pdf_path,
        responses_dir=responses_dir,
        metadata_dir=metadata_dir,
        generated_output_state=generated_output_state,
        default_model=default_model,
        stem=stem,
        prompt_spec=source_prompt,
        prompt_outputs_cache=prompt_outputs_cache,
        force=False,
        force_generation=False,
        index=index,
        total=total,
    )
