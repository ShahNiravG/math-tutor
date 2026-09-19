from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from math_tutor import cli


def _parse(argv: list[str]) -> object:
    with patch.object(sys, "argv", ["math-tutor", *argv]):
        return cli.parse_args()


class DryRunFlagTests(unittest.TestCase):
    def test_dry_run_alone_parses_without_error(self) -> None:
        args = _parse(["--course", "algebra-2-trig", "--dry-run"])
        self.assertTrue(args.dry_run)

    def test_dry_run_with_print_prompt_parses(self) -> None:
        args = _parse(
            ["--course", "algebra-2-trig", "--dry-run", "--print-prompt", "study-guide"]
        )
        self.assertTrue(args.dry_run)
        self.assertEqual(args.print_prompt_slugs, ["study-guide"])

    def test_course_is_required(self) -> None:
        with self.assertRaises(SystemExit):
            _parse(["--dry-run"])

    def test_calculus_course_is_accepted(self) -> None:
        args = _parse(["--course", "ap-calculus-ab", "--chapter", "2", "--fetch-only"])

        self.assertEqual(args.course_id, "ap-calculus-ab")

    def test_calculus_rejects_generation_during_fetch_phase(self) -> None:
        with self.assertRaises(SystemExit):
            _parse(["--course", "ap-calculus-ab", "--chapter", "2"])

    def test_calculus_requires_exactly_chapter_two_during_fetch_phase(self) -> None:
        with self.assertRaises(SystemExit):
            _parse(["--course", "ap-calculus-ab", "--fetch-only"])
        with self.assertRaises(SystemExit):
            _parse(["--course", "ap-calculus-ab", "--chapter", "3", "--fetch-only"])

    def test_calculus_rejects_assignment_fetch_during_chapter_note_phase(self) -> None:
        with self.assertRaises(SystemExit):
            _parse(
                [
                    "--course",
                    "ap-calculus-ab",
                    "--chapter",
                    "2",
                    "--fetch-only",
                    "--fetch-assignments",
                ]
            )


if __name__ == "__main__":
    unittest.main()
