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
        args = _parse(["--dry-run"])
        self.assertTrue(args.dry_run)

    def test_dry_run_with_print_prompt_parses(self) -> None:
        args = _parse(["--dry-run", "--print-prompt", "study-guide"])
        self.assertTrue(args.dry_run)
        self.assertEqual(args.print_prompt_slugs, ["study-guide"])


if __name__ == "__main__":
    unittest.main()
