from __future__ import annotations

import unittest

from math_tutor.prompt_catalog import (
    PROMPTS_BY_SLUG,
    STUDY_GUIDE_PROMPT,
    prompt_title_from_slug,
    resolve_prompt_slug_set,
    resolve_selected_prompts,
)


class PromptCatalogTests(unittest.TestCase):
    def test_prompt_title_from_slug_uses_catalog_title(self) -> None:
        self.assertEqual(prompt_title_from_slug("study-guide"), "Study Guide")
        self.assertEqual(prompt_title_from_slug("auto-grading-assignment"), "Auto Grading Assignment")

    def test_resolve_selected_prompts_includes_dependents(self) -> None:
        prompts = resolve_selected_prompts(["mental-math-gpt5"])
        slugs = [prompt.slug for prompt in prompts]
        self.assertIn("mental-math-gpt5", slugs)
        self.assertIn("mental-math-gpt5-mcq", slugs)

    def test_resolve_selected_prompts_excludes_explicit_only_by_default(self) -> None:
        slugs = [prompt.slug for prompt in resolve_selected_prompts(None)]
        self.assertNotIn("auto-grading-assignment", slugs)

    def test_resolve_selected_prompts_allows_explicit_auto_grading_request(self) -> None:
        slugs = [prompt.slug for prompt in resolve_selected_prompts(["auto-grading-assignment"])]
        self.assertEqual(slugs, ["auto-grading-assignment"])

    def test_resolve_prompt_slug_set(self) -> None:
        self.assertEqual(resolve_prompt_slug_set(["a", "b", "a"]), {"a", "b"})

    def test_study_guide_prompt_export(self) -> None:
        self.assertIs(STUDY_GUIDE_PROMPT, PROMPTS_BY_SLUG["study-guide"])

    def test_auto_grading_assignment_prompt_exists(self) -> None:
        prompt = PROMPTS_BY_SLUG["auto-grading-assignment"]
        self.assertEqual(prompt.title, "Auto Grading Assignment")
        self.assertIn("expert academic grader", prompt.text)
        self.assertEqual(prompt.model, "gemini-3.1-pro-preview")
        self.assertTrue(prompt.assignment_only)
        self.assertEqual(prompt.required_filename_substrings, ("work",))
        self.assertTrue(prompt.explicit_only)

    def test_inspiring_videos_default_prompt_uses_gpt_5_4_without_grounding(self) -> None:
        prompt = PROMPTS_BY_SLUG["inspiring-videos"]
        self.assertEqual(prompt.model, "gpt-5.4")
        self.assertFalse(prompt.use_google_search)

    def test_inspiring_videos_gemini_variant_carries_gemini_model(self) -> None:
        prompt = PROMPTS_BY_SLUG["inspiring-videos-gemini"]
        self.assertEqual(prompt.model, "gemini-3.1-pro-preview")

    def test_inspiring_videos_gpt5_variant_carries_gpt5_model(self) -> None:
        prompt = PROMPTS_BY_SLUG["inspiring-videos-gpt5"]
        self.assertEqual(prompt.model, "gpt-5.4")

    def test_other_gemini_prompts_remain_on_gemini_3_1_pro_without_grounding(self) -> None:
        for slug in (
            "mental-math-gemini",
            "mental-math-gemini-mcq",
            "olympiad-problems-gemini",
            "olympiad-solutions-gemini",
            "olympiad-problems-gemini-mcq",
            "auto-grading-assignment",
        ):
            prompt = PROMPTS_BY_SLUG[slug]
            self.assertEqual(prompt.model, "gemini-3.1-pro-preview", slug)
            self.assertFalse(prompt.use_google_search, slug)


if __name__ == "__main__":
    unittest.main()
