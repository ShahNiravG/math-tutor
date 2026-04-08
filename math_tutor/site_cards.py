"""Reusable site-card rendering helpers for document pages."""

from __future__ import annotations

import html
import re
import shutil
from pathlib import Path
from typing import Callable

from math_tutor.chaptering import format_assignment_display_name, parse_assignment_chapters, parse_display_name_chapter
from math_tutor.prompt_catalog import DEFAULT_MODEL, PromptSpec
from math_tutor.response_artifacts import pretty_title
from math_tutor.site_assets import build_site_href
from math_tutor.site_models import DocumentRecord, PromptOutputRecord


def record_page_filename(record: DocumentRecord) -> str:
    return f"doc-{record.file_id}.html"


CHAPTER_TITLES: dict[str, str] = {
    "5.1": "Radians, Arc Length, and Sector Area",
    "5.2": "Right Triangle Trigonometry",
    "5.3": "Trigonometric Functions of Angles",
    "5.4": "Inverse Trigonometric Functions",
    "5.5": "Law of Sines",
    "5.6": "Law of Cosines",
    "6.1": "The Unit Circle",
    "6.2": "Trigonometric Functions on the Unit Circle",
    "6.3": "Graphs of Sine and Cosine",
    "6.4": "Graphs of Tangent, Cotangent, Secant, and Cosecant",
    "6.5": "Graphs and Properties of Inverse Trig Functions",
    "7.1": "Fundamental Trigonometric Identities",
    "7.2": "Addition and Subtraction Formulas",
    "7.3": "Double-Angle, Half-Angle, and Product Formulas",
    "7.4 & 7.5": "Solving Trigonometric Equations",
    "11.1": "Circles and Parabolas",
    "11.2": "Ellipses",
    "11.3": "Hyperbolas",
    "11.4": "Shifted Conics",
}


def chapter_title(chapter: str | None) -> str | None:
    if not chapter:
        return None
    normalized = " ".join(chapter.split())
    return CHAPTER_TITLES.get(normalized)


def generated_document_title(record: DocumentRecord) -> str | None:
    chapter = parse_display_name_chapter(record.display_name)
    for prompt_output in record.prompt_outputs:
        if prompt_output.slug != "study-guide":
            continue
        generated_title = _extract_study_guide_title(prompt_output.response_markdown)
        if generated_title:
            return _normalize_generated_title(generated_title, chapter)
        if prompt_output.response_html_path and prompt_output.response_html_path.exists():
            generated_title = _extract_study_guide_title_from_html(prompt_output.response_html_path.read_text(encoding="utf-8"))
            if generated_title:
                return _normalize_generated_title(generated_title, chapter)
    return None


def document_title(record: DocumentRecord) -> str:
    generated_title = generated_document_title(record)
    if generated_title:
        return generated_title
    chapter = parse_display_name_chapter(record.display_name)
    title = chapter_title(chapter)
    if title:
        return title
    return pretty_title(record.display_name)


def document_label(record: DocumentRecord) -> str:
    chapter = parse_display_name_chapter(record.display_name)
    title = document_title(record)
    if chapter and title:
        return f"Chapter {chapter}: {title}"
    if chapter:
        return f"Chapter {chapter}"
    return title


def _extract_study_guide_title(markdown_text: str | None) -> str | None:
    if not markdown_text:
        return None

    match = re.search(
        r"(?ims)^\s*#{1,6}\s*(?:chapter\s+)?title\s*$\n(.*?)(?=^\s*#{1,6}\s+|^\s*\d+\.\s+|\Z)",
        markdown_text,
    )
    if match:
        return _first_content_line(match.group(1))

    match = re.search(r"(?im)^\s*(?:chapter\s+)?title\s*:\s*(.+?)\s*$", markdown_text)
    if match:
        return match.group(1).strip()

    return None


