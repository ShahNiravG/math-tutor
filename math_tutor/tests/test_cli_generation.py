from __future__ import annotations

import unittest
from unittest.mock import Mock

from math_tutor.cli_generation import (
    build_openai_generation_client,
    initialize_gemini_client,
    resolve_openai_api_key,
)
from math_tutor.prompt_catalog import PROMPTS_BY_SLUG


class CliGenerationTests(unittest.TestCase):
    def test_resolve_openai_api_key_returns_none_for_fetch_only(self) -> None:
        api_key = resolve_openai_api_key(
            prompts=(PROMPTS_BY_SLUG["study-guide"],),
            fetch_only=True,
            fetch_assignments=False,
            env={"OPENAI_API_KEY": "secret"},
        )

        self.assertIsNone(api_key)

    def test_resolve_openai_api_key_returns_none_for_gemini_only_prompts(self) -> None:
        api_key = resolve_openai_api_key(
            prompts=(PROMPTS_BY_SLUG["mental-math-gemini"],),
            fetch_only=False,
            fetch_assignments=False,
            env={},
        )

        self.assertIsNone(api_key)

    def test_resolve_openai_api_key_requires_key_when_openai_prompt_selected(self) -> None:
        with self.assertRaises(SystemExit):
            resolve_openai_api_key(
                prompts=(PROMPTS_BY_SLUG["study-guide"],),
                fetch_only=False,
                fetch_assignments=False,
                env={},
            )

    def test_initialize_gemini_client_uses_supplied_factory(self) -> None:
        factory = Mock(return_value="gemini-client")
        logger = Mock()

        client = initialize_gemini_client(
            env={"GEMINI_API_KEY": "gem-secret"},
            client_factory=factory,
            log=logger,
        )

        self.assertEqual(client, "gemini-client")
        factory.assert_called_once_with("gem-secret")
        logger.assert_called_once_with("Gemini client initialized.")

    def test_build_openai_generation_client_returns_none_without_key(self) -> None:
        self.assertIsNone(build_openai_generation_client(None))


if __name__ == "__main__":
    unittest.main()
