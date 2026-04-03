"""Record and prompt-output loading helpers for site generation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from math_tutor.site_models import DocumentRecord, PromptOutputRecord
from math_tutor.site_prompt_cards import PROMPT_ORDER
from math_tutor.state_store import canonical_generated_output_state_path, load_generated_output_state


def load_records(output_dir: Path) -> list[DocumentRecord]:
    fetch_state = load_state(output_dir / "fetch_state.json", "fetched")
    generated_output_state = load_generated_output_state(
        canonical_generated_output_state_path(output_dir)
    ).processed

    file_ids = sorted(
        set(fetch_state) | set(generated_output_state),
        key=sort_key_from_id_and_name(fetch_state, generated_output_state),
    )
    records: list[DocumentRecord] = []
    for file_id in file_ids:
        fetched = fetch_state.get(file_id, {})
        pdf_path_str = fetched.get("pdf_path") or ""
        if "/downloads/assignments/" in pdf_path_str:
            continue
        processed = generated_output_state.get(file_id, {})
        display_name = (
            first_prompt_value(processed, "display_name")
            or fetched.get("display_name")
            or f"File {file_id}"
        )
        prompt_outputs = load_prompt_outputs(processed)
        records.append(
            DocumentRecord(
                file_id=file_id,
                display_name=display_name,
                pdf_path=path_or_none(fetched.get("pdf_path")),
                download_url=fetched.get("download_url"),
                fetched_at=fetched.get("fetched_at"),
                prompt_outputs=prompt_outputs,
            )
        )
    return records


def load_prompt_outputs(processed: dict[str, Any]) -> list[PromptOutputRecord]:
    outputs_by_slug: dict[str, PromptOutputRecord] = {}
    for prompt_spec in PROMPT_ORDER:
        prompt_entry = processed.get(prompt_spec.slug, {})
        if not isinstance(prompt_entry, dict):
            prompt_entry = {}
        response_path = path_or_none(prompt_entry.get("response_path"))
        response_html_path = path_or_none(prompt_entry.get("response_html_path"))
        response_pdf_path = path_or_none(prompt_entry.get("response_pdf_path"))
        metadata_path = path_or_none(prompt_entry.get("metadata_path"))
        response_markdown = (
            response_path.read_text(encoding="utf-8")
            if response_path and response_path.exists()
            else None
        )
        outputs_by_slug[prompt_spec.slug] = PromptOutputRecord(
            slug=prompt_spec.slug,
            title=prompt_entry.get("prompt_title") or prompt_spec.title,
            response_path=response_path,
            response_html_path=response_html_path,
            response_pdf_path=response_pdf_path,
            metadata_path=metadata_path,
            processed_at=prompt_entry.get("processed_at"),
            response_markdown=response_markdown,
        )
    return [outputs_by_slug[prompt_spec.slug] for prompt_spec in PROMPT_ORDER]


def first_prompt_value(processed: dict[str, Any], key: str) -> str | None:
    for prompt_spec in PROMPT_ORDER:
        prompt_entry = processed.get(prompt_spec.slug, {})
        if isinstance(prompt_entry, dict):
            value = prompt_entry.get(key)
            if isinstance(value, str) and value:
                return value
    for prompt_entry in processed.values():
        if not isinstance(prompt_entry, dict):
            continue
        value = prompt_entry.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def load_state(path: Path, key: str) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    data = payload.get(key, {})
    return data if isinstance(data, dict) else {}


def path_or_none(value: Any) -> Path | None:
    if isinstance(value, str) and value:
        return Path(value)
    return None


def sort_key_from_id_and_name(
    fetch_state: dict[str, dict[str, Any]],
    generated_output_state: dict[str, dict[str, Any]],
):
    def key(file_id: str) -> tuple[float, str]:
        display_name = (
            first_prompt_value(generated_output_state.get(file_id, {}), "display_name")
            or fetch_state.get(file_id, {}).get("display_name")
            or ""
        )
        match = re.search(r"chp\s+(\d+(?:\.\d+)?)", display_name.lower())
        chapter = float(match.group(1)) if match else 10_000.0
        return (chapter, display_name.lower())

    return key
