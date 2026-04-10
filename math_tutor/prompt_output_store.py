"""Persistence helpers for generated prompt outputs."""

from __future__ import annotations

import os
import time
from pathlib import Path

from math_tutor.atomic_io import atomic_write_json
from math_tutor.canvas_course import CanvasFile
from math_tutor.generated_metadata import build_generated_metadata, provider_name_for_model
from math_tutor.prompt_catalog import PromptSpec
from math_tutor.prompt_generation import PromptResponseResult
from math_tutor.response_artifacts import build_response_html, build_response_pdf
from math_tutor.state_store import GeneratedOutputState, save_generated_output_state


def persist_prompt_output(
    *,
    canvas_file: CanvasFile,
    prompt_spec: PromptSpec,
    pdf_path: Path,
    response_path: Path,
    response_html_path: Path,
    response_pdf_path: Path,
    metadata_path: Path,
    result: PromptResponseResult,
    effective_model: str,
    generated_output_state: GeneratedOutputState,
    pdf_browser: object,
) -> None:
    response_path.write_text(result.output_text, encoding="utf-8")
    response_html_path.write_text(
        build_response_html(
            title=canvas_file.display_name,
            prompt_title=prompt_spec.title,
            markdown_text=result.output_text,
            pdf_label=pdf_path.name if prompt_spec.include_source_pdf_link else None,
            pdf_href=(
                Path(os.path.relpath(pdf_path, start=response_html_path.parent)).as_posix()
                if prompt_spec.include_source_pdf_link
                else None
            ),
            prompt_slug=prompt_spec.slug,
        ),
        encoding="utf-8",
    )
    if prompt_spec.generate_response_pdf:
        build_response_pdf(
            response_html_path=response_html_path,
            response_pdf_path=response_pdf_path,
            browser=pdf_browser,
        )

    metadata = build_generated_metadata(
        canvas_file=canvas_file,
        prompt_spec=prompt_spec,
        pdf_path=pdf_path,
        response_path=response_path,
        response_html_path=response_html_path,
        response_pdf_path=response_pdf_path if prompt_spec.generate_response_pdf else None,
        model_name=effective_model,
        response_id=result.response_id,
    )
    atomic_write_json(metadata_path, metadata, indent=2)

    file_state = generated_output_state.processed.setdefault(str(canvas_file.file_id), {})
    file_state[prompt_spec.slug] = {
        "display_name": canvas_file.display_name,
        "prompt_slug": prompt_spec.slug,
        "prompt_title": prompt_spec.title,
        "response_path": str(response_path),
        "response_html_path": str(response_html_path),
        "response_pdf_path": metadata["response_pdf_path"],
        "metadata_path": str(metadata_path),
        "processed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "provider": provider_name_for_model(effective_model),
        "response_id": result.response_id,
        "source_prompt_slug": prompt_spec.source_prompt_slug or "",
        "model": effective_model,
    }
    save_generated_output_state(generated_output_state)
