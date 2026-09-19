"""Course definitions used by the generated multi-course site."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class CourseConfig:
    course_id: str
    display_name: str
    short_name: str
    description: str
    section_label: str
    content_ready: bool
    canvas_course_url: str
    document_name_pattern: str
    include_assignments_in_note_fetch: bool
    supports_live_tutor: bool
    supports_challenges: bool


COURSE_REGISTRY: tuple[CourseConfig, ...] = (
    CourseConfig(
        course_id="algebra-2-trig",
        display_name="Algebra II / Trigonometry",
        short_name="Algebra II Trig",
        description="Chapter notes, guided study, practice, and challenge exams.",
        section_label="Chapter",
        content_ready=True,
        canvas_course_url="https://mitty.instructure.com/courses/4187",
        document_name_pattern=r"(?:note\.docx|note\.pdf)|\bnote(?:\s*\([^)]*\))?(?:\.docx)?\.pdf$",
        include_assignments_in_note_fetch=True,
        supports_live_tutor=True,
        supports_challenges=True,
    ),
    CourseConfig(
        course_id="ap-calculus-ab",
        display_name="AP Calculus AB",
        short_name="Calculus AB",
        description="A new course space for limits, derivatives, integrals, and their applications.",
        section_label="Chapter",
        content_ready=False,
        canvas_course_url="https://mitty.instructure.com/courses/4446",
        document_name_pattern=r"^chapter\s+\d+\s+notetakers\.pdf$",
        include_assignments_in_note_fetch=False,
        supports_live_tutor=False,
        supports_challenges=False,
    ),
)


def get_course(course_id: str) -> CourseConfig:
    for course in COURSE_REGISTRY:
        if course.course_id == course_id:
            return course
    raise ValueError(f"Unknown course: {course_id}")


def matches_course_document(course_id: str, display_name: str) -> bool:
    course = get_course(course_id)
    return bool(
        re.search(
            course.document_name_pattern,
            display_name.strip(),
            flags=re.IGNORECASE,
        )
    )
