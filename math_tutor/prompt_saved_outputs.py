"""Helpers for saved prompt-output reuse, skipping, and printing."""

from __future__ import annotations

import subprocess
from pathlib import Path

from math_tutor.canvas_course import CanvasFile
from math_tutor.print_targets import collect_print_targets
from math_tutor.prompt_catalog import PromptSpec
from math_tutor.response_artifacts import pretty_title
from math_tutor.state_store import (
    GeneratedOutputState,
    canonical_generated_output_state_path,
    load_fetch_state,
    load_generated_output_state,
)


def print_saved_prompt_pdfs(
    *,
    output_dir: Path,
    prompt_slugs: tuple[str, ...],
    chapter_filters: list[str],
    printer: str,
    dry_run: bool = False,
) -> None:
    fetch_state = load_fetch_state(output_dir / "fetch_state.json")
    generated_output_state = load_generated_output_state(
        canonical_generated_output_state_path(output_dir)
    )
    targets = collect_print_targets(
        fetch_state=fetch_state,
        generated_output_state=generated_output_state,
        prompt_slugs=prompt_slugs,
        chapter_filters=chapter_filters,
        pretty_title=pretty_title,
    )
    if not targets:
        chapter_text = f" for chapters {', '.join(chapter_filters)}" if chapter_filters else ""
        raise SystemExit(
            f"No printable PDFs were found for prompts {', '.join(prompt_slugs)}{chapter_text}."
        )

    if dry_run:
        print(f"Dry run — {len(targets)} PDF(s) would be sent to printer {printer}:")
        for target in targets:
            print(f"  {target.chapter_label} - {target.prompt_title}: {target.pdf_path.name}")
        return

    print(f"Sending {len(targets)} PDF(s) to printer {printer}...")
    for target in targets:
        try:
            subprocess.run(
                ["lp", "-d", printer, "-o", "sides=two-sided-long-edge", str(target.pdf_path)],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError as exc:
            raise SystemExit("The 'lp' command is not available on this system.") from exc
        except subprocess.CalledProcessError as exc:
            details = (exc.stderr or exc.stdout or "").strip()
            if details:
                raise SystemExit(f"Printing failed for {target.pdf_path.name}: {details}") from exc
            raise SystemExit(f"Printing failed for {target.pdf_path.name}.") from exc

        print(f"Printed {target.chapter_label} - {target.prompt_title}: {target.pdf_path}")


PROMPT_FAMILY_PREFIXES: tuple[str, ...] = ("study-guide", "inspiring-videos")


def _family_prefix_for_slug(slug: str) -> str | None:
    for prefix in PROMPT_FAMILY_PREFIXES:
        if slug == prefix or slug.startswith(f"{prefix}-"):
            return prefix
    return None


def _family_sibling_exists(*, response_path: Path, family_prefix: str) -> bool:
    responses_dir = response_path.parent
    stem = response_path.stem.rsplit("__", 1)[0]
    for sibling in responses_dir.glob(f"{stem}__{family_prefix}*.md"):
        if sibling.exists():
            return True
    return False


def evaluate_generation_decision(
    *,
    prompt_spec: PromptSpec,
    response_path: Path,
    response_html_path: Path,
    response_pdf_path: Path,
    requested_prompt_slugs: set[str] | frozenset[str] = frozenset(),
) -> str | None:
    has_all_artifacts = response_path.exists() and response_html_path.exists()
    if prompt_spec.generate_response_pdf:
        has_all_artifacts = has_all_artifacts and response_pdf_path.exists()
    if has_all_artifacts:
        return "output files already exist"

    family_prefix = _family_prefix_for_slug(prompt_spec.slug)
    if (
        family_prefix
        and prompt_spec.slug not in requested_prompt_slugs
        and _family_sibling_exists(response_path=response_path, family_prefix=family_prefix)
    ):
        return (
            f"another {family_prefix} variant already exists "
            f"(pass --prompt {prompt_spec.slug} to force generation)"
        )

    return None


def should_skip_generation(
    *,
    canvas_file: CanvasFile,
    prompt_spec: PromptSpec,
    response_path: Path,
    response_html_path: Path,
    response_pdf_path: Path,
    generated_output_state: GeneratedOutputState,
    force: bool,
    force_generation: bool,
    index: int,
    total: int,
    requested_prompt_slugs: set[str] | frozenset[str] = frozenset(),
) -> bool:
    del generated_output_state

    if force or force_generation:
        return False

    reason = evaluate_generation_decision(
        prompt_spec=prompt_spec,
        response_path=response_path,
        response_html_path=response_html_path,
        response_pdf_path=response_pdf_path,
        requested_prompt_slugs=requested_prompt_slugs,
    )
    if reason is None:
        return False

    print(
        f"[{index}/{total}] Skipping {canvas_file.display_name} ({prompt_spec.title}); {reason}."
    )
    return True
