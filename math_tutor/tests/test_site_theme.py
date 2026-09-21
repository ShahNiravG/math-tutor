from __future__ import annotations

import unittest

from math_tutor.site_theme import BASE_SITE_PAGE_STYLES


class SiteThemeTests(unittest.TestCase):
    def test_ai_challenge_cards_have_responsive_actions_status_and_prompt_fallback_styles(self) -> None:
        css = BASE_SITE_PAGE_STYLES

        self.assertIn(".ai-challenge-actions", css)
        self.assertIn(".ai-challenge-status", css)
        self.assertIn(".ai-challenge-fallback", css)
        self.assertIn(".ai-challenge-fallback textarea", css)
        self.assertIn(".ai-challenge-copy", css)
        self.assertIn("@media (max-width: 520px)", css)
        self.assertIn(".ai-challenge-provider", css)


if __name__ == "__main__":
    unittest.main()
