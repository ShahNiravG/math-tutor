"""Guarded production build and deployment workflow."""

from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

from math_tutor.env_config import load_dotenv_if_present
from math_tutor.site_builder import build_site


PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = PACKAGE_DIR / "output"
DEFAULT_DEPLOY_ROOT = DEFAULT_OUTPUT_DIR / "deploy" / "math_tutor"
PRODUCTION_BASE_PATH = ""
REMOTE_DESTINATION = "bupbismy@aksharconsultants.com:public_html/math_tutor/"
LIVE_GUIDE_URL = (
    "https://mathdelight.com/courses/ap-calculus-ab/responses/"
    "4839635_chapter-2-notetakers__study-guide-gpt5.html"
)
LIVE_ALGEBRA_URL = "https://mathdelight.com/courses/algebra-2-trig/"
LIVE_CHAPTER_TWO_URL = "https://mathdelight.com/courses/ap-calculus-ab/doc-4839635.html"


class ProductionLayoutError(ValueError):
    """Raised when a deploy tree does not match the production contract."""


def build_production_site(*, deploy_root: Path = DEFAULT_DEPLOY_ROOT) -> Path:
    deploy_root = deploy_root.resolve()
    return build_site(
        output_dir=DEFAULT_OUTPUT_DIR,
        site_dir=deploy_root,
        base_path=PRODUCTION_BASE_PATH,
    )


def validate_production_tree(deploy_root: Path) -> None:
    deploy_root = deploy_root.resolve()
    obsolete_site_dir = deploy_root / "site"
    if obsolete_site_dir.exists():
        raise ProductionLayoutError(
            f"Production tree contains obsolete nested site directory: {obsolete_site_dir}"
        )

    site_dir = deploy_root
    guide_path = (
        site_dir
        / "courses"
        / "ap-calculus-ab"
        / "responses"
        / "4839635_chapter-2-notetakers__study-guide-gpt5.html"
    )
    required = (
        site_dir / "index.html",
        site_dir / "courses" / "ap-calculus-ab" / "doc-4839635.html",
        site_dir / "courses" / "algebra-2-trig" / "index.html",
        guide_path,
    )
    missing = [path.relative_to(deploy_root).as_posix() for path in required if not path.is_file()]
    if missing:
        raise ProductionLayoutError(
            "Production tree is incomplete; missing: " + ", ".join(missing)
        )

    stale_links = [
        path.relative_to(deploy_root).as_posix()
        for path in deploy_root.rglob("*.html")
        if '"/site/' in path.read_text(encoding="utf-8")
    ]
    if stale_links:
        raise ProductionLayoutError(
            "Production HTML contains obsolete /site/ links: " + ", ".join(stale_links)
        )

    guide_html = guide_path.read_text(encoding="utf-8")
    if r"<li>\[</li>" in guide_html:
        raise ProductionLayoutError("Study guide contains an orphan MathJax display delimiter.")
    expected_math = r"\[ \lim_{x\to c}f(x)=\infty \] means \(f(x)\)"
    if expected_math not in guide_html:
        raise ProductionLayoutError("Study guide is missing the corrected infinite-limit expression.")


def verify_live_site() -> None:
    checks = (
        (LIVE_GUIDE_URL, "Mastery Goals"),
        (LIVE_GUIDE_URL, r"\[ \lim_{x\to c}f(x)=\infty \] means \(f(x)\)"),
        (LIVE_ALGEBRA_URL, "Algebra II"),
        (LIVE_CHAPTER_TWO_URL, 'id="ai-challenge"'),
    )
    cache: dict[str, str] = {}
    for url, expected in checks:
        if url not in cache:
            request = Request(url, headers={"User-Agent": "math-tutor-production-verifier/1.0"})
            with urlopen(request, timeout=30) as response:
                if response.status != 200:
                    raise RuntimeError(f"Live verification failed for {url}: HTTP {response.status}")
                cache[url] = response.read().decode("utf-8")
        if expected not in cache[url]:
            raise RuntimeError(f"Live verification failed for {url}: expected content missing")


def deploy_production_site(
    *,
    confirm_production: bool,
    deploy_root: Path | None = None,
) -> None:
    if not confirm_production:
        raise ValueError("Production deployment requires --confirm-production.")
    resolved_root = (deploy_root or DEFAULT_DEPLOY_ROOT).resolve()
    build_production_site(deploy_root=resolved_root)
    validate_production_tree(resolved_root)
    subprocess.run(
        ["rsync", "-a", f"{resolved_root}/", REMOTE_DESTINATION],
        check=True,
    )
    verify_live_site()


def _deploy_root_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--deploy-root",
        type=Path,
        default=DEFAULT_DEPLOY_ROOT,
        help=f"Production sync root. Defaults to {DEFAULT_DEPLOY_ROOT}.",
    )


def main_build() -> None:
    parser = argparse.ArgumentParser(description="Build and validate the production domain-root tree.")
    _deploy_root_argument(parser)
    args = parser.parse_args()
    load_dotenv_if_present()
    index_path = build_production_site(deploy_root=args.deploy_root)
    validate_production_tree(args.deploy_root)
    print(f"Validated production site at {index_path}")


def main_deploy() -> None:
    parser = argparse.ArgumentParser(
        description="Build, validate, deploy, and verify the production domain-root tree."
    )
    _deploy_root_argument(parser)
    parser.add_argument(
        "--confirm-production",
        action="store_true",
        help="Required acknowledgement that this command changes the live site.",
    )
    args = parser.parse_args()
    if not args.confirm_production:
        parser.error("--confirm-production is required")
    load_dotenv_if_present()
    deploy_production_site(
        confirm_production=args.confirm_production,
        deploy_root=args.deploy_root,
    )
    print("Production deployment and live verification succeeded.")
