from __future__ import annotations

import unittest
from dataclasses import replace

from math_tutor.calculus_chapters import AP_CALCULUS_CHAPTER_2_MANIFEST
from math_tutor.site_textbook import (
    AP_CALCULUS_CHAPTER_2_TEXTBOOK,
    TextbookNavigation,
    TextbookSection,
    build_textbook_navigation,
    get_textbook_navigation,
    render_textbook_navigation,
    validate_textbook_navigation,
)
from math_tutor.site_theme import BASE_SITE_PAGE_STYLES


class SiteTextbookTests(unittest.TestCase):
    def test_navigation_and_labels_are_built_from_a_chapter_manifest(self) -> None:
        chapter_three = replace(
            AP_CALCULUS_CHAPTER_2_MANIFEST,
            chapter="3",
            title="Differentiation Rules",
            sections=tuple(
                replace(
                    section,
                    section_id=section.section_id.replace("2.", "3."),
                    challenge_note=(
                        section.challenge_note.replace("2.", "3.")
                        if section.challenge_note is not None
                        else None
                    ),
                )
                for section in AP_CALCULUS_CHAPTER_2_MANIFEST.sections
            ),
        )

        navigation = build_textbook_navigation(chapter_three)
        rendered = render_textbook_navigation(navigation)

        self.assertEqual(navigation.chapter, "3")
        self.assertIn("Chapter 3 textbook", rendered)
        self.assertIn("Open Chapter 3 through Canvas", rendered)
        self.assertNotIn("Chapter 2 textbook", rendered)

    def test_chapter_two_navigation_is_complete_and_course_scoped(self) -> None:
        navigation = get_textbook_navigation("ap-calculus-ab", "2")

        self.assertEqual(navigation, AP_CALCULUS_CHAPTER_2_TEXTBOOK)
        self.assertEqual(
            [section.section_id for section in navigation.sections],
            ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8"],
        )
        self.assertIsNone(navigation.sections[3].canvas_assignment_url)
        self.assertIsNone(get_textbook_navigation("algebra-2-trig", "2"))

    def test_chapter_three_navigation_uses_discovered_canvas_assignments(self) -> None:
        navigation = get_textbook_navigation("ap-calculus-ab", "3")

        self.assertIsNotNone(navigation)
        assert navigation is not None
        self.assertEqual(len(navigation.sections), 10)
        self.assertTrue(navigation.access_bootstrap_url.endswith("/299784"))
        self.assertTrue(navigation.sections[-1].canvas_assignment_url.endswith("/299793"))

    def test_assignment_links_remain_matched_to_verified_sections(self) -> None:
        assignments = {
            section.section_id: section.canvas_assignment_url
            for section in AP_CALCULUS_CHAPTER_2_TEXTBOOK.sections
        }

        self.assertTrue(assignments["2.1"].endswith("/299777"))
        self.assertIsNone(assignments["2.4"])
        self.assertTrue(assignments["2.5"].endswith("/299780"))
        self.assertTrue(assignments["2.8"].endswith("/299783"))

    def test_validation_rejects_session_bearing_reader_url(self) -> None:
        unsafe = replace(
            AP_CALCULUS_CHAPTER_2_TEXTBOOK,
            reader_url=(
                "https://ng.cengage.com/static/nb/ui/evo/index.html"
                "?snapshotId=1529049&id=677758950&eISBN=9780357049105&token=secret"
            ),
        )

        with self.assertRaisesRegex(ValueError, "reader URL query parameter"):
            validate_textbook_navigation(unsafe)

    def test_validation_rejects_off_domain_assignment_url(self) -> None:
        unsafe_section = replace(
            AP_CALCULUS_CHAPTER_2_TEXTBOOK.sections[0],
            canvas_assignment_url="https://example.com/courses/4446/assignments/299777",
        )
        unsafe = replace(
            AP_CALCULUS_CHAPTER_2_TEXTBOOK,
            sections=(unsafe_section, *AP_CALCULUS_CHAPTER_2_TEXTBOOK.sections[1:]),
        )

        with self.assertRaisesRegex(ValueError, "Canvas assignment URL"):
            validate_textbook_navigation(unsafe)

    def test_validation_rejects_duplicate_or_unordered_sections(self) -> None:
        unsafe = TextbookNavigation(
            course_id="ap-calculus-ab",
            chapter="2",
            title="Chapter 2: Limits and Derivatives",
            reader_url=AP_CALCULUS_CHAPTER_2_TEXTBOOK.reader_url,
            access_bootstrap_url=AP_CALCULUS_CHAPTER_2_TEXTBOOK.access_bootstrap_url,
            sections=(
                TextbookSection("2.2", "The Limit of a Function", None),
                TextbookSection("2.1", "The Tangent and Velocity Problems", None),
            ),
        )

        with self.assertRaisesRegex(ValueError, "strictly ordered"):
            validate_textbook_navigation(unsafe)

    def test_render_navigation_explains_access_and_lists_every_section(self) -> None:
        html = render_textbook_navigation(AP_CALCULUS_CHAPTER_2_TEXTBOOK)

        self.assertIn('id="textbook"', html)
        self.assertIn("Chapter 2 textbook", html)
        self.assertIn("Authorization Required", html)
        self.assertIn('class="chip chip-lock"', html)
        self.assertIn('class="auth-icon" aria-hidden="true"', html)
        self.assertIn("Open Chapter 2 through Canvas", html)
        self.assertIn("Read It", html)
        self.assertIn("Full Book", html)
        self.assertNotIn("Open the textbook", html)
        self.assertIn('target="_blank"', html)
        self.assertIn('rel="noopener noreferrer"', html)
        self.assertIn("https://mitty.instructure.com/courses/4446/assignments/299777", html)
        self.assertNotIn("snapshotId=1529049", html)
        self.assertEqual(html.count('class="textbook-section"'), 8)
        self.assertLess(html.index("2.1"), html.index("2.8"))

        section_24_start = html.index('<span class="textbook-section-number">2.4</span>')
        section_25_start = html.index('<span class="textbook-section-number">2.5</span>')
        section_24 = html[section_24_start:section_25_start]
        self.assertIn("Textbook section", section_24)
        self.assertNotIn("Open homework", section_24)

    def test_textbook_navigation_has_responsive_component_styles(self) -> None:
        for selector in (
            ".textbook-panel",
            ".textbook-access-path",
            ".textbook-access-step",
            ".textbook-sections",
            ".textbook-section",
            ".textbook-access-note",
        ):
            self.assertIn(selector, BASE_SITE_PAGE_STYLES)
        self.assertIn("grid-template-columns: 1fr;", BASE_SITE_PAGE_STYLES)


if __name__ == "__main__":
    unittest.main()