def _extract_study_guide_title_from_html(content: str) -> str | None:
    match = re.search(
        r'(?is)<h[1-6][^>]*>\s*(?:chapter\s+)?title\s*</h[1-6]>(.*?)(?=<h[1-6][^>]*>|<hr\s*/?>|\Z)',
        content,
    )
    if not match:
        return None

    raw_html = match.group(1)
    raw_html = re.sub(r"<br\s*/?>", "\n", raw_html, flags=re.IGNORECASE)
    raw_html = re.sub(r"</p\s*>", "\n", raw_html, flags=re.IGNORECASE)
    plain = re.sub(r"<[^>]+>", " ", raw_html)
    plain = html.unescape(plain)
    plain = re.sub(r"[ \t]+", " ", plain)
    return _first_content_line(plain)


def _first_content_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped
    return None


def _normalize_generated_title(title: str, chapter: str | None) -> str | None:
    cleaned = title.strip().strip('"').strip("'")
    cleaned = re.sub(r"[*_`#]+", "", cleaned).strip(" :-")
    if chapter:
        cleaned = re.sub(
            rf"(?i)^chapter\s+{re.escape(chapter)}\s*[:\-]\s*",
            "",
            cleaned,
        ).strip()
    cleaned = re.sub(r"(?i)^chapter\s+\d+(?:\.\d+)?(?:\s*&\s*\d+(?:\.\d+)?)?\s*[:\-]\s*", "", cleaned).strip()
    return cleaned or None


def load_assignment_files(output_dir: Path) -> list[Path]:
    assignments_dir = output_dir / "downloads" / "assignments"
    if not assignments_dir.exists():
        return []
    return sorted(assignments_dir.glob("*.pdf"))


def match_assignments_to_record(assignments: list[Path], record: DocumentRecord) -> list[Path]:
    record_chapter = parse_display_name_chapter(record.display_name)
    if not record_chapter:
        return []
    return sorted(
        (path for path in assignments if any(chapter in record_chapter for chapter in parse_assignment_chapters(path.name))),
        key=lambda path: path.name,
    )


def render_assignments_card(assignments: list[Path], site_dir: Path, base_path: str) -> str:
    return render_assignments_card_with_variant(
        assignments=assignments,
        site_dir=site_dir,
        base_path=base_path,
        assignment_prompt_outputs_by_filename={},
        experience_variant="default",
    )


def render_assignments_card_with_variant(
    *,
    assignments: list[Path],
    site_dir: Path,
    base_path: str,
    assignment_prompt_outputs_by_filename: dict[str, list[PromptOutputRecord]],
    experience_variant: str = "default",
) -> str:
    if not assignments:
        return ""
    assignments_dir = site_dir / "assignments"
    assignments_dir.mkdir(parents=True, exist_ok=True)
    rows: list[str] = []
    for source in assignments:
        destination = assignments_dir / source.name
        if not destination.exists() or source.stat().st_mtime_ns != destination.stat().st_mtime_ns:
            shutil.copy2(source, destination)
        href = f"{base_path}assignments/{source.name}" if base_path else f"assignments/{source.name}"
        primary_link = f'<a href="{html.escape(href)}">{html.escape("Open Assignment")}</a>'
        grading_links = _render_assignment_artifact_links(
            assignment_filename=source.name,
            assignment_prompt_outputs_by_filename=assignment_prompt_outputs_by_filename,
            site_dir=site_dir,
            base_path=base_path,
        )
        rows.append(
            f"""
          <div class="assignment-row">
            <div class="assignment-row-label">{html.escape(format_assignment_display_name(source))}</div>
            <div class="link-row">
              {primary_link}
              {grading_links}
            </div>
          </div>
        """
        )
    intro_html = (
        '<p class="task-copy">Use these when you want the exact class worksheet after you finish the on-site practice.</p>'
        if experience_variant == "staging"
        else ""
    )
    return f"""
      <section class="prompt-card{' prompt-card-staging' if experience_variant == 'staging' else ''}">
        <h3>{'Class Assignments' if experience_variant == 'staging' else 'Assignments'}</h3>
        {intro_html}
        <div class="chip-row"><span class="chip chip-lock"><span class="auth-icon" aria-hidden="true">&#128737;&#65038;</span>Authorization Required</span></div>
        <div class="assignment-list">
          {''.join(rows)}
        </div>
      </section>
    """


