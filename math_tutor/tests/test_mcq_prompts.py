from __future__ import annotations

import unittest

from math_tutor.mcq_prompts import build_mcq_prompt


class MCQPromptsTests(unittest.TestCase):
    def test_build_mcq_prompt_uses_mental_math_template(self) -> None:
        prompt = build_mcq_prompt(prompt_type="mental_math", questions_text="1. 2+2")

        self.assertIn("mental math questions", prompt)
        self.assertIn("1. 2+2", prompt)

    def test_build_mcq_prompt_uses_olympiad_template(self) -> None:
        prompt = build_mcq_prompt(prompt_type="olympiad", questions_text="1. Prove ...")

        self.assertIn("Olympiad-style math problems", prompt)
        self.assertIn("1. Prove ...", prompt)


if __name__ == "__main__":
    unittest.main()
