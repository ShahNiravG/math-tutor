from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

from math_tutor.production_deploy import (
    ProductionLayoutError,
    build_production_site,
    deploy_production_site,
    main_deploy,
    validate_production_tree,
    verify_live_site,
)


class ProductionDeployTests(unittest.TestCase):
    def test_build_production_site_uses_canonical_domain_root_and_empty_base_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            deploy_root = Path(temp_dir) / "math_tutor"
            with patch("math_tutor.production_deploy.build_site") as build_site:
                build_site.return_value = deploy_root / "index.html"

                result = build_production_site(deploy_root=deploy_root)

        self.assertEqual(result, deploy_root / "index.html")
        build_site.assert_called_once()
        kwargs = build_site.call_args.kwargs
        self.assertEqual(kwargs["site_dir"], deploy_root)
        self.assertEqual(kwargs["base_path"], "")

    def test_validate_production_tree_rejects_nested_site_tree(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            deploy_root = Path(temp_dir) / "math_tutor"
            site = deploy_root / "site"
            site.mkdir(parents=True)
            (site / "index.html").write_text("obsolete nested site", encoding="utf-8")

            with self.assertRaisesRegex(ProductionLayoutError, "obsolete nested site"):
                validate_production_tree(deploy_root)

    def test_validate_production_tree_accepts_domain_root_and_math_fix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            deploy_root = Path(temp_dir) / "math_tutor"
            calculus = deploy_root / "courses" / "ap-calculus-ab"
            algebra = deploy_root / "courses" / "algebra-2-trig"
            responses = calculus / "responses"
            responses.mkdir(parents=True)
            algebra.mkdir(parents=True)
            (deploy_root / "index.html").write_text('href="courses/"', encoding="utf-8")
            (calculus / "doc-4839635.html").write_text("Read Guide", encoding="utf-8")
            (algebra / "index.html").write_text("Algebra II", encoding="utf-8")
            (responses / "4839635_chapter-2-notetakers__study-guide-gpt5.html").write_text(
                r"<li>\[ \lim_{x\to c}f(x)=\infty \] means \(f(x)\)</li>",
                encoding="utf-8",
            )

            validate_production_tree(deploy_root)

    def test_validate_production_tree_rejects_obsolete_site_links(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            deploy_root = Path(temp_dir) / "math_tutor"
            calculus = deploy_root / "courses" / "ap-calculus-ab"
            algebra = deploy_root / "courses" / "algebra-2-trig"
            responses = calculus / "responses"
            responses.mkdir(parents=True)
            algebra.mkdir(parents=True)
            (deploy_root / "index.html").write_text(
                'href="/site/courses/ap-calculus-ab/"', encoding="utf-8"
            )
            (calculus / "doc-4839635.html").write_text("Read Guide", encoding="utf-8")
            (algebra / "index.html").write_text("Algebra II", encoding="utf-8")
            (responses / "4839635_chapter-2-notetakers__study-guide-gpt5.html").write_text(
                r"<li>\[ \lim_{x\to c}f(x)=\infty \] means \(f(x)\)</li>",
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ProductionLayoutError, "obsolete /site/ links"):
                validate_production_tree(deploy_root)

    def test_deploy_requires_explicit_confirmation_before_build_or_sync(self) -> None:
        with patch("math_tutor.production_deploy.build_production_site") as build_site:
            with patch("math_tutor.production_deploy.subprocess.run") as run:
                with self.assertRaisesRegex(ValueError, "confirm-production"):
                    deploy_production_site(confirm_production=False)

        build_site.assert_not_called()
        run.assert_not_called()

    def test_deploy_cli_reports_clean_usage_error_without_confirmation(self) -> None:
        with patch("sys.argv", ["math-tutor-deploy-production"]):
            with self.assertRaisesRegex(SystemExit, "2"):
                main_deploy()

    def test_deploy_builds_validates_syncs_canonical_root_once_then_verifies(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            deploy_root = Path(temp_dir) / "math_tutor"
            with patch("math_tutor.production_deploy.build_production_site") as build_site:
                with patch("math_tutor.production_deploy.validate_production_tree") as validate:
                    with patch("math_tutor.production_deploy.subprocess.run") as run:
                        with patch("math_tutor.production_deploy.verify_live_site") as verify:
                            deploy_production_site(
                                confirm_production=True,
                                deploy_root=deploy_root,
                            )

        build_site.assert_called_once_with(deploy_root=deploy_root)
        validate.assert_called_once_with(deploy_root)
        self.assertEqual(
            run.call_args_list,
            [
                call(
                    [
                        "rsync",
                        "-a",
                        f"{deploy_root}/",
                        "bupbismy@aksharconsultants.com:public_html/math_tutor/",
                    ],
                    check=True,
                ),
            ],
        )
        verify.assert_called_once_with()

    def test_verify_live_site_checks_only_canonical_root_urls(self) -> None:
        response = MagicMock()
        response.__enter__.return_value.status = 200
        response.__enter__.return_value.read.return_value = (
            b'Mastery Goals \\[ \\lim_{x\\to c}f(x)=\\infty \\] means \\(f(x)\\) '
            b'Algebra II id="ai-challenge"'
        )

        with patch("math_tutor.production_deploy.urlopen", return_value=response) as urlopen:
            verify_live_site()

        requested_urls = [request.full_url for request in (item.args[0] for item in urlopen.call_args_list)]
        self.assertIn(
            "https://mathdelight.com/courses/ap-calculus-ab/doc-4839635.html",
            requested_urls,
        )
        self.assertIn(
            "https://mathdelight.com/courses/ap-calculus-ab/responses/"
            "4839635_chapter-2-notetakers__study-guide-gpt5.html",
            requested_urls,
        )
        self.assertIn("https://mathdelight.com/courses/algebra-2-trig/", requested_urls)
        self.assertNotIn(
            "https://mathdelight.com/site/courses/ap-calculus-ab/doc-4839635.html",
            requested_urls,
        )


if __name__ == "__main__":
    unittest.main()
