"""Authentication input helpers for the operator CLI."""

from __future__ import annotations

import os
from collections.abc import Mapping


def resolve_canvas_credentials(
    *,
    username: str | None,
    password: str | None,
    skip_fetch: bool,
    env: Mapping[str, str] | None = None,
) -> tuple[str, str] | None:
    if skip_fetch:
        return None

    environment = os.environ if env is None else env
    resolved_username = (
        username
        or environment.get("MATH_TUTOR_USERNAME")
        or environment.get("CANVAS_USERNAME")
    )
    resolved_password = (
        password
        or environment.get("MATH_TUTOR_PASSWORD")
        or environment.get("CANVAS_PASSWORD")
    )
    if not resolved_username or not resolved_password:
        raise SystemExit(
            "MATH_TUTOR_USERNAME and MATH_TUTOR_PASSWORD are required in .env "
            "unless --username and --password are supplied explicitly."
        )
    return resolved_username, resolved_password
