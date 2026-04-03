from __future__ import annotations

import unittest

from math_tutor.site_sections import render_index_card, render_surface_header


class SiteSectionsTests(unittest.TestCase):
    def test_render_surface_header_uses_site_page_href_callback(self) -> None:
        html = render_surface_header(
            active="library",
            base_path="/site/",
            eyebrow="Math Delight",
            title="Algebra II Trig Tutor",
            site_page_href=lambda filename, base_path: f"{base_path}{filename}",
        )
        self.assertIn("/site/library.html", html)
        self.assertIn("Challenge Exams", html)

    def test_render_index_card_includes_summary_and_link(self) -> None:
        html = render_index_card(
            heading="Chapter 5.1",
            prompt_count=5,
            page_href="doc-4401267.html",
            class_note_link='<a href="note.pdf">Class Note PDF</a>',
            summary_html='<div class="card-summary"><p>Summary text</p></div>',
        )
        self.assertIn("Chapter 5.1", html)
        self.assertIn("doc-4401267.html", html)
        self.assertIn("Summary text", html)


if __name__ == "__main__":
    unittest.main()
