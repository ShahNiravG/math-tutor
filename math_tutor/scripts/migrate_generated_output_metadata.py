"""Migrate stored generated-output JSON artifacts to neutral metadata keys."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from math_tutor.generated_metadata import normalize_metadata_payload, provider_name_for_model
from math_tutor.state_store import canonical_generated_output_state_path


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = REPO_ROOT / "math_tutor" / "output"


def migrate_prompt_payload(payload: dict[str, Any]) -> bool:
    normalized = dict(payload)

    model_name = normalized.get("model")
    legacy_model_name = normalized.get("openai_model")
    if not isinstance(model_name, str) and isinstance(legacy_model_name, str):
        normalized["model"] = legacy_model_name
        model_name = legacy_model_name

    if normalized.get("response_id") is None and "openai_response_id" in normalized:
        normalized["response_id"] = normalized.get("openai_response_id")

    if not isinstance(normalized.get("provider"), str) and isinstance(model_name, str):
        normalized["provider"] = provider_name_for_model(model_name)

    normalized.pop("openai_model", None)
    normalized.pop("openai_response_id", None)
    normalized = normalize_metadata_payload(normalized)
    changed = normalized != payload
    if changed:
        payload.clear()
        payload.update(normalized)
    return changed


def migrate_generated_output_state(output_dir: Path) -> int:
    state_path = canonical_generated_output_state_path(output_dir)
    if not state_path.exists():
        return 0

    payload = json.loads(state_path.read_text(encoding="utf-8"))
    processed = payload.get("processed", {})
    changes = 0
    if isinstance(processed, dict):
        for file_entry in processed.values():
            if not isinstance(file_entry, dict):
                continue
            for prompt_entry in file_entry.values():
                if not isinstance(prompt_entry, dict):
                    continue
                if migrate_prompt_payload(prompt_entry):
                    changes += 1

    if changes:
        state_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return changes


def migrate_metadata_files(output_dir: Path) -> int:
    metadata_dir = output_dir / "metadata"
    if not metadata_dir.exists():
        return 0

    changes = 0
    for metadata_path in sorted(metadata_dir.glob("*.json")):
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            continue
        if migrate_prompt_payload(payload):
            metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
            changes += 1
    return changes


def main() -> None:
    output_dir = DEFAULT_OUTPUT_DIR.resolve()
    state_changes = migrate_generated_output_state(output_dir)
    metadata_changes = migrate_metadata_files(output_dir)
    print(
        f"Migrated {state_changes} generated-output state entr"
        f"{'y' if state_changes == 1 else 'ies'} and "
        f"{metadata_changes} metadata file{'s' if metadata_changes != 1 else ''}."
    )


if __name__ == "__main__":
    main()
