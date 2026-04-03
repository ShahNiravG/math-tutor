"""Provider client bootstrap and dispatch for MCQ generation."""

from __future__ import annotations

from typing import Any

from math_tutor.mcq_prompts import GEMINI_MODEL, GPT_MODEL


def build_mcq_clients(*, openai_api_key: str | None, gemini_api_key: str | None) -> tuple[Any, Any]:
    openai_client = None
    gemini_client = None

    if openai_api_key:
        from openai import OpenAI

        openai_client = OpenAI(api_key=openai_api_key)

    if gemini_api_key:
        try:
            from google import genai as google_genai

            gemini_client = google_genai.Client(api_key=gemini_api_key)
        except ImportError:
            print("Warning: GEMINI_API_KEY set but google-genai not installed. Gemini skipped.")

    return openai_client, gemini_client


def generate_mcq_text(
    *,
    provider: str,
    prompt: str,
    openai_client: Any,
    gemini_client: Any,
) -> str | None:
    if provider == "gpt":
        if openai_client is None:
            print("  Skipping — OPENAI_API_KEY not set")
            return None
        return _call_gpt(openai_client, prompt)

    if gemini_client is None:
        print("  Skipping — GEMINI_API_KEY not set")
        return None
    return _call_gemini(gemini_client, prompt)


def _call_gpt(client: Any, prompt: str) -> str:
    print(f"  -> Waiting for OpenAI ({GPT_MODEL}) response...", flush=True)
    response = client.responses.create(
        model=GPT_MODEL,
        input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
    )
    return response.output_text


def _call_gemini(gemini_client: Any, prompt: str) -> str:
    from google.genai import types as genai_types

    print(f"  -> Waiting for Gemini ({GEMINI_MODEL}) response...", flush=True)
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            genai_types.Content(
                role="user",
                parts=[genai_types.Part(text=prompt)],
            )
        ],
    )
    return response.text
