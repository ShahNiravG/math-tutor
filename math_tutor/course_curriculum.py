"""Verified, course-scoped curriculum metadata used across generation and the site."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CurriculumSection:
    section_id: str
    title: str


@dataclass(frozen=True)
class ChapterCurriculum:
    course_id: str
    chapter: str
    title: str
    sections: tuple[CurriculumSection, ...]
    provenance: str
    verified_at: str

    @property
    def display_label(self) -> str:
        return f"Chapter {self.chapter}: {self.title}"


AP_CALCULUS_CHAPTER_2 = ChapterCurriculum(
    course_id="ap-calculus-ab",
    chapter="2",
    title="Limits and Derivatives",
    sections=(
        CurriculumSection("2.1", "The Tangent and Velocity Problems"),
        CurriculumSection("2.2", "The Limit of a Function"),
        CurriculumSection("2.3", "Calculating Limits Using the Limit Laws"),
        CurriculumSection("2.4", "The Precise Definition of a Limit"),
        CurriculumSection("2.5", "Continuity"),
        CurriculumSection("2.6", "Limits at Infinity; Horizontal Asymptotes"),
        CurriculumSection("2.7", "Derivatives and Rates of Change"),
        CurriculumSection("2.8", "The Derivative as a Function"),
    ),
    provenance="authenticated-cengage-toc",
    verified_at="2026-09-19",
)


CHAPTER_CURRICULA: tuple[ChapterCurriculum, ...] = (AP_CALCULUS_CHAPTER_2,)


def _section_sort_key(section_id: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in section_id.split("."))
    except ValueError as exc:
        raise ValueError(f"Invalid curriculum section ID: {section_id}") from exc


def validate_chapter_curriculum(curriculum: ChapterCurriculum) -> None:
    if not all(
        (
            curriculum.course_id,
            curriculum.chapter,
            curriculum.title,
            curriculum.provenance,
            curriculum.verified_at,
        )
    ):
        raise ValueError("Chapter curriculum identity and provenance must be complete.")
    section_ids = [section.section_id for section in curriculum.sections]
    if not section_ids or section_ids != sorted(set(section_ids), key=_section_sort_key):
        raise ValueError("Curriculum sections must be unique and strictly ordered.")
    if any(not section.section_id or not section.title for section in curriculum.sections):
        raise ValueError("Curriculum section identity must be complete.")


def get_chapter_curriculum(course_id: str, chapter: str) -> ChapterCurriculum | None:
    for curriculum in CHAPTER_CURRICULA:
        if curriculum.course_id == course_id and curriculum.chapter == chapter:
            validate_chapter_curriculum(curriculum)
            return curriculum
    return None


for _curriculum in CHAPTER_CURRICULA:
    validate_chapter_curriculum(_curriculum)
