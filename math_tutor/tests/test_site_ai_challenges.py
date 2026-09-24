from __future__ import annotations

import unittest
from dataclasses import replace
from pathlib import Path
import tomllib

from math_tutor.calculus_chapters import (
    AP_CALCULUS_CHAPTER_2_MANIFEST,
    AP_CALCULUS_CHAPTER_3_MANIFEST,
)
from math_tutor.site_ai_challenges import (
    AI_CHALLENGE_PROVIDERS,
    build_ai_challenge_prompts,
    format_reviewed_list,
    render_ai_challenge_section,
)


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"


def _reviewed_chapter_two_prompts() -> tuple[str, str]:
    fixture = tomllib.loads(
        (FIXTURE_DIR / "calculus-chapter-2-ai-challenges.toml").read_text(encoding="utf-8")
    )
    self_contained = fixture["prompts"]
    assert fixture["source"]["trailing_newline"] is False
    return self_contained["medium"], self_contained["hard"]


class SiteAIChallengesTests(unittest.TestCase):
    def test_chapter_two_fixture_carries_complete_reviewable_provenance(self) -> None:
        fixture = tomllib.loads(
            (FIXTURE_DIR / "calculus-chapter-2-ai-challenges.toml").read_text(
                encoding="utf-8"
            )
        )
        source = fixture["source"]

        self.assertRegex(source["reviewed_source_commit"], r"^[0-9a-f]{7,40}$")
        self.assertRegex(
            source["url"],
            r"^https://mathdelight\.com/courses/ap-calculus-ab/doc-\d+\.html$",
        )
        self.assertRegex(source["page_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(source["retrieved_at"], r"^\d{4}-\d{2}-\d{2}$")
        self.assertEqual(source["encoding"], "UTF-8")
        self.assertIs(source["trailing_newline"], False)
        self.assertEqual(set(fixture["prompts"]), {"medium", "hard"})
        for prompt in _reviewed_chapter_two_prompts():
            self.assertTrue(prompt.strip())
            self.assertFalse(prompt.endswith("\n"))

    def test_reviewed_list_formatter_handles_one_two_and_many_items(self) -> None:
        self.assertEqual(format_reviewed_list(("domain",)), "domain")
        self.assertEqual(
            format_reviewed_list(("domain", "endpoint")),
            "domain and endpoint",
        )
        self.assertEqual(
            format_reviewed_list(("domain", "endpoint", "infinite-limit")),
            "domain, endpoint, and infinite-limit",
        )

    def test_chapter_two_manifest_prompts_preserve_the_reviewed_contract_exactly(self) -> None:
        medium, hard = build_ai_challenge_prompts(AP_CALCULUS_CHAPTER_2_MANIFEST)

        self.assertEqual((medium, hard), _reviewed_chapter_two_prompts())

    def test_chapter_three_prompts_explicitly_forbid_later_calculus_topics(self) -> None:
        medium, hard = build_ai_challenge_prompts(AP_CALCULUS_CHAPTER_3_MANIFEST)

        for prompt in (medium, hard):
            self.assertIn("Mean Value Theorem", prompt)
            self.assertIn("L'Hôpital", prompt)
            self.assertIn("optimization", prompt)
            self.assertIn("integration", prompt)
            self.assertIn("hyperbolic functions", prompt)

    def test_hard_guidance_uses_the_manifest_chapter_instead_of_copied_free_text(self) -> None:
        chapter_four = replace(
            AP_CALCULUS_CHAPTER_3_MANIFEST,
            chapter="4",
            sections=tuple(
                replace(section, section_id=section.section_id.replace("3.", "4.", 1))
                for section in AP_CALCULUS_CHAPTER_3_MANIFEST.sections
            ),
        )

        _medium, hard = build_ai_challenge_prompts(chapter_four)

        self.assertIn("allowed Chapter 4 scope", hard)
        self.assertNotIn("allowed Chapter 3 scope", hard)

    def test_chapter_three_card_description_is_not_limit_specific(self) -> None:
        rendered = render_ai_challenge_section(course_id="ap-calculus-ab", chapter="3")

        self.assertNotIn("subtle domain or limit behavior", rendered)

    def test_prompt_builder_uses_manifest_chapter_scope_and_exclusions(self) -> None:
        chapter_three = replace(
            AP_CALCULUS_CHAPTER_2_MANIFEST,
            chapter="3",
            title="Differentiation Rules",
            sections=tuple(
                replace(
                    section,
                    section_id=section.section_id.replace("2.", "3."),
                    challenge_status="excluded" if index == 0 else "included",
                    challenge_note="Do not test section 3.1." if index == 0 else None,
                )
                for index, section in enumerate(AP_CALCULUS_CHAPTER_2_MANIFEST.sections)
            ),
        )

        medium, hard = build_ai_challenge_prompts(chapter_three)

        for prompt in (medium, hard):
            self.assertIn("Chapter 3: Differentiation Rules", prompt)
            self.assertIn("3.2", prompt)
            self.assertIn("Do not test section 3.1.", prompt)
            self.assertNotIn("Chapter 2: Limits and Derivatives", prompt)

    def test_component_is_isolated_to_reviewed_ap_calculus_chapters(self) -> None:
        self.assertEqual(
            render_ai_challenge_section(course_id="algebra-2-trig", chapter="2"),
            "",
        )
        self.assertNotEqual(
            render_ai_challenge_section(course_id="ap-calculus-ab", chapter="3"), ""
        )
        self.assertNotEqual(
            render_ai_challenge_section(course_id="ap-calculus-ab", chapter="2"),
            "",
        )

    def test_prompts_are_original_scoped_sequential_ten_question_challenges(self) -> None:
        medium_prompt, hard_prompt = _reviewed_chapter_two_prompts()
        for prompt in (medium_prompt, hard_prompt):
            self.assertIn("exactly 10 original multiple-choice questions", prompt)
            self.assertIn("Ask one question at a time", prompt)
            self.assertIn("Do not reveal the answer before the student responds", prompt)
            self.assertIn("Do not test the formal epsilon-delta definition", prompt)
            self.assertIn("Do not quote, reproduce, paraphrase, imitate, or transform", prompt)
            self.assertIn("exactly one option is correct", prompt)
            self.assertIn("After question 10", prompt)
        self.assertIn("Difficulty: MEDIUM", medium_prompt)
        self.assertIn("one- or two-step calculations", medium_prompt)
        self.assertIn("Difficulty: HARD", hard_prompt)
        self.assertIn("multi-step reasoning", hard_prompt)

    def test_provider_destinations_are_exact_parameter_free_https_urls(self) -> None:
        self.assertEqual(
            [(provider.label, provider.url) for provider in AI_CHALLENGE_PROVIDERS],
            [
                ("Open Gemini", "https://gemini.google.com/app"),
                ("Open ChatGPT", "https://chatgpt.com/"),
            ],
        )

    def test_rendered_component_has_secure_links_accessible_status_and_copy_fallback(self) -> None:
        rendered = render_ai_challenge_section(course_id="ap-calculus-ab", chapter="2")

        self.assertEqual(rendered.count('target="_blank"'), 4)
        self.assertEqual(rendered.count('rel="noopener noreferrer"'), 4)
        self.assertEqual(rendered.count('role="status" aria-live="polite"'), 2)
        self.assertEqual(rendered.count("View or copy the prompt manually"), 2)
        self.assertEqual(rendered.count('class="chapter-challenge-action ai-challenge-copy"'), 2)
        self.assertIn("navigator.clipboard.writeText", rendered)
        self.assertIn("document.execCommand('copy')", rendered)
        self.assertIn("Automatic copy was blocked", rendered)

    def test_rendered_component_does_not_claim_or_select_a_provider_model(self) -> None:
        rendered = render_ai_challenge_section(course_id="ap-calculus-ab", chapter="2")

        self.assertNotIn("model=", rendered)
        self.assertNotIn("gemini-3", rendered.lower())
        self.assertNotIn("gpt-", rendered.lower())


if __name__ == "__main__":
    unittest.main()
