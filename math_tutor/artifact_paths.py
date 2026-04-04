"""Path construction helpers for generated response artifacts."""

from __future__ import annotations

from pathlib import Path

from math_tutor.prompt_catalog import DEFAULT_MODEL, PromptSpec

EXPLICIT_MODEL_SUFFIXES = ("gpt4", "gpt5", "gemini")


def model_name_to_artifact_suffix(model_name: str) -> str:
    normalized = model_name.strip().lower()
    if normalized.startswith("gpt-5"):
        return "gpt5"
    if normalized.startswith("gpt-4.1"):
        return "gpt4"
    if normalized.startswith("gemini"):
        return "gemini"
    return normalized.replace(".", "-").replace("_", "-")


def artifact_slug_for_prompt(*, prompt_spec: PromptSpec, model_name: str | None = None) -> str:
    if prompt_spec.slug.endswith(tuple(f"-{suffix}" for suffix in EXPLICIT_MODEL_SUFFIXES)):
        return prompt_spec.slug
    effective_model = model_name or prompt_spec.model or DEFAULT_MODEL
    model_suffix = model_name_to_artifact_suffix(effective_model)
    if prompt_spec.slug.endswith(f"-{model_suffix}"):
        return prompt_spec.slug
    return f"{prompt_spec.slug}-{model_suffix}"


def build_prompt_paths(
    *,
    responses_dir: Path,
    metadata_dir: Path,
    stem: str,
    prompt_spec: PromptSpec,
    model_name: str | None = None,
) -> tuple[Path, Path, Path, Path]:
    artifact_slug = artifact_slug_for_prompt(prompt_spec=prompt_spec, model_name=model_name)
    response_base = responses_dir / f"{stem}__{artifact_slug}"
    metadata_path = metadata_dir / f"{stem}__{artifact_slug}.json"
    return (
        response_base.with_suffix(".md"),
        response_base.with_suffix(".html"),
        response_base.with_suffix(".pdf"),
        metadata_path,
    )
