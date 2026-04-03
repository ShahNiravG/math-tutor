from __future__ import annotations

import unittest

from math_tutor.challenge_builder import build_chapter_exam_sets


class ChallengeBuilderTests(unittest.TestCase):
    def test_build_chapter_exam_sets_groups_all_available_chapters(self) -> None:
        questions = [
            {
                "id": "chp51-mm-gpt54-q1",
                "chapter": "5.1",
                "type": "mm",
                "model": "gpt54",
                "model_label": "GPT-5.4",
                "source_label": "Chapter 5.1 / Mental Math / GPT-5.4 / Q1",
                "question_number": 1,
                "text": "Q1",
                "options": ["(A) 1", "(B) 2", "(C) 3", "(D) 4"],
                "correct": "A",
            },
            {
                "id": "chp51-op-gem-q1",
                "chapter": "5.1",
                "type": "op",
                "model": "gem",
                "model_label": "Gemini 3.1 Pro",
                "source_label": "Chapter 5.1 / Olympiad Problems / Gemini 3.1 Pro / Q1",
                "question_number": 1,
                "text": "Q2",
                "options": ["(A) 1", "(B) 2", "(C) 3", "(D) 4"],
                "correct": "B",
            },
            {
                "id": "chp61-mm-gem-q1",
                "chapter": "6.1",
                "type": "mm",
                "model": "gem",
                "model_label": "Gemini 3.1 Pro",
                "source_label": "Chapter 6.1 / Mental Math / Gemini 3.1 Pro / Q1",
                "question_number": 1,
                "text": "Q3",
                "options": ["(A) 1", "(B) 2", "(C) 3", "(D) 4"],
                "correct": "C",
            },
        ]

        exams = build_chapter_exam_sets(questions)

        self.assertEqual(
            [exam["id"] for exam in exams],
            ["chp51-mm", "chp51-op", "chp61-mm"],
        )
        self.assertEqual(exams[0]["questions"][0]["id"], "chp51-mm-gpt54-q1")
        self.assertEqual(exams[1]["questions"][0]["id"], "chp51-op-gem-q1")
        self.assertEqual(exams[2]["questions"][0]["id"], "chp61-mm-gem-q1")


if __name__ == "__main__":
    unittest.main()
