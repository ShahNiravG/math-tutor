"""Generate multiple-choice options for existing mental-math and olympiad question files."""
from __future__ import annotations

import argparse
import os
import re
from pathlib import Path
from typing import Any

from math_tutor.cli import (
    build_response_html,
    build_response_pdf,
    load_dotenv_if_present,
    markdown_to_html,
)

PACKAGE_DIR = Path(__file__).resolve().parent
RESPONSES_DIR = PACKAGE_DIR / "output" / "responses"

# Maps source prompt suffix → (mcq suffix, model, prompt template key)
SOURCE_CONFIGS = [
    ("__mental-math-gpt5.md",        "__mental-math-gpt5-mcq",        "gpt",    "mental_math"),
    ("__mental-math-gemini.md",      "__mental-math-gemini-mcq",      "gemini", "mental_math"),
    ("__olympiad-problems-gpt5.md",  "__olympiad-problems-gpt5-mcq",  "gpt",    "olympiad"),
    ("__olympiad-problems-gemini.md","__olympiad-problems-gemini-mcq","gemini", "olympiad"),
]

GPT_MODEL    = "gpt-5.4"
GEMINI_MODEL = "gemini-3.1-pro-preview"

MENTAL_MATH_PROMPT = """\
Below are mental math questions on a math topic. For each question, provide exactly 4 \
multiple-choice options (A, B, C, D). One must be the mathematically correct answer; \
the other three must be plausible but incorrect — use common errors such as sign mistakes, \
degree/radian confusion, off-by-one errors, or arithmetic slips.

Rules:
- Options must be concise: a single number, fraction, expression, or short phrase.
- The correct answer must be verified.
- Distractors must reflect realistic student mistakes, not random values.
- Randomly vary which letter (A/B/C/D) holds the correct answer across questions.
- Number the blocks to match the question numbers in the input.
- Output ONLY the answer blocks below — no explanations, no restating questions, no extra text.

Format (one block per question):

1.
(A) ...
(B) ...
(C) ...
(D) ...
Answer: [letter]

2.
...

Here are the questions:

{questions}
"""

OLYMPIAD_PROMPT = """\
Below are Olympiad-style math problems. For each problem, provide exactly 4 multiple-choice \
options (A, B, C, D). One must be the mathematically correct answer; the other three should \
be plausible — use values that arise from partial progress, sign errors, missing factors, \
or near-correct approaches.

Rules:
- Options must be concise: a single value, expression, angle measure, or short result. \
LaTeX is fine for mathematical expressions.
- The correct answer must be mathematically verified.
- Distractors should reflect genuine mathematical mistakes, not arbitrary values.
- Randomly vary which letter (A/B/C/D) holds the correct answer across problems.
- Number the blocks to match the problem numbers in the input.
- Output ONLY the answer blocks below — no explanations, no restating problems, no extra text.

Format (one block per problem):

1.
(A) ...
(B) ...
(C) ...
(D) ...
Answer: [letter]

2.
...

Here are the problems:

{questions}
"""


def _call_gpt(client: Any, prompt: str) -> str:
    print(f"  -> Waiting for OpenAI ({GPT_MODEL}) response...", flush=True)
    response = client.responses.create(
        model=GPT_MODEL,
        input=[{"role": "user", "content": [{"type": "input_text", "text": prompt}]}],
        reasoning={"effort": "medium"},
    )
    return response.output_text


def _call_gemini(gemini_client: Any, prompt: str) -> str:
    from google.genai import types as genai_types
    print(f"  -> Waiting for Gemini ({GEMINI_MODEL}) response...", flush=True)
    response = gemini_client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=prompt)],
        )],
    )
    return response.text


