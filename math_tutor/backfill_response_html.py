from __future__ import annotations

import json
import os
from pathlib import Path
from math_tutor.atomic_io import atomic_write_json
from math_tutor.generated_metadata import normalize_metadata_payload
from math_tutor.prompt_catalog import PROMPTS_BY_SLUG, STUDY_GUIDE_PROMPT
from math_tutor.response_artifacts import build_response_html, build_response_pdf
from math_tutor.state_store import (
    canonical_generated_output_state_path,
    load_generated_output_state,
    save_generated_output_state,
)


DEFAULT_OUTPUT_DIR = Path("math_tutor/output")


def main() -> None:
    output_dir = DEFAULT_OUTPUT_DIR.resolve()
    responses_dir = output_dir / "responses"
    metadata_dir = output_dir / "metadata"
    generated_output_state_path = canonical_generated_output_state_path(output_dir)
    generated_output_state = load_generated_output_state(generated_output_state_path)

    generated = 0
    for response_path in sorted(responses_dir.glob("*.md")):
        metadata_path = metadata_dir / f"{response_path.stem}.json"
        if not metadata_path.exists():
            continue

        metadata = normalize_metadata_payload(json.loads(metadata_path.read_text(encoding="utf-8")))
        prompt_slug = metadata.get("prompt_slug") or STUDY_GUIDE_PROMPT.slug
        prompt_spec = PROMPTS_BY_SLUG.get(prompt_slug)
        if prompt_spec is None:
            continue

        html_path = response_path.with_suffix(".html")
        pdf_response_path = response_path.with_suffix(".pdf")

        pdf_path = Path(metadata["pdf_path"])
        display_name = metadata["display_name"]
        markdown_text = response_path.read_text(encoding="utf-8")
        html_path.write_text(
            build_response_html(
                title=display_name,
                prompt_title=metadata.get("prompt_title") or prompt_spec.title,
                markdown_text=markdown_text,
                pdf_label=pdf_path.name if prompt_spec.include_source_pdf_link else None,
                pdf_href=(
                    Path(os.path.relpath(pdf_path, start=html_path.parent)).as_posix()
                    if prompt_spec.include_source_pdf_link
                    else None
                ),
                prompt_slug=prompt_spec.slug,
            ),
            encoding="utf-8",
        )
        if prompt_spec.generate_response_pdf:
            build_response_pdf(response_html_path=html_path, response_pdf_path=pdf_response_path)

        metadata["prompt_slug"] = prompt_spec.slug
        metadata["prompt_title"] = metadata.get("prompt_title") or prompt_spec.title
        metadata["response_html_path"] = str(html_path)
        metadata["response_pdf_path"] = str(pdf_response_path) if prompt_spec.generate_response_pdf else ""
        atomic_write_json(metadata_path, metadata, indent=2)

        file_id = str(metadata["canvas_file_id"])
        file_state = generated_output_state.processed.setdefault(file_id, {})
        prompt_state = file_state.setdefault(prompt_spec.slug, {})
        prompt_state["display_name"] = display_name
        prompt_state["prompt_slug"] = prompt_spec.slug
        prompt_state["prompt_title"] = metadata["prompt_title"]
        prompt_state["response_path"] = str(response_path)
        prompt_state["response_html_path"] = str(html_path)
        prompt_state["response_pdf_path"] = (
            str(pdf_response_path) if prompt_spec.generate_response_pdf else ""
        )
        prompt_state["metadata_path"] = str(metadata_path)
        if isinstance(metadata.get("provider"), str):
            prompt_state["provider"] = metadata["provider"]
        response_id = metadata.get("response_id")
        if isinstance(response_id, str):
            prompt_state["response_id"] = response_id
        model_name = metadata.get("model")
        if isinstance(model_name, str):
            prompt_state["model"] = model_name

        generated += 1

    save_generated_output_state(generated_output_state)
    print(f"Generated {generated} HTML/PDF response file set(s).")


if __name__ == "__main__":
    main()
