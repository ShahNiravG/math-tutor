from __future__ import annotations

import unittest
from pathlib import Path

from math_tutor.site_models import DocumentRecord
from math_tutor.site_navigation import render_sidebar_html


def _record(file_id: str = "1", display_name: str = "Alg 2 Trig H Chp 5.1 Note.docx") -> DocumentRecord:
    return DocumentRecord(
        file_id=file_id,
        display_name=display_name,
        pdf_path=Path(f"/tmp/{file_id}.pdf"),
        download_url=None,
        fetched_at=None,
        prompt_outputs=[],
    )


def _sidebar(page_kind: str) -> str:
    return render_sidebar_html(
        records=[_record()],
        active_record=None,
        base_path="/site/courses/algebra-2-trig/",
        site_page_href=lambda filename, base_path: f"{base_path}{filename}",
        page_kind=page_kind,
    )


# page_kind values actually produced by site_pages.py.
LIVE_PAGE_KINDS = ("home", "library", "record", "live-tutor")


class SidebarTests(unittest.TestCase):
    def test_sidebar_never_hardcodes_a_course_name(self) -> None:
        """The sidebar is shared by every course, so it cannot name one.

        The surface header in site_sections.py owns course identity and renders
        it from the CourseConfig.
        """

        for page_kind in LIVE_PAGE_KINDS:
            with self.subTest(page_kind=page_kind):
                self.assertNotIn("Algebra II", _sidebar(page_kind))

    def test_sidebar_does_not_carry_its_own_copy_of_the_brand_mark(self) -> None:
        """Brand marks come from site_brand.py via the header, never inline here."""

        for page_kind in LIVE_PAGE_KINDS:
            with self.subTest(page_kind=page_kind):
                self.assertNotIn("brand-mark", _sidebar(page_kind))

    def test_sidebar_does_not_run_a_second_hardcoded_nav(self) -> None:
        """Capability-aware nav belongs to the surface header alone.

        A hardcoded Live Tutor / Challenge Exams list here would offer Calculus
        destinations that the course does not support.
        """

        for page_kind in LIVE_PAGE_KINDS:
            with self.subTest(page_kind=page_kind):
                sidebar = _sidebar(page_kind)
                self.assertNotIn("Live Tutor", sidebar)
                self.assertNotIn("Challenge Exams", sidebar)

    def test_library_sidebar_still_lists_chapters(self) -> None:
        sidebar = _sidebar("library")

        self.assertIn("Chapter 5.1", sidebar)
        self.assertIn('class="toc"', sidebar)

    def test_non_library_pages_render_no_sidebar(self) -> None:
        for page_kind in ("home", "record", "live-tutor"):
            with self.subTest(page_kind=page_kind):
                self.assertEqual(_sidebar(page_kind).strip(), "")


if __name__ == "__main__":
    unittest.main()
