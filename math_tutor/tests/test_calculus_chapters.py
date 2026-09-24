from __future__ import annotations

import unittest
from dataclasses import replace

from math_tutor.calculus_chapters import (
    AP_CALCULUS_CHAPTER_2_MANIFEST,
    AP_CALCULUS_CHAPTER_3_MANIFEST,
    CalculusSectionManifest,
    get_calculus_chapter_manifest,
    validate_calculus_chapter_manifest,
)


class CalculusChapterManifestTests(unittest.TestCase):
    def test_chapter_two_manifest_is_the_single_reviewed_source(self) -> None:
        manifest = get_calculus_chapter_manifest("ap-calculus-ab", "2")

        self.assertIs(manifest, AP_CALCULUS_CHAPTER_2_MANIFEST)
        self.assertEqual(manifest.title, "Limits and Derivatives")
        self.assertEqual([section.section_id for section in manifest.sections], [f"2.{index}" for index in range(1, 9)])
        self.assertEqual(manifest.access_bootstrap_assignment_id, "299777")
        self.assertEqual(manifest.sections[3].challenge_status, "excluded")
        self.assertEqual(manifest.sections[7].challenge_status, "limited")

    def test_chapter_three_manifest_drives_the_complete_page_scope(self) -> None:
        manifest = get_calculus_chapter_manifest("ap-calculus-ab", "3")

        self.assertIsNotNone(manifest)
        assert manifest is not None
        self.assertEqual(manifest.title, "Differentiation Rules")
        self.assertEqual(
            [section.section_id for section in manifest.sections],
            [f"3.{index}" for index in range(1, 11)],
        )
        self.assertTrue(all(section.canvas_assignment_id for section in manifest.sections))

    def test_manifest_rejects_unordered_sections(self) -> None:
        unsafe = replace(
            AP_CALCULUS_CHAPTER_2_MANIFEST,
            sections=(
                CalculusSectionManifest("2.2", "The Limit of a Function", "299778"),
                CalculusSectionManifest("2.1", "The Tangent and Velocity Problems", "299777"),
            ),
        )

        with self.assertRaisesRegex(ValueError, "strictly ordered"):
            validate_calculus_chapter_manifest(unsafe)

    def test_manifest_rejects_invalid_assignment_and_challenge_metadata(self) -> None:
        invalid_assignment = replace(
            AP_CALCULUS_CHAPTER_2_MANIFEST,
            access_bootstrap_assignment_id="not-an-id",
        )
        invalid_status = replace(
            AP_CALCULUS_CHAPTER_2_MANIFEST,
            sections=(
                replace(AP_CALCULUS_CHAPTER_2_MANIFEST.sections[0], challenge_status="invented"),
            ),
        )

        with self.assertRaisesRegex(ValueError, "assignment IDs"):
            validate_calculus_chapter_manifest(invalid_assignment)
        with self.assertRaisesRegex(ValueError, "challenge status"):
            validate_calculus_chapter_manifest(invalid_status)

    def test_limited_challenge_section_requires_a_reviewed_topic_label(self) -> None:
        limited_without_label = replace(
            AP_CALCULUS_CHAPTER_2_MANIFEST,
            sections=(
                replace(
                    AP_CALCULUS_CHAPTER_2_MANIFEST.sections[0],
                    challenge_status="limited",
                    challenge_note="Use only the reviewed subset.",
                    challenge_topic_label=None,
                ),
                *AP_CALCULUS_CHAPTER_2_MANIFEST.sections[1:],
            ),
        )

        with self.assertRaisesRegex(ValueError, "reviewed topic label"):
            validate_calculus_chapter_manifest(limited_without_label)

    def test_challenge_scope_requires_forbidden_topics(self) -> None:
        with self.assertRaisesRegex(ValueError, "forbidden topics"):
            validate_calculus_chapter_manifest(
                replace(AP_CALCULUS_CHAPTER_2_MANIFEST, challenge_forbidden_topics=())
            )

    def test_challenge_scope_requires_hard_subtleties(self) -> None:
        with self.assertRaisesRegex(ValueError, "hard subtleties"):
            validate_calculus_chapter_manifest(
                replace(AP_CALCULUS_CHAPTER_2_MANIFEST, challenge_hard_subtleties=())
            )

    def test_reviewed_free_text_rejects_references_to_another_chapter(self) -> None:
        chapter_four_sections = tuple(
            replace(section, section_id=section.section_id.replace("3.", "4.", 1))
            for section in AP_CALCULUS_CHAPTER_3_MANIFEST.sections
        )
        chapter_four = replace(
            AP_CALCULUS_CHAPTER_3_MANIFEST,
            chapter="4",
            sections=chapter_four_sections,
        )
        unsafe_manifests = (
            replace(
                chapter_four,
                sections=(
                    replace(
                        chapter_four.sections[0],
                        challenge_topic_label="review section 3.10",
                    ),
                    *chapter_four.sections[1:],
                ),
            ),
            replace(
                chapter_four,
                sections=(
                    replace(
                        chapter_four.sections[0],
                        challenge_note="Do not use Chapter 3 shortcuts.",
                    ),
                    *chapter_four.sections[1:],
                ),
            ),
            replace(
                chapter_four,
                challenge_forbidden_topics=("section 3.x review",),
            ),
            replace(
                chapter_four,
                challenge_hard_subtleties=("domain", "Chapter 3 behavior"),
            ),
        )

        for manifest in unsafe_manifests:
            with self.subTest(manifest=manifest), self.assertRaisesRegex(
                ValueError, "another chapter"
            ):
                validate_calculus_chapter_manifest(manifest)

    def test_cross_chapter_error_names_the_field_and_matched_text(self) -> None:
        sections = list(AP_CALCULUS_CHAPTER_3_MANIFEST.sections)
        sections[9] = replace(sections[9], challenge_topic_label="error within 0.1")
        decimal_label = replace(AP_CALCULUS_CHAPTER_3_MANIFEST, sections=tuple(sections))
        copied_subtlety = replace(
            AP_CALCULUS_CHAPTER_3_MANIFEST,
            challenge_hard_subtleties=("domain", "Chapter 2 behavior"),
        )

        with self.assertRaisesRegex(
            ValueError, r"challenge_topic_label for section 3\.10 .*'0\.1'.*'error within 0\.1'"
        ):
            validate_calculus_chapter_manifest(decimal_label)
        with self.assertRaisesRegex(
            ValueError, r"challenge_hard_subtleties .*'Chapter 2'.*'Chapter 2 behavior'"
        ):
            validate_calculus_chapter_manifest(copied_subtlety)

    def test_cross_chapter_check_recognizes_chapter_abbreviations(self) -> None:
        for subtlety in ("Ch. 2 behavior", "Chp 2 behavior", "ch 2 behavior"):
            with self.subTest(subtlety=subtlety), self.assertRaisesRegex(
                ValueError, "another chapter"
            ):
                validate_calculus_chapter_manifest(
                    replace(
                        AP_CALCULUS_CHAPTER_3_MANIFEST,
                        challenge_hard_subtleties=("domain", subtlety),
                    )
                )
        for subtlety in ("Ch. 3 behavior", "Chain 2-step rule", "each 2 steps"):
            with self.subTest(subtlety=subtlety):
                validate_calculus_chapter_manifest(
                    replace(
                        AP_CALCULUS_CHAPTER_3_MANIFEST,
                        challenge_hard_subtleties=("domain", subtlety),
                    )
                )


if __name__ == "__main__":
    unittest.main()