def _render_assignment_artifact_links(
    *,
    assignment_filename: str,
    assignment_prompt_outputs_by_filename: dict[str, list[PromptOutputRecord]],
    site_dir: Path,
    base_path: str,
) -> str:
    prompt_outputs = assignment_prompt_outputs_by_filename.get(assignment_filename, [])
    parts: list[str] = []

    for prompt_output in prompt_outputs:
        if prompt_output.slug != "auto-grading-assignment":
            continue
        if prompt_output.response_html_path and prompt_output.response_html_path.exists():
            href = _build_assignment_scoped_href(
                source=prompt_output.response_html_path,
                site_dir=site_dir,
                base_path=base_path,
            )
            parts.append(f'<a href="{html.escape(href)}" class="button-study-guide">AI Grade</a>')
        if prompt_output.response_pdf_path and prompt_output.response_pdf_path.exists():
            href = _build_assignment_scoped_href(
                source=prompt_output.response_pdf_path,
                site_dir=site_dir,
                base_path=base_path,
            )
            parts.append(f'<a href="{html.escape(href)}" class="pdf-link">PDF</a>')

    return " ".join(parts)


def _build_assignment_scoped_href(*, source: Path, site_dir: Path, base_path: str) -> str:
    assignment_outputs_dir = site_dir / "assignments" / "ai-grading"
    assignment_outputs_dir.mkdir(parents=True, exist_ok=True)
    destination = assignment_outputs_dir / source.name
    if not destination.exists() or source.stat().st_mtime_ns != destination.stat().st_mtime_ns:
        shutil.copy2(source, destination)
    if base_path:
        return f"{base_path}assignments/ai-grading/{destination.name}"
    return build_site_href(path=destination, output_dir=site_dir, site_dir=site_dir, base_path=base_path)


def render_single_model_row_card(
    *,
    title: str,
    specs: tuple[PromptSpec, ...],
    outputs_by_slug: dict[str, PromptOutputRecord],
    link_label: str,
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    build_site_href: Callable[..., str],
    model_label_for_spec: Callable[[PromptSpec], str],
    hide_model: bool = False,
    link_class: str = "",
    description: str = "",
    supplemental_html: str = "",
    experience_variant: str = "default",
) -> str:
    model_rows = _build_model_rows(
        specs=specs,
        outputs_by_slug=outputs_by_slug,
        link_label=link_label,
        output_dir=output_dir,
        site_dir=site_dir,
        base_path=base_path,
        build_site_href=build_site_href,
        model_label_for_spec=model_label_for_spec,
        hide_model=hide_model,
        link_class=link_class,
    )

    if not model_rows and not supplemental_html:
        return ""

    description_html = f'<p class="task-copy">{html.escape(description)}</p>' if description else ""
    return f"""
      <section class="prompt-card{' prompt-card-staging' if experience_variant == 'staging' else ''}">
        <h3>{html.escape(title)}</h3>
        {description_html}
        <div class="chip-row"><span class="chip chip-ai">Generated by AI</span></div>
        {''.join(model_rows)}
        {supplemental_html}
      </section>
    """


def render_inspiring_videos_card(
    *,
    specs: tuple[PromptSpec, ...],
    outputs_by_slug: dict[str, PromptOutputRecord],
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    build_site_href: Callable[..., str],
    model_label_for_spec: Callable[[PromptSpec], str],
    description: str = "",
    experience_variant: str = "default",
) -> str:
    return render_single_model_row_card(
        title="Inspiring Videos",
        specs=specs,
        outputs_by_slug=outputs_by_slug,
        link_label="Watch Picks",
        output_dir=output_dir,
        site_dir=site_dir,
        base_path=base_path,
        build_site_href=build_site_href,
        model_label_for_spec=model_label_for_spec,
        link_class="button-watch-picks",
        description=description,
        experience_variant=experience_variant,
    )


