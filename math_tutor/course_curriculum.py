"""Verified, course-scoped curriculum metadata used across generation and the site."""

from __future__ import annotations

from dataclasses import dataclass

from math_tutor.calculus_chapters import (
    AP_CALCULUS_CHAPTER_2_MANIFEST,
    CALCULUS_CHAPTER_MANIFESTS,
)


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


def _curriculum_from_manifest(manifest) -> ChapterCurriculum:
    return ChapterCurriculum(
        course_id=manifest.course_id,
        chapter=manifest.chapter,
        title=manifest.title,
        sections=tuple(
            CurriculumSection(section.section_id, section.title)
            for section in manifest.sections
        ),
        provenance=manifest.provenance,
        verified_at=manifest.verified_at,
    )


AP_CALCULUS_CHAPTER_2 = _curriculum_from_manifest(AP_CALCULUS_CHAPTER_2_MANIFEST)


CHAPTER_CURRICULA: tuple[ChapterCurriculum, ...] = tuple(
    _curriculum_from_manifest(manifest) for manifest in CALCULUS_CHAPTER_MANIFESTS
)


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
