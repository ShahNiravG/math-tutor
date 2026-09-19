import unittest

from math_tutor.course_curriculum import (
    AP_CALCULUS_CHAPTER_2,
    ChapterCurriculum,
    CurriculumSection,
    get_chapter_curriculum,
    validate_chapter_curriculum,
)


class CourseCurriculumTests(unittest.TestCase):
    def test_calculus_chapter_two_has_verified_course_scoped_identity(self) -> None:
        curriculum = get_chapter_curriculum("ap-calculus-ab", "2")

        self.assertEqual(curriculum, AP_CALCULUS_CHAPTER_2)
        self.assertEqual(curriculum.title, "Limits and Derivatives")
        self.assertEqual(curriculum.display_label, "Chapter 2: Limits and Derivatives")
        self.assertEqual(
            [section.section_id for section in curriculum.sections],
            ["2.1", "2.2", "2.3", "2.4", "2.5", "2.6", "2.7", "2.8"],
        )
        self.assertEqual(curriculum.provenance, "authenticated-cengage-toc")
        self.assertTrue(curriculum.verified_at)

    def test_chapter_number_does_not_cross_course_boundary(self) -> None:
        self.assertIsNone(get_chapter_curriculum("algebra-2-trig", "2"))
        self.assertIsNone(get_chapter_curriculum("ap-calculus-ab", "3"))

    def test_validation_rejects_duplicate_or_unordered_sections(self) -> None:
        invalid = ChapterCurriculum(
            course_id="ap-calculus-ab",
            chapter="2",
            title="Limits and Derivatives",
            sections=(
                CurriculumSection("2.2", "The Limit of a Function"),
                CurriculumSection("2.1", "The Tangent and Velocity Problems"),
            ),
            provenance="authenticated-cengage-toc",
            verified_at="2026-09-19",
        )

        with self.assertRaisesRegex(ValueError, "unique and strictly ordered"):
            validate_chapter_curriculum(invalid)


if __name__ == "__main__":
    unittest.main()
