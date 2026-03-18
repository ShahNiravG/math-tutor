from __future__ import annotations

import argparse
import html
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_OUTPUT_DIR = "math_tutor/output"
DEFAULT_SITE_DIRNAME = "site"


@dataclass
class DocumentRecord:
    file_id: str
    display_name: str
    pdf_path: Path | None
    response_path: Path | None
    metadata_path: Path | None
    download_url: str | None
    processed_at: str | None
    fetched_at: str | None
    response_markdown: str | None


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
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir).resolve()
    site_dir = Path(args.site_dir).resolve() if args.site_dir else output_dir / DEFAULT_SITE_DIRNAME
    site_dir.mkdir(parents=True, exist_ok=True)

    records = load_records(output_dir)
    html_text = build_html(records=records, output_dir=output_dir, site_dir=site_dir)
    index_path = site_dir / "index.html"
    index_path.write_text(html_text, encoding="utf-8")
    print(f"Built tutoring page at {index_path}")


def load_records(output_dir: Path) -> list[DocumentRecord]:
    fetch_state = load_state(output_dir / "fetch_state.json", "fetched")
    openai_state = load_state(output_dir / "openai_state.json", "processed")
    metadata_dir = output_dir / "metadata"

    file_ids = sorted(set(fetch_state) | set(openai_state), key=sort_key_from_id_and_name(fetch_state, openai_state))
    records: list[DocumentRecord] = []
    for file_id in file_ids:
        fetched = fetch_state.get(file_id, {})
        processed = openai_state.get(file_id, {})
        display_name = (
            processed.get("display_name")
            or fetched.get("display_name")
            or f"File {file_id}"
        )
        pdf_path = path_or_none(fetched.get("pdf_path"))
        response_path = path_or_none(processed.get("response_path"))
        metadata_path = path_or_none(processed.get("metadata_path"))
        if metadata_path is None:
            inferred = infer_metadata_path(metadata_dir, response_path)
            metadata_path = inferred
        download_url = fetched.get("download_url")
        response_markdown = response_path.read_text(encoding="utf-8") if response_path and response_path.exists() else None
        records.append(
            DocumentRecord(
                file_id=file_id,
                display_name=display_name,
                pdf_path=pdf_path,
                response_path=response_path,
                metadata_path=metadata_path,
                download_url=download_url,
                processed_at=processed.get("processed_at"),
                fetched_at=fetched.get("fetched_at"),
                response_markdown=response_markdown,
            )
        )
    return records


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


def infer_metadata_path(metadata_dir: Path, response_path: Path | None) -> Path | None:
    if response_path is None:
        return None
    candidate = metadata_dir / f"{response_path.stem}.json"
    return candidate if candidate.exists() else None


def sort_key_from_id_and_name(
    fetch_state: dict[str, dict[str, Any]], openai_state: dict[str, dict[str, Any]]
):
    def key(file_id: str) -> tuple[float, str]:
        display_name = (
            openai_state.get(file_id, {}).get("display_name")
            or fetch_state.get(file_id, {}).get("display_name")
            or ""
        )
        match = re.search(r"chp\s+(\d+(?:\.\d+)?)", display_name.lower())
        chapter = float(match.group(1)) if match else 10_000.0
        return (chapter, display_name.lower())

    return key


def build_html(*, records: list[DocumentRecord], output_dir: Path, site_dir: Path) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    toc_items = "\n".join(
        f'<li><a href="#doc-{record.file_id}">{html.escape(pretty_title(record.display_name))}</a></li>'
        for record in records
    )
    sections = "\n".join(render_record(record, site_dir) for record in records)
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
      --code: #f0e7db;
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
      width: min(1180px, calc(100vw - 32px));
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
    .response {{
      border-top: 1px solid var(--line);
      padding-top: 18px;
    }}
    .response h3, .response h4 {{
      margin: 1.2em 0 0.45em;
      color: #243645;
    }}
    .response p, .response li {{
      line-height: 1.65;
    }}
    .response ul {{
      padding-left: 22px;
    }}
    .response hr {{
      border: 0;
      border-top: 1px solid var(--line);
      margin: 20px 0;
    }}
    .response code {{
      background: var(--code);
      padding: 0.1em 0.35em;
      border-radius: 6px;
      font-size: 0.95em;
    }}
    .empty {{
      color: var(--muted);
      font-style: italic;
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
      <p>Browse saved class note PDFs alongside the generated tutoring responses. This page is built from local project state, so it does not require any refetch or extra OpenAI calls.</p>
      <ol class="toc">
        {toc_items}
      </ol>
      <div class="meta">
        <div><strong>Documents:</strong> {len(records)}</div>
        <div><strong>Built:</strong> {generated_at}</div>
        <div><strong>Output root:</strong> {html.escape(str(output_dir))}</div>
      </div>
    </aside>
    <main class="main">
      {sections}
    </main>
  </div>
</body>
</html>
"""


def render_record(record: DocumentRecord, site_dir: Path) -> str:
    links: list[str] = []
    if record.pdf_path and record.pdf_path.exists():
        links.append(link_tag(record.pdf_path, site_dir, "Open PDF"))
    if record.response_path and record.response_path.exists():
        links.append(link_tag(record.response_path, site_dir, "Open Markdown Response"))
    if record.metadata_path and record.metadata_path.exists():
        links.append(link_tag(record.metadata_path, site_dir, "Open Metadata"))
    if record.download_url:
        links.append(
            f'<a href="{html.escape(record.download_url)}" target="_blank" rel="noreferrer">Open Canvas File</a>'
        )

    chips: list[str] = []
    if record.fetched_at:
        chips.append(f'<span class="chip">Fetched {html.escape(record.fetched_at)}</span>')
    if record.processed_at:
        chips.append(f'<span class="chip">OpenAI processed {html.escape(record.processed_at)}</span>')
    if not record.processed_at:
        chips.append('<span class="chip">No OpenAI response yet</span>')

    response_html = (
        markdown_to_html(record.response_markdown)
        if record.response_markdown
        else '<p class="empty">No saved tutoring response yet for this document.</p>'
    )

    return f"""
    <section class="content-card" id="doc-{record.file_id}">
      <div class="doc-header">
        <h2>{html.escape(pretty_title(record.display_name))}</h2>
      </div>
      <div class="chip-row">
        {' '.join(chips)}
      </div>
      <div class="link-row">
        {' '.join(links)}
      </div>
      <div class="response">
        {response_html}
      </div>
    </section>
    """


def link_tag(path: Path, site_dir: Path, label: str) -> str:
    rel = Path(os.path.relpath(path, start=site_dir)).as_posix()
    return f'<a href="{html.escape(rel)}" target="_blank" rel="noreferrer">{html.escape(label)}</a>'


def pretty_title(display_name: str) -> str:
    cleaned = display_name.removesuffix(".pdf").replace(".docx", "")
    cleaned = re.sub(r"\s+\(\d+\)$", "", cleaned)
    cleaned = cleaned.replace("_", " ")
    return cleaned


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
            level = min(len(heading_match.group(1)) + 1, 4)
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
    escaped = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped)
    escaped = re.sub(r"`(.+?)`", r"<code>\1</code>", escaped)
    return escaped


if __name__ == "__main__":
    main()
