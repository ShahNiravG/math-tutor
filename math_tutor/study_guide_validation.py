"""Fail-closed validation for generated outputs that require a strict contract."""

from __future__ import annotations

import re

from math_tutor.course_curriculum import AP_CALCULUS_CHAPTER_2
from math_tutor.prompt_catalog import PromptSpec


CALCULUS_STUDY_GUIDE_HEADINGS = (
    "Title",
    "Mastery Goals",
    "Short Summary",
    "Section Coverage",
    "Core Definitions, Theorems, and Formulas",
    "Conceptual Connections",
    "Worked Study Guide",
    "Common Misconceptions and Error Checks",
    "Mastery Practice",
    "Fully Worked Answers",
    "Mastery Checklist",
    "Assumptions, Corrections, and Scope Boundaries",
)
ALLOWED_COVERAGE_STATUSES = ("Covered", "Partially covered", "Not covered")
_PROVIDER_ERROR = re.compile(
    r"(?im)^\s*(?:provider\s+error|error\s*:|\[error\]|request\s+failed)",
)


def validate_prompt_output(prompt_spec: PromptSpec, output_text: str) -> None:
    profile = prompt_spec.validation_profile
    if profile is None:
        return
    if profile != "calculus-study-guide-v1":
        raise ValueError(f"Unknown output validation profile: {profile}")
    _validate_calculus_study_guide(output_text)


def _validate_calculus_study_guide(output_text: str) -> None:
    if not output_text.strip():
        raise ValueError("Calculus study guide output must not be empty.")
    if _PROVIDER_ERROR.search(output_text):
        raise ValueError("Calculus study guide output contains provider error text.")

    headings = re.findall(r"(?m)^## ([^#\n].*?)\s*$", output_text)
    for heading in CALCULUS_STUDY_GUIDE_HEADINGS:
        if headings.count(heading) != 1:
            raise ValueError(f"Required heading must appear exactly once: ## {heading}")
    if tuple(headings) != CALCULUS_STUDY_GUIDE_HEADINGS:
        raise ValueError("Calculus study guide headings must use the required order exactly.")

    title_match = re.search(
        r"(?ms)^## Title\s*\n(.*?)(?=^## )",
        output_text,
    )
    title_lines = [line.strip() for line in title_match.group(1).splitlines() if line.strip()]
    if title_lines != [AP_CALCULUS_CHAPTER_2.title]:
        raise ValueError("Calculus study guide must contain the exact canonical title.")

    section_match = re.search(
        r"(?ms)^## Section Coverage\s*\n(.*?)(?=^## )",
        output_text,
    )
    section_body = section_match.group(1)
    section_headings = re.findall(r"(?m)^### (.+?)\s*$", section_body)
    expected_headings = [
        f"{section.section_id}: {section.title}"
        for section in AP_CALCULUS_CHAPTER_2.sections
    ]
    if section_headings != expected_headings:
        raise ValueError("Calculus study guide must contain exact ordered section coverage entries.")

    chunks = re.split(r"(?m)(?=^### )", section_body)
    section_chunks = [chunk for chunk in chunks if chunk.startswith("### ")]
    status_pattern = re.compile(
        r"(?m)^\*\*Coverage:\*\* (Covered|Partially covered|Not covered)\s*$"
    )
    for expected, chunk in zip(expected_headings, section_chunks, strict=True):
        statuses = status_pattern.findall(chunk)
        if len(statuses) != 1:
            raise ValueError(f"Section {expected} must contain exactly one allowed coverage status.")
        for field in ("PDF evidence", "Mastery scope", "Excluded material"):
            if len(re.findall(rf"(?m)^\*\*{re.escape(field)}:\*\*", chunk)) != 1:
                raise ValueError(f"Section {expected} must contain exactly one {field} field.")

    for heading in ("Worked Study Guide", "Mastery Practice", "Fully Worked Answers"):
        if "**Supplemental mastery aid**" not in _heading_body(output_text, heading):
            raise ValueError(f"{heading} must identify supplemental material as Supplemental mastery aid.")

    not_covered_sections = [
        section
        for section, chunk in zip(AP_CALCULUS_CHAPTER_2.sections, section_chunks, strict=True)
        if status_pattern.findall(chunk) == ["Not covered"]
    ]
    instructional_headings = (
        "Mastery Goals",
        "Core Definitions, Theorems, and Formulas",
        "Conceptual Connections",
        "Worked Study Guide",
        "Common Misconceptions and Error Checks",
        "Mastery Practice",
        "Fully Worked Answers",
        "Mastery Checklist",
    )
    instructional_text = "\n".join(
        _heading_body(output_text, heading) for heading in instructional_headings
    )
    for section in not_covered_sections:
        forbidden_patterns = (
            rf"\bsection\s+{re.escape(section.section_id)}\b",
            re.escape(section.title),
            r"\bepsilon[-–— ]delta\b" if section.section_id == "2.4" else r"(?!)",
        )
        if any(re.search(pattern, instructional_text, flags=re.IGNORECASE) for pattern in forbidden_patterns):
            raise ValueError(
                f"Instructional content includes not-covered section {section.section_id}."
            )

    for heading in ("Mastery Practice", "Fully Worked Answers"):
        item_numbers = [
            int(value)
            for value in re.findall(
                r"(?m)^\s*(?:\*\*)?(\d+)\.(?:\*\*)?\s+",
                _heading_body(output_text, heading),
            )
        ]
        if item_numbers != list(range(1, 11)):
            raise ValueError(f"{heading} must contain exactly ten items numbered 1 through 10.")


def _heading_body(output_text: str, heading: str) -> str:
    match = re.search(
        rf"(?ms)^## {re.escape(heading)}\s*\n(.*?)(?=^## |\Z)",
        output_text,
    )
    return match.group(1) if match else ""
