"""Runtime helper contracts for the operator CLI."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
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

        display_name = pdf_path_check.name
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


def build_saved_assignment_files_for_names(
    *,
    fetch_state: FetchState,
    assignments_dir: Path,
    assignment_names: list[str],
) -> list[CanvasFile]:
    if not assignment_names:
        return []

    assignments_root = assignments_dir.resolve()
    saved_files_by_name: dict[str, CanvasFile] = {}

    for file_id, info in fetch_state.fetched.items():
        pdf_path_check = Path(info["pdf_path"])
        if not pdf_path_check.is_relative_to(assignments_root):
            continue

        canvas_file = CanvasFile(
            file_id=int(file_id),
            display_name=pdf_path_check.name,
            download_url=info.get("download_url") or "",
            content_type=info.get("content_type", "application/pdf"),
            size=None,
            updated_at=None,
        )
        normalized_candidates = {
            _normalize_assignment_name(pdf_path_check.name),
            _normalize_assignment_name(info.get("display_name", "")),
        }
        for normalized_name in normalized_candidates:
            if normalized_name and normalized_name not in saved_files_by_name:
                saved_files_by_name[normalized_name] = canvas_file

    ordered_files: list[CanvasFile] = []
    seen_file_ids: set[int] = set()
    for assignment_name in assignment_names:
        canvas_file = saved_files_by_name.get(_normalize_assignment_name(assignment_name))
        if canvas_file is None or canvas_file.file_id in seen_file_ids:
            continue
        ordered_files.append(canvas_file)
        seen_file_ids.add(canvas_file.file_id)
    return ordered_files


def build_missing_assignment_entries(
    *,
    assignment_entries: list[tuple[str, str]],
    saved_files: list[CanvasFile],
) -> list[tuple[str, str]]:
    saved_names = {_normalize_assignment_name(file.display_name) for file in saved_files}
    return [
        (name, url)
        for name, url in assignment_entries
        if _normalize_assignment_name(name) not in saved_names
    ]


def build_cached_fetch_files_for_chapters(
    *,
    fetch_state: FetchState,
    assignments_dir: Path,
    normalized_chapter_filters: list[str],
    fetch_assignments: bool,
    limit: int | None,
) -> list[CanvasFile]:
    if not normalized_chapter_filters:
        return []

    saved_files = (
        build_saved_assignment_files(
            fetch_state=fetch_state,
            assignments_dir=assignments_dir,
            normalized_chapter_filters=normalized_chapter_filters,
            limit=None,
        )
        if fetch_assignments
        else build_saved_class_note_files(
            fetch_state=fetch_state,
            assignments_dir=assignments_dir,
            normalized_chapter_filters=normalized_chapter_filters,
            limit=None,
        )
    )
    if not saved_files:
        return []
    if not saved_files_cover_chapter_filters(
        saved_files=saved_files,
        normalized_chapter_filters=normalized_chapter_filters,
        fetch_assignments=fetch_assignments,
    ):
        return []
    if limit is not None:
        return saved_files[:limit]
    return saved_files


def saved_files_cover_chapter_filters(
    *,
    saved_files: list[CanvasFile],
    normalized_chapter_filters: list[str],
    fetch_assignments: bool,
) -> bool:
    if not normalized_chapter_filters:
        return False
    return all(
        any(
            _saved_file_matches_single_chapter_filter(
                canvas_file=canvas_file,
                chapter_filter=chapter_filter,
                fetch_assignments=fetch_assignments,
            )
            for canvas_file in saved_files
        )
        for chapter_filter in normalized_chapter_filters
    )


def _saved_file_matches_single_chapter_filter(
    *,
    canvas_file: CanvasFile,
    chapter_filter: str,
    fetch_assignments: bool,
) -> bool:
    if not fetch_assignments:
        return display_name_matches_chapter_filters(canvas_file.display_name, [chapter_filter])

    assignment_chapters = parse_assignment_chapters(canvas_file.display_name)
    combined_label = " & ".join(sorted(assignment_chapters, key=chapter_sort_key))
    if combined_label and chapter_matches_filters(combined_label, canvas_file.display_name, [chapter_filter]):
        return True
    return any(
        chapter_matches_filters(chapter, canvas_file.display_name, [chapter_filter])
        for chapter in assignment_chapters
    )


def needs_openai_generation_client(prompts: tuple[PromptSpec, ...]) -> bool:
    return any(not (prompt.model or "").startswith("gemini") for prompt in prompts)


def needs_pdf_browser(prompts: tuple[PromptSpec, ...]) -> bool:
    return any(prompt.generate and prompt.generate_response_pdf for prompt in prompts)


def _normalize_assignment_name(name: str) -> str:
    base_name = re.sub(r"\.pdf$", "", Path(name).name, flags=re.IGNORECASE)
    base_name = re.sub(r"^\d+_", "", base_name)
    return re.sub(r"[^a-z0-9]+", " ", base_name.lower()).strip()
