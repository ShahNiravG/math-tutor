"""Reviewed, non-secret manifests for AP Calculus AB chapters."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CalculusSectionManifest:
    section_id: str
    title: str
    canvas_assignment_id: str | None = None
    challenge_status: str = "included"
    challenge_note: str | None = None


@dataclass(frozen=True)
class CalculusChapterManifest:
    course_id: str
    chapter: str
    title: str
    sections: tuple[CalculusSectionManifest, ...]
    reader_url: str
    access_bootstrap_assignment_id: str
    provenance: str
    verified_at: str


AP_CALCULUS_CHAPTER_2_MANIFEST = CalculusChapterManifest(
    course_id="ap-calculus-ab",
    chapter="2",
    title="Limits and Derivatives",
    sections=(
        CalculusSectionManifest("2.1", "The Tangent and Velocity Problems", "299777"),
        CalculusSectionManifest("2.2", "The Limit of a Function", "299778"),
        CalculusSectionManifest("2.3", "Calculating Limits Using the Limit Laws", "299779"),
        CalculusSectionManifest(
            "2.4",
            "The Precise Definition of a Limit",
            challenge_status="excluded",
            challenge_note="Do not test the formal epsilon-delta definition.",
        ),
        CalculusSectionManifest("2.5", "Continuity", "299780"),
        CalculusSectionManifest("2.6", "Limits at Infinity; Horizontal Asymptotes", "299781"),
        CalculusSectionManifest("2.7", "Derivatives and Rates of Change", "299782"),
        CalculusSectionManifest(
            "2.8",
            "The Derivative as a Function",
            "299783",
            challenge_status="limited",
            challenge_note="Use introductory derivative-as-a-function concepts only.",
        ),
    ),
    reader_url=(
        "https://ng.cengage.com/static/nb/ui/evo/index.html"
        "?snapshotId=1529049&id=677758950&eISBN=9780357049105"
    ),
    access_bootstrap_assignment_id="299777",
    provenance="authenticated-cengage-toc",
    verified_at="2026-09-19",
)


AP_CALCULUS_CHAPTER_3_MANIFEST = CalculusChapterManifest(
    course_id="ap-calculus-ab",
    chapter="3",
    title="Differentiation Rules",
    sections=(
        CalculusSectionManifest(
            "3.1", "Derivatives of Polynomials and Exponential Functions", "299784"
        ),
        CalculusSectionManifest("3.2", "Product and Quotient Rules", "299785"),
        CalculusSectionManifest("3.3", "Derivatives of Trigonometric Functions", "299786"),
        CalculusSectionManifest("3.4", "The Chain Rule", "299787"),
        CalculusSectionManifest("3.5", "Implicit Differentiation", "299788"),
        CalculusSectionManifest(
            "3.6", "Derivatives of Logarithmic and Inverse Trigonometric Functions", "299789"
        ),
        CalculusSectionManifest("3.7", "Rates of Change and Physics Applications", "299790"),
        CalculusSectionManifest("3.8", "Exponential Growth and Decay", "299791"),
        CalculusSectionManifest("3.9", "Related Rates", "299792"),
        CalculusSectionManifest("3.10", "Linear Approximations and Differentials", "299793"),
    ),
    reader_url=(
        "https://ng.cengage.com/static/nb/ui/evo/index.html"
        "?snapshotId=1529049&id=677758950&eISBN=9780357049105"
    ),
    access_bootstrap_assignment_id="299784",
    provenance="school-pdf-and-authenticated-canvas-cengage-assignments",
    verified_at="2026-09-23",
)


CALCULUS_CHAPTER_MANIFESTS: tuple[CalculusChapterManifest, ...] = (
    AP_CALCULUS_CHAPTER_2_MANIFEST,
    AP_CALCULUS_CHAPTER_3_MANIFEST,
)


def _section_sort_key(section_id: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in section_id.split("."))
    except ValueError as exc:
        raise ValueError(f"Invalid section ID: {section_id}") from exc


def validate_calculus_chapter_manifest(manifest: CalculusChapterManifest) -> None:
    if not all(
        (
            manifest.course_id,
            manifest.chapter,
            manifest.title,
            manifest.reader_url,
            manifest.access_bootstrap_assignment_id,
            manifest.provenance,
            manifest.verified_at,
        )
    ):
        raise ValueError("Calculus chapter identity and provenance must be complete.")
    if manifest.course_id != "ap-calculus-ab" or not manifest.chapter.isdigit():
        raise ValueError("Calculus chapter identity is invalid.")
    section_ids = [section.section_id for section in manifest.sections]
    if not section_ids or section_ids != sorted(set(section_ids), key=_section_sort_key):
        raise ValueError("Calculus sections must be unique and strictly ordered.")
    if any(not section_id.startswith(f"{manifest.chapter}.") for section_id in section_ids):
        raise ValueError("Calculus section IDs must belong to their chapter.")
    assignment_ids = [
        section.canvas_assignment_id
        for section in manifest.sections
        if section.canvas_assignment_id is not None
    ]
    if (
        not manifest.access_bootstrap_assignment_id.isdigit()
        or any(not assignment_id.isdigit() for assignment_id in assignment_ids)
        or manifest.access_bootstrap_assignment_id not in assignment_ids
    ):
        raise ValueError("Canvas assignment IDs must be numeric and include the access bootstrap.")
    allowed_statuses = {"included", "limited", "excluded"}
    for section in manifest.sections:
        if not section.section_id or not section.title:
            raise ValueError("Calculus section identity must be complete.")
        if section.challenge_status not in allowed_statuses:
            raise ValueError(f"Invalid challenge status: {section.challenge_status}")
        if section.challenge_status != "included" and not section.challenge_note:
            raise ValueError("Limited or excluded challenge sections require a review note.")


def get_calculus_chapter_manifest(
    course_id: str,
    chapter: str,
) -> CalculusChapterManifest | None:
    for manifest in CALCULUS_CHAPTER_MANIFESTS:
        if manifest.course_id == course_id and manifest.chapter == chapter:
            validate_calculus_chapter_manifest(manifest)
            return manifest
    return None


for _manifest in CALCULUS_CHAPTER_MANIFESTS:
    validate_calculus_chapter_manifest(_manifest)
