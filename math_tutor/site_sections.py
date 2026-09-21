"""Reusable page-section renderers for site pages."""

from __future__ import annotations

import html
from urllib.parse import quote

from math_tutor.site_brand import brand_mark_id_for_course, render_brand_mark
from math_tutor.site_courses import CourseConfig


def render_surface_header(
    *,
    active: str,
    base_path: str,
    eyebrow: str,
    title: str,
    site_page_href,
    course: CourseConfig,
    portal_href: str,
    experience_variant: str = "default",
) -> str:
    home_href = site_page_href("index.html", base_path)
    library_href = site_page_href("library.html", base_path)
    live_tutor_href = site_page_href("live-tutor.html", base_path)
    challenges_href = f"{base_path}challenges/index.html" if base_path else "challenges/index.html"
    subtitle_html = ""
    if experience_variant == "staging":
        subtitle_html = (
            '<p class="surface-subtitle">The exact school material, organized chapter by chapter.</p>'
            if not course.supports_live_tutor and not course.supports_challenges
            else '<p class="surface-subtitle">Clear next steps, visible progress, and faster paths from chapter review to practice.</p>'
            if active == "home"
            else '<p class="surface-subtitle">Built for quick review, low-friction practice, and calm challenge mode.</p>'
        )
    optional_nav_links = ""
    if course.supports_live_tutor:
        optional_nav_links += f'<a class="nav-pill{" active" if active == "live-tutor" else ""}" href="{html.escape(live_tutor_href)}">Live Tutor</a>'
    if course.supports_challenges:
        optional_nav_links += f'<a class="nav-pill{" active" if active == "challenges" else ""}" href="{html.escape(challenges_href)}">Challenge Exams</a>'
    return f"""
    <section class="surface-header{' surface-header-staging' if experience_variant == 'staging' else ''}">
      <div class="surface-brand">
        <div class="brand-mark">{render_brand_mark(mark_id=brand_mark_id_for_course(course.course_id), variant_id="surface")}</div>
        <div class="surface-brand-copy">
          <span class="eyebrow">{html.escape(eyebrow)}</span>
          <h2>{html.escape(title)}</h2>
          <span class="course-context">{html.escape(course.display_name)}</span>
        </div>
      </div>
      {subtitle_html}
      <nav class="surface-nav" aria-label="Site sections">
        <a class="nav-pill{' active' if active == 'home' else ''}" href="{html.escape(home_href)}">Home</a>
        <a class="nav-pill{' active' if active == 'library' else ''}" href="{html.escape(library_href)}">Library</a>
        {optional_nav_links}
        <a class="nav-pill nav-pill-switch" href="{html.escape(portal_href)}">Switch Course</a>
      </nav>
    </section>
    """


def render_guided_learning_card(
    *,
    title: str,
    description: str,
    prompt_text: str,
    extra_links: list[str],
    experience_variant: str = "default",
) -> str:
    escaped_prompt = html.escape(prompt_text, quote=True)
    gemini_href = f"https://gemini.google.com/guided-learning?query={quote(prompt_text)}"
    buttons: list[str] = [
        f'<a href="{html.escape(gemini_href, quote=True)}" target="_blank" rel="noopener noreferrer">Open Gemini</a>',
        '<a href="https://chatgpt.com/studymode" target="_blank" rel="noopener noreferrer">Open ChatGPT</a>',
        (
            f'<button type="button" data-chatgpt-prompt="{escaped_prompt}" '
            f'onclick="copyChatgptPrompt(this)">Copy Prompt</button>'
        ),
    ]
    buttons.extend(extra_links)

    prompt_summary = (
        "Use this only when you want an external AI coach. Math Delight should still feel complete even if you skip it."
        if experience_variant == "staging"
        else "Use the copied prompt as your starting context. In Gemini, switch to Guided Learning. In ChatGPT, use Study Mode."
    )
    summary_label = "See setup prompt" if experience_variant == "staging" else "Show prompt"
    return f"""
      <section class="guided-card{' guided-card-staging' if experience_variant == 'staging' else ''}">
        <h3>{html.escape(title)}</h3>
        <p>{html.escape(description)}</p>
        <div class="button-row">
          {' '.join(buttons)}
        </div>
        <p class="guided-note">{html.escape(prompt_summary)}</p>
        <details>
          <summary>{html.escape(summary_label)}</summary>
          <pre>{html.escape(prompt_text)}</pre>
        </details>
      </section>
    """


def render_index_card(
    *,
    heading: str,
    kicker: str | None = None,
    prompt_count: int,
    page_href: str,
    class_note_link: str | None,
    summary_html: str,
    practice_href: str | None = None,
    challenge_href: str | None = None,
    experience_variant: str = "default",
    learning_only: bool = False,
) -> str:
    if experience_variant == "staging":
        source_only = prompt_count == 0
        action_links: list[str] = (
            [f'<a href="{html.escape(page_href)}">Open Chapter</a>']
            if source_only
            else [f'<a href="{html.escape(page_href)}">Open Study Guide</a>']
            if learning_only
            else [
                f'<a href="{html.escape(page_href)}">Learn</a>',
                f'<a href="{html.escape(practice_href or page_href)}">Practice</a>',
                f'<a href="{html.escape(challenge_href or page_href)}">Challenge</a>',
            ]
        )
        if class_note_link:
            action_links.append(class_note_link)
        return f"""
          <section class="prompt-card overview-card-staging">
            <div class="task-head">
              {f'<span class="task-kicker">{html.escape(kicker)}</span>' if kicker else ''}
              <h3>{html.escape(heading)}</h3>
            </div>
            <div class="chip-row">
              <span class="chip">{'Class note ready' if source_only else f'{prompt_count} study tools ready'}</span>
            </div>
            {summary_html}
            <div class="link-row">
              {' '.join(action_links)}
            </div>
          </section>
        """
    links = [f'<a href="{html.escape(page_href)}">Enter the Lab</a>']
    if class_note_link:
        links.append(class_note_link)
    return f"""
      <section class="prompt-card">
        <h3>{html.escape(heading)}</h3>
        <div class="chip-row">
          <span class="chip">{prompt_count} AI generated section(s)</span>
        </div>
        <div class="link-row">
          {' '.join(links)}
        </div>
        {summary_html}
      </section>
    """
