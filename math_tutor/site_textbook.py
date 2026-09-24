"""Validated, non-secret textbook navigation metadata for generated course pages."""

from __future__ import annotations

from dataclasses import dataclass
import html
from urllib.parse import parse_qsl, urlsplit

from math_tutor.calculus_chapters import (
    AP_CALCULUS_CHAPTER_2_MANIFEST,
    CALCULUS_CHAPTER_MANIFESTS,
    CalculusChapterManifest,
    validate_calculus_chapter_manifest,
)


CANVAS_HOST = "mitty.instructure.com"
CENGAGE_READER_HOST = "ng.cengage.com"
CENGAGE_READER_PATH = "/static/nb/ui/evo/index.html"
ALLOWED_READER_QUERY_KEYS = {"snapshotId", "id", "eISBN"}


@dataclass(frozen=True)
class TextbookSection:
    section_id: str
    title: str
    canvas_assignment_url: str | None


@dataclass(frozen=True)
class TextbookNavigation:
    course_id: str
    chapter: str
    title: str
    reader_url: str
    access_bootstrap_url: str
    sections: tuple[TextbookSection, ...]


def _canvas_assignment_url(assignment_id: str) -> str:
    return f"https://{CANVAS_HOST}/courses/4446/assignments/{assignment_id}"


def build_textbook_navigation(manifest: CalculusChapterManifest) -> TextbookNavigation:
    validate_calculus_chapter_manifest(manifest)
    return TextbookNavigation(
        course_id=manifest.course_id,
        chapter=manifest.chapter,
        title=f"Chapter {manifest.chapter}: {manifest.title}",
        reader_url=manifest.reader_url,
        access_bootstrap_url=_canvas_assignment_url(manifest.access_bootstrap_assignment_id),
        sections=tuple(
            TextbookSection(
                section.section_id,
                section.title,
                (
                    _canvas_assignment_url(section.canvas_assignment_id)
                    if section.canvas_assignment_id is not None
                    else None
                ),
            )
            for section in manifest.sections
        ),
    )


AP_CALCULUS_CHAPTER_2_TEXTBOOK = build_textbook_navigation(AP_CALCULUS_CHAPTER_2_MANIFEST)


TEXTBOOK_NAVIGATION: tuple[TextbookNavigation, ...] = tuple(
    build_textbook_navigation(manifest) for manifest in CALCULUS_CHAPTER_MANIFESTS
)


def validate_textbook_navigation(navigation: TextbookNavigation) -> None:
    if not navigation.course_id or not navigation.chapter or not navigation.title:
        raise ValueError("Textbook navigation identity must be complete.")

    reader = urlsplit(navigation.reader_url)
    if (
        reader.scheme != "https"
        or reader.hostname != CENGAGE_READER_HOST
        or reader.path != CENGAGE_READER_PATH
        or reader.fragment
    ):
        raise ValueError("Textbook reader URL must use the approved Cengage reader location.")
    reader_query_keys = {key for key, _value in parse_qsl(reader.query, keep_blank_values=True)}
    if reader_query_keys != ALLOWED_READER_QUERY_KEYS:
        raise ValueError("Textbook reader URL query parameter set is not approved.")

    _validate_canvas_assignment_url(navigation.access_bootstrap_url)

    section_ids = [section.section_id for section in navigation.sections]
    if section_ids != sorted(set(section_ids), key=_section_sort_key):
        raise ValueError("Textbook sections must be unique and strictly ordered.")
    for section in navigation.sections:
        if not section.section_id or not section.title:
            raise ValueError("Textbook section identity must be complete.")
        if section.canvas_assignment_url is not None:
            _validate_canvas_assignment_url(section.canvas_assignment_url)


def _validate_canvas_assignment_url(url: str) -> None:
    parsed = urlsplit(url)
    path_parts = parsed.path.strip("/").split("/")
    if (
        parsed.scheme != "https"
        or parsed.hostname != CANVAS_HOST
        or parsed.query
        or parsed.fragment
        or len(path_parts) != 4
        or path_parts[:3] != ["courses", "4446", "assignments"]
        or not path_parts[3].isdigit()
    ):
        raise ValueError("Canvas assignment URL must use the approved course assignment path.")


def _section_sort_key(section_id: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in section_id.split("."))
    except ValueError as exc:
        raise ValueError(f"Invalid textbook section ID: {section_id}") from exc


def get_textbook_navigation(course_id: str, chapter: str) -> TextbookNavigation | None:
    for navigation in TEXTBOOK_NAVIGATION:
        if navigation.course_id == course_id and navigation.chapter == chapter:
            validate_textbook_navigation(navigation)
            return navigation
    return None


def render_textbook_navigation(navigation: TextbookNavigation) -> str:
    validate_textbook_navigation(navigation)
    sections_html = "\n".join(_render_textbook_section(section) for section in navigation.sections)
    bootstrap_url = html.escape(navigation.access_bootstrap_url, quote=True)
    chapter_label = f"Chapter {navigation.chapter}"
    return f"""
    <section class="content-card section-card section-surface textbook-panel" id="textbook">
      <div class="textbook-heading">
        <div>
          <span class="eyebrow">Cengage reference</span>
          <h3>{html.escape(chapter_label)} textbook</h3>
          <p class="page-intro">Open the protected textbook through the school&apos;s normal Canvas launch.</p>
          <div class="chip-row"><span class="chip chip-lock"><span class="auth-icon" aria-hidden="true">&#128737;&#65038;</span>Authorization Required</span></div>
        </div>
        <span class="textbook-edition">{html.escape(navigation.title)}</span>
      </div>
      <div class="textbook-access-path" aria-label="How to open the protected textbook">
        <div class="textbook-access-step">
          <span class="textbook-step-number">1</span>
          <div>
            <strong>Open {html.escape(chapter_label)} through Canvas</strong>
            <p>Canvas opens the entitled WebAssign course. In WebAssign, choose <strong>Read It</strong> beside a problem to open the textbook.</p>
            <a class="hero-action primary" href="{bootstrap_url}" target="_blank" rel="noopener noreferrer">Open {html.escape(chapter_label)} through Canvas</a>
          </div>
        </div>
      </div>
      <div class="textbook-section-head">
        <span class="eyebrow">Chapter map</span>
        <p>Choose a section below. For a textbook-only section, open <strong>Full Book</strong> in MindTap after using a Canvas launch.</p>
      </div>
      <div class="textbook-sections">
        {sections_html}
      </div>
      <p class="textbook-access-note">Cengage login and an active course entitlement are required. Math Delight does not store your Cengage session.</p>
    </section>
    """


def _render_textbook_section(section: TextbookSection) -> str:
    if section.canvas_assignment_url is None:
        action_html = '<span class="textbook-section-status">Textbook section</span>'
    else:
        assignment_url = html.escape(section.canvas_assignment_url, quote=True)
        action_html = (
            f'<a href="{assignment_url}" target="_blank" rel="noopener noreferrer">'
            "Open homework</a>"
        )
    return f"""
        <div class="textbook-section">
          <span class="textbook-section-number">{html.escape(section.section_id)}</span>
          <div class="textbook-section-copy">
            <strong>{html.escape(section.title)}</strong>
            {action_html}
          </div>
        </div>"""


for _navigation in TEXTBOOK_NAVIGATION:
    validate_textbook_navigation(_navigation)
