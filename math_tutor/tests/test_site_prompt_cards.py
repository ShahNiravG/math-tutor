from __future__ import annotations

import unittest
from pathlib import Path

from math_tutor.site_models import PromptOutputRecord
from math_tutor.site_prompt_cards import render_prompt_output_card


class SitePromptCardsTests(unittest.TestCase):
    def test_render_prompt_output_card_uses_provider_neutral_empty_state_text(self) -> None:
        prompt_output = PromptOutputRecord(
            slug="custom-slug",
            title="Custom Output",
            response_path=None,
            response_html_path=None,
            response_pdf_path=None,
            metadata_path=None,
            processed_at=None,
            response_markdown=None,
        )

        html = render_prompt_output_card(
            prompt_output=prompt_output,
            output_dir=Path("."),
            site_dir=Path("."),
            base_path="/site/",
        )

        self.assertIn("No generated response yet", html)
        self.assertNotIn("No OpenAI response yet", html)


if __name__ == "__main__":
    unittest.main()
