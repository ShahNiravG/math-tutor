"""Reusable page-section renderers for site pages."""

from __future__ import annotations

import html
from urllib.parse import quote


def render_surface_header(
    *,
    active: str,
    base_path: str,
    eyebrow: str,
    title: str,
    site_page_href,
    experience_variant: str = "default",
) -> str:
    home_href = site_page_href("index.html", base_path)
    library_href = site_page_href("library.html", base_path)
    live_tutor_href = site_page_href("live-tutor.html", base_path)
    challenges_href = f"{base_path}challenges/index.html" if base_path else "challenges/index.html"
    subtitle_html = ""
    if experience_variant == "staging":
        subtitle_html = (
            '<p class="surface-subtitle">Clear next steps, visible progress, and faster paths from chapter review to practice.</p>'
            if active == "home"
            else '<p class="surface-subtitle">Built for quick review, low-friction practice, and calm challenge mode.</p>'
        )
    return f"""
    <section class="surface-header{' surface-header-staging' if experience_variant == 'staging' else ''}">
      <div class="surface-brand">
        <div class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 72 72" role="img" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="surfaceBrandGlow" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#fff5da"/>
                <stop offset="55%" stop-color="#f3c98f"/>
                <stop offset="100%" stop-color="#cf7c43"/>
              </linearGradient>
            </defs>
            <rect width="72" height="72" rx="16" fill="url(#surfaceBrandGlow)"/>
            <circle cx="36" cy="36" r="22" fill="none" stroke="#8b4a2c" stroke-width="2.4" opacity="0.35"/>
            <circle cx="36" cy="36" r="14" fill="none" stroke="#8b4a2c" stroke-width="1.7" opacity="0.22"/>
            <path d="M12 43 C21 28, 28 52, 37 37 S53 21, 60 33" fill="none" stroke="#134f59" stroke-width="3.2" stroke-linecap="round"/>
            <circle cx="24" cy="25" r="3.4" fill="#fff7f0" stroke="#8b4a2c" stroke-width="1.4"/>
            <circle cx="51" cy="21" r="2.8" fill="#fff7f0" stroke="#8b4a2c" stroke-width="1.2"/>
            <text x="36" y="53" text-anchor="middle" font-size="21" font-family="Georgia, serif" font-weight="700" fill="#8b4a2c">π</text>
          </svg>
        </div>
        <div class="surface-brand-copy">
          <span class="eyebrow">{html.escape(eyebrow)}</span>
          <h2>{html.escape(title)}</h2>
        </div>
      </div>
      {subtitle_html}
      <nav class="surface-nav" aria-label="Site sections">
        <a class="nav-pill{' active' if active == 'home' else ''}" href="{html.escape(home_href)}">Home</a>
        <a class="nav-pill{' active' if active == 'library' else ''}" href="{html.escape(library_href)}">Library</a>
        <a class="nav-pill{' active' if active == 'live-tutor' else ''}" href="{html.escape(live_tutor_href)}">Live Tutor</a>
        <a class="nav-pill{' active' if active == 'challenges' else ''}" href="{html.escape(challenges_href)}">Challenge Exams</a>
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
    prompt_count: int,
    page_href: str,
    class_note_link: str | None,
    summary_html: str,
    practice_href: str | None = None,
    challenge_href: str | None = None,
    experience_variant: str = "default",
) -> str:
    if experience_variant == "staging":
        action_links: list[str] = [
            f'<a href="{html.escape(page_href)}">Learn</a>',
            f'<a href="{html.escape(practice_href or page_href)}">Practice</a>',
            f'<a href="{html.escape(challenge_href or page_href)}">Challenge</a>',
        ]
        if class_note_link:
            action_links.append(class_note_link)
        return f"""
          <section class="prompt-card overview-card-staging">
            <div class="task-head">
              <span class="task-kicker">{html.escape(heading)}</span>
            </div>
            <div class="chip-row">
              <span class="chip">{prompt_count} study tools ready</span>
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
