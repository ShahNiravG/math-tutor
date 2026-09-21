from __future__ import annotations

import unittest

from math_tutor.site_ai_challenges import (
    AI_CHALLENGE_PROVIDERS,
    HARD_CHALLENGE_PROMPT,
    MEDIUM_CHALLENGE_PROMPT,
    render_ai_challenge_section,
)


class SiteAIChallengesTests(unittest.TestCase):
    def test_component_is_isolated_to_ap_calculus_chapter_two(self) -> None:
        self.assertEqual(
            render_ai_challenge_section(course_id="algebra-2-trig", chapter="2"),
            "",
        )
        self.assertEqual(
            render_ai_challenge_section(course_id="ap-calculus-ab", chapter="3"),
            "",
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
