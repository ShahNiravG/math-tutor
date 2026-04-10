from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from math_tutor.challenge_outputs import (
    copy_static_challenge_assets,
    materialize_chapter_exam_outputs,
    materialize_exam_outputs,
    write_json,
)


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
                        "bank_title": "AI-Generated",
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
            self.assertEqual(index_payload["exams"][0]["bank_title"], "AI-Generated")
            self.assertEqual(index_payload["exams"][0]["bank_label"], "AI-Generated")
            self.assertEqual(index_payload["exams"][0]["question_count"], 2)
            self.assertEqual(exam_payload["id"], "exam-01")
            self.assertEqual(exam_payload["generated_at"], bundle["generated_at"])
            # stale.json cleanup is the builder's responsibility, not materialize_exam_outputs

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


    def test_materialize_exam_outputs_does_not_delete_non_bundle_files(self) -> None:
        """Files not in the bundle (e.g. chapter exams) must not be deleted by materialize_exam_outputs."""
        with tempfile.TemporaryDirectory() as temp_dir:
            challenges_dir = Path(temp_dir)
            exams_subdir = challenges_dir / "exams"
            exams_subdir.mkdir()
            (exams_subdir / "chp51-mm.json").write_text('{"id":"chp51-mm"}', encoding="utf-8")
            bundle = {
                "generated_at": "2026-04-02T00:00:00+00:00",
                "exams": [
                    {
                        "id": "exam-01",
                        "title": "Exam 1",
                        "bank": "classic",
                        "bank_title": "AI-Generated",
                        "questions": [{"id": "q1", "chapter": "5.1", "type": "mm"}],
                    }
                ],
            }
            materialize_exam_outputs(challenges_dir=challenges_dir, bundle=bundle, full_bundle_size=4096)
            self.assertTrue((exams_subdir / "chp51-mm.json").exists(), "chapter exam file must not be deleted")

    def test_materialize_exam_outputs_returns_written_exam_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            challenges_dir = Path(temp_dir)
            bundle = {
                "generated_at": "2026-04-02T00:00:00+00:00",
                "exams": [
                    {
                        "id": "exam-01",
                        "title": "Exam 1",
                        "bank": "classic",
                        "bank_title": "AI-Generated",
                        "questions": [{"id": "q1", "chapter": "5.1", "type": "mm"}],
                    }
                ],
            }
            stats = materialize_exam_outputs(challenges_dir=challenges_dir, bundle=bundle, full_bundle_size=4096)
            self.assertEqual(stats["written_exam_ids"], ["exam-01"])

    def test_materialize_chapter_exam_outputs_returns_written_exam_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            challenges_dir = Path(temp_dir)
            bundle = {
                "generated_at": "2026-04-02T00:00:00+00:00",
                "exams": [
                    {
                        "id": "chp51-mm",
                        "title": "Chapter 5.1 MM",
                        "chapter": "5.1",
                        "challenge_type": "mm",
                        "questions": [{"id": "q1", "type": "mm", "model_label": "GPT-5"}],
                    }
                ],
            }
            stats = materialize_chapter_exam_outputs(challenges_dir=challenges_dir, bundle=bundle)
            self.assertEqual(stats["written_exam_ids"], ["chp51-mm"])

    def test_write_json_skips_write_if_content_unchanged(self) -> None:
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "test.json"
            payload = {"key": "value", "count": 42}
            write_json(path, payload)
            with patch("math_tutor.challenge_outputs.atomic_write_text") as mock_write:
                write_json(path, payload)
                mock_write.assert_not_called()

    def test_write_json_writes_when_content_changed(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "test.json"
            write_json(path, {"key": "old"})
            write_json(path, {"key": "new"})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"key": "new"})

    def test_copy_static_challenge_assets_skips_unchanged_files(self) -> None:
        import math_tutor.challenge_outputs as co
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir()
            dest_dir = Path(temp_dir) / "dest"
            dest_dir.mkdir()
            (source_dir / "exam.html").write_bytes(b"<html>test</html>")
            copy_static_challenge_assets(source_dir=source_dir, challenges_dir=dest_dir)
            # After the fix, unchanged files skip shutil.copy2 entirely
            with patch.object(co.shutil, "copy2") as mock_copy2:
                copy_static_challenge_assets(source_dir=source_dir, challenges_dir=dest_dir)
                mock_copy2.assert_not_called()

    def test_materialize_exam_outputs_skips_write_if_content_unchanged(self) -> None:
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp_dir:
            challenges_dir = Path(temp_dir)
            bundle = {
                "generated_at": "2026-04-02T00:00:00+00:00",
                "exams": [
                    {
                        "id": "exam-01",
                        "title": "Exam 1",
                        "bank": "classic",
                        "bank_title": "AI-Generated",
                        "questions": [{"id": "q1", "chapter": "5.1", "type": "mm"}],
                    }
                ],
            }
            materialize_exam_outputs(challenges_dir=challenges_dir, bundle=bundle, full_bundle_size=4096)
            with patch.object(Path, "write_text") as mock_write:
                materialize_exam_outputs(challenges_dir=challenges_dir, bundle=bundle, full_bundle_size=4096)
                mock_write.assert_not_called()


    def test_copy_static_challenge_assets_skips_unchanged_directory(self) -> None:
        import math_tutor.challenge_outputs as co
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as temp_dir:
            source_dir = Path(temp_dir) / "source"
            source_dir.mkdir()
            admin_src = source_dir / "admin"
            admin_src.mkdir()
            (admin_src / "index.php").write_bytes(b"<?php echo 'admin'; ?>")
            dest_dir = Path(temp_dir) / "dest"
            dest_dir.mkdir()
            copy_static_challenge_assets(source_dir=source_dir, challenges_dir=dest_dir)
            with patch.object(co.shutil, "rmtree") as mock_rmtree:
                copy_static_challenge_assets(source_dir=source_dir, challenges_dir=dest_dir)
                mock_rmtree.assert_not_called()


if __name__ == "__main__":
    unittest.main()
