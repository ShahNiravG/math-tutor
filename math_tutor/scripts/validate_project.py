"""Run local validation checks that avoid network calls and preserve saved outputs.

This script is meant to be the first command run before refactoring or merging
changes. It intentionally validates only local, reproducible behaviors:

- unit tests for pure logic and rendering contracts
- Python compilation for the core entry-point modules

It does not fetch from Canvas, regenerate model outputs, or rewrite the current
deploy tree.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = REPO_ROOT / "math_tutor"
CORE_MODULES = [
    "math_tutor/artifact_paths.py",
    "math_tutor/canvas_files.py",
    "math_tutor/canvas_login.py",
    "math_tutor/canvas_course.py",
    "math_tutor/chaptering.py",
    "math_tutor/challenge_builder.py",
    "math_tutor/cli_auth.py",
    "math_tutor/cli.py",
    "math_tutor/cli_commands.py",
    "math_tutor/cli_context.py",
    "math_tutor/cli_generation.py",
    "math_tutor/cli_runtime.py",
    "math_tutor/cli_workflows.py",
    "math_tutor/env_config.py",
    "math_tutor/generated_metadata.py",
    "math_tutor/mcq_generator.py",
    "math_tutor/print_targets.py",
    "math_tutor/prompt_generation.py",
    "math_tutor/prompt_pipeline.py",
    "math_tutor/prompt_catalog.py",
    "math_tutor/prompt_output_store.py",
    "math_tutor/prompt_saved_outputs.py",
    "math_tutor/response_artifacts.py",
    "math_tutor/site_data.py",
    "math_tutor/site_assets.py",
    "math_tutor/site_cards.py",
    "math_tutor/site_challenges.py",
    "math_tutor/site_content.py",
    "math_tutor/site_models.py",
    "math_tutor/site_navigation.py",
    "math_tutor/site_pages.py",
    "math_tutor/site_prompt_cards.py",
    "math_tutor/site_records.py",
    "math_tutor/site_sections.py",
    "math_tutor/site_shell.py",
    "math_tutor/site_theme.py",
    "math_tutor/site_builder.py",
    "math_tutor/state_store.py",
    "math_tutor/video_recommendations.py",
    "math_tutor/backfill_response_html.py",
]


def run(command: list[str]) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=REPO_ROOT, check=True)


def main() -> None:
    run([sys.executable, "-m", "unittest", "discover", "-s", "math_tutor/tests", "-t", "."])
    run([sys.executable, "-m", "py_compile", *CORE_MODULES])
    print("\nValidation completed successfully.", flush=True)


if __name__ == "__main__":
    main()
