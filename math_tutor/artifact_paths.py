"""Path construction helpers for generated response artifacts."""

from __future__ import annotations

from pathlib import Path

from math_tutor.prompt_catalog import PromptSpec


def build_prompt_paths(
    *,
    responses_dir: Path,
    metadata_dir: Path,
    stem: str,
    prompt_spec: PromptSpec,
) -> tuple[Path, Path, Path, Path]:
    if prompt_spec.slug == "study-guide":
        response_base = responses_dir / stem
        metadata_path = metadata_dir / f"{stem}.json"
    else:
        response_base = responses_dir / f"{stem}__{prompt_spec.slug}"
        metadata_path = metadata_dir / f"{stem}__{prompt_spec.slug}.json"
    return (
        response_base.with_suffix(".md"),
        response_base.with_suffix(".html"),
        response_base.with_suffix(".pdf"),
        metadata_path,
    )
