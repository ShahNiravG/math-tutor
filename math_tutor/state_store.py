"""Saved-state loading and normalization for fetch and generated output artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from math_tutor.generated_metadata import normalize_metadata_payload
from math_tutor.prompt_catalog import STUDY_GUIDE_PROMPT, prompt_title_from_slug

GENERATED_OUTPUT_STATE_FILENAME = "generated_output_state.json"


@dataclass
class FetchState:
    path: Path
    fetched: dict[str, dict[str, str]]


@dataclass
class GeneratedOutputState:
    path: Path
    processed: dict[str, dict[str, dict[str, str]]]


def load_fetch_state(path: Path) -> FetchState:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        fetched = payload.get("fetched", {})
        if isinstance(fetched, dict):
            return FetchState(path=path, fetched=fetched)
    return FetchState(path=path, fetched={})


def save_fetch_state(fetch_state: FetchState) -> None:
    payload = {"fetched": fetch_state.fetched}
    fetch_state.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def canonical_generated_output_state_path(output_dir: Path) -> Path:
    return output_dir / GENERATED_OUTPUT_STATE_FILENAME


def load_generated_output_state(path: Path) -> GeneratedOutputState:
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        processed = payload.get("processed", {})
        if isinstance(processed, dict):
            return GeneratedOutputState(path=path, processed=normalize_generated_output_state(processed))
    return GeneratedOutputState(path=path, processed={})


def save_generated_output_state(generated_output_state: GeneratedOutputState) -> None:
    payload = {"processed": generated_output_state.processed}
    generated_output_state.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def normalize_generated_output_state(processed: dict[str, dict[str, Any]]) -> dict[str, dict[str, dict[str, str]]]:
    normalized: dict[str, dict[str, dict[str, str]]] = {}
    for file_id, entry in processed.items():
        if not isinstance(entry, dict):
            continue
        if "response_path" in entry:
            prompt_entry = dict(entry)
            prompt_entry.setdefault("prompt_slug", STUDY_GUIDE_PROMPT.slug)
            prompt_entry.setdefault("prompt_title", STUDY_GUIDE_PROMPT.title)
            normalized[file_id] = {STUDY_GUIDE_PROMPT.slug: prompt_entry}
            continue

        prompt_map: dict[str, dict[str, str]] = {}
        for prompt_slug, prompt_entry in entry.items():
            if not isinstance(prompt_entry, dict):
                continue
            prompt_entry_copy = normalize_metadata_payload(prompt_entry)
            prompt_entry_copy.setdefault("prompt_slug", prompt_slug)
            prompt_entry_copy.setdefault("prompt_title", prompt_title_from_slug(prompt_slug))
            prompt_map[prompt_slug] = prompt_entry_copy
        if prompt_map:
            normalized[file_id] = prompt_map
    return normalized
