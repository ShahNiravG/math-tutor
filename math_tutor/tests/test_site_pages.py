from __future__ import annotations

import unittest
from pathlib import Path

from math_tutor.site_pages import build_index_html


class SitePagesTests(unittest.TestCase):
    def test_build_index_html_includes_core_destinations(self) -> None:
        html = build_index_html(
            records=[],
            output_dir=Path("/tmp/output"),
            site_dir=Path("/tmp/site"),
            base_path="/site/",
            include_guided_learning=False,
            site_page_href=lambda filename, base_path: f"{base_path}{filename}",
        )

        self.assertIn("Challenge Exams", html)
        self.assertIn("Live Tutor", html)
        self.assertIn("Math Delight", html)


if __name__ == "__main__":
    unittest.main()
