"""Generation bootstrap helpers for the operator CLI."""

from __future__ import annotations

import os
from collections.abc import Callable, Mapping
from typing import Any

from openai import OpenAI

from math_tutor.cli_runtime import needs_openai_generation_client


def resolve_openai_api_key(
    *,
    prompts: tuple[Any, ...],
    fetch_only: bool,
    fetch_assignments: bool,
    env: Mapping[str, str] | None = None,
) -> str | None:
    environment = os.environ if env is None else env
    if fetch_only or fetch_assignments:
        return None
    if not needs_openai_generation_client(prompts):
        return None

    openai_api_key = environment.get("OPENAI_API_KEY")
    if not openai_api_key:
        raise SystemExit("OPENAI_API_KEY must be set in the environment unless --fetch-only is used.")
    return openai_api_key


def initialize_gemini_client(
    *,
    env: Mapping[str, str] | None = None,
    client_factory: Callable[[str], Any] | None = None,
    log: Callable[[str], None] | None = None,
) -> Any:
    environment = os.environ if env is None else env
    gemini_api_key = environment.get("GEMINI_API_KEY")
    if not gemini_api_key:
        return None

    logger = log or print
    if client_factory is None:
        try:
            from google import genai as google_genai
        except ImportError:
            logger(
                "Warning: GEMINI_API_KEY is set but google-genai is not installed. Gemini prompts will be skipped."
            )
            return None

        client_factory = lambda api_key: google_genai.Client(api_key=api_key)

    client = client_factory(gemini_api_key)
    logger("Gemini client initialized.")
    return client


def build_openai_generation_client(openai_api_key: str | None) -> OpenAI | None:
    if not openai_api_key:
        return None
    return OpenAI(api_key=openai_api_key)
