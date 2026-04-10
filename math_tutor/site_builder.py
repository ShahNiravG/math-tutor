from __future__ import annotations

import argparse
from pathlib import Path

from math_tutor.challenge_builder import build_challenges
from math_tutor.experience_variants import CLI_EXPERIENCE_CHOICES
from math_tutor.experience_variants import PRIMARY_EXPERIENCE_VARIANT
from math_tutor.experience_variants import normalize_experience_variant
from math_tutor.site_assets import (
    determine_base_path,
)
from math_tutor.site_cards import (
    load_assignment_files,
    record_page_filename,
)
from math_tutor.site_data import load_records
from math_tutor.site_data import load_assignment_prompt_outputs
from math_tutor.site_pages import (
    build_index_html as render_index_page,
    build_library_page_html as render_library_page,
    build_live_tutor_page_html as render_live_tutor_page,
    build_privacy_policy_page_html as render_privacy_policy_page,
    build_record_page_html as render_record_page,
)
from math_tutor.env_config import load_dotenv_if_present


PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = str(PACKAGE_DIR / "output")
DEFAULT_SITE_DIRNAME = "site"
DEFAULT_EXPERIENCE_VARIANT = PRIMARY_EXPERIENCE_VARIANT


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a readable HTML tutoring page from saved math_tutor outputs."
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory containing downloads, responses, metadata, and state files. Defaults to {DEFAULT_OUTPUT_DIR}.",
    )
    parser.add_argument(
        "--site-dir",
        default=None,
        help="Directory where the generated HTML site should be written. Defaults to <output-dir>/site.",
    )
    parser.add_argument(
        "--base-path",
        default="",
        help=(
            "Optional deployed site prefix such as /math_tutor/. "
            "When provided, generated links use that path instead of relative filesystem-style links."
        ),
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of saved PDFs to include in the generated page.",
    )
    parser.add_argument(
        "--include-guided-learning",
        action="store_true",
        help=(
            "Add a Guided Learning section for each PDF with a ChatGPT Study Mode helper button and prompt copy action."
        ),
    )
    parser.add_argument(
        "--experience",
        choices=CLI_EXPERIENCE_CHOICES,
        default=DEFAULT_EXPERIENCE_VARIANT,
        help=(
            f"Choose which site experience variant to build. Defaults to {DEFAULT_EXPERIENCE_VARIANT}. "
            "Use archived for the older pre-refresh styling."
        ),
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv_if_present()
    args = parse_args()
    index_path = build_site(
        output_dir=Path(args.output_dir).resolve(),
        site_dir=Path(args.site_dir).resolve() if args.site_dir else None,
        base_path=args.base_path,
        limit=args.limit,
        include_guided_learning=args.include_guided_learning,
        experience_variant=normalize_experience_variant(args.experience),
    )
    print(f"Built tutoring page at {index_path}")


def build_site(
    *,
    output_dir: Path,
    site_dir: Path | None = None,
    base_path: str = "",
    limit: int | None = None,
    include_guided_learning: bool = False,
    file_ids: set[str] | None = None,
    experience_variant: str = DEFAULT_EXPERIENCE_VARIANT,
) -> Path:
    experience_variant = normalize_experience_variant(experience_variant)
    resolved_site_dir = site_dir.resolve() if site_dir else output_dir / DEFAULT_SITE_DIRNAME
    resolved_site_dir.mkdir(parents=True, exist_ok=True)
    build_challenges(
        output_dir=output_dir,
        site_dir=resolved_site_dir,
        experience_variant=experience_variant,
    )
    resolved_base_path = determine_base_path(
        raw_base_path=base_path,
        output_dir=output_dir,
        site_dir=resolved_site_dir,
    )

    records = load_records(output_dir)
    if file_ids is not None:
        records = [record for record in records if record.file_id in file_ids]
    if limit is not None:
        records = records[:limit]
    assignments = load_assignment_files(output_dir)
    assignment_prompt_outputs = load_assignment_prompt_outputs(output_dir)
    html_text = render_index_page(
        records=records,
        output_dir=output_dir,
        site_dir=resolved_site_dir,
        base_path=resolved_base_path,
        include_guided_learning=include_guided_learning,
        site_page_href=site_page_href,
        experience_variant=experience_variant,
    )
    index_path = resolved_site_dir / "index.html"
    _write_html_if_changed(index_path, html_text)
    _write_html_if_changed(
        resolved_site_dir / "library.html",
        render_library_page(
            records=records,
            output_dir=output_dir,
            site_dir=resolved_site_dir,
            base_path=resolved_base_path,
            include_guided_learning=include_guided_learning,
            site_page_href=site_page_href,
            experience_variant=experience_variant,
        ),
    )
    _write_html_if_changed(
        resolved_site_dir / "live-tutor.html",
        render_live_tutor_page(
            records=records,
            base_path=resolved_base_path,
            site_page_href=site_page_href,
            experience_variant=experience_variant,
        ),
    )
    _write_html_if_changed(
        resolved_site_dir / "privacy-policy.html",
        render_privacy_policy_page(
            records=records,
            base_path=resolved_base_path,
            site_page_href=site_page_href,
            experience_variant=experience_variant,
        ),
    )
    for record in records:
        _write_html_if_changed(
            resolved_site_dir / record_page_filename(record),
            render_record_page(
                record=record,
                records=records,
                output_dir=output_dir,
                site_dir=resolved_site_dir,
                base_path=resolved_base_path,
                include_guided_learning=include_guided_learning,
                assignments=assignments,
                assignment_prompt_outputs=assignment_prompt_outputs,
                site_page_href=site_page_href,
                experience_variant=experience_variant,
            ),
        )
    return index_path


def _write_html_if_changed(path: Path, content: str) -> None:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return
    path.write_text(content, encoding="utf-8")


def site_page_href(filename: str, base_path: str) -> str:
    return f"{base_path}{filename}" if base_path else filename


if __name__ == "__main__":
    main()
