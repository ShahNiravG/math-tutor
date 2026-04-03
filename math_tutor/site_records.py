"""Reusable record-page and record-card rendering for generated site pages."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Callable

from math_tutor.response_artifacts import render_inline
from math_tutor.site_assets import link_tag
from math_tutor.site_challenges import render_chapter_challenge_card
from math_tutor.site_cards import document_label, record_page_filename
from math_tutor.site_content import (
    build_guided_learning_prompt,
    extract_record_summary_html,
    render_record_summary,
)
from math_tutor.site_models import DocumentRecord
from math_tutor.site_prompt_cards import build_document_prompt_cards_html
from math_tutor.site_sections import render_guided_learning_card, render_index_card


def render_document_overview_card(
    record: DocumentRecord,
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    *,
    include_guided_learning: bool,
    site_page_href: Callable[[str, str], str],
) -> str:
    prompt_count = sum(1 for prompt_output in record.prompt_outputs if prompt_output.processed_at)
    class_note_link = None
    if record.pdf_path and record.pdf_path.exists():
        class_note_link = link_tag(record.pdf_path, output_dir, site_dir, "Class Note PDF", base_path)
    record_summary_html = extract_record_summary_html(record)
    summary_html = f'<div class="card-summary">{record_summary_html}</div>' if record_summary_html else ""
    if include_guided_learning and not summary_html:
        summary_html = f"<p>{render_inline(build_guided_learning_prompt(record))}</p>"
    return render_index_card(
        heading=document_label(record),
        prompt_count=prompt_count,
        page_href=site_page_href(record_page_filename(record), base_path),
        class_note_link=class_note_link,
        summary_html=summary_html,
    )


def render_document_page_content(
    record: DocumentRecord,
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    *,
    include_guided_learning: bool,
    assignments: list[Path] | None = None,
    site_page_href: Callable[[str, str], str],
) -> str:
    document_links: list[str] = []
    if record.pdf_path and record.pdf_path.exists():
        document_links.append(link_tag(record.pdf_path, output_dir, site_dir, "Class Note PDF", base_path))

    document_chips: list[str] = []
    if record.fetched_at:
        document_chips.append(f'<span class="chip">Fetched {html.escape(record.fetched_at)}</span>')

    summary_html = render_record_summary(record)
    prompt_cards_html = build_document_prompt_cards_html(
        record=record,
        output_dir=output_dir,
        site_dir=site_dir,
        base_path=base_path,
        assignments=assignments,
    )
    guided_learning_html = ""
    if include_guided_learning:
        guided_learning_html = render_guided_learning_section(record, output_dir, site_dir, base_path)
    chapter_challenge_html = render_chapter_challenge_card(record, base_path, site_page_href)

    return f"""
    <section class="content-card" id="doc-{record.file_id}">
      <div class="doc-header">
        <h2>{html.escape(document_label(record))}</h2>
      </div>
      <div class="chip-row">
        {' '.join(document_chips)}
      </div>
      <div class="link-row">
        {' '.join(document_links)}
      </div>
      {summary_html}
      {guided_learning_html}
      <div class="prompt-grid">
        {prompt_cards_html}
      </div>
      {chapter_challenge_html}
    </section>
    """


def render_guided_learning_section(record: DocumentRecord, output_dir: Path, site_dir: Path, base_path: str) -> str:
    prompt_text = build_guided_learning_prompt(record)
    extra_links: list[str] = []
    if record.pdf_path and record.pdf_path.exists():
        extra_links.append(link_tag(record.pdf_path, output_dir, site_dir, "Class Note PDF", base_path))
    return render_guided_learning_card(
        title="Guided Learning",
        description="Open Gemini or ChatGPT Study Mode, then paste the summary prompt below to begin.",
        prompt_text=prompt_text,
        extra_links=extra_links,
    )
