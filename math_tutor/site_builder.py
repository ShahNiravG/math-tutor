from __future__ import annotations

import argparse
import html
import json
import os
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from math_tutor.cli import (
    INSPIRING_VIDEOS_PROMPT,
    MENTAL_MATH_PROMPT,
    OLYMPIAD_PROBLEMS_PROMPT,
    OLYMPIAD_SOLUTIONS_PROMPT,
    PROMPTS_BY_SLUG,
    STUDY_GUIDE_PROMPT,
    PromptSpec,
    load_openai_state,
    pretty_title,
)


DEFAULT_OUTPUT_DIR = "math_tutor/output"
DEFAULT_SITE_DIRNAME = "site"
PROMPT_ORDER: tuple[PromptSpec, ...] = (
    STUDY_GUIDE_PROMPT,
    INSPIRING_VIDEOS_PROMPT,
    MENTAL_MATH_PROMPT,
    OLYMPIAD_PROBLEMS_PROMPT,
    OLYMPIAD_SOLUTIONS_PROMPT,
)


@dataclass
class PromptOutputRecord:
    slug: str
    title: str
    response_path: Path | None
    response_html_path: Path | None
    response_pdf_path: Path | None
    metadata_path: Path | None
    processed_at: str | None
    response_markdown: str | None