def _build_mcq_html(stem: str, mcq_md: str) -> str:
    """Render MCQ answer blocks as a clean HTML page."""
    # Build a title from the stem (e.g. "chp-5-1 Mental Math GPT-5 MCQ")
    title = re.sub(r"^\d+_", "", stem)   # strip file_id prefix
    rendered = markdown_to_html(mcq_md)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title} — MCQ Options</title>
  <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
      }}
    }};
  </script>
  <script defer src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
  <style>
    :root {{
      --bg: #f6f1e8; --paper: #fffdf8; --ink: #1d2833;
      --muted: #667784; --line: #dfd5c8; --accent: #0f6a73;
    }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; font-family: Georgia, "Times New Roman", serif;
            color: var(--ink);
            background: radial-gradient(circle at top left, #f4d7c4 0, transparent 24%),
                        linear-gradient(180deg, #f8f3eb 0%, var(--bg) 100%); }}
    .page {{ width: min(920px, calc(100vw - 32px)); margin: 24px auto 48px;
             background: var(--paper); border: 1px solid var(--line);
             border-radius: 20px; box-shadow: 0 16px 36px rgba(48,36,23,.08);
             overflow: hidden; }}
    header {{ padding: 24px 28px 18px; border-bottom: 1px solid var(--line);
              background: linear-gradient(180deg,#fffaf3 0%,#fbf6ee 100%); }}
    header h1 {{ margin: 0 0 8px; font-size: 1.6rem; line-height: 1.1; }}
    header p {{ margin: 0; color: var(--muted); }}
    main {{ padding: 24px 28px 32px; }}
    p, li {{ line-height: 1.7; }}
    hr {{ border: 0; border-top: 1px solid var(--line); margin: 22px 0; }}
  </style>
</head>
<body>
  <article class="page">
    <header>
      <h1>{title}</h1>
      <p>Multiple-choice options and correct answers</p>
    </header>
    <main>{rendered}</main>
  </article>
</body>
</html>
"""


def process_file(
    source_md: Path,
    mcq_slug: str,
    api_type: str,
    prompt_type: str,
    client: Any,
    gemini_client: Any,
    force: bool,
) -> None:
    stem = source_md.stem  # e.g. "4401267_alg-2trig-h-chp-5-1-note-docx__mental-math-gpt5"
    # Build output stem by replacing source suffix with mcq suffix
    # e.g. "__mental-math-gpt5" → "__mental-math-gpt5-mcq"
    base_stem = stem[: stem.rfind("__")]  # "4401267_alg-2trig-h-chp-5-1-note-docx"
    out_stem = base_stem + mcq_slug       # "...__mental-math-gpt5-mcq"

    out_md   = RESPONSES_DIR / f"{out_stem}.md"
    out_html = RESPONSES_DIR / f"{out_stem}.html"
    out_pdf  = RESPONSES_DIR / f"{out_stem}.pdf"

    if not force and out_md.exists():
        print(f"  Skipping {out_md.name} (already exists)")
        return

    questions_text = source_md.read_text(encoding="utf-8")
    template = MENTAL_MATH_PROMPT if prompt_type == "mental_math" else OLYMPIAD_PROMPT
    prompt = template.format(questions=questions_text)

    print(f"\nProcessing: {source_md.name}")

    if api_type == "gpt":
        if client is None:
            print(f"  Skipping — OPENAI_API_KEY not set")
            return
        mcq_text = _call_gpt(client, prompt)
    else:
        if gemini_client is None:
            print(f"  Skipping — GEMINI_API_KEY not set")
            return
        mcq_text = _call_gemini(gemini_client, prompt)

    out_md.write_text(mcq_text, encoding="utf-8")
    print(f"  Wrote {out_md.name}")

    html_content = _build_mcq_html(out_stem, mcq_text)
    out_html.write_text(html_content, encoding="utf-8")
    print(f"  Wrote {out_html.name}")

    build_response_pdf(response_html_path=out_html, response_pdf_path=out_pdf)
    print(f"  Wrote {out_pdf.name}")


def main() -> None:
    load_dotenv_if_present()

    parser = argparse.ArgumentParser(
        description="Generate MCQ options for existing mental-math and olympiad question files."
    )
    parser.add_argument("--responses-dir", default=str(RESPONSES_DIR),
                        help="Directory containing *__mental-math-*.md and *__olympiad-*.md files.")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate even if MCQ output already exists.")
    parser.add_argument("--dry-run", action="store_true",
                        help="Show what would be processed without making API calls.")
    args = parser.parse_args()

    responses_dir = Path(args.responses_dir).resolve()

    # Build clients
    client = None
    gemini_client = None

    openai_key = os.environ.get("OPENAI_API_KEY")
    if openai_key:
        from openai import OpenAI
        client = OpenAI(api_key=openai_key)

    gemini_key = os.environ.get("GEMINI_API_KEY")
    if gemini_key:
        try:
            from google import genai as google_genai
            gemini_client = google_genai.Client(api_key=gemini_key)
        except ImportError:
            print("Warning: GEMINI_API_KEY set but google-genai not installed. Gemini skipped.")

    total = 0
    skipped = 0
    processed = 0

    for source_suffix, mcq_slug, api_type, prompt_type in SOURCE_CONFIGS:
        source_files = sorted(responses_dir.glob(f"*{source_suffix}"))
        for source_md in source_files:
            total += 1
            base_stem = source_md.stem[: source_md.stem.rfind("__")]
            out_md = responses_dir / f"{base_stem}{mcq_slug}.md"

            if not args.force and out_md.exists():
                skipped += 1
                if args.dry_run:
                    print(f"  [skip] {out_md.name}")
                continue

            if args.dry_run:
                print(f"  [would process] {source_md.name} → {out_md.name}")
                processed += 1
                continue

            process_file(
                source_md=source_md,
                mcq_slug=mcq_slug,
                api_type=api_type,
                prompt_type=prompt_type,
                client=client,
                gemini_client=gemini_client,
                force=args.force,
            )
            processed += 1

    print(f"\nDone. {processed} processed, {skipped} skipped, {total} total.")