def render_inspiring_videos_inline_section(
    *,
    specs: tuple[PromptSpec, ...],
    outputs_by_slug: dict[str, PromptOutputRecord],
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    build_site_href: Callable[..., str],
    model_label_for_spec: Callable[[PromptSpec], str],
    description: str = "",
) -> str:
    model_rows = _build_model_rows(
        specs=specs,
        outputs_by_slug=outputs_by_slug,
        link_label="Watch Picks",
        output_dir=output_dir,
        site_dir=site_dir,
        base_path=base_path,
        build_site_href=build_site_href,
        model_label_for_spec=model_label_for_spec,
        link_class="button-watch-picks",
    )
    if not model_rows:
        return ""
    description_html = f'<p class="task-copy">{html.escape(description)}</p>' if description else ""
    return f"""
      <div class="prompt-card-subsection prompt-card-subsection-video">
        <div class="prompt-card-subsection-head">
          <h4>Inspiring Videos</h4>
        </div>
        {description_html}
        <div class="chip-row"><span class="chip chip-ai">Generated by AI</span></div>
        {''.join(model_rows)}
      </div>
    """


def render_learning_idea_card(
    *,
    class_note_link: str | None,
    study_specs: tuple[PromptSpec, ...],
    video_specs: tuple[PromptSpec, ...],
    outputs_by_slug: dict[str, PromptOutputRecord],
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    build_site_href: Callable[..., str],
    model_label_for_spec: Callable[[PromptSpec], str],
    experience_variant: str = "default",
) -> str:
    study_rows = _build_model_rows(
        specs=study_specs,
        outputs_by_slug=outputs_by_slug,
        link_label="Read Guide" if experience_variant == "staging" else "Open Guide",
        output_dir=output_dir,
        site_dir=site_dir,
        base_path=base_path,
        build_site_href=build_site_href,
        model_label_for_spec=model_label_for_spec,
        link_class="button-study-guide",
    )
    video_section = render_inspiring_videos_inline_section(
        specs=video_specs,
        outputs_by_slug=outputs_by_slug,
        output_dir=output_dir,
        site_dir=site_dir,
        base_path=base_path,
        build_site_href=build_site_href,
        model_label_for_spec=model_label_for_spec,
        description="Use these when you want a visual walkthrough or a different explanation style before practice.",
    )
    class_note_section = ""
    if class_note_link:
        class_note_section = f"""
      <div class="prompt-card-subsection">
        <div class="prompt-card-subsection-head">
          <h4>Class Notes</h4>
        </div>
        <p class="task-copy">Start here for the exact class notes.</p>
        <div class="link-row">
          {class_note_link}
        </div>
      </div>
    """
    study_section = ""
    if study_rows:
        study_section = f"""
      <div class="prompt-card-subsection">
        <div class="prompt-card-subsection-head">
          <h4>Quick Reference</h4>
        </div>
        <p class="task-copy">Short explanations, examples, and formulas before you solve.</p>
        <div class="chip-row"><span class="chip chip-ai">Generated by AI</span></div>
        {''.join(study_rows)}
      </div>
    """
    if not class_note_section and not study_section and not video_section:
        return ""
    return f"""
      <section class="prompt-card{' prompt-card-staging' if experience_variant == 'staging' else ''}">
        <h3>Learn the Idea</h3>
        <div class="prompt-card-stack">
          {class_note_section}
          {study_section}
          {video_section}
        </div>
      </section>
    """


