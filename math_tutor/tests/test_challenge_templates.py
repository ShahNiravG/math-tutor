from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ChallengeTemplateTests(unittest.TestCase):
    def test_result_template_uses_hidden_copy_payload_instead_of_inline_json(self) -> None:
        template = (ROOT / "challenges_src" / "result.php").read_text(encoding="utf-8")

        self.assertIn('class="copy-payload"', template)
        self.assertIn('onclick="copyRawText(this)"', template)
        self.assertNotIn('onclick="copyRawText(this,<?= json_encode($copy_text) ?>)"', template)

    def test_partial_result_template_uses_hidden_copy_payload_instead_of_inline_json(self) -> None:
        template = (ROOT / "challenges_src" / "partial_result.php").read_text(encoding="utf-8")

        self.assertIn('class="copy-payload"', template)
        self.assertIn('onclick="copyRawText(this)"', template)
        self.assertNotIn('onclick="copyRawText(this,<?= json_encode($copy_text) ?>)"', template)


if __name__ == "__main__":
    unittest.main()
