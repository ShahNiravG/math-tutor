"""Rename generated artifacts to model-explicit filenames and update saved references."""

from __future__ import annotations

import json
from pathlib import Path

from math_tutor.atomic_io import atomic_write_json
from math_tutor.artifact_paths import build_prompt_paths
from math_tutor.generated_metadata import normalize_metadata_payload, provider_name_for_model
from math_tutor.prompt_catalog import PROMPTS_BY_SLUG
from math_tutor.response_artifacts import slugify
from math_tutor.state_store import (
    canonical_generated_output_state_path,
    load_generated_output_state,
    save_generated_output_state,
)


LEGACY_MODEL_FALLBACKS = {
    "study-guide": "gpt-4.1",
    "inspiring-videos": "gpt-4.1",
}


def infer_model_name(*, prompt_slug: str, prompt_entry: dict[str, str], metadata: dict[str, object] | None) -> str | None:
    entry_model = prompt_entry.get("model")
    if isinstance(entry_model, str) and entry_model:
        return entry_model
    if metadata is not None:
        metadata_model = metadata.get("model")
        if isinstance(metadata_model, str) and metadata_model:
            return metadata_model
    return LEGACY_MODEL_FALLBACKS.get(prompt_slug)


def rename_if_present(source: Path, destination: Path) -> bool:
    if source == destination or not source.exists():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        return False
    source.rename(destination)
    return True


def path_or_none(value: str) -> Path | None:
    if not value:
        return None
    return Path(value)


def derive_source_stem(*, file_id: str, prompt_entry: dict[str, str]) -> str:
    display_name = prompt_entry.get("display_name", "")
    if display_name:
        return f"{file_id}_{slugify(Path(display_name).stem)}"
    response_path = Path(prompt_entry.get("response_path", ""))
    if response_path.stem:
        return response_path.stem.split("__", 1)[0]
    raise RuntimeError(f"Unable to derive artifact stem for file {file_id}.")


def migrate_output_dir(output_dir: Path) -> int:
    responses_dir = output_dir / "responses"
    metadata_dir = output_dir / "metadata"
    state_path = canonical_generated_output_state_path(output_dir)
    generated_output_state = load_generated_output_state(state_path)

    migrated = 0
    for file_id, prompt_map in generated_output_state.processed.items():
        for prompt_slug, prompt_entry in prompt_map.items():
            prompt_spec = PROMPTS_BY_SLUG.get(prompt_slug)
            if prompt_spec is None:
                continue

            old_response_path = path_or_none(prompt_entry.get("response_path", ""))
            old_response_html_path = path_or_none(prompt_entry.get("response_html_path", ""))
            old_response_pdf_path = path_or_none(prompt_entry.get("response_pdf_path", ""))
            old_metadata_path = path_or_none(prompt_entry.get("metadata_path", ""))
            if old_response_path is None or old_response_html_path is None:
                continue

            metadata_payload = None
            if old_metadata_path is not None and old_metadata_path.exists():
                metadata_payload = normalize_metadata_payload(json.loads(old_metadata_path.read_text(encoding="utf-8")))

            model_name = infer_model_name(
                prompt_slug=prompt_slug,
                prompt_entry=prompt_entry,
                metadata=metadata_payload,
            )
            if not model_name:
                continue

            stem = derive_source_stem(file_id=file_id, prompt_entry=prompt_entry)
            new_response_path, new_response_html_path, new_response_pdf_path, new_metadata_path = build_prompt_paths(
                responses_dir=responses_dir,
                metadata_dir=metadata_dir,
                stem=stem,
                prompt_spec=prompt_spec,
                model_name=model_name,
            )

            changed = False
            changed = rename_if_present(old_response_path, new_response_path) or changed
            changed = rename_if_present(old_response_html_path, new_response_html_path) or changed
            if old_response_pdf_path is not None:
                changed = rename_if_present(old_response_pdf_path, new_response_pdf_path) or changed
            if old_metadata_path is not None:
                changed = rename_if_present(old_metadata_path, new_metadata_path) or changed

            if (
                str(old_response_path) != str(new_response_path)
                or str(old_response_html_path) != str(new_response_html_path)
                or str(old_response_pdf_path) != str(new_response_pdf_path)
                or str(old_metadata_path) != str(new_metadata_path)
            ):
                changed = True

            prompt_entry["response_path"] = str(new_response_path)
            prompt_entry["response_html_path"] = str(new_response_html_path)
            prompt_entry["response_pdf_path"] = str(new_response_pdf_path) if old_response_pdf_path is not None else ""
            prompt_entry["metadata_path"] = str(new_metadata_path) if (old_metadata_path is not None or new_metadata_path.exists()) else ""
            prompt_entry["model"] = model_name
            prompt_entry.setdefault("provider", provider_name_for_model(model_name))

            if new_metadata_path.exists():
                payload = normalize_metadata_payload(json.loads(new_metadata_path.read_text(encoding="utf-8")))
                payload["prompt_slug"] = prompt_slug
                payload["prompt_title"] = prompt_entry.get("prompt_title", payload.get("prompt_title", prompt_slug))
                payload["model"] = model_name
                payload["provider"] = provider_name_for_model(model_name)
                payload["response_path"] = str(new_response_path)
                payload["response_html_path"] = str(new_response_html_path)
                payload["response_pdf_path"] = str(new_response_pdf_path) if payload.get("response_pdf_path") else ""
                atomic_write_json(new_metadata_path, payload, indent=2)

            if changed:
                migrated += 1

    save_generated_output_state(generated_output_state)
    return migrated


def main() -> None:
    output_dir = (Path(__file__).resolve().parent / "output").resolve()
    migrated = migrate_output_dir(output_dir)
    print(f"Migrated {migrated} generated artifact mapping(s).")


if __name__ == "__main__":
    main()
