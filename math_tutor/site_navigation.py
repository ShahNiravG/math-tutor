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
    """Return the chapter-list sidebar, which only the library page uses.

    Course identity and the capability-aware nav live in the surface header
    (``site_sections.render_surface_header``). This sidebar is shared by every
    course, so it deliberately names no course and carries no brand mark.
    """

    if page_kind != "library":
        return ""

    toc_items = "\n".join(
        render_sidebar_item(record, active_record, base_path, site_page_href) for record in records
    )
    return f"""
    <aside class="sidebar sidebar-library">
      <div class="sidebar-compact-head">
        <span class="eyebrow">Library</span>
        <h2>Chapters</h2>
        <p>Jump directly into any chapter from here.</p>
      </div>
      <ol class="toc">
        {toc_items}
      </ol>
    </aside>
    """
