from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from math_tutor.site_assets import (
    build_site_href,
    determine_base_path,
    is_deploy_site_dir,
    normalize_base_path,
)


class SiteAssetsTests(unittest.TestCase):
    def test_normalize_and_determine_base_path(self) -> None:
        self.assertEqual(normalize_base_path("math_tutor"), "/math_tutor/")
        self.assertEqual(normalize_base_path("/math_tutor/"), "/math_tutor/")
        self.assertEqual(
            determine_base_path(
                raw_base_path="math_tutor",
                output_dir=Path("/tmp/out"),
                site_dir=Path("/tmp/out/site"),
            ),
            "/math_tutor/",
        )

    def test_is_deploy_site_dir(self) -> None:
        output_dir = Path("/tmp/project/output")
        self.assertTrue(is_deploy_site_dir(output_dir=output_dir, site_dir=Path("/tmp/project/output/deploy/math_tutor/site")))
        self.assertFalse(is_deploy_site_dir(output_dir=output_dir, site_dir=Path("/tmp/project/output/site")))

    def test_build_site_href_copies_into_deploy_tree(self) -> None:
        with TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "output"
            site_dir = output_dir / "deploy" / "math_tutor" / "site"
            responses_dir = output_dir / "responses"
            responses_dir.mkdir(parents=True, exist_ok=True)
            site_dir.mkdir(parents=True, exist_ok=True)
            source = responses_dir / "example.html"
            source.write_text("<html></html>", encoding="utf-8")

            href = build_site_href(
                path=source,
                output_dir=output_dir,
                site_dir=site_dir,
                base_path="",
            )

            self.assertEqual(href, "responses/example.html")
            self.assertTrue((site_dir / "responses" / "example.html").exists())


if __name__ == "__main__":
    unittest.main()
