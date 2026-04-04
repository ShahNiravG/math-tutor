"""Prompt-card ordering and rendering for generated chapter pages."""

from __future__ import annotations

import html
from pathlib import Path

from math_tutor.prompt_catalog import DEFAULT_MODEL, PROMPTS_BY_SLUG, PromptSpec
from math_tutor.site_assets import build_site_href, link_tag
from math_tutor.site_cards import (
    match_assignments_to_record,
    render_assignments_card_with_variant,
    render_inspiring_videos_card,
    render_learning_idea_card,
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
    experience_variant: str = "default",
) -> str:
    grouped_cards = build_document_prompt_card_groups(
        record=record,
        output_dir=output_dir,
        site_dir=site_dir,
        base_path=base_path,
        assignments=assignments,
        experience_variant=experience_variant,
    )
    return "\n".join(grouped_cards["all"])


def build_document_prompt_card_groups(
    *,
    record: DocumentRecord,
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    assignments: list[Path] | None = None,
    experience_variant: str = "default",
) -> dict[str, list[str]]:
    outputs_by_slug = {prompt_output.slug: prompt_output for prompt_output in record.prompt_outputs}
    rendered_slugs: set[str] = set()
    learn_cards: list[str] = []
    practice_cards: list[str] = []
    resource_cards: list[str] = []
    extra_cards: list[str] = []

    if experience_variant == "staging":
        class_note_link = None
        if record.pdf_path and record.pdf_path.exists():
            class_note_link = link_tag(
                record.pdf_path,
                output_dir,
                site_dir,
                "Class Note PDF",
                base_path,
                css_class="button-class-note",
            )
        learning_card = render_learning_idea_card(
            class_note_link=class_note_link,
            study_specs=STUDY_GUIDE_SPECS,
            video_specs=INSPIRING_VIDEOS_SPECS,
            outputs_by_slug=outputs_by_slug,
            output_dir=output_dir,
            site_dir=site_dir,
            base_path=base_path,
            build_site_href=build_site_href,
            model_label_for_spec=model_label_for_prompt_spec,
            experience_variant=experience_variant,
        )
        if learning_card:
            learn_cards.append(learning_card)

    for title, specs, label, hide_model in (
        (
            "Quick Practice" if experience_variant == "staging" else "Mental Math",
            MENTAL_MATH_SPECS,
            "Start Practice" if experience_variant == "staging" else "Mental Math",
            False,
        ),
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
            link_class="button-quick-practice",
            hide_model=hide_model,
            description=(
                "Work a few fast problems first to build confidence before you move into stretch questions."
                if experience_variant == "staging"
                else ""
            ),
            experience_variant=experience_variant,
        )
        if card:
            practice_cards.append(card)

    if experience_variant != "staging":
        study_guide_card = render_single_model_row_card(
            title="Study Guide",
            specs=STUDY_GUIDE_SPECS,
            outputs_by_slug=outputs_by_slug,
            link_label="Open Guide",
            output_dir=output_dir,
            site_dir=site_dir,
            base_path=base_path,
            build_site_href=build_site_href,
            model_label_for_spec=model_label_for_prompt_spec,
            link_class="button-study-guide",
            hide_model=False,
            description="",
            experience_variant=experience_variant,
        )
        if study_guide_card:
            learn_cards.append(study_guide_card)

    inspiring_videos_card = render_inspiring_videos_card(
        specs=INSPIRING_VIDEOS_SPECS,
        outputs_by_slug=outputs_by_slug,
        output_dir=output_dir,
        site_dir=site_dir,
        base_path=base_path,
        build_site_href=build_site_href,
        model_label_for_spec=model_label_for_prompt_spec,
        description=(
            "Use these when you want a different explanation or a quick warm-up before practice."
            if experience_variant == "staging"
            else ""
        ),
        experience_variant=experience_variant,
    )
    if inspiring_videos_card and experience_variant != "staging":
        resource_cards.append(inspiring_videos_card)

    olympiad_card = render_olympiad_combined(
        problem_specs=OLYMPIAD_PROBLEMS_SPECS,
        solution_specs=OLYMPIAD_SOLUTIONS_SPECS,
        outputs_by_slug=outputs_by_slug,
        output_dir=output_dir,
        site_dir=site_dir,
        base_path=base_path,
        build_site_href=build_site_href,
        model_label_for_spec=model_label_for_prompt_spec,
        description=(
            "Try these after quick practice when you want deeper thinking and multi-step work."
            if experience_variant == "staging"
            else ""
        ),
        experience_variant=experience_variant,
    )
    if olympiad_card:
        practice_cards.append(olympiad_card)

    record_assignments = match_assignments_to_record(assignments or [], record)
    assignments_card = render_assignments_card_with_variant(
        assignments=record_assignments,
        site_dir=site_dir,
        base_path=base_path,
        experience_variant=experience_variant,
    )
    if assignments_card:
        resource_cards.append(assignments_card)

    for prompt_spec in PROMPT_ORDER:
        rendered_slugs.add(prompt_spec.slug)
    for prompt_output in record.prompt_outputs:
        if prompt_output.slug not in rendered_slugs:
            extra_cards.append(render_prompt_output_card(prompt_output, output_dir, site_dir, base_path))

    all_cards = [*learn_cards, *practice_cards, *resource_cards, *extra_cards]
    return {
        "learn": learn_cards,
        "practice": practice_cards,
        "resources": resource_cards,
        "extras": extra_cards,
        "all": all_cards,
    }


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
