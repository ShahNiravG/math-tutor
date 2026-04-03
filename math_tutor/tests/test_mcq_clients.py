from __future__ import annotations

import unittest

from math_tutor.mcq_clients import build_mcq_clients, generate_mcq_text


class MCQClientsTests(unittest.TestCase):
    def test_build_mcq_clients_returns_none_when_keys_missing(self) -> None:
        openai_client, gemini_client = build_mcq_clients(
            openai_api_key=None,
            gemini_api_key=None,
        )

        self.assertIsNone(openai_client)
        self.assertIsNone(gemini_client)

    def test_generate_mcq_text_returns_none_when_required_client_missing(self) -> None:
        result = generate_mcq_text(
            provider="gpt",
            prompt="hello",
            openai_client=None,
            gemini_client=None,
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
