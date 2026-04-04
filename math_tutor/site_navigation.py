"""Sidebar and navigation rendering for generated site pages."""

from __future__ import annotations

import html
from typing import Callable

from math_tutor.chaptering import parse_display_name_chapter
from math_tutor.site_cards import document_label, record_page_filename
from math_tutor.site_models import DocumentRecord


def render_sidebar_item(
    record: DocumentRecord,
    active_record: DocumentRecord | None,
    base_path: str,
    site_page_href: Callable[[str, str], str],
) -> str:
    href = site_page_href(record_page_filename(record), base_path)
    classes = "active" if active_record and active_record.file_id == record.file_id else ""
    chapter = parse_display_name_chapter(record.display_name)
    label = f"Chapter {chapter}" if chapter else document_label(record)
    return f'<li><a class="{classes}" href="{html.escape(href)}">{html.escape(label)}</a></li>'


def render_sidebar_html(
    *,
    records: list[DocumentRecord],
    active_record: DocumentRecord | None,
    base_path: str,
    site_page_href: Callable[[str, str], str],
    page_kind: str,
) -> str:
    toc_items = "\n".join(
        render_sidebar_item(record, active_record, base_path, site_page_href) for record in records
    )
    toc_html = (
        f"""
      <ol class="toc">
        {toc_items}
      </ol>
    """
        if page_kind == "library"
        else ""
    )
    if page_kind == "library":
        return f"""
    <aside class="sidebar sidebar-library">
      <div class="sidebar-compact-head">
        <span class="eyebrow">Library</span>
        <h2>Chapters</h2>
        <p>Jump directly into any chapter from here.</p>
      </div>
      {toc_html}
    </aside>
    """

    home_href = site_page_href("index.html", base_path)
    library_href = site_page_href("library.html", base_path)
    live_tutor_href = site_page_href("live-tutor.html", base_path)
    challenges_href = f"{base_path}challenges/index.html" if base_path else "challenges/index.html"
    home_active = " active" if page_kind == "home" else ""
    library_active = " active" if page_kind in {"library", "record"} else ""
    live_tutor_active = " active" if page_kind == "live-tutor" else ""
    return f"""
    <aside class="sidebar">
      <div class="brand-head">
        <div class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 72 72" role="img" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="brandGlow" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#fff5da"/>
                <stop offset="55%" stop-color="#f3c98f"/>
                <stop offset="100%" stop-color="#cf7c43"/>
              </linearGradient>
            </defs>
            <rect width="72" height="72" rx="16" fill="url(#brandGlow)"/>
            <circle cx="36" cy="36" r="22" fill="none" stroke="#8b4a2c" stroke-width="2.4" opacity="0.35"/>
            <circle cx="36" cy="36" r="14" fill="none" stroke="#8b4a2c" stroke-width="1.7" opacity="0.22"/>
            <path d="M12 43 C21 28, 28 52, 37 37 S53 21, 60 33" fill="none" stroke="#134f59" stroke-width="3.2" stroke-linecap="round"/>
            <circle cx="24" cy="25" r="3.4" fill="#fff7f0" stroke="#8b4a2c" stroke-width="1.4"/>
            <circle cx="51" cy="21" r="2.8" fill="#fff7f0" stroke="#8b4a2c" stroke-width="1.2"/>
            <text x="36" y="53" text-anchor="middle" font-size="21" font-family="Georgia, serif" font-weight="700" fill="#8b4a2c">π</text>
          </svg>
        </div>
        <h1><span class="brand-keep">Algebra II</span> <span class="brand-keep">Trig Tutor</span></h1>
      </div>
      <p>Browse saved class note PDFs alongside the generated tutoring outputs.</p>
      <nav class="global-nav" aria-label="Site sections">
        <a class="nav-pill{home_active}" href="{html.escape(home_href)}">Home</a>
        <a class="nav-pill{library_active}" href="{html.escape(library_href)}">Library</a>
        <a class="nav-pill{live_tutor_active}" href="{html.escape(live_tutor_href)}">Live Tutor</a>
        <a class="nav-pill" href="{html.escape(challenges_href)}">Challenge Exams</a>
      </nav>
      {toc_html}
    </aside>
    """
