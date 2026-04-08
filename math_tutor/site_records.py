"""Reusable record-page and record-card rendering for generated site pages."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Callable

from math_tutor.chaptering import parse_display_name_chapter
from math_tutor.response_artifacts import render_inline
from math_tutor.site_assets import link_tag
from math_tutor.site_challenges import render_chapter_challenge_card
from math_tutor.site_cards import document_label, document_title, record_page_filename
from math_tutor.site_content import (
    build_guided_learning_prompt,
    extract_record_summary_html,
)
from math_tutor.site_models import DocumentRecord, PromptOutputRecord
from math_tutor.site_prompt_cards import build_document_prompt_card_groups, build_document_prompt_cards_html
from math_tutor.site_sections import render_guided_learning_card, render_index_card


def render_document_overview_card(
    record: DocumentRecord,
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    *,
    include_guided_learning: bool,
    site_page_href: Callable[[str, str], str],
    experience_variant: str = "default",
) -> str:
    prompt_count = sum(1 for prompt_output in record.prompt_outputs if prompt_output.processed_at)
    chapter = parse_display_name_chapter(record.display_name)
    record_summary_html = extract_record_summary_html(record)
    summary_html = f'<div class="card-summary">{record_summary_html}</div>' if record_summary_html else ""
    if include_guided_learning and not summary_html:
        summary_html = f"<p>{render_inline(build_guided_learning_prompt(record))}</p>"
    return render_index_card(
        heading=document_title(record) if experience_variant == "staging" else document_label(record),
        kicker=f"Chapter {chapter}" if experience_variant == "staging" and chapter else None,
        prompt_count=prompt_count,
        page_href=site_page_href(record_page_filename(record), base_path),
        class_note_link=None,
        summary_html="" if experience_variant == "staging" else summary_html,
        practice_href=f'{site_page_href(record_page_filename(record), base_path)}#practice',
        challenge_href=f'{site_page_href(record_page_filename(record), base_path)}#challenge',
        experience_variant=experience_variant,
    )


def render_document_page_content(
    record: DocumentRecord,
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    *,
    include_guided_learning: bool,
    assignments: list[Path] | None = None,
    assignment_prompt_outputs: dict[str, list[PromptOutputRecord]] | None = None,
    site_page_href: Callable[[str, str], str],
    experience_variant: str = "default",
) -> str:
    document_links: list[str] = []
    if record.pdf_path and record.pdf_path.exists():
        document_links.append(
            link_tag(
                record.pdf_path,
                output_dir,
                site_dir,
                "Class Note PDF",
                base_path,
                css_class="button-class-note",
            )
        )

    document_chips: list[str] = []

    prompt_cards_html = build_document_prompt_cards_html(
        record=record,
        output_dir=output_dir,
        site_dir=site_dir,
        base_path=base_path,
        assignments=assignments,
        assignment_prompt_outputs=assignment_prompt_outputs or {},
        experience_variant=experience_variant,
    )
    prompt_groups = build_document_prompt_card_groups(
        record=record,
        output_dir=output_dir,
        site_dir=site_dir,
        base_path=base_path,
        assignments=assignments,
        assignment_prompt_outputs=assignment_prompt_outputs or {},
        experience_variant=experience_variant,
    )
    guided_learning_html = ""
    if include_guided_learning:
        guided_learning_html = render_guided_learning_section(
            record,
            output_dir,
            site_dir,
            base_path,
            experience_variant=experience_variant,
        )
    chapter_challenge_html = render_chapter_challenge_card(
        record,
        base_path,
        site_page_href,
        experience_variant=experience_variant,
    )

    if experience_variant == "staging":
        summary_body = extract_record_summary_html(record) or "<p>No chapter summary is available yet. Start with the class note, then move into practice.</p>"
        learn_cards_html = "\n".join(prompt_groups["learn"])
        practice_cards_html = "\n".join(prompt_groups["practice"])
        resource_cards_html = "\n".join(prompt_groups["resources"] + prompt_groups["extras"])
        resource_panel = f"""
        <aside class="chapter-support-card">
          <h3>Best next move</h3>
          <ol class="chapter-support-list">
            <li><span class="chapter-support-index">1</span><div><strong>Read the chapter idea.</strong> Spend one minute here so the symbols and formulas feel familiar.</div></li>
            <li><span class="chapter-support-index">2</span><div><strong>Do quick practice first.</strong> Build fluency with short questions before taking on tougher work.</div></li>
            <li><span class="chapter-support-index">3</span><div><strong>Save challenge mode for the end.</strong> Use it once you are ready to test yourself.</div></li>
          </ol>
          <div class="hero-action-grid">
            <a class="hero-action primary" href="#practice">Start Practice</a>
            <a class="hero-action" href="#learn">Review Key Idea</a>
            <a class="hero-action" href="#challenge">Take Challenge</a>
          </div>
        </aside>
        """
        resources_section = (
            f"""
        <section class="content-card section-card section-surface" id="resources">
          <div class="section-head">
            <div>
              <span class="eyebrow">Resources</span>
              <h3>Use these when you need a different format</h3>
            </div>
          </div>
          <div class="prompt-grid prompt-grid-compact">
            {resource_cards_html}
          </div>
        </section>
        """
            if resource_cards_html
            else ""
        )
        coach_section = (
            f"""
        <section class="content-card section-card section-surface" id="coach">
          <div class="section-head">
            <div>
              <span class="eyebrow">AI Coach</span>
              <h3>Optional guided help</h3>
            </div>
          </div>
          {guided_learning_html}
        </section>
        """
            if guided_learning_html
            else ""
        )
        challenge_section = (
            f"""
        <section class="content-card section-card section-surface" id="challenge">
          <div class="section-head">
            <div>
              <span class="eyebrow">Challenge</span>
              <h3>Check what sticks without extra hints</h3>
            </div>
          </div>
          {chapter_challenge_html}
        </section>
        """
            if chapter_challenge_html
            else ""
        )
        return f"""
        <section class="content-card chapter-hero-card" id="doc-{record.file_id}">
          <div class="chapter-hero-grid">
            <div class="chapter-hero-main">
              <span class="chapter-kicker">Chapter Focus</span>
              <div class="doc-header">
                <h2>{html.escape(document_label(record))}</h2>
              </div>
              <div class="chip-row">
                {' '.join(document_chips)}
                <span class="chip">Learn</span>
                <span class="chip">Practice</span>
                <span class="chip">Challenge</span>
              </div>
              <div class="chapter-summary-panel">
                <h3>What this chapter is about</h3>
                <div class="card-summary">
                  {summary_body}
                </div>
              </div>
            </div>
            {resource_panel}
          </div>
        </section>
        <section class="content-card section-card section-surface" id="learn">
          <div class="section-head">
            <div>
              <span class="eyebrow">Learn</span>
              <h3>Review the idea before you solve</h3>
            </div>
          </div>
          <div class="prompt-grid">
            {learn_cards_html}
          </div>
        </section>
        <section class="content-card section-card section-surface" id="practice">
          <div class="section-head">
            <div>
              <span class="eyebrow">Practice</span>
              <h3>Build speed first, then stretch</h3>
            </div>
          </div>
          <p class="page-intro">Start with quick wins. Once those feel easy, move to the stretch problems.</p>
          <div class="prompt-grid">
            {practice_cards_html}
          </div>
        </section>
        {coach_section}
        {challenge_section}
        {resources_section}
        """

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
      <section class="guided-card summary-card">
        <h3>Summary</h3>
        <div class="card-summary">
          {extract_record_summary_html(record) or ""}
        </div>
      </section>
      {guided_learning_html}
      <div class="prompt-grid">
        {prompt_cards_html}
      </div>
      {chapter_challenge_html}
    </section>
    """


def render_guided_learning_section(
    record: DocumentRecord,
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    *,
    experience_variant: str = "default",
) -> str:
    prompt_text = build_guided_learning_prompt(record)
    extra_links: list[str] = []
    if record.pdf_path and record.pdf_path.exists():
        extra_links.append(link_tag(record.pdf_path, output_dir, site_dir, "Class Note PDF", base_path))
    return render_guided_learning_card(
        title="AI Study Coach" if experience_variant == "staging" else "Guided Learning",
        description=(
            "Open Gemini or ChatGPT Study Mode only when you want guided back-and-forth after your own first attempt."
            if experience_variant == "staging"
            else "Open Gemini or ChatGPT Study Mode, then paste the summary prompt below to begin."
        ),
        prompt_text=prompt_text,
        extra_links=extra_links,
        experience_variant=experience_variant,
    )