@dataclass
class DocumentRecord:
    file_id: str
    display_name: str
    pdf_path: Path | None
    download_url: str | None
    fetched_at: str | None
    prompt_outputs: list[PromptOutputRecord]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a readable HTML tutoring page from saved math_tutor outputs."
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory containing downloads, responses, metadata, and state files. Defaults to {DEFAULT_OUTPUT_DIR}.",
    )
    parser.add_argument(
        "--site-dir",
        default=None,
        help="Directory where the generated HTML site should be written. Defaults to <output-dir>/site.",
    )
    parser.add_argument(
        "--base-path",
        default="",
        help=(
            "Optional deployed site prefix such as /math_tutor/. "
            "When provided, generated links use that path instead of relative filesystem-style links."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    site_dir = Path(args.site_dir).resolve() if args.site_dir else output_dir / DEFAULT_SITE_DIRNAME
    site_dir.mkdir(parents=True, exist_ok=True)
    base_path = determine_base_path(raw_base_path=args.base_path, output_dir=output_dir, site_dir=site_dir)

    records = load_records(output_dir)
    html_text = build_html(records=records, output_dir=output_dir, site_dir=site_dir, base_path=base_path)
    index_path = site_dir / "index.html"
    index_path.write_text(html_text, encoding="utf-8")
    print(f"Built tutoring page at {index_path}")


def load_records(output_dir: Path) -> list[DocumentRecord]:
    fetch_state = load_state(output_dir / "fetch_state.json", "fetched")
    openai_state = load_openai_state(output_dir / "openai_state.json").processed

    file_ids = sorted(set(fetch_state) | set(openai_state), key=sort_key_from_id_and_name(fetch_state, openai_state))
    records: list[DocumentRecord] = []
    for file_id in file_ids:
        fetched = fetch_state.get(file_id, {})
        processed = openai_state.get(file_id, {})
        display_name = (
            first_prompt_value(processed, "display_name")
            or fetched.get("display_name")
            or f"File {file_id}"
        )
        prompt_outputs = load_prompt_outputs(processed)
        records.append(
            DocumentRecord(
                file_id=file_id,
                display_name=display_name,
                pdf_path=path_or_none(fetched.get("pdf_path")),
                download_url=fetched.get("download_url"),
                fetched_at=fetched.get("fetched_at"),
                prompt_outputs=prompt_outputs,
            )
        )
    return records


def load_prompt_outputs(processed: dict[str, Any]) -> list[PromptOutputRecord]:
    outputs_by_slug: dict[str, PromptOutputRecord] = {}
    for prompt_spec in PROMPT_ORDER:
        prompt_entry = processed.get(prompt_spec.slug, {})
        if not isinstance(prompt_entry, dict):
            prompt_entry = {}
        response_path = path_or_none(prompt_entry.get("response_path"))
        response_html_path = path_or_none(prompt_entry.get("response_html_path"))
        response_pdf_path = path_or_none(prompt_entry.get("response_pdf_path"))
        metadata_path = path_or_none(prompt_entry.get("metadata_path"))
        response_markdown = (
            response_path.read_text(encoding="utf-8")
            if response_path and response_path.exists()
            else None
        )
        outputs_by_slug[prompt_spec.slug] = PromptOutputRecord(
            slug=prompt_spec.slug,
            title=prompt_entry.get("prompt_title") or prompt_spec.title,
            response_path=response_path,
            response_html_path=response_html_path,
            response_pdf_path=response_pdf_path,
            metadata_path=metadata_path,
            processed_at=prompt_entry.get("processed_at"),
            response_markdown=response_markdown,
        )
    return [outputs_by_slug[prompt_spec.slug] for prompt_spec in PROMPT_ORDER]


def first_prompt_value(processed: dict[str, Any], key: str) -> str | None:
    for prompt_spec in PROMPT_ORDER:
        prompt_entry = processed.get(prompt_spec.slug, {})
        if isinstance(prompt_entry, dict):
            value = prompt_entry.get(key)
            if isinstance(value, str) and value:
                return value
    for prompt_entry in processed.values():
        if not isinstance(prompt_entry, dict):
            continue
        value = prompt_entry.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def load_state(path: Path, key: str) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8"))
    data = payload.get(key, {})
    return data if isinstance(data, dict) else {}


def path_or_none(value: Any) -> Path | None:
    if isinstance(value, str) and value:
        return Path(value)
    return None


def sort_key_from_id_and_name(
    fetch_state: dict[str, dict[str, Any]], openai_state: dict[str, dict[str, Any]]
):
    def key(file_id: str) -> tuple[float, str]:
        display_name = (
            first_prompt_value(openai_state.get(file_id, {}), "display_name")
            or fetch_state.get(file_id, {}).get("display_name")
            or ""
        )
        match = re.search(r"chp\s+(\d+(?:\.\d+)?)", display_name.lower())
        chapter = float(match.group(1)) if match else 10_000.0
        return (chapter, display_name.lower())

    return key


def build_html(*, records: list[DocumentRecord], output_dir: Path, site_dir: Path, base_path: str) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    toc_items = "\n".join(
        f'<li><a href="#doc-{record.file_id}">{html.escape(pretty_title(record.display_name))}</a></li>'
        for record in records
    )
    sections = "\n".join(render_record(record, output_dir, site_dir, base_path) for record in records)
    total_prompt_outputs = sum(
        1 for record in records for prompt_output in record.prompt_outputs if prompt_output.processed_at
    )
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Math Tutor Library</title>
  <style>
    :root {{
      --bg: #f5f1e8;
      --panel: #fffaf2;
      --ink: #1f2a33;
      --muted: #5b6a74;
      --accent: #a14d2e;
      --accent-soft: #ead2c5;
      --line: #d8cfc2;
      --line-strong: #cabaa4;
      --code: #f0e7db;
      --prompt-bg: #fffef9;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #f8dfc8 0, transparent 28%),
        linear-gradient(180deg, #f6efe3 0%, var(--bg) 100%);
    }}
    a {{ color: var(--accent); }}
    .page {{
      width: min(1240px, calc(100vw - 32px));
      margin: 24px auto 48px;
      display: grid;
      grid-template-columns: 280px 1fr;
      gap: 24px;
    }}
    .sidebar, .content-card {{
      background: color-mix(in srgb, var(--panel) 94%, white);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 12px 30px rgba(78, 55, 32, 0.08);
    }}
    .sidebar {{
      padding: 20px;
      position: sticky;
      top: 20px;
      align-self: start;
    }}
    .sidebar h1 {{
      margin: 0 0 8px;
      font-size: 1.8rem;
      line-height: 1.05;
    }}
    .sidebar p {{
      color: var(--muted);
      margin: 0 0 18px;
      line-height: 1.45;
    }}
    .toc {{
      margin: 0;
      padding-left: 18px;
      display: grid;
      gap: 8px;
    }}
    .meta {{
      margin-top: 18px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .main {{
      display: grid;
      gap: 18px;
    }}
    .content-card {{
      padding: 24px;
    }}
    .doc-header {{
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }}
    .doc-header h2 {{
      margin: 0;
      font-size: 1.7rem;
      line-height: 1.1;
    }}
    .chip-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 16px;
    }}
    .chip {{
      display: inline-block;
      padding: 6px 10px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: #6a2e16;
      font-size: 0.88rem;
    }}
    .link-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 18px;
    }}
    .link-row a {{
      text-decoration: none;
      font-weight: 600;
      border: 1px solid var(--line);
      background: #fff;
      padding: 9px 12px;
      border-radius: 999px;
    }}
    .prompt-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
    }}
    .prompt-card {{
      border: 1px solid var(--line-strong);
      background: var(--prompt-bg);
      border-radius: 16px;
      padding: 18px;
    }}
    .prompt-card h3 {{
      margin: 0 0 10px;
      font-size: 1.25rem;
      color: #243645;
    }}
    .prompt-card .link-row {{
      margin-bottom: 14px;
    }}
    @media (max-width: 960px) {{
      .page {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <aside class="sidebar">
      <h1>Math Tutor Library</h1>
      <p>Browse saved class note PDFs alongside the generated tutoring outputs. Each document can have separate Study Guide, Mental Math, Olympiad Problems, and Olympiad Solutions responses, and this page is built entirely from local saved state.</p>
      <ol class="toc">
        {toc_items}
      </ol>
      <div class="meta">
        <div><strong>Documents:</strong> {len(records)}</div>
        <div><strong>Saved prompt outputs:</strong> {total_prompt_outputs}</div>
        <div><strong>Built:</strong> {generated_at}</div>
      </div>
    </aside>
    <main class="main">
      {sections}
    </main>
  </div>
</body>
</html>
"""


def render_record(record: DocumentRecord, output_dir: Path, site_dir: Path, base_path: str) -> str:
    document_links: list[str] = []
    if record.pdf_path and record.pdf_path.exists():
        document_links.append(link_tag(record.pdf_path, output_dir, site_dir, "Open PDF", base_path))
    if record.download_url:
        document_links.append(
            f'<a href="{html.escape(record.download_url)}">Open Canvas File</a>'
        )

    document_chips: list[str] = []
    if record.fetched_at:
        document_chips.append(f'<span class="chip">Fetched {html.escape(record.fetched_at)}</span>')

    prompt_cards = "\n".join(
        render_prompt_output(prompt_output, output_dir, site_dir, base_path) for prompt_output in record.prompt_outputs
    )
    return f"""
    <section class="content-card" id="doc-{record.file_id}">
      <div class="doc-header">
        <h2>{html.escape(pretty_title(record.display_name))}</h2>
      </div>
      <div class="chip-row">
        {' '.join(document_chips)}
      </div>
      <div class="link-row">
        {' '.join(document_links)}
      </div>
      <div class="prompt-grid">
        {prompt_cards}
      </div>
    </section>
    """


def render_prompt_output(prompt_output: PromptOutputRecord, output_dir: Path, site_dir: Path, base_path: str) -> str:
    links: list[str] = []
    prompt_spec = PROMPTS_BY_SLUG.get(prompt_output.slug)
    if prompt_output.response_html_path and prompt_output.response_html_path.exists():
        links.append(link_tag(prompt_output.response_html_path, output_dir, site_dir, "Open HTML", base_path))
    if (
        prompt_spec is not None
        and prompt_spec.generate_response_pdf
        and prompt_output.response_pdf_path
        and prompt_output.response_pdf_path.exists()
    ):
        links.append(link_tag(prompt_output.response_pdf_path, output_dir, site_dir, "Open PDF", base_path))

    chips: list[str] = []
    if prompt_output.processed_at:
        chips.append(f'<span class="chip">OpenAI processed {html.escape(prompt_output.processed_at)}</span>')
    else:
        chips.append('<span class="chip">No OpenAI response yet</span>')

    summary_html = ""
    if prompt_output.slug == "study-guide" and prompt_output.response_markdown:
        summary_html = extract_study_guide_summary_html(prompt_output.response_markdown)

    return f"""
      <section class="prompt-card">
        <h3>{html.escape(prompt_output.title)}</h3>
        <div class="chip-row">
          {' '.join(chips)}
        </div>
        <div class="link-row">
          {' '.join(links)}
        </div>
        {summary_html}
      </section>
    """


def link_tag(path: Path, output_dir: Path, site_dir: Path, label: str, base_path: str) -> str:
    href = build_site_href(path=path, output_dir=output_dir, site_dir=site_dir, base_path=base_path)
    return f'<a href="{html.escape(href)}">{html.escape(label)}</a>'


def resolve_site_asset_path(*, path: Path, output_dir: Path, site_dir: Path, deploy_assets: bool) -> Path:
    try:
        relative_to_output = path.relative_to(output_dir)
    except ValueError:
        return path

    deployed_copy = site_dir / relative_to_output
    if not deploy_assets:
        if deployed_copy.exists():
            return deployed_copy
        return path

    deployed_copy.parent.mkdir(parents=True, exist_ok=True)
    if not deployed_copy.exists() or path.stat().st_mtime_ns != deployed_copy.stat().st_mtime_ns:
        shutil.copy2(path, deployed_copy)
    return deployed_copy


def build_site_href(*, path: Path, output_dir: Path, site_dir: Path, base_path: str) -> str:
    deploy_assets = should_copy_site_assets(output_dir=output_dir, site_dir=site_dir, base_path=base_path)
    resolved_path = resolve_site_asset_path(
        path=path,
        output_dir=output_dir,
        site_dir=site_dir,
        deploy_assets=deploy_assets,
    )

    if base_path:
        try:
            relative_to_site = resolved_path.relative_to(site_dir).as_posix()
            return f"{base_path}{relative_to_site}"
        except ValueError:
            pass

    rel = Path(os.path.relpath(resolved_path, start=site_dir)).as_posix()
    return rel


def determine_base_path(*, raw_base_path: str, output_dir: Path, site_dir: Path) -> str:
    normalized = normalize_base_path(raw_base_path)
    if normalized:
        return normalized
    if should_use_math_tutor_base_path(output_dir=output_dir, site_dir=site_dir):
        return "/math_tutor/"
    return ""


def normalize_base_path(value: str) -> str:
    if not value:
        return ""
    stripped = value.strip().strip("/")
    if not stripped:
        return ""
    return f"/{stripped}/"


def should_use_math_tutor_base_path(*, output_dir: Path, site_dir: Path) -> bool:
    return site_dir.name == "math_tutor" and not site_dir.is_relative_to(output_dir)


def should_copy_site_assets(*, output_dir: Path, site_dir: Path, base_path: str) -> bool:
    return bool(base_path) or not site_dir.is_relative_to(output_dir)


def extract_study_guide_summary_html(markdown_text: str) -> str:
    summary_lines = extract_study_guide_summary_lines(markdown_text)
    if not summary_lines:
        return ""

    paragraphs = "\n".join(f"<p>{render_inline(line)}</p>" for line in summary_lines if line)
    return f"""
        <div class="response">
          <h4>Short Summary</h4>
          {paragraphs}
        </div>
    """


def extract_study_guide_summary_lines(markdown_text: str) -> list[str]:
    lines = markdown_text.splitlines()
    in_summary = False
    collected: list[str] = []

    for raw_line in lines:
        stripped = raw_line.strip()
        lowered = stripped.lower()
        normalized = re.sub(r"[*_`]", "", lowered)

        if not in_summary:
            if (
                "short summary" in normalized
                and re.match(r"^#{1,6}\s*", stripped)
            ):
                in_summary = True
            continue

        if not stripped:
            if collected and collected[-1] != "":
                collected.append("")
            continue
        if re.fullmatch(r"-{3,}", stripped):
            break
        next_normalized = re.sub(r"[*_`]", "", stripped.lower())
        if re.match(r"^#{1,6}\s+", stripped) and "short summary" not in next_normalized:
            break
        if re.match(r"^\d+\.\s+", stripped) and "short summary" not in next_normalized:
            break

        collected.append(stripped)

    while collected and collected[-1] == "":
        collected.pop()
    return collected


def markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    parts: list[str] = []
    paragraph: list[str] = []
    in_list = False

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            parts.append(f"<p>{render_inline(' '.join(paragraph).strip())}</p>")
            paragraph = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            parts.append("</ul>")
            in_list = False

    for raw_line in lines:
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            close_list()
            continue
        if re.fullmatch(r"-{3,}", stripped):
            flush_paragraph()
            close_list()
            parts.append("<hr>")
            continue
        heading_match = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if heading_match:
            flush_paragraph()
            close_list()
            level = min(len(heading_match.group(1)) + 1, 5)
            parts.append(f"<h{level}>{render_inline(heading_match.group(2))}</h{level}>")
            continue
        if stripped.startswith(("- ", "* ")):
            flush_paragraph()
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{render_inline(stripped[2:].strip())}</li>")
            continue
        close_list()
        paragraph.append(stripped)

    flush_paragraph()
    close_list()
    return "\n".join(parts)


def render_inline(text: str) -> str:
    escaped = html.escape(text)
    escaped = re.sub(
        r"\[([^\]]+)\]\((https?://[^\s)]+)\)",
        r'<a href="\2">\1</a>',
        escaped,
    )
    escaped = re.sub(
        r"(?<![\"'=>])(https?://[^\s<]+)",
        r'<a href="\1">\1</a>',
        escaped,
    )
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
    return escaped


if __name__ == "__main__":
    main()
