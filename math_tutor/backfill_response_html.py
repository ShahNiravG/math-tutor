from __future__ import annotations

import json
import os
from pathlib import Path

from math_tutor.cli import (
    PROMPTS_BY_SLUG,
    STUDY_GUIDE_PROMPT,
    build_prompt_paths,
    build_response_html,
    build_response_pdf,
    load_openai_state,
    save_openai_state,
)


DEFAULT_OUTPUT_DIR = Path("math_tutor/output")


def main() -> None:
    output_dir = DEFAULT_OUTPUT_DIR.resolve()
    responses_dir = output_dir / "responses"
    metadata_dir = output_dir / "metadata"
    openai_state_path = output_dir / "openai_state.json"
    openai_state = load_openai_state(openai_state_path)

    generated = 0
    for response_path in sorted(responses_dir.glob("*.md")):
        metadata_path = metadata_dir / f"{response_path.stem}.json"
        if not metadata_path.exists():
            continue

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        prompt_slug = metadata.get("prompt_slug") or STUDY_GUIDE_PROMPT.slug
        prompt_spec = PROMPTS_BY_SLUG.get(prompt_slug)
        if prompt_spec is None:
            continue

        if prompt_slug == STUDY_GUIDE_PROMPT.slug and "__" not in response_path.stem:
            expected_md_path, html_path, pdf_response_path, expected_metadata_path = build_prompt_paths(
                responses_dir=responses_dir,
                metadata_dir=metadata_dir,
                stem=response_path.stem,
                prompt_spec=STUDY_GUIDE_PROMPT,
            )
            if expected_md_path != response_path or expected_metadata_path != metadata_path:
                continue
        else:
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
            ),
            encoding="utf-8",
        )
        if prompt_spec.generate_response_pdf:
            build_response_pdf(response_html_path=html_path, response_pdf_path=pdf_response_path)

        metadata["prompt_slug"] = prompt_spec.slug
        metadata["prompt_title"] = metadata.get("prompt_title") or prompt_spec.title
        metadata["response_html_path"] = str(html_path)
        metadata["response_pdf_path"] = str(pdf_response_path) if prompt_spec.generate_response_pdf else ""
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

        file_id = str(metadata["canvas_file_id"])
        file_state = openai_state.processed.setdefault(file_id, {})
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
        if isinstance(metadata.get("openai_response_id"), str):
            prompt_state["openai_response_id"] = metadata["openai_response_id"]
        if isinstance(metadata.get("openai_model"), str):
            prompt_state["model"] = metadata["openai_model"]

        generated += 1

    save_openai_state(openai_state)
    print(f"Generated {generated} HTML/PDF response file set(s).")


if __name__ == "__main__":
    main()
