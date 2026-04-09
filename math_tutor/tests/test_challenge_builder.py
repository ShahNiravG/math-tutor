from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from math_tutor.challenge_builder import build_deploy_exam_bundle, sync_curated_exam_bundle
from math_tutor.challenge_catalog import build_chapter_exam_sets, load_curated_exam_banks


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

    def test_load_curated_exam_banks_combines_amc_files_into_one_bank_with_source_independent_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            exams_dir = Path(temp_dir)
            source_path = exams_dir / "AMC-gemini-pro.json"
            payload = [
                {
                    "problem_number": index,
                    "source": "AMC",
                    "concept": "Trig",
                    "question": f"Question {index}",
                    "options": {
                        "A": "1",
                        "B": "2",
                        "C": "3",
                        "D": "4",
                        "E": "5",
                    },
                    "correct_option": "E",
                }
                for index in range(1, 11)
            ]
            source_path.write_text(json.dumps(payload), encoding="utf-8")

            original_exams = load_curated_exam_banks(exams_dir)

            second_source_path = exams_dir / "AMC-gemini-pro-2.json"
            second_payload = [
                {
                    "problem_number": index,
                    "source": "AMC",
                    "concept": "Sequences",
                    "question": f"Follow-up Question {index}",
                    "options": {
                        "A": "10",
                        "B": "20",
                        "C": "30",
                        "D": "40",
                        "E": "50",
                    },
                    "correct_option": "C",
                }
                for index in range(1, 7)
            ]
            second_source_path.write_text(json.dumps(second_payload), encoding="utf-8")

            exams = load_curated_exam_banks(exams_dir)

            self.assertEqual([exam["id"] for exam in original_exams], ["amc-01", "amc-02"])
            self.assertEqual([exam["id"] for exam in exams], ["amc-01", "amc-02", "amc-03", "amc-04"])
            self.assertEqual([len(exam["questions"]) for exam in exams], [5, 5, 5, 1])
            self.assertEqual(exams[0]["bank"], "amc")
            self.assertEqual(exams[0]["bank_title"], "AMC & AIME")
            self.assertEqual(exams[2]["bank"], "amc")
            self.assertEqual(exams[2]["bank_title"], "AMC & AIME")
            self.assertEqual(exams[:2], original_exams)
            self.assertEqual(exams[0]["title"], "AMC & AIME Exam 1")
            self.assertEqual([question["id"] for question in exams[2]["questions"]], ["amc-q011", "amc-q012", "amc-q013", "amc-q014", "amc-q015"])
            self.assertEqual(exams[0]["questions"][0]["options"][-1], "(E) 5")
            self.assertEqual(exams[0]["questions"][0]["correct"], "E")

    def test_build_deploy_exam_bundle_appends_curated_exams_without_mutating_classic_ids(self) -> None:
        classic_bundle = {
            "generated_at": "2026-04-03T00:38:25.088604+00:00",
            "exams": [
                {"id": "exam-01", "title": "Challenge Exam 1", "bank": "classic", "bank_title": "Classic", "questions": []},
                {"id": "exam-02", "title": "Challenge Exam 2", "bank": "classic", "bank_title": "Classic", "questions": []},
            ],
        }
        curated_exams = [
            {"id": "amc-gemini-pro-01", "title": "AMC Gemini Pro Exam 1", "bank": "amc-gemini-pro", "bank_title": "AMC Gemini Pro", "questions": []}
        ]

        full = build_deploy_exam_bundle(classic_bundle=classic_bundle, curated_exams=curated_exams)

        self.assertEqual(
            [exam["id"] for exam in full["exams"]],
            ["exam-01", "exam-02", "amc-gemini-pro-01"],
        )
        self.assertEqual(full["generated_at"], classic_bundle["generated_at"])

    def test_sync_curated_exam_bundle_appends_new_questions_without_remapping_existing_exams(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            exams_dir = temp_root / "exams"
            exams_dir.mkdir()
            canonical_path = temp_root / "curated_exams.json"

            source_path = exams_dir / "AMC-gemini-pro.json"
            original_payload = [
                {
                    "problem_number": index,
                    "source": "AMC",
                    "concept": "Trig",
                    "question": f"Original Question {index}",
                    "options": {
                        "A": "1",
                        "B": "2",
                        "C": "3",
                        "D": "4",
                        "E": "5",
                    },
                    "correct_option": "E",
                }
                for index in range(1, 7)
            ]
            source_path.write_text(json.dumps(original_payload), encoding="utf-8")

            first_bundle = sync_curated_exam_bundle(
                exams_dir=exams_dir,
                canonical_curated_exams_json=canonical_path,
            )
            self.assertEqual(
                [exam["id"] for exam in first_bundle["exams"]],
                ["amc-01", "amc-02"],
            )
            self.assertEqual(
                [question["id"] for question in first_bundle["exams"][1]["questions"]],
                ["amc-q006"],
            )

            updated_payload = [
                {
                    "problem_number": index,
                    "source": "AMC",
                    "concept": "Trig",
                    "question": ("Edited " if index == 1 else "Original ") + f"Question {index}",
                    "options": {
                        "A": "1",
                        "B": "2",
                        "C": "3",
                        "D": "4",
                        "E": "5",
                    },
                    "correct_option": "E",
                }
                for index in range(1, 11)
            ]
            source_path.write_text(json.dumps(updated_payload), encoding="utf-8")

            second_bundle = sync_curated_exam_bundle(
                exams_dir=exams_dir,
                canonical_curated_exams_json=canonical_path,
            )

            self.assertEqual(
                [exam["id"] for exam in second_bundle["exams"]],
                ["amc-01", "amc-02", "amc-03"],
            )
            self.assertEqual(
                [question["id"] for question in second_bundle["exams"][1]["questions"]],
                ["amc-q006"],
            )
            self.assertEqual(
                [question["id"] for question in second_bundle["exams"][2]["questions"]],
                [
                    "amc-q007",
                    "amc-q008",
                    "amc-q009",
                    "amc-q010",
                    "amc-q011",
                ],
            )
            self.assertEqual(second_bundle["exams"][2]["questions"][0]["text"], "Edited Question 1")
            self.assertEqual(second_bundle["exams"][0]["questions"][0]["text"], "Original Question 1")
            self.assertEqual(second_bundle["exams"][0]["questions"][0]["curated_problem_number"], 1)
            self.assertEqual(second_bundle["exams"][0]["questions"][0]["curated_source"], "AMC")
            self.assertEqual(len(second_bundle["exams"][0]["questions"][0]["curated_question_checksum"]), 64)
            self.assertNotIn("curated_fingerprint", second_bundle["exams"][0]["questions"][0])

    def test_sync_curated_exam_bundle_preserves_source_metadata_and_link_for_aime_questions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            exams_dir = temp_root / "exams"
            exams_dir.mkdir()
            canonical_path = temp_root / "curated_exams.json"

            aime_path = exams_dir / "AIMI-gemini-pro.json"
            aime_path.write_text(
                json.dumps(
                    [
                        {
                            "problem_number": 31,
                            "source": "1983 AIME, Problem 3",
                            "concept": "Circles and Parametric Equations",
                            "question": "What is the largest value of 3x+4y?",
                            "options": {
                                "A": "68",
                                "B": "73",
                                "C": "75",
                                "D": "80",
                                "E": "85",
                            },
                            "correct_option": "B",
                            "link": "https://artofproblemsolving.com/wiki/index.php/1983_AIME_Problems/Problem_3",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            bundle = sync_curated_exam_bundle(
                exams_dir=exams_dir,
                canonical_curated_exams_json=canonical_path,
            )

            self.assertEqual(bundle["exams"][0]["bank"], "amc")
            self.assertEqual(bundle["exams"][0]["bank_title"], "AMC & AIME")
            self.assertEqual(bundle["exams"][0]["title"], "AMC & AIME Exam 1")
            question = bundle["exams"][0]["questions"][0]
            self.assertEqual(question["curated_source"], "1983 AIME, Problem 3")
            self.assertEqual(question["curated_concept"], "Circles and Parametric Equations")
            self.assertEqual(
                question["curated_source_link"],
                "https://artofproblemsolving.com/wiki/index.php/1983_AIME_Problems/Problem_3",
            )

    def test_sync_curated_exam_bundle_migrates_legacy_source_named_canonical_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            exams_dir = temp_root / "exams"
            exams_dir.mkdir()
            canonical_path = temp_root / "curated_exams.json"
            canonical_path.write_text(
                json.dumps(
                    {
                        "generated_at": "2026-04-08T00:00:00+00:00",
                        "exams": [
                            {
                                "id": "amc-gemini-pro-01",
                                "title": "AMC Gemini Pro Exam 1",
                                "bank": "amc",
                                "bank_title": "AMC",
                                "source_stem": "amc-gemini-pro",
                                "questions": [
                                    {
                                        "id": "amc-gemini-pro-q1",
                                        "source_stem": "amc-gemini-pro",
                                        "question_number": 1,
                                        "text": "Legacy Question 1",
                                        "options": ["(A) 1", "(B) 2", "(C) 3", "(D) 4", "(E) 5"],
                                        "correct": "A",
                                    }
                                ],
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            bundle = sync_curated_exam_bundle(
                exams_dir=exams_dir,
                canonical_curated_exams_json=canonical_path,
            )

            self.assertEqual([exam["id"] for exam in bundle["exams"]], ["amc-01"])
            self.assertEqual([question["id"] for question in bundle["exams"][0]["questions"]], ["amc-q001"])
            self.assertEqual(bundle["exams"][0]["questions"][0]["text"], "Legacy Question 1")

    def test_sync_curated_exam_bundle_skips_duplicate_content_even_with_new_file_and_problem_numbers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            exams_dir = temp_root / "exams"
            exams_dir.mkdir()
            canonical_path = temp_root / "curated_exams.json"

            first_source = exams_dir / "AMC-a.json"
            first_source.write_text(
                json.dumps(
                    [
                        {
                            "problem_number": 1,
                            "source": "AMC",
                            "concept": "Trig",
                            "question": "What is sin(30 degrees)?",
                            "options": {
                                "A": "0",
                                "B": "1/2",
                                "C": "sqrt(2)/2",
                                "D": "1",
                                "E": "2",
                            },
                            "correct_option": "B",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            first_bundle = sync_curated_exam_bundle(
                exams_dir=exams_dir,
                canonical_curated_exams_json=canonical_path,
            )
            self.assertEqual([exam["id"] for exam in first_bundle["exams"]], ["amc-01"])
            self.assertEqual([question["id"] for question in first_bundle["exams"][0]["questions"]], ["amc-q001"])

            second_source = exams_dir / "AMC-renamed.json"
            second_source.write_text(
                json.dumps(
                    [
                        {
                            "problem_number": 99,
                            "source": "AMC Archive",
                            "concept": "Angles",
                            "question": " What is   sin(30 degrees)? ",
                            "options": {
                                "A": "0",
                                "B": "1/2",
                                "C": "sqrt(2)/2",
                                "D": "1",
                                "E": "2",
                            },
                            "correct_option": "b",
                        }
                    ]
                ),
                encoding="utf-8",
            )

            second_bundle = sync_curated_exam_bundle(
                exams_dir=exams_dir,
                canonical_curated_exams_json=canonical_path,
            )

            self.assertEqual([exam["id"] for exam in second_bundle["exams"]], ["amc-01"])
            self.assertEqual([question["id"] for question in second_bundle["exams"][0]["questions"]], ["amc-q001"])
            self.assertEqual(len(second_bundle["exams"][0]["questions"][0]["curated_question_checksum"]), 64)


if __name__ == "__main__":
    unittest.main()
