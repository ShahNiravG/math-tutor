from __future__ import annotations

import unittest
from unittest.mock import patch

from math_tutor import challenge_builder
from math_tutor import site_builder


class ExperienceDefaultTests(unittest.TestCase):
    def test_site_builder_cli_defaults_to_staging(self) -> None:
        with patch("sys.argv", ["math-tutor-build-site"]):
            args = site_builder.parse_args()
        self.assertEqual(args.experience, "staging")

    def test_challenge_builder_default_experience_is_staging(self) -> None:
        self.assertEqual(challenge_builder.DEFAULT_EXPERIENCE_VARIANT, "staging")
        self.assertEqual(site_builder.DEFAULT_EXPERIENCE_VARIANT, "staging")

    def test_cli_accepts_archived_name(self) -> None:
        with patch("sys.argv", ["math-tutor-build-site", "--experience", "archived"]):
            archived_args = site_builder.parse_args()
        self.assertEqual(archived_args.experience, "archived")

    def test_cli_rejects_removed_default_alias(self) -> None:
        with patch("sys.argv", ["math-tutor-build-site", "--experience", "default"]):
            with self.assertRaises(SystemExit):
                site_builder.parse_args()


if __name__ == "__main__":
    unittest.main()
