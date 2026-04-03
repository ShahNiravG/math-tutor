from __future__ import annotations

import unittest

from math_tutor.cli_auth import resolve_canvas_credentials


class CliAuthTests(unittest.TestCase):
    def test_resolve_canvas_credentials_prefers_arguments(self) -> None:
        credentials = resolve_canvas_credentials(
            username="user@example.com",
            password="secret",
            skip_fetch=False,
            env={},
        )

        self.assertEqual(credentials, ("user@example.com", "secret"))

    def test_resolve_canvas_credentials_uses_environment(self) -> None:
        credentials = resolve_canvas_credentials(
            username=None,
            password=None,
            skip_fetch=False,
            env={
                "MATH_TUTOR_USERNAME": "env-user@example.com",
                "MATH_TUTOR_PASSWORD": "env-secret",
            },
        )

        self.assertEqual(credentials, ("env-user@example.com", "env-secret"))

    def test_resolve_canvas_credentials_returns_none_when_skip_fetch_enabled(self) -> None:
        credentials = resolve_canvas_credentials(
            username=None,
            password=None,
            skip_fetch=True,
            env={},
        )

        self.assertIsNone(credentials)

    def test_resolve_canvas_credentials_requires_both_values(self) -> None:
        with self.assertRaises(SystemExit):
            resolve_canvas_credentials(
                username=None,
                password=None,
                skip_fetch=False,
                env={},
            )


if __name__ == "__main__":
    unittest.main()
