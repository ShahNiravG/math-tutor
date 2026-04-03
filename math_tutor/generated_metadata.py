"""Provider-neutral metadata helpers for generated tutoring artifacts."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from math_tutor.prompt_catalog import PromptSpec

if TYPE_CHECKING:
    from math_tutor.canvas_course import CanvasFile


def provider_name_for_model(model: str) -> str:
    return "gemini" if model.startswith("gemini") else "openai"


def normalize_metadata_payload(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = dict(payload)
    model_name = normalized.get("model")
    if not isinstance(normalized.get("provider"), str) and isinstance(model_name, str):
        normalized["provider"] = provider_name_for_model(model_name)
    return normalized


def build_generated_metadata(
    *,
    canvas_file: CanvasFile,
    prompt_spec: PromptSpec,
    pdf_path: Path,
    response_path: Path,
    response_html_path: Path,
    response_pdf_path: Path | None,
    model_name: str,
    response_id: str | None,
) -> dict[str, Any]:
    effective_pdf_path = str(response_pdf_path) if response_pdf_path is not None else ""
    return {
        "canvas_file_id": canvas_file.file_id,
        "display_name": canvas_file.display_name,
        "download_url": canvas_file.download_url,
        "content_type": canvas_file.content_type,
        "size": canvas_file.size,
        "updated_at": canvas_file.updated_at,
        "provider": provider_name_for_model(model_name),
        "model": model_name,
        "response_id": response_id,
        "prompt_slug": prompt_spec.slug,
        "prompt_title": prompt_spec.title,
        "source_prompt_slug": prompt_spec.source_prompt_slug,
        "pdf_path": str(pdf_path),
        "response_path": str(response_path),
        "response_html_path": str(response_html_path),
        "response_pdf_path": effective_pdf_path,
    }
