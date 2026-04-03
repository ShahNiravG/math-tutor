"""Prompt-card ordering and rendering for generated chapter pages."""

from __future__ import annotations

import html
from pathlib import Path

from math_tutor.prompt_catalog import DEFAULT_MODEL, PROMPTS_BY_SLUG, PromptSpec
from math_tutor.site_assets import build_site_href, link_tag
from math_tutor.site_cards import (
    match_assignments_to_record,
    render_assignments_card,
    render_inspiring_videos_card,
    render_olympiad_combined,
    render_single_model_row_card,
)
from math_tutor.site_models import DocumentRecord, PromptOutputRecord


def _specs(*slugs: str) -> tuple[PromptSpec, ...]:
    return tuple(PROMPTS_BY_SLUG[slug] for slug in slugs if slug in PROMPTS_BY_SLUG)


STUDY_GUIDE_SPECS = _specs("study-guide", "study-guide-gpt5", "study-guide-gemini")
INSPIRING_VIDEOS_SPECS = _specs("inspiring-videos", "inspiring-videos-gpt5", "inspiring-videos-gemini")
MENTAL_MATH_SPECS = _specs("mental-math", "mental-math-gpt5", "mental-math-gemini")
OLYMPIAD_PROBLEMS_SPECS = _specs("olympiad-problems", "olympiad-problems-gpt5", "olympiad-problems-gemini")
OLYMPIAD_SOLUTIONS_SPECS = _specs("olympiad-solutions", "olympiad-solutions-gpt5", "olympiad-solutions-gemini")
PROMPT_ORDER: tuple[PromptSpec, ...] = (
    *STUDY_GUIDE_SPECS,
    *INSPIRING_VIDEOS_SPECS,
    *MENTAL_MATH_SPECS,
    *OLYMPIAD_PROBLEMS_SPECS,
    *OLYMPIAD_SOLUTIONS_SPECS,
)

MODEL_DISPLAY_NAMES: dict[str, str] = {
    "gpt-4.1": "GPT-4.1",
    "gpt-5.4": "GPT-5.4",
    "gemini-3.1-pro-preview": "Gemini 3.1 Pro",
    "gemini-3.1-pro": "Gemini 3.1 Pro",
}


def model_label_for_prompt_spec(prompt_spec: PromptSpec) -> str:
    raw = prompt_spec.model or DEFAULT_MODEL
    return MODEL_DISPLAY_NAMES.get(raw, raw.replace("-preview", ""))


def build_document_prompt_cards_html(
    *,
    record: DocumentRecord,
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    assignments: list[Path] | None = None,
) -> str:
    outputs_by_slug = {prompt_output.slug: prompt_output for prompt_output in record.prompt_outputs}
    rendered_slugs: set[str] = set()
    cards: list[str] = []

    for title, specs, label, hide_model in (
        ("Study Guide", STUDY_GUIDE_SPECS, "Open Guide", False),
        ("Mental Math", MENTAL_MATH_SPECS, "Mental Math", False),
    ):
        card = render_single_model_row_card(
            title=title,
            specs=specs,
            outputs_by_slug=outputs_by_slug,
            link_label=label,
            output_dir=output_dir,
            site_dir=site_dir,
            base_path=base_path,
            build_site_href=build_site_href,
            model_label_for_spec=model_label_for_prompt_spec,
            hide_model=hide_model,
        )
        if card:
            cards.append(card)

    inspiring_videos_card = render_inspiring_videos_card(
        specs=INSPIRING_VIDEOS_SPECS,
        outputs_by_slug=outputs_by_slug,
        output_dir=output_dir,
        site_dir=site_dir,
        base_path=base_path,
        build_site_href=build_site_href,
        model_label_for_spec=model_label_for_prompt_spec,
    )
    if inspiring_videos_card:
        cards.insert(1 if cards else 0, inspiring_videos_card)

    olympiad_card = render_olympiad_combined(
        problem_specs=OLYMPIAD_PROBLEMS_SPECS,
        solution_specs=OLYMPIAD_SOLUTIONS_SPECS,
        outputs_by_slug=outputs_by_slug,
        output_dir=output_dir,
        site_dir=site_dir,
        base_path=base_path,
        build_site_href=build_site_href,
        model_label_for_spec=model_label_for_prompt_spec,
    )
    if olympiad_card:
        cards.append(olympiad_card)

    record_assignments = match_assignments_to_record(assignments or [], record)
    assignments_card = render_assignments_card(record_assignments, site_dir, base_path)
    if assignments_card:
        cards.append(assignments_card)

    for prompt_spec in PROMPT_ORDER:
        rendered_slugs.add(prompt_spec.slug)
    for prompt_output in record.prompt_outputs:
        if prompt_output.slug not in rendered_slugs:
            cards.append(render_prompt_output_card(prompt_output, output_dir, site_dir, base_path))

    return "\n".join(cards)


def render_prompt_output_card(
    prompt_output: PromptOutputRecord,
    output_dir: Path,
    site_dir: Path,
    base_path: str,
) -> str:
    links: list[str] = []
    prompt_spec = PROMPTS_BY_SLUG.get(prompt_output.slug)
    if prompt_output.response_html_path and prompt_output.response_html_path.exists():
        links.append(link_tag(prompt_output.response_html_path, output_dir, site_dir, "Open HTML", base_path))
    if (
        prompt_spec is not None
        and prompt_spec.generate_response_pdf
        and prompt_output.response_pdf_path
        and prompt_output.response_pdf_path.exists()
    ):
        links.append(link_tag(prompt_output.response_pdf_path, output_dir, site_dir, "Open PDF", base_path))

    chips: list[str] = []
    if prompt_spec is not None and prompt_spec.model:
        chips.append(f'<span class="chip chip-model">{html.escape(prompt_spec.model)}</span>')
    if prompt_output.processed_at:
        chips.append(f'<span class="chip">Generated by AI {html.escape(prompt_output.processed_at)}</span>')
    else:
        chips.append('<span class="chip">No generated response yet</span>')

    return f"""
      <section class="prompt-card">
        <h3>{html.escape(prompt_output.title)}</h3>
        <div class="chip-row">
          {' '.join(chips)}
        </div>
        <div class="link-row">
          {' '.join(links)}
        </div>
      </section>
    """
