"""Low-level provider request helpers for prompt generation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI

from math_tutor.prompt_catalog import PromptSpec
from math_tutor.video_recommendations import (
    parse_gemini_video_recommendations,
    render_inspiring_videos_markdown,
)


@dataclass(frozen=True)
class PromptResponseResult:
    output_text: str
    response_id: str | None


def generate_tutor_response(
    client: OpenAI,
    pdf_path: Path,
    model: str,
    prompt_text: str,
    reasoning_effort: str | None = None,
) -> Any:
    print(f"  -> Uploading {pdf_path.name} to OpenAI...", flush=True)
    with pdf_path.open("rb") as handle:
        uploaded_file = client.files.create(file=handle, purpose="user_data")
    print(f"  -> Waiting for OpenAI ({model}) response...", flush=True)
    kwargs: dict[str, Any] = {
        "model": model,
        "input": [
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt_text},
                    {"type": "input_file", "file_id": uploaded_file.id},
                ],
            }
        ],
    }
    if reasoning_effort:
        kwargs["reasoning"] = {"effort": reasoning_effort}
    return client.responses.create(**kwargs)


def generate_text_only_response(
    client: OpenAI,
    model: str,
    prompt_text: str,
    reasoning_effort: str | None = None,
) -> Any:
    print(f"  -> Waiting for OpenAI ({model}) response (text-only)...", flush=True)
    kwargs: dict[str, Any] = {
        "model": model,
        "input": [{"role": "user", "content": [{"type": "input_text", "text": prompt_text}]}],
    }
    if reasoning_effort:
        kwargs["reasoning"] = {"effort": reasoning_effort}
    return client.responses.create(**kwargs)


def generate_gemini_tutor_response(
    client: Any,
    pdf_path: Path,
    model: str,
    prompt_spec: PromptSpec,
) -> PromptResponseResult:
    from google.genai import types as genai_types

    print(f"  -> Uploading {pdf_path.name} to Gemini...", flush=True)
    with pdf_path.open("rb") as handle:
        uploaded_file = client.files.upload(
            file=handle,
            config=genai_types.UploadFileConfig(
                mime_type="application/pdf",
                display_name=pdf_path.name,
            ),
        )
    print(f"  -> Waiting for Gemini ({model}) response...", flush=True)
    config = None
    if prompt_spec.use_google_search:
        config = genai_types.GenerateContentConfig(
            tools=[genai_types.Tool(google_search=genai_types.GoogleSearch())],
        )
    response = client.models.generate_content(
        model=model,
        contents=[
            genai_types.Content(
                role="user",
                parts=[
                    genai_types.Part(text=prompt_spec.text),
                    genai_types.Part(
                        file_data=genai_types.FileData(
                            mime_type="application/pdf",
                            file_uri=uploaded_file.uri,
                        )
                    ),
                ],
            )
        ],
        config=config,
    )
    output_text = response.text or ""
    if not prompt_spec.use_google_search:
        return PromptResponseResult(output_text=output_text, response_id=None)

    recommendations = parse_gemini_video_recommendations(
        output_text=output_text,
        prompt_slug=prompt_spec.slug,
    )
    return PromptResponseResult(
        output_text=render_inspiring_videos_markdown(recommendations),
        response_id=None,
    )


def generate_gemini_text_only_response(
    client: Any,
    model: str,
    prompt_text: str,
) -> PromptResponseResult:
    from google.genai import types as genai_types

    print(f"  -> Waiting for Gemini ({model}) response (text-only)...", flush=True)
    response = client.models.generate_content(
        model=model,
        contents=[genai_types.Content(role="user", parts=[genai_types.Part(text=prompt_text)])],
    )
    return PromptResponseResult(output_text=response.text, response_id=None)


def generate_prompt_response(
    *,
    client: OpenAI,
    gemini_client: Any,
    pdf_path: Path,
    default_model: str,
    prompt_spec: PromptSpec,
    source_output: str | None,
) -> PromptResponseResult:
    effective_model = prompt_spec.model or default_model
    if effective_model.startswith("gemini"):
        if gemini_client is None:
            raise RuntimeError("GEMINI_API_KEY must be set to run Gemini prompts.")
        if prompt_spec.source_prompt_slug is None:
            return generate_gemini_tutor_response(gemini_client, pdf_path, effective_model, prompt_spec)
        if source_output is None:
            raise RuntimeError(f"{prompt_spec.title} requires a source prompt output.")
        prompt_text = prompt_spec.text.replace(prompt_spec.source_placeholder, source_output)
        return generate_gemini_text_only_response(gemini_client, effective_model, prompt_text)

    reasoning_effort = prompt_spec.reasoning_effort
    if prompt_spec.source_prompt_slug is None:
        response = generate_tutor_response(client, pdf_path, effective_model, prompt_spec.text, reasoning_effort)
    else:
        if source_output is None:
            raise RuntimeError(f"{prompt_spec.title} requires a source prompt output.")
        prompt_text = prompt_spec.text.replace(prompt_spec.source_placeholder, source_output)
        response = generate_text_only_response(client, effective_model, prompt_text, reasoning_effort)
    return PromptResponseResult(output_text=response.output_text, response_id=response.id)
