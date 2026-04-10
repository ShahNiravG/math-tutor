"""Tests for the atomic-write helper module.

These tests enforce the crash-safety contract documented in
:mod:`math_tutor.atomic_io`: a failed write must never leave the destination
file in a truncated or partially-written state.
"""

from __future__ import annotations

import json
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from math_tutor.atomic_io import atomic_write_json, atomic_write_text


class AtomicWriteTextTests(unittest.TestCase):
    def test_writes_content_to_new_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "out.txt"

            atomic_write_text(target, "hello")

            self.assertEqual(target.read_text(encoding="utf-8"), "hello")

    def test_overwrites_existing_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "out.txt"
            target.write_text("old", encoding="utf-8")

            atomic_write_text(target, "new")

            self.assertEqual(target.read_text(encoding="utf-8"), "new")

    def test_failure_mid_write_preserves_original_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "out.txt"
            target.write_text("original", encoding="utf-8")

            with patch("math_tutor.atomic_io.os.replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    atomic_write_text(target, "replacement")

            self.assertEqual(target.read_text(encoding="utf-8"), "original")

    def test_failure_mid_write_leaves_no_temp_file_behind(self) -> None:
        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "out.txt"
            target.write_text("original", encoding="utf-8")

            with patch("math_tutor.atomic_io.os.replace", side_effect=OSError("disk full")):
                with self.assertRaises(OSError):
                    atomic_write_text(target, "replacement")

            residual = [p.name for p in Path(temp_dir).iterdir() if p.name != "out.txt"]
            self.assertEqual(residual, [])

    def test_creates_parent_directories(self) -> None:
        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "nested" / "dir" / "out.txt"

            atomic_write_text(target, "hello")

            self.assertEqual(target.read_text(encoding="utf-8"), "hello")

    def test_temp_file_created_in_same_directory_as_target(self) -> None:
        """Cross-device rename would break atomicity, so the temp must be a sibling."""
        observed_temp_dirs: list[str] = []
        real_replace = os.replace

        def spy_replace(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
            observed_temp_dirs.append(os.path.dirname(os.fspath(src)))
            real_replace(src, dst)

        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "nested" / "out.txt"
            with patch("math_tutor.atomic_io.os.replace", side_effect=spy_replace):
                atomic_write_text(target, "hello")

            self.assertEqual(observed_temp_dirs, [str(target.parent)])


class AtomicWriteJsonTests(unittest.TestCase):
    def test_writes_json_payload(self) -> None:
        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "state.json"

            atomic_write_json(target, {"a": 1, "b": [2, 3]})

            self.assertEqual(
                json.loads(target.read_text(encoding="utf-8")),
                {"a": 1, "b": [2, 3]},
            )

    def test_respects_indent_parameter(self) -> None:
        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "state.json"

            atomic_write_json(target, {"a": 1}, indent=2)

            self.assertIn("\n  ", target.read_text(encoding="utf-8"))

    def test_failure_mid_write_preserves_original_state_file(self) -> None:
        with TemporaryDirectory() as temp_dir:
            target = Path(temp_dir) / "state.json"
            target.write_text('{"processed": {"legacy": true}}', encoding="utf-8")

            with patch("math_tutor.atomic_io.os.replace", side_effect=OSError("crash")):
                with self.assertRaises(OSError):
                    atomic_write_json(target, {"processed": {"new": True}})

            self.assertEqual(
                json.loads(target.read_text(encoding="utf-8")),
                {"processed": {"legacy": True}},
            )


if __name__ == "__main__":
    unittest.main()
