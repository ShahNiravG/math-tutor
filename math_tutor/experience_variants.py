from __future__ import annotations


PRIMARY_EXPERIENCE_VARIANT = "staging"
ARCHIVED_EXPERIENCE_VARIANT = "archived"
CLI_EXPERIENCE_CHOICES = (
    PRIMARY_EXPERIENCE_VARIANT,
    ARCHIVED_EXPERIENCE_VARIANT,
)


def normalize_experience_variant(raw_value: str | None) -> str:
    return raw_value or PRIMARY_EXPERIENCE_VARIANT