def render_olympiad_combined(
    *,
    problem_specs: tuple[PromptSpec, ...],
    solution_specs: tuple[PromptSpec, ...],
    outputs_by_slug: dict[str, PromptOutputRecord],
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    build_site_href: Callable[..., str],
    model_label_for_spec: Callable[[PromptSpec], str],
    description: str = "",
    experience_variant: str = "default",
) -> str:
    model_rows: list[str] = []

    for problem_spec, solution_spec in zip(problem_specs, solution_specs):
        problem_output = outputs_by_slug.get(problem_spec.slug)
        solution_output = outputs_by_slug.get(solution_spec.slug)
        has_data = (problem_output and problem_output.processed_at) or (solution_output and solution_output.processed_at)
        if not has_data:
            continue

        def inline_links(output: PromptOutputRecord | None, spec: PromptSpec, label: str) -> str:
            if not output:
                return ""
            parts: list[str] = []
            if output.response_html_path and output.response_html_path.exists():
                href = build_site_href(path=output.response_html_path, output_dir=output_dir, site_dir=site_dir, base_path=base_path)
                parts.append(f'<a href="{html.escape(href)}" class="button-olympiad">{html.escape(label)}</a>')
            if spec.generate_response_pdf and output.response_pdf_path and output.response_pdf_path.exists():
                href = build_site_href(path=output.response_pdf_path, output_dir=output_dir, site_dir=site_dir, base_path=base_path)
                parts.append(f'<a href="{html.escape(href)}" class="pdf-link">PDF</a>')
            return " ".join(parts)

        items_html = "   ".join(part for part in [
            inline_links(problem_output, problem_spec, "Problems"),
            inline_links(solution_output, solution_spec, "Solutions"),
        ] if part)

        model_rows.append(f"""
      <div class="olympiad-model-row">
        {model_chip(problem_spec, model_label_for_spec)}
        <div class="olympiad-links">
          {items_html}
        </div>
      </div>""")

    if not model_rows:
        return ""

    description_html = f'<p class="task-copy">{html.escape(description)}</p>' if description else ""
    return f"""
      <section class="prompt-card{' prompt-card-staging' if experience_variant == 'staging' else ''}">
        <h3>Olympiad Problems &amp; Solutions</h3>
        {description_html}
        <div class="chip-row"><span class="chip chip-ai">Generated by AI</span></div>
        {''.join(model_rows)}
      </section>
    """


def _build_model_rows(
    *,
    specs: tuple[PromptSpec, ...],
    outputs_by_slug: dict[str, PromptOutputRecord],
    link_label: str,
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    build_site_href: Callable[..., str],
    model_label_for_spec: Callable[[PromptSpec], str],
    hide_model: bool = False,
    link_class: str = "",
) -> list[str]:
    model_rows: list[str] = []
    for spec in specs:
        output = outputs_by_slug.get(spec.slug)
        if not output or not output.processed_at:
            continue
        parts: list[str] = []
        if output.response_html_path and output.response_html_path.exists():
            href = build_site_href(path=output.response_html_path, output_dir=output_dir, site_dir=site_dir, base_path=base_path)
            class_attr = f' class="{html.escape(link_class)}"' if link_class else ""
            parts.append(f'<a href="{html.escape(href)}"{class_attr}>{html.escape(link_label)}</a>')
        if spec.generate_response_pdf and output.response_pdf_path and output.response_pdf_path.exists():
            href = build_site_href(path=output.response_pdf_path, output_dir=output_dir, site_dir=site_dir, base_path=base_path)
            parts.append(f'<a href="{html.escape(href)}" class="pdf-link">PDF</a>')
        model_rows.append(f"""
      <div class="olympiad-model-row">
        {"" if hide_model else model_chip(spec, model_label_for_spec)}
        <div class="olympiad-links">
          {' '.join(parts)}
        </div>
      </div>""")
    return model_rows


def model_chip(prompt_spec: PromptSpec, model_label_for_spec: Callable[[PromptSpec], str]) -> str:
    label = model_label_for_spec(prompt_spec)
    model_name = prompt_spec.model or DEFAULT_MODEL
    if prompt_spec.model is None:
        css = "chip"
    elif model_name.startswith("gemini"):
        css = "chip chip-gemini"
    else:
        css = "chip chip-model"
    return f'<span class="{css}">{html.escape(label)}</span>'
