from dataclasses import replace
import unittest

from math_tutor.prompt_catalog import PROMPTS_BY_SLUG, resolve_selected_prompts
from math_tutor.study_guide_validation import validate_prompt_output


def valid_calculus_study_guide() -> str:
    section_titles = (
        ("2.1", "The Tangent and Velocity Problems"),
        ("2.2", "The Limit of a Function"),
        ("2.3", "Calculating Limits Using the Limit Laws"),
        ("2.4", "The Precise Definition of a Limit"),
        ("2.5", "Continuity"),
        ("2.6", "Limits at Infinity; Horizontal Asymptotes"),
        ("2.7", "Derivatives and Rates of Change"),
        ("2.8", "The Derivative as a Function"),
    )
    coverage = "\n\n".join(
        f"### {section_id}: {title}\n"
        f"**Coverage:** {'Not covered' if section_id == '2.4' else 'Covered'}\n"
        "**PDF evidence:** Evidence.\n"
        "**Mastery scope:** Supported scope.\n"
        "**Excluded material:** None."
        for section_id, title in section_titles
    )
    return f"""## Title
Limits and Derivatives

## Mastery Goals
Master limits and derivatives covered by the PDF.

## Short Summary
Limits lead to derivatives.

## Section Coverage
{coverage}

## Core Definitions, Theorems, and Formulas
Content.

## Conceptual Connections
Content.

## Worked Study Guide
**Supplemental mastery aid**
Content.

## Common Misconceptions and Error Checks
Content.

## Mastery Practice
**Supplemental mastery aid**
1. Problem one.
2. Problem two.
3. Problem three.
4. Problem four.
5. Problem five.
6. Problem six.
7. Problem seven.
8. Problem eight.
9. Problem nine.
10. Problem ten.

## Fully Worked Answers
**Supplemental mastery aid**
1. Answer one.
2. Answer two.
3. Answer three.
4. Answer four.
5. Answer five.
6. Answer six.
7. Answer seven.
8. Answer eight.
9. Answer nine.
10. Answer ten.

## Mastery Checklist
Checklist.

## Assumptions, Corrections, and Scope Boundaries
Section 2.4 is not covered and is intentionally excluded from teaching and practice.
"""


class StudyGuideValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.prompt = resolve_selected_prompts(
            ["study-guide"], course_id="ap-calculus-ab"
        )[0]

    def test_valid_calculus_study_guide_passes(self) -> None:
        validate_prompt_output(self.prompt, valid_calculus_study_guide())

    def test_rejects_wrong_or_duplicate_title(self) -> None:
        with self.assertRaisesRegex(ValueError, "canonical title"):
            validate_prompt_output(
                self.prompt,
                valid_calculus_study_guide().replace(
                    "Limits and Derivatives", "A Different Title", 1
                ),
            )
        with self.assertRaisesRegex(ValueError, "exactly once"):
            validate_prompt_output(
                self.prompt,
                valid_calculus_study_guide() + "\n## Title\nLimits and Derivatives\n",
            )

    def test_rejects_missing_reordered_or_invalid_coverage(self) -> None:
        with self.assertRaisesRegex(ValueError, "ordered section coverage"):
            validate_prompt_output(
                self.prompt,
                valid_calculus_study_guide().replace("### 2.1:", "### 2.8:", 1),
            )
        with self.assertRaisesRegex(ValueError, "coverage status"):
            validate_prompt_output(
                self.prompt,
                valid_calculus_study_guide().replace(
                    "**Coverage:** Covered", "**Coverage:** Mostly covered", 1
                ),
            )

    def test_rejects_missing_supplemental_aid_disclosure(self) -> None:
        with self.assertRaisesRegex(ValueError, "Supplemental mastery aid"):
            validate_prompt_output(
                self.prompt,
                valid_calculus_study_guide().replace("**Supplemental mastery aid**\n", ""),
            )

    def test_rejects_unlabeled_supplemental_practice_or_answers(self) -> None:
        for heading in ("Mastery Practice", "Fully Worked Answers"):
            with self.subTest(heading=heading), self.assertRaisesRegex(
                ValueError, "must identify supplemental material"
            ):
                validate_prompt_output(
                    self.prompt,
                    valid_calculus_study_guide().replace(
                        f"## {heading}\n**Supplemental mastery aid**\n",
                        f"## {heading}\n",
                    ),
                )

    def test_rejects_not_covered_section_in_teaching_or_practice(self) -> None:
        leaked = valid_calculus_study_guide().replace(
            "## Mastery Practice\n**Supplemental mastery aid**\n1. Problem one.",
            "## Mastery Practice\n**Supplemental mastery aid**\n"
            "Use the epsilon-delta definition from section 2.4.\n1. Problem one.",
        )

        with self.assertRaisesRegex(ValueError, "not-covered section"):
            validate_prompt_output(self.prompt, leaked)

    def test_rejects_incomplete_numbered_practice_or_answers(self) -> None:
        with self.assertRaisesRegex(ValueError, "numbered 1 through 10"):
            validate_prompt_output(
                self.prompt,
                valid_calculus_study_guide().replace("10. Problem ten.\n", ""),
            )
        with self.assertRaisesRegex(ValueError, "numbered 1 through 10"):
            validate_prompt_output(
                self.prompt,
                valid_calculus_study_guide().replace("10. Answer ten.\n", ""),
            )

    def test_rejects_provider_error_text(self) -> None:
        with self.assertRaisesRegex(ValueError, "provider error"):
            validate_prompt_output(self.prompt, "Provider error: unavailable")

    def test_algebra_prompt_has_no_calculus_validation_profile(self) -> None:
        algebra_prompt = PROMPTS_BY_SLUG["study-guide"]
        self.assertIsNone(algebra_prompt.validation_profile)
        validate_prompt_output(algebra_prompt, "existing algebra response format")

    def test_unknown_validation_profile_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown output validation profile"):
            validate_prompt_output(
                replace(self.prompt, validation_profile="unknown"),
                valid_calculus_study_guide(),
            )


if __name__ == "__main__":
    unittest.main()
