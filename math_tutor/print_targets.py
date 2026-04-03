"""Print-target selection helpers for saved artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from math_tutor.chaptering import chapter_sort_key, parse_display_name_chapter
from math_tutor.prompt_catalog import (
    ASSIGNMENT_PRINT_SLUG,
    CLASS_NOTE_PRINT_SLUG,
    PROMPTS_BY_SLUG,
    prompt_title_from_slug,
)
from math_tutor.state_store import FetchState, GeneratedOutputState


@dataclass(frozen=True)
class PrintTarget:
    file_id: str
    chapter_label: str
    display_name: str
    prompt_slug: str
    prompt_title: str
    pdf_path: Path


def first_processed_value(processed: dict[str, dict[str, str]], key: str) -> str | None:
    for prompt_slug in PROMPTS_BY_SLUG:
        prompt_entry = processed.get(prompt_slug, {})
        if isinstance(prompt_entry, dict):
            value = prompt_entry.get(key)
            if isinstance(value, str) and value:
                return value
    return None


def normalize_chapter_filter(value: str) -> str:
    return " ".join(value.strip().lower().split())


def chapter_matches_filters(chapter_label: str, display_name: str, chapter_filters: list[str]) -> bool:
    chapter_text = normalize_chapter_filter(chapter_label)
    for chapter_filter in chapter_filters:
        if chapter_filter == chapter_text:
            return True
        if chapter_text.startswith(chapter_filter + "."):
            return True
        if chapter_text.startswith(chapter_filter + " "):
            return True
    return False


def sort_key_from_states(
    fetch_state: dict[str, dict[str, Any]],
    generated_output_state: dict[str, dict[str, Any]],
) -> Callable[[str], tuple[float, str]]:
    def key(file_id: str) -> tuple[float, str]:
        display_name = (
            first_processed_value(generated_output_state.get(file_id, {}), "display_name")
            or fetch_state.get(file_id, {}).get("display_name")
            or ""
        )
        chapter_label = parse_display_name_chapter(display_name)
        chapter_value = chapter_sort_key(chapter_label) if chapter_label else 10_000.0
        return (chapter_value, display_name.lower())

    return key


def collect_print_targets(
    *,
    fetch_state: FetchState,
    generated_output_state: GeneratedOutputState,
    prompt_slugs: tuple[str, ...],
    chapter_filters: list[str],
    pretty_title: Callable[[str], str],
) -> list[PrintTarget]:
    chapter_filters_normalized = [normalize_chapter_filter(value) for value in chapter_filters if value.strip()]
    file_ids = sorted(
        set(fetch_state.fetched) | set(generated_output_state.processed),
        key=sort_key_from_states(fetch_state.fetched, generated_output_state.processed),
    )
    targets: list[PrintTarget] = []
    for file_id in file_ids:
        fetched = fetch_state.fetched.get(file_id, {})
        processed = generated_output_state.processed.get(file_id, {})
        display_name = (
            first_processed_value(processed, "display_name")
            or fetched.get("display_name")
            or f"File {file_id}"
        )
        parsed_chapter = parse_display_name_chapter(display_name)
        chapter_label = parsed_chapter or pretty_title(display_name)
        if chapter_filters_normalized and not chapter_matches_filters(chapter_label, display_name, chapter_filters_normalized):
            continue
        chapter_display = f"Chapter {chapter_label}" if parsed_chapter else chapter_label

        for prompt_slug in prompt_slugs:
            if prompt_slug == ASSIGNMENT_PRINT_SLUG:
                pdf_value = fetched.get("pdf_path", "")
                if not pdf_value or "/assignments/" not in pdf_value:
                    continue
                pdf_path = Path(pdf_value)
                if not pdf_path.exists():
                    continue
                targets.append(
                    PrintTarget(
                        file_id=file_id,
                        chapter_label=chapter_display,
                        display_name=display_name,
                        prompt_slug=prompt_slug,
                        prompt_title="Assignment",
                        pdf_path=pdf_path,
                    )
                )
                continue

            if not processed:
                continue

            if prompt_slug == CLASS_NOTE_PRINT_SLUG:
                pdf_value = fetched.get("pdf_path", "")
                if not pdf_value:
                    continue
                pdf_path = Path(pdf_value)
                if not pdf_path.exists():
                    continue
                targets.append(
                    PrintTarget(
                        file_id=file_id,
                        chapter_label=chapter_display,
                        display_name=display_name,
                        prompt_slug=prompt_slug,
                        prompt_title="Class Note",
                        pdf_path=pdf_path,
                    )
                )
                continue

            prompt_state = processed.get(prompt_slug, {})
            pdf_value = prompt_state.get("response_pdf_path", "")
            if not pdf_value:
                continue
            pdf_path = Path(pdf_value)
            if not pdf_path.exists():
                continue
            targets.append(
                PrintTarget(
                    file_id=file_id,
                    chapter_label=chapter_display,
                    display_name=display_name,
                    prompt_slug=prompt_slug,
                    prompt_title=prompt_state.get("prompt_title") or prompt_title_from_slug(prompt_slug),
                    pdf_path=pdf_path,
                )
            )
    return targets
