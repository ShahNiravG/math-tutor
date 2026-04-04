"""Runtime helper contracts for the operator CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from math_tutor.canvas_course import CanvasFile
from math_tutor.chaptering import chapter_sort_key, parse_assignment_chapters, parse_display_name_chapter
from math_tutor.print_targets import chapter_matches_filters, normalize_chapter_filter
from math_tutor.state_store import FetchState

if TYPE_CHECKING:
    from math_tutor.prompt_catalog import PromptSpec


@dataclass(frozen=True)
class OutputLayout:
    output_dir: Path
    downloads_dir: Path
    assignments_dir: Path
    responses_dir: Path
    metadata_dir: Path


def build_output_layout(output_dir: Path) -> OutputLayout:
    return OutputLayout(
        output_dir=output_dir,
        downloads_dir=output_dir / "downloads",
        assignments_dir=output_dir / "downloads" / "assignments",
        responses_dir=output_dir / "responses",
        metadata_dir=output_dir / "metadata",
    )


def ensure_output_layout(layout: OutputLayout) -> None:
    layout.downloads_dir.mkdir(parents=True, exist_ok=True)
    layout.assignments_dir.mkdir(parents=True, exist_ok=True)
    layout.responses_dir.mkdir(parents=True, exist_ok=True)
    layout.metadata_dir.mkdir(parents=True, exist_ok=True)


def normalize_cli_chapter_filters(chapter_filters: list[str] | None) -> list[str]:
    return [normalize_chapter_filter(chapter) for chapter in chapter_filters or []]


def display_name_matches_chapter_filters(
    display_name: str,
    normalized_chapter_filters: list[str],
) -> bool:
    if not normalized_chapter_filters:
        return True
    chapter_label = parse_display_name_chapter(display_name)
    if not chapter_label:
        return False
    return chapter_matches_filters(chapter_label, display_name, normalized_chapter_filters)


def build_saved_class_note_files(
    *,
    fetch_state: FetchState,
    assignments_dir: Path,
    normalized_chapter_filters: list[str],
    limit: int | None,
) -> list[CanvasFile]:
    saved_files: list[CanvasFile] = []
    assignments_root = assignments_dir.resolve()

    for file_id, info in fetch_state.fetched.items():
        pdf_path_check = Path(info["pdf_path"])
        if pdf_path_check.is_relative_to(assignments_root):
            continue

        display_name = info["display_name"]
        if not display_name_matches_chapter_filters(display_name, normalized_chapter_filters):
            continue

        saved_files.append(
            CanvasFile(
                file_id=int(file_id),
                display_name=display_name,
                download_url=info.get("download_url") or "",
                content_type=info.get("content_type", "application/pdf"),
                size=None,
                updated_at=None,
            )
        )

    if limit is not None:
        return saved_files[:limit]
    return saved_files


def build_saved_assignment_files(
    *,
    fetch_state: FetchState,
    assignments_dir: Path,
    normalized_chapter_filters: list[str],
    limit: int | None,
) -> list[CanvasFile]:
    saved_files: list[CanvasFile] = []
    assignments_root = assignments_dir.resolve()

    for file_id, info in fetch_state.fetched.items():
        pdf_path_check = Path(info["pdf_path"])
        if not pdf_path_check.is_relative_to(assignments_root):
            continue

        assignment_chapters = parse_assignment_chapters(pdf_path_check.name)
        if normalized_chapter_filters:
            combined_label = " & ".join(sorted(assignment_chapters, key=chapter_sort_key))
            matches_filter = (
                (combined_label and chapter_matches_filters(combined_label, pdf_path_check.name, normalized_chapter_filters))
                or any(
                    chapter_matches_filters(chapter, pdf_path_check.name, normalized_chapter_filters)
                    for chapter in assignment_chapters
                )
            )
            if not matches_filter:
                continue

        display_name = info["display_name"]
        saved_files.append(
            CanvasFile(
                file_id=int(file_id),
                display_name=display_name,
                download_url=info.get("download_url") or "",
                content_type=info.get("content_type", "application/pdf"),
                size=None,
                updated_at=None,
            )
        )

    if limit is not None:
        return saved_files[:limit]
    return saved_files


def needs_openai_generation_client(prompts: tuple[PromptSpec, ...]) -> bool:
    return any(not (prompt.model or "").startswith("gemini") for prompt in prompts)


def needs_pdf_browser(prompts: tuple[PromptSpec, ...]) -> bool:
    return any(prompt.generate and prompt.generate_response_pdf for prompt in prompts)
