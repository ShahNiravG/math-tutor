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

    def test_resolve_selected_prompts_includes_dependents(self) -> None:
        prompts = resolve_selected_prompts(["mental-math-gpt5"])
        slugs = [prompt.slug for prompt in prompts]
        self.assertIn("mental-math-gpt5", slugs)
        self.assertIn("mental-math-gpt5-mcq", slugs)

    def test_resolve_prompt_slug_set(self) -> None:
        self.assertEqual(resolve_prompt_slug_set(["a", "b", "a"]), {"a", "b"})

    def test_study_guide_prompt_export(self) -> None:
        self.assertIs(STUDY_GUIDE_PROMPT, PROMPTS_BY_SLUG["study-guide"])


if __name__ == "__main__":
    unittest.main()
