from __future__ import annotations

import unittest
from dataclasses import replace

from math_tutor.calculus_chapters import AP_CALCULUS_CHAPTER_2_MANIFEST
from math_tutor.site_ai_challenges import (
    AI_CHALLENGE_PROVIDERS,
    HARD_CHALLENGE_PROMPT,
    MEDIUM_CHALLENGE_PROMPT,
    build_ai_challenge_prompts,
    render_ai_challenge_section,
)


class SiteAIChallengesTests(unittest.TestCase):
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
        for prompt in (MEDIUM_CHALLENGE_PROMPT, HARD_CHALLENGE_PROMPT):
            self.assertIn("exactly 10 original multiple-choice questions", prompt)
            self.assertIn("Ask one question at a time", prompt)
            self.assertIn("Do not reveal the answer before the student responds", prompt)
            self.assertIn("Do not test the formal epsilon-delta definition", prompt)
            self.assertIn("Do not quote, reproduce, paraphrase, imitate, or transform", prompt)
            self.assertIn("exactly one option is correct", prompt)
            self.assertIn("After question 10", prompt)
        self.assertIn("Difficulty: MEDIUM", MEDIUM_CHALLENGE_PROMPT)
        self.assertIn("one- or two-step calculations", MEDIUM_CHALLENGE_PROMPT)
        self.assertIn("Difficulty: HARD", HARD_CHALLENGE_PROMPT)
        self.assertIn("multi-step reasoning", HARD_CHALLENGE_PROMPT)

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
