from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock

from math_tutor.cli_commands import handle_print_command


class CliCommandTests(unittest.TestCase):
    def test_handle_print_command_returns_false_when_no_print_flags_are_set(self) -> None:
        result = handle_print_command(
            output_dir=Path("/tmp/output"),
            print_all=False,
            print_prompt_slugs=None,
            chapter_filters=None,
            printer="Brother",
            dry_run=False,
        )

        self.assertFalse(result)

    def test_handle_print_command_dispatches_print_request(self) -> None:
        print_saved_prompt_pdfs = Mock()

        result = handle_print_command(
            output_dir=Path("/tmp/output"),
            print_all=False,
            print_prompt_slugs=["study-guide"],
            chapter_filters=["5.1"],
            printer="Brother",
            dry_run=True,
            print_saved_prompt_pdfs_fn=print_saved_prompt_pdfs,
        )

        self.assertTrue(result)
        print_saved_prompt_pdfs.assert_called_once()


if __name__ == "__main__":
    unittest.main()
