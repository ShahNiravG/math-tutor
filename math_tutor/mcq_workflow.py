"""Per-file MCQ workflow helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from math_tutor.mcq_artifacts import build_mcq_html, build_mcq_output_paths
from math_tutor.mcq_clients import generate_mcq_text
from math_tutor.mcq_prompts import MCQSourceConfig, build_mcq_prompt
from math_tutor.response_artifacts import build_response_pdf


def process_mcq_file(
    *,
    source_md: Path,
    source_config: MCQSourceConfig,
    responses_dir: Path,
    openai_client: Any,
    gemini_client: Any,
    force: bool,
    build_prompt_fn: Callable[..., str] = build_mcq_prompt,
    generate_mcq_text_fn: Callable[..., str | None] = generate_mcq_text,
    build_html_fn: Callable[[str, str], str] = build_mcq_html,
    build_pdf_fn: Callable[..., None] = build_response_pdf,
) -> None:
    output_paths = build_mcq_output_paths(
        source_md=source_md,
        mcq_slug=source_config.mcq_suffix,
        responses_dir=responses_dir,
    )

    if not force and output_paths.markdown_path.exists():
        print(f"  Skipping {output_paths.markdown_path.name} (already exists)")
        return

    questions_text = source_md.read_text(encoding="utf-8")
    prompt = build_prompt_fn(prompt_type=source_config.prompt_type, questions_text=questions_text)

    print(f"\nProcessing: {source_md.name}")
    mcq_text = generate_mcq_text_fn(
        provider=source_config.provider,
        prompt=prompt,
        openai_client=openai_client,
        gemini_client=gemini_client,
    )
    if mcq_text is None:
        return

    output_paths.markdown_path.write_text(mcq_text, encoding="utf-8")
    print(f"  Wrote {output_paths.markdown_path.name}")

    html_content = build_html_fn(output_paths.output_stem, mcq_text)
    output_paths.html_path.write_text(html_content, encoding="utf-8")
    print(f"  Wrote {output_paths.html_path.name}")

    build_pdf_fn(response_html_path=output_paths.html_path, response_pdf_path=output_paths.pdf_path)
    print(f"  Wrote {output_paths.pdf_path.name}")
