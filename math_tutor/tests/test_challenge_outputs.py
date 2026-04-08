from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from math_tutor.challenge_outputs import materialize_chapter_exam_outputs, materialize_exam_outputs


class ChallengeOutputsTests(unittest.TestCase):
    def test_materialize_exam_outputs_writes_index_and_individual_exam_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            challenges_dir = Path(temp_dir)
            exams_subdir = challenges_dir / "exams"
            exams_subdir.mkdir()
            (exams_subdir / "stale.json").write_text("{}", encoding="utf-8")
            bundle = {
                "generated_at": "2026-04-02T00:00:00+00:00",
                "exams": [
                    {
                        "id": "exam-01",
                        "title": "Challenge Exam 1",
                        "bank": "classic",
                        "bank_title": "Classic",
                        "questions": [
                            {"id": "q1", "chapter": "5.1", "type": "mm"},
                            {"id": "q2", "chapter": "5.2", "type": "op"},
                        ],
                    }
                ],
            }

            stats = materialize_exam_outputs(
                challenges_dir=challenges_dir,
                bundle=bundle,
                full_bundle_size=4096,
            )

            index_payload = json.loads((challenges_dir / "exams-index.json").read_text(encoding="utf-8"))
            exam_payload = json.loads((challenges_dir / "exams" / "exam-01.json").read_text(encoding="utf-8"))

            self.assertEqual(stats["exam_count"], 1)
            self.assertEqual(index_payload["exams"][0]["chapters"], ["5.1", "5.2"])
            self.assertEqual(index_payload["exams"][0]["bank"], "classic")
            self.assertEqual(index_payload["exams"][0]["bank_id"], "classic")
            self.assertEqual(index_payload["exams"][0]["bank_title"], "Classic")
            self.assertEqual(index_payload["exams"][0]["bank_label"], "Classic")
            self.assertEqual(index_payload["exams"][0]["question_count"], 2)
            self.assertEqual(exam_payload["id"], "exam-01")
            self.assertEqual(exam_payload["generated_at"], bundle["generated_at"])
            self.assertFalse((exams_subdir / "stale.json").exists())

    def test_materialize_chapter_exam_outputs_writes_per_chapter_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            challenges_dir = Path(temp_dir)
            bundle = {
                "generated_at": "2026-04-02T00:00:00+00:00",
                "exams": [
                    {
                        "id": "chp51-mm",
                        "title": "Chapter 5.1 Mental Math Challenge",
                        "chapter": "5.1",
                        "challenge_type": "mm",
                        "questions": [
                            {"id": "q1", "type": "mm", "model_label": "GPT-5.4"},
                        ],
                    },
                    {
                        "id": "chp51-op",
                        "title": "Chapter 5.1 Olympiad Challenge",
                        "chapter": "5.1",
                        "challenge_type": "op",
                        "questions": [
                            {"id": "q2", "type": "op", "model_label": "Gemini 3.1 Pro"},
                        ],
                    },
                ],
            }

            stats = materialize_chapter_exam_outputs(challenges_dir=challenges_dir, bundle=bundle)

            chapter_index = json.loads((challenges_dir / "chapter-exams" / "index.json").read_text(encoding="utf-8"))
            chapter_file = json.loads((challenges_dir / "chapter-exams" / "chp51.json").read_text(encoding="utf-8"))

            self.assertEqual(stats["chapter_exam_count"], 2)
            self.assertEqual(len(chapter_index["exams"]), 2)
            self.assertEqual(chapter_file["chapter"], "5.1")
            self.assertEqual([exam["id"] for exam in chapter_file["exams"]], ["chp51-mm", "chp51-op"])


if __name__ == "__main__":
    unittest.main()
