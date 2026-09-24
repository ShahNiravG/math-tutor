from __future__ import annotations

import unittest
from dataclasses import replace

from math_tutor.calculus_chapters import (
    AP_CALCULUS_CHAPTER_2_MANIFEST,
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


if __name__ == "__main__":
    unittest.main()
