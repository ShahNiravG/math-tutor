from __future__ import annotations

import sys
import unittest
from unittest.mock import patch

from math_tutor import cli


def _parse(argv: list[str]) -> object:
    with patch.object(sys, "argv", ["math-tutor", *argv]):
        return cli.parse_args()


class DryRunGuardTests(unittest.TestCase):
    def test_dry_run_without_print_flags_raises(self) -> None:
        args = _parse(["--dry-run"])
        with self.assertRaises(SystemExit):
            cli.validate_args(args)

    def test_dry_run_with_print_prompt_is_allowed(self) -> None:
        args = _parse(["--dry-run", "--print-prompt", "study-guide"])
        cli.validate_args(args)

    def test_dry_run_with_print_all_is_allowed(self) -> None:
        args = _parse(["--dry-run", "--print-all"])
        cli.validate_args(args)

    def test_no_dry_run_is_allowed(self) -> None:
        args = _parse([])
        cli.validate_args(args)


if __name__ == "__main__":
    unittest.main()
