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
from urllib.parse import quote

from math_tutor.challenge_builder import build_challenges
from math_tutor.cli import (
    load_dotenv_if_present,
    DEFAULT_MODEL,
    MATHJAX_SCRIPT,
    PROMPTS_BY_SLUG,
    PromptSpec,
    load_openai_state,
    pretty_title,
)


PACKAGE_DIR = Path(__file__).resolve().parent
DEFAULT_OUTPUT_DIR = str(PACKAGE_DIR / "output")
DEFAULT_SITE_DIRNAME = "site"
SITE_TITLE = "Algebra II with Trigonometry Tutor"
SIDEBAR_TITLE = "Algebra II Trig Tutor"
def _specs(*slugs: str) -> tuple[PromptSpec, ...]:
    return tuple(PROMPTS_BY_SLUG[s] for s in slugs if s in PROMPTS_BY_SLUG)


STUDY_GUIDE_SPECS    = _specs("study-guide", "study-guide-gpt5", "study-guide-gemini")
INSPIRING_VIDEOS_SPECS = _specs("inspiring-videos", "inspiring-videos-gpt5", "inspiring-videos-gemini")
MENTAL_MATH_SPECS    = _specs("mental-math", "mental-math-gpt5", "mental-math-gemini")
OLYMPIAD_PROBLEMS_SPECS = _specs("olympiad-problems", "olympiad-problems-gpt5", "olympiad-problems-gemini")
OLYMPIAD_SOLUTIONS_SPECS = _specs("olympiad-solutions", "olympiad-solutions-gpt5", "olympiad-solutions-gemini")
PROMPT_ORDER: tuple[PromptSpec, ...] = (
    *STUDY_GUIDE_SPECS,
    *INSPIRING_VIDEOS_SPECS,
    *MENTAL_MATH_SPECS,
    *OLYMPIAD_PROBLEMS_SPECS,
    *OLYMPIAD_SOLUTIONS_SPECS,
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
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional limit on number of saved PDFs to include in the generated page.",
    )
    parser.add_argument(
        "--include-guided-learning",
        action="store_true",
        help=(
            "Add a Guided Learning section for each PDF with a ChatGPT Study Mode helper button and prompt copy action."
        ),
    )
    parser.add_argument(
        "--force-challenges",
        action="store_true",
        help="Regenerate challenge exams even if exams.json already exists.",
    )
    return parser.parse_args()


def main() -> None:
    load_dotenv_if_present()
    args = parse_args()
    index_path = build_site(
        output_dir=Path(args.output_dir).resolve(),
        site_dir=Path(args.site_dir).resolve() if args.site_dir else None,
        base_path=args.base_path,
        limit=args.limit,
        include_guided_learning=args.include_guided_learning,
        force_challenges=args.force_challenges,
    )
    print(f"Built tutoring page at {index_path}")


def build_site(
    *,
    output_dir: Path,
    site_dir: Path | None = None,
    base_path: str = "",
    limit: int | None = None,
    include_guided_learning: bool = False,
    file_ids: set[str] | None = None,
    force_challenges: bool = False,
) -> Path:
    resolved_site_dir = site_dir.resolve() if site_dir else output_dir / DEFAULT_SITE_DIRNAME
    resolved_site_dir.mkdir(parents=True, exist_ok=True)
    resolved_base_path = determine_base_path(
        raw_base_path=base_path,
        output_dir=output_dir,
        site_dir=resolved_site_dir,
    )

    records = load_records(output_dir)
    if file_ids is not None:
        records = [record for record in records if record.file_id in file_ids]
    if limit is not None:
        records = records[:limit]
    assignments = load_assignment_files(output_dir)
    html_text = build_index_html(
        records=records,
        output_dir=output_dir,
        site_dir=resolved_site_dir,
        base_path=resolved_base_path,
        include_guided_learning=include_guided_learning,
    )
    index_path = resolved_site_dir / "index.html"
    index_path.write_text(html_text, encoding="utf-8")
    library_path = resolved_site_dir / "library.html"
    library_path.write_text(
        build_library_page_html(
            records=records,
            output_dir=output_dir,
            site_dir=resolved_site_dir,
            base_path=resolved_base_path,
            include_guided_learning=include_guided_learning,
        ),
        encoding="utf-8",
    )
    live_tutor_path = resolved_site_dir / "live-tutor.html"
    live_tutor_path.write_text(
        build_live_tutor_page_html(
            records=records,
            output_dir=output_dir,
            site_dir=resolved_site_dir,
            base_path=resolved_base_path,
        ),
        encoding="utf-8",
    )
    for record in records:
        record_path = resolved_site_dir / record_page_filename(record)
        record_path.write_text(
            build_record_page_html(
                record=record,
                records=records,
                output_dir=output_dir,
                site_dir=resolved_site_dir,
                base_path=resolved_base_path,
                include_guided_learning=include_guided_learning,
                assignments=assignments,
            ),
            encoding="utf-8",
        )
    build_challenges(output_dir=output_dir, site_dir=resolved_site_dir, force=force_challenges)
    return index_path


def load_records(output_dir: Path) -> list[DocumentRecord]:
    fetch_state = load_state(output_dir / "fetch_state.json", "fetched")
    openai_state = load_openai_state(output_dir / "openai_state.json").processed

    file_ids = sorted(set(fetch_state) | set(openai_state), key=sort_key_from_id_and_name(fetch_state, openai_state))
    records: list[DocumentRecord] = []
    for file_id in file_ids:
        fetched = fetch_state.get(file_id, {})
        pdf_path_str = fetched.get("pdf_path") or ""
        if "/downloads/assignments/" in pdf_path_str:
            continue
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


def build_index_html(
    *,
    records: list[DocumentRecord],
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    include_guided_learning: bool,
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_prompt_outputs = sum(
        1 for record in records for prompt_output in record.prompt_outputs if prompt_output.processed_at
    )
    library_href = site_page_href("library.html", base_path)
    challenges_href = f"{base_path}challenges/index.html" if base_path else "challenges/index.html"
    live_tutor_href = site_page_href("live-tutor.html", base_path)
    library_preview_cards = "\n".join(
        render_index_card(
            record,
            output_dir,
            site_dir,
            base_path,
            include_guided_learning=include_guided_learning,
        )
        for record in records[:6]
    )
    library_preview = f"""
      <div class="library-preview-grid">
        {library_preview_cards}
      </div>
    """ if library_preview_cards else ""
    body_html = f"""
    <section class="landing-hero">
      <div class="landing-copy">
        <span class="eyebrow">Algebra II with Trigonometry</span>
        <h2>Choose how you want to study today.</h2>
        <p class="page-intro">Start in the class-note library, jump into a timed challenge exam, or use the future live tutor once it is ready.</p>
      </div>
      <div class="landing-stats">
        <div class="stat-pill"><strong>{len(records)}</strong><span>chapters</span></div>
        <div class="stat-pill"><strong>{total_prompt_outputs}</strong><span>saved outputs</span></div>
        <div class="stat-pill"><strong>{generated_at}</strong><span>last build</span></div>
      </div>
    </section>
    <section class="landing-grid">
      <a class="destination-card destination-library" href="{html.escape(library_href)}">
        <span class="destination-kicker">01</span>
        <h3>Library</h3>
        <p>Browse chapter notes, summaries, guided study prompts, and AI-generated practice resources.</p>
        <span class="destination-link">Open library</span>
      </a>
      <a class="destination-card destination-challenges" href="{html.escape(challenges_href)}">
        <span class="destination-kicker">02</span>
        <h3>Challenge Exams</h3>
        <p>Work through mixed mental-math and olympiad sets with the focused exam flow already built into the site.</p>
        <span class="destination-link">Start an exam</span>
      </a>
      <a class="destination-card destination-live" href="{html.escape(live_tutor_href)}">
        <span class="destination-kicker">03</span>
        <h3>Live Tutor</h3>
        <p>Launch a full-curriculum guided learning session with one prompt that covers every chapter and can generate custom exams on demand.</p>
        <span class="destination-link">Open live tutor</span>
      </a>
    </section>
    <section class="content-card section-card">
      <div class="section-head">
        <div>
          <span class="eyebrow">Library Preview</span>
          <h3>Recent chapters</h3>
        </div>
        <a class="section-link" href="{html.escape(library_href)}">See full library</a>
      </div>
      <p class="page-intro">A quick glance at the first few note pages so the landing page still feels alive.</p>
      {library_preview}
    </section>
    """
    return render_page_shell(
        title=SITE_TITLE,
        records=records,
        active_record=None,
        body_html=body_html,
        total_prompt_outputs=total_prompt_outputs,
        generated_at=generated_at,
        base_path=base_path,
        page_kind="home",
    )


def build_record_page_html(
    *,
    record: DocumentRecord,
    records: list[DocumentRecord],
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    include_guided_learning: bool,
    assignments: list[Path] | None = None,
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_prompt_outputs = sum(
        1 for doc in records for prompt_output in doc.prompt_outputs if prompt_output.processed_at
    )
    body_html = render_record(
        record,
        output_dir,
        site_dir,
        base_path,
        include_guided_learning=True,  # always show on per-document pages
        assignments=assignments or [],
    )
    return render_page_shell(
        title=f"{document_label(record)} - {SITE_TITLE}",
        records=records,
        active_record=record,
        body_html=body_html,
        total_prompt_outputs=total_prompt_outputs,
        generated_at=generated_at,
        base_path=base_path,
        page_kind="record",
    )


def render_page_shell(
    *,
    title: str,
    records: list[DocumentRecord],
    active_record: DocumentRecord | None,
    body_html: str,
    total_prompt_outputs: int,
    generated_at: str,
    base_path: str,
    page_kind: str = "record",
) -> str:
    toc_items = "\n".join(render_sidebar_item(record, active_record, base_path) for record in records)
    home_href = site_page_href("index.html", base_path)
    library_href = site_page_href("library.html", base_path)
    live_tutor_href = site_page_href("live-tutor.html", base_path)
    challenges_href = f"{base_path}challenges/index.html" if base_path else "challenges/index.html"
    active_label = (
        html.escape(document_label(active_record))
        if active_record is not None
        else "Library Overview"
    )
    page_class = "page-home" if page_kind == "home" else "page-doc"
    home_active = " active" if page_kind == "home" else ""
    library_active = " active" if page_kind in {"library", "record"} else ""
    live_tutor_active = " active" if page_kind == "live-tutor" else ""
    shell_html = f"""
  <div class="page {page_class}">
    <aside class="sidebar">
      <div class="brand-head">
        <div class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 72 72" role="img" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="brandGlow" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#fff5da"/>
                <stop offset="55%" stop-color="#f3c98f"/>
                <stop offset="100%" stop-color="#cf7c43"/>
              </linearGradient>
            </defs>
            <rect width="72" height="72" rx="16" fill="url(#brandGlow)"/>
            <circle cx="36" cy="36" r="22" fill="none" stroke="#8b4a2c" stroke-width="2.4" opacity="0.35"/>
            <circle cx="36" cy="36" r="14" fill="none" stroke="#8b4a2c" stroke-width="1.7" opacity="0.22"/>
            <path d="M12 43 C21 28, 28 52, 37 37 S53 21, 60 33" fill="none" stroke="#134f59" stroke-width="3.2" stroke-linecap="round"/>
            <circle cx="24" cy="25" r="3.4" fill="#fff7f0" stroke="#8b4a2c" stroke-width="1.4"/>
            <circle cx="51" cy="21" r="2.8" fill="#fff7f0" stroke="#8b4a2c" stroke-width="1.2"/>
            <text x="36" y="53" text-anchor="middle" font-size="21" font-family="Georgia, serif" font-weight="700" fill="#8b4a2c">π</text>
          </svg>
        </div>
        <h1>{html.escape(SIDEBAR_TITLE)}</h1>
      </div>
      <p>Browse saved class note PDFs alongside the generated tutoring outputs.</p>
      <nav class="global-nav" aria-label="Site sections">
        <a class="nav-pill{home_active}" href="{html.escape(home_href)}">Home</a>
        <a class="nav-pill{library_active}" href="{html.escape(library_href)}">Library</a>
        <a class="nav-pill{live_tutor_active}" href="{html.escape(live_tutor_href)}">Live Tutor</a>
        <a class="nav-pill" href="{html.escape(challenges_href)}">Challenge Exams</a>
      </nav>
      <ol class="toc">
        {toc_items}
      </ol>
      <div class="meta">
        <div><strong>Viewing:</strong> {active_label}</div>
        <div><strong>Documents:</strong> {len(records)}</div>
        <div><strong>Saved prompt outputs:</strong> {total_prompt_outputs}</div>
        <div><strong>Built:</strong> {generated_at}</div>
      </div>
    </aside>
    <main class="main">
      {body_html}
    </main>
  </div>
    """ if page_kind != "home" else f"""
  <div class="page page-home">
    <main class="main">
      {body_html}
    </main>
  </div>
    """
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [['\\\\(', '\\\\)'], ['$', '$']],
        displayMath: [['\\\\[', '\\\\]'], ['$$', '$$']],
      }},
      options: {{
        skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre'],
      }},
    }};
  </script>
  <script defer src="{html.escape(MATHJAX_SCRIPT)}"></script>
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
      grid-template-columns: 220px 1fr;
      gap: 24px;
    }}
    .page-home {{
      width: min(1240px, calc(100vw - 32px));
      display: block;
    }}
    .sidebar, .content-card {{
      background: color-mix(in srgb, var(--panel) 94%, white);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 12px 30px rgba(78, 55, 32, 0.08);
    }}
    .sidebar {{
      padding: 18px;
      position: sticky;
      top: 20px;
      align-self: start;
      max-height: calc(100vh - 40px);
      overflow: auto;
    }}
    .sidebar h1 {{
      margin: 0 0 8px;
      font-size: 1.8rem;
      line-height: 1.05;
    }}
    .brand-head {{
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 10px;
    }}
    .brand-mark {{
      width: 56px;
      height: 56px;
      flex: 0 0 56px;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 10px 24px rgba(78, 55, 32, 0.12);
    }}
    .brand-mark svg {{
      display: block;
      width: 100%;
      height: 100%;
    }}
    .sidebar p {{
      color: var(--muted);
      margin: 0 0 18px;
      line-height: 1.45;
    }}
    .sidebar-home {{
      display: inline-block;
      margin-bottom: 14px;
      font-weight: 600;
      text-decoration: none;
    }}
    .global-nav {{
      display: grid;
      gap: 8px;
      margin: 0 0 16px;
    }}
    .nav-pill {{
      display: block;
      text-decoration: none;
      padding: 10px 12px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.72);
      color: var(--ink);
      font-weight: 600;
    }}
    .nav-pill.active {{
      background: var(--accent-soft);
      border-color: var(--line-strong);
      color: #6a2e16;
    }}
    .toc {{
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 8px;
    }}
    .toc a {{
      display: block;
      text-decoration: none;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid transparent;
      color: var(--ink);
    }}
    .toc a:hover {{
      border-color: var(--line);
      background: rgba(255, 255, 255, 0.6);
    }}
    .toc a.active {{
      background: var(--accent-soft);
      border-color: var(--line-strong);
      color: #6a2e16;
      font-weight: 700;
    }}
    .meta {{
      margin-top: 18px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.92rem;
    }}
    .sidebar-challenges {{
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
      display: flex;
      flex-direction: column;
      gap: 6px;
    }}
    .challenges-nav-link {{
      font-weight: 700;
      text-decoration: none;
      color: var(--accent);
      font-size: 0.95rem;
    }}
    .challenges-nav-link:hover {{ text-decoration: underline; }}
    .main {{
      display: grid;
      gap: 18px;
    }}
    .content-card {{
      padding: 24px;
    }}
    .landing-hero {{
      position: relative;
      overflow: hidden;
      background:
        radial-gradient(circle at top right, rgba(243, 201, 143, 0.42), transparent 30%),
        linear-gradient(135deg, rgba(255, 248, 238, 0.96), rgba(253, 245, 232, 0.96));
      border: 1px solid var(--line);
      border-radius: 28px;
      padding: 38px 34px;
      box-shadow: 0 16px 34px rgba(78, 55, 32, 0.1);
    }}
    .landing-copy h2 {{
      margin: 8px 0 14px;
      font-size: clamp(2.3rem, 6vw, 4rem);
      line-height: 0.98;
      max-width: 10ch;
    }}
    .eyebrow {{
      display: inline-block;
      font-size: 0.78rem;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--muted);
      font-family: system-ui, sans-serif;
      font-weight: 700;
    }}
    .landing-stats {{
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 22px;
    }}
    .stat-pill {{
      min-width: 148px;
      padding: 14px 16px;
      border-radius: 18px;
      border: 1px solid rgba(202, 186, 164, 0.9);
      background: rgba(255,255,255,0.72);
      display: grid;
      gap: 4px;
    }}
    .stat-pill strong {{
      font-size: 1.05rem;
      color: #243645;
    }}
    .stat-pill span {{
      color: var(--muted);
      font-size: 0.88rem;
    }}
    .landing-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px;
    }}
    .destination-card {{
      position: relative;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      gap: 14px;
      min-height: 260px;
      padding: 26px;
      border-radius: 24px;
      border: 1px solid var(--line);
      text-decoration: none;
      color: var(--ink);
      box-shadow: 0 16px 34px rgba(78, 55, 32, 0.08);
      transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
    }}
    .destination-card:hover {{
      transform: translateY(-4px);
      box-shadow: 0 22px 38px rgba(78, 55, 32, 0.13);
      border-color: var(--line-strong);
    }}
    .destination-library {{
      background: linear-gradient(160deg, #fffaf2 0%, #f8efe2 100%);
    }}
    .destination-challenges {{
      background: linear-gradient(160deg, #eef7f7 0%, #e4f0ef 100%);
    }}
    .destination-live {{
      background: linear-gradient(160deg, #f8f0e7 0%, #f3e4d6 100%);
    }}
    .destination-kicker {{
      font-family: system-ui, sans-serif;
      font-size: 0.82rem;
      font-weight: 800;
      letter-spacing: 0.12em;
      color: var(--muted);
    }}
    .destination-card h3 {{
      margin: 0;
      font-size: 1.75rem;
      line-height: 1.05;
    }}
    .destination-card p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.55;
      max-width: 30ch;
    }}
    .destination-link,
    .destination-soon {{
      margin-top: auto;
      align-self: flex-start;
      padding: 10px 14px;
      border-radius: 999px;
      font-family: system-ui, sans-serif;
      font-size: 0.92rem;
      font-weight: 700;
    }}
    .destination-link {{
      background: rgba(255,255,255,0.82);
      border: 1px solid rgba(202, 186, 164, 0.9);
    }}
    .destination-soon {{
      background: rgba(255,255,255,0.58);
      border: 1px dashed rgba(161, 77, 46, 0.45);
      color: var(--accent);
    }}
    .section-card {{
      padding: 28px;
    }}
    .section-head {{
      display: flex;
      flex-wrap: wrap;
      align-items: end;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
    }}
    .section-head h3 {{
      margin: 6px 0 0;
      font-size: 1.5rem;
    }}
    .section-link {{
      text-decoration: none;
      font-weight: 700;
    }}
    .library-preview-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
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
    .page-intro {{
      color: var(--muted);
      line-height: 1.5;
      margin: 0 0 18px;
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
      font-weight: 600;
    }}
    .chip-model {{
      background: #dbeafe;
      color: #1e40af;
      font-weight: 600;
    }}
    .chip-gemini {{
      background: #dcfce7;
      color: #166534;
      font-weight: 600;
    }}
    .chip-ai {{
      background: #e2e8f0;
      color: #334155;
      font-weight: 400;
    }}
    .chip-lock {{
      background: #fef9c3;
      color: #854d0e;
      font-weight: 600;
    }}
    .olympiad-model-row {{
      display: flex;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 10px;
    }}
    .olympiad-model-row .chip {{
      white-space: nowrap;
      min-width: 120px;
      text-align: center;
    }}
    .olympiad-links {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }}
    .olympiad-links a {{
      text-decoration: none;
      font-weight: 600;
      border: 1px solid var(--line);
      background: #fff;
      padding: 9px 12px;
      border-radius: 999px;
    }}
    .olympiad-links a.pdf-link {{
      font-weight: 500;
      font-size: 0.78rem;
      padding: 5px 10px;
      border-color: var(--line);
      background: #f5f5f5;
      color: #555;
      letter-spacing: 0.03em;
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
    .guided-card {{
      border: 1px solid var(--line-strong);
      background: linear-gradient(180deg, #fff7ec 0%, #fffdf8 100%);
      border-radius: 16px;
      padding: 18px;
      margin-bottom: 18px;
    }}
    .guided-card h3 {{
      margin: 0 0 10px;
      font-size: 1.25rem;
      color: #243645;
    }}
    .guided-card p {{
      margin: 0 0 12px;
      line-height: 1.5;
      color: var(--muted);
    }}
    .button-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 12px;
    }}
    .button-row button,
    .button-row a {{
      appearance: none;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--accent);
      text-decoration: none;
      font: inherit;
      font-weight: 600;
      padding: 9px 12px;
      border-radius: 999px;
      cursor: pointer;
    }}
    .guided-note {{
      font-size: 0.95rem;
      color: var(--muted);
    }}
    details pre {{
      white-space: pre-wrap;
      word-break: break-word;
      overflow-wrap: break-word;
      max-width: 100%;
      overflow: hidden;
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
    .card-summary {{
      color: var(--muted);
      line-height: 1.55;
    }}
    .card-summary p {{
      margin: 0;
    }}
    @media (max-width: 960px) {{
      .page {{ grid-template-columns: 1fr; }}
      .sidebar {{ position: static; max-height: none; }}
      .landing-grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
{shell_html}
  <script>
    async function copyChatgptPrompt(button) {{
      const prompt = button.dataset.chatgptPrompt || "";
      const status = button.parentElement && button.parentElement.nextElementSibling;
      if (!prompt || !navigator.clipboard || !navigator.clipboard.writeText) {{
        if (status) {{
          status.textContent = "Copy failed in this browser. Use the prompt text shown below.";
        }}
        return;
      }}
      try {{
        await navigator.clipboard.writeText(prompt);
        if (status) {{
          status.textContent = "Prompt copied.";
        }}
      }} catch (error) {{
        if (status) {{
          status.textContent = "Copy failed in this browser. Use the prompt text shown below.";
        }}
      }}
    }}
  </script>
</body>
</html>
"""


def render_sidebar_item(record: DocumentRecord, active_record: DocumentRecord | None, base_path: str) -> str:
    href = site_page_href(record_page_filename(record), base_path)
    classes = "active" if active_record and active_record.file_id == record.file_id else ""
    return f'<li><a class="{classes}" href="{html.escape(href)}">{html.escape(document_label(record))}</a></li>'


def build_library_page_html(
    *,
    records: list[DocumentRecord],
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    include_guided_learning: bool,
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_prompt_outputs = sum(
        1 for record in records for prompt_output in record.prompt_outputs if prompt_output.processed_at
    )
    overview_cards = "\n".join(
        render_index_card(
            record,
            output_dir,
            site_dir,
            base_path,
            include_guided_learning=include_guided_learning,
        )
        for record in records
    )
    body_html = f"""
    <section class="content-card section-card">
      <div class="section-head">
        <div>
          <span class="eyebrow">Library</span>
          <h3>Chapter collection</h3>
        </div>
        <a class="section-link" href="{html.escape(site_page_href('index.html', base_path))}">Back to home</a>
      </div>
      <p class="page-intro">Choose a chapter to open its study guide, practice tools, assignments, and guided learning links.</p>
      <div class="prompt-grid">
        {overview_cards}
      </div>
    </section>
    """
    return render_page_shell(
        title=f"Library - {SITE_TITLE}",
        records=records,
        active_record=None,
        body_html=body_html,
        total_prompt_outputs=total_prompt_outputs,
        generated_at=generated_at,
        base_path=base_path,
        page_kind="library",
    )


def build_live_tutor_page_html(
    *,
    records: list[DocumentRecord],
    output_dir: Path,
    site_dir: Path,
    base_path: str,
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_prompt_outputs = sum(
        1 for record in records for prompt_output in record.prompt_outputs if prompt_output.processed_at
    )
    curriculum_prompt = build_curriculum_guided_learning_prompt(records)
    body_html = f"""
    <section class="content-card section-card">
      <div class="section-head">
        <div>
          <span class="eyebrow">Live Tutor</span>
          <h3>Whole-course guided learning</h3>
        </div>
        <a class="section-link" href="{html.escape(site_page_href('index.html', base_path))}">Back to home</a>
      </div>
      <p class="page-intro">This uses the same guided-learning launch pattern as the chapter pages, but with a single prompt covering the full Algebra II with Trigonometry curriculum.</p>
      {render_guided_learning_card(
          title="Live Tutor",
          description="Open Gemini or ChatGPT Study Mode, then use the curriculum-wide prompt below. Students can ask for a live exam at any difficulty after the session starts.",
          prompt_text=curriculum_prompt,
          extra_links=[],
      )}
    </section>
    """
    return render_page_shell(
        title=f"Live Tutor - {SITE_TITLE}",
        records=records,
        active_record=None,
        body_html=body_html,
        total_prompt_outputs=total_prompt_outputs,
        generated_at=generated_at,
        base_path=base_path,
        page_kind="live-tutor",
    )


def render_index_card(
    record: DocumentRecord,
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    *,
    include_guided_learning: bool,
) -> str:
    prompt_count = sum(1 for prompt_output in record.prompt_outputs if prompt_output.processed_at)
    links = [f'<a href="{html.escape(site_page_href(record_page_filename(record), base_path))}">Enter the Lab</a>']
    if record.pdf_path and record.pdf_path.exists():
        links.append(link_tag(record.pdf_path, output_dir, site_dir, "Class Note PDF", base_path))
    record_summary_html = extract_record_summary_html(record)
    summary_html = f'<div class="card-summary">{record_summary_html}</div>' if record_summary_html else ""
    if include_guided_learning and not summary_html:
        summary_html = f"<p>{render_inline(build_guided_learning_prompt(record))}</p>"
    return f"""
      <section class="prompt-card">
        <h3>{html.escape(document_label(record))}</h3>
        <div class="chip-row">
          <span class="chip">{prompt_count} AI generated section(s)</span>
        </div>
        <div class="link-row">
          {' '.join(links)}
        </div>
        {summary_html}
      </section>
    """


def site_page_href(filename: str, base_path: str) -> str:
    return f"{base_path}{filename}" if base_path else filename


def record_page_filename(record: DocumentRecord) -> str:
    return f"doc-{record.file_id}.html"


def document_label(record: DocumentRecord) -> str:
    chapter = extract_chapter_label(record.display_name)
    if chapter:
        return f"Chapter {chapter}"
    return pretty_title(record.display_name)


def extract_chapter_label(display_name: str) -> str | None:
    match = re.search(r"chp\s+(\d+(?:\.\d+)?(?:\s*&\s*\d+(?:\.\d+)?)*)", display_name.lower())
    if not match:
        return None
    return re.sub(r"\s+", " ", match.group(1).strip())


def extract_chapters_from_assignment_name(filename: str) -> set[str]:
    """Extract chapter numbers from assignment filename like 'chp-5-1-note' or 'chp-6-1-6-2-work'."""
    stem = re.sub(r'^\d+_', '', Path(filename).stem)
    m = re.match(r'chp-([\d][\d-]*)', stem)
    if not m:
        return set()
    chapter_part = m.group(1).rstrip('-')
    digits = chapter_part.split('-')
    chapters: set[str] = set()
    i = 0
    while i + 1 < len(digits):
        chapters.add(f"{digits[i]}.{digits[i + 1]}")
        i += 2
    return chapters


def assignment_display_name(path: Path) -> str:
    """Format assignment filename into a readable label like 'Chp 5.1 Note'."""
    stem = re.sub(r'^\d+_', '', path.stem)
    parts = stem.split('-')
    result: list[str] = []
    i = 0
    if parts and parts[0].lower() == 'chp':
        result.append('Chp')
        i = 1
        while i + 1 < len(parts) and parts[i].isdigit() and parts[i + 1].isdigit():
            result.append(f"{parts[i]}.{parts[i + 1]}")
            i += 2
    while i < len(parts):
        result.append(parts[i].capitalize())
        i += 1
    return ' '.join(result)


def load_assignment_files(output_dir: Path) -> list[Path]:
    assignments_dir = output_dir / "downloads" / "assignments"
    if not assignments_dir.exists():
        return []
    return sorted(assignments_dir.glob("*.pdf"))


def match_assignments_to_record(assignments: list[Path], record: DocumentRecord) -> list[Path]:
    record_chapter = extract_chapter_label(record.display_name)
    if not record_chapter:
        return []
    return sorted(
        (p for p in assignments if any(ch in record_chapter for ch in extract_chapters_from_assignment_name(p.name))),
        key=lambda p: p.name,
    )


def render_assignments_card(assignments: list[Path], site_dir: Path, base_path: str) -> str:
    if not assignments:
        return ""
    assignments_dir = site_dir / "assignments"
    assignments_dir.mkdir(parents=True, exist_ok=True)
    links: list[str] = []
    for src in assignments:
        dest = assignments_dir / src.name
        if not dest.exists() or src.stat().st_mtime_ns != dest.stat().st_mtime_ns:
            shutil.copy2(src, dest)
        href = f"{base_path}assignments/{src.name}" if base_path else f"assignments/{src.name}"
        links.append(f'<a href="{html.escape(href)}">{html.escape(assignment_display_name(src))}</a>')
    return f"""
      <section class="prompt-card">
        <h3>Assignments</h3>
        <div class="chip-row"><span class="chip chip-lock">Login Required</span></div>
        <div class="link-row">
          {' '.join(links)}
        </div>
      </section>
    """


def _model_chip(spec: PromptSpec) -> str:
    label = _model_label(spec)
    if spec.model is None:
        css = "chip"
    elif spec.model.startswith("gemini"):
        css = "chip chip-gemini"
    else:
        css = "chip chip-model"
    return f'<span class="{css}">{html.escape(label)}</span>'


def render_single_model_row_card(
    title: str,
    specs: tuple[PromptSpec, ...],
    outputs_by_slug: dict[str, PromptOutputRecord],
    link_label: str,
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    hide_model: bool = False,
) -> str:
    model_rows: list[str] = []

    for spec in specs:
        out = outputs_by_slug.get(spec.slug)
        if not out or not out.processed_at:
            continue
        parts: list[str] = []
        if out.response_html_path and out.response_html_path.exists():
            href = build_site_href(path=out.response_html_path, output_dir=output_dir, site_dir=site_dir, base_path=base_path)
            parts.append(f'<a href="{html.escape(href)}">{html.escape(link_label)}</a>')
        if spec.generate_response_pdf and out.response_pdf_path and out.response_pdf_path.exists():
            href = build_site_href(path=out.response_pdf_path, output_dir=output_dir, site_dir=site_dir, base_path=base_path)
            parts.append(f'<a href="{html.escape(href)}" class="pdf-link">PDF</a>')
        model_rows.append(f"""
      <div class="olympiad-model-row">
        {"" if hide_model else _model_chip(spec)}
        <div class="olympiad-links">
          {' '.join(parts)}
        </div>
      </div>""")

    if not model_rows:
        return ""

    return f"""
      <section class="prompt-card">
        <h3>{html.escape(title)}</h3>
        <div class="chip-row"><span class="chip chip-ai">Generated by AI</span></div>
        {''.join(model_rows)}
      </section>
    """


def render_olympiad_combined(
    outputs_by_slug: dict[str, PromptOutputRecord],
    output_dir: Path,
    site_dir: Path,
    base_path: str,
) -> str:
    model_rows: list[str] = []
    header_chips: list[str] = []

    for prob_spec, sol_spec in zip(OLYMPIAD_PROBLEMS_SPECS, OLYMPIAD_SOLUTIONS_SPECS):
        prob_out = outputs_by_slug.get(prob_spec.slug)
        sol_out = outputs_by_slug.get(sol_spec.slug)
        has_data = (prob_out and prob_out.processed_at) or (sol_out and sol_out.processed_at)
        if not has_data:
            continue

        def _inline_links(out: PromptOutputRecord | None, spec: PromptSpec, label: str) -> str:
            if not out:
                return ""
            parts: list[str] = []
            if out.response_html_path and out.response_html_path.exists():
                href = build_site_href(path=out.response_html_path, output_dir=output_dir, site_dir=site_dir, base_path=base_path)
                parts.append(f'<a href="{html.escape(href)}">{html.escape(label)}</a>')
            if spec.generate_response_pdf and out.response_pdf_path and out.response_pdf_path.exists():
                href = build_site_href(path=out.response_pdf_path, output_dir=output_dir, site_dir=site_dir, base_path=base_path)
                parts.append(f'<a href="{html.escape(href)}" class="pdf-link">PDF</a>')
            return " ".join(parts)

        prob_part = _inline_links(prob_out, prob_spec, "Problems")
        sol_part = _inline_links(sol_out, sol_spec, "Solutions")
        item_parts = [p for p in [prob_part, sol_part] if p]
        items_html = "   ".join(item_parts)

        header_chips.append(_model_chip(prob_spec))
        model_rows.append(f"""
      <div class="olympiad-model-row">
        {_model_chip(prob_spec)}
        <div class="olympiad-links">
          {items_html}
        </div>
      </div>""")

    if not model_rows:
        return ""

    return f"""
      <section class="prompt-card">
        <h3>Olympiad Problems &amp; Solutions</h3>
        <div class="chip-row"><span class="chip chip-ai">Generated by AI</span></div>
        {''.join(model_rows)}
      </section>
    """


def render_record(
    record: DocumentRecord,
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    *,
    include_guided_learning: bool,
    assignments: list[Path] | None = None,
) -> str:
    document_links: list[str] = []
    if record.pdf_path and record.pdf_path.exists():
        document_links.append(link_tag(record.pdf_path, output_dir, site_dir, "Class Note PDF", base_path))

    document_chips: list[str] = []
    if record.fetched_at:
        document_chips.append(f'<span class="chip">Fetched {html.escape(record.fetched_at)}</span>')

    summary_html = render_record_summary(record)
    outputs_by_slug = {po.slug: po for po in record.prompt_outputs}
    rendered_slugs: set[str] = set()
    cards: list[str] = []

    for title, specs, label, hide_model in (
        ("Study Guide", STUDY_GUIDE_SPECS, "Open Guide", False),
        ("Inspiring Videos", INSPIRING_VIDEOS_SPECS, "Watch Picks", False),
        ("Mental Math", MENTAL_MATH_SPECS, "Mental Math", False),
    ):
        card = render_single_model_row_card(title, specs, outputs_by_slug, label, output_dir, site_dir, base_path, hide_model=hide_model)
        if card:
            cards.append(card)

    olympiad_card = render_olympiad_combined(outputs_by_slug, output_dir, site_dir, base_path)
    if olympiad_card:
        cards.append(olympiad_card)

    record_assignments = match_assignments_to_record(assignments or [], record)
    assignments_card = render_assignments_card(record_assignments, site_dir, base_path)
    if assignments_card:
        cards.append(assignments_card)

    for spec in (*STUDY_GUIDE_SPECS, *INSPIRING_VIDEOS_SPECS, *MENTAL_MATH_SPECS, *OLYMPIAD_PROBLEMS_SPECS, *OLYMPIAD_SOLUTIONS_SPECS):
        rendered_slugs.add(spec.slug)
    for prompt_output in record.prompt_outputs:
        if prompt_output.slug not in rendered_slugs:
            cards.append(render_prompt_output(prompt_output, output_dir, site_dir, base_path))
    prompt_cards = "\n".join(cards)
    guided_learning_html = ""
    if include_guided_learning:
        guided_learning_html = render_guided_learning(record, output_dir, site_dir, base_path)
    return f"""
    <section class="content-card" id="doc-{record.file_id}">
      <div class="doc-header">
        <h2>{html.escape(document_label(record))}</h2>
      </div>
      <div class="chip-row">
        {' '.join(document_chips)}
      </div>
      <div class="link-row">
        {' '.join(document_links)}
      </div>
      {summary_html}
      {guided_learning_html}
      <div class="prompt-grid">
        {prompt_cards}
      </div>
    </section>
    """


def render_guided_learning(record: DocumentRecord, output_dir: Path, site_dir: Path, base_path: str) -> str:
    prompt_text = build_guided_learning_prompt(record)
    extra_links: list[str] = []
    if record.pdf_path and record.pdf_path.exists():
        extra_links.append(link_tag(record.pdf_path, output_dir, site_dir, "Class Note PDF", base_path))
    return render_guided_learning_card(
        title="Guided Learning",
        description="Open Gemini or ChatGPT Study Mode, then paste the summary prompt below to begin.",
        prompt_text=prompt_text,
        extra_links=extra_links,
    )


def render_guided_learning_card(
    *,
    title: str,
    description: str,
    prompt_text: str,
    extra_links: list[str],
) -> str:
    escaped_prompt = html.escape(prompt_text, quote=True)
    gemini_href = f"https://gemini.google.com/guided-learning?query={quote(prompt_text)}"
    buttons: list[str] = [
        f'<a href="{html.escape(gemini_href, quote=True)}" target="_blank" rel="noopener noreferrer">Open Gemini</a>',
        '<a href="https://chatgpt.com/studymode" target="_blank" rel="noopener noreferrer">Open ChatGPT</a>',
        (
            f'<button type="button" data-chatgpt-prompt="{escaped_prompt}" '
            f'onclick="copyChatgptPrompt(this)">Copy Prompt</button>'
        ),
    ]
    buttons.extend(extra_links)

    return f"""
      <section class="guided-card">
        <h3>{html.escape(title)}</h3>
        <p>{html.escape(description)}</p>
        <div class="button-row">
          {' '.join(buttons)}
        </div>
        <p class="guided-note">Use the copied prompt as your starting context. In Gemini, switch to Guided Learning. In ChatGPT, use Study Mode.</p>
        <details>
          <summary>Show prompt</summary>
          <pre>{html.escape(prompt_text)}</pre>
        </details>
      </section>
    """


def build_guided_learning_prompt(record: DocumentRecord) -> str:
    for prompt_output in record.prompt_outputs:
        if prompt_output.slug != "study-guide":
            continue
        # Prefer reading from the HTML file to get full summary including bullets and math.
        if prompt_output.response_html_path and prompt_output.response_html_path.exists():
            content = prompt_output.response_html_path.read_text(encoding="utf-8")
            m = re.search(
                r'<h[2-4][^>]*>.*?[Ss]hort\s+[Ss]ummary.*?</h[2-4]>(.*?)(?=<h[2-4]|<hr\s*/?>)',
                content,
                re.DOTALL,
            )
            if m:
                raw_html = m.group(1).strip()
                # Convert <li> items to "- item" plain text, then strip remaining tags.
                plain = re.sub(r'<li[^>]*>(.*?)</li>', lambda mo: f"- {mo.group(1).strip()}\n", raw_html, flags=re.DOTALL)
                plain = re.sub(r'<[^>]+>', ' ', plain)
                plain = re.sub(r'[ \t]+', ' ', plain)
                plain = re.sub(r'\n{3,}', '\n\n', plain).strip()
                if plain:
                    return normalize_summary_text(plain)
        # Fallback: use the markdown stub.
        if prompt_output.response_markdown:
            summary_lines = extract_study_guide_summary_lines(prompt_output.response_markdown)
            if summary_lines:
                return normalize_summary_text("\n".join(summary_lines))
    return pretty_title(record.display_name)


def build_curriculum_guided_learning_prompt(records: list[DocumentRecord]) -> str:
    chapter_summaries: list[str] = []
    for record in records:
        summary_text = extract_record_summary_text(record)
        if not summary_text:
            continue
        chapter_summaries.append(f"{document_label(record)}\n{summary_text}")

    if not chapter_summaries:
        return (
            "You are my live Algebra II with Trigonometry tutor. Help me review the full course, "
            "adapt to my level, and generate practice or exams at any difficulty I request."
        )

    joined_summaries = "\n\n".join(chapter_summaries)
    return (
        "You are my live Algebra II with Trigonometry tutor. Use the curriculum notes below as the course context for this session.\n\n"
        "How to tutor me:\n"
        "- Diagnose my current level first with a short warm-up if I do not specify a topic.\n"
        "- Teach with guided learning, not just final answers.\n"
        "- When I ask for practice, create problems at easy, medium, hard, honors, or olympiad difficulty.\n"
        "- When I ask for a live exam, generate a balanced exam from the full curriculum or from the units I specify, wait for my answers, then grade and coach me.\n"
        "- Keep explanations concise at first, then expand only if I ask.\n"
        "- Prioritize exact math notation and clearly labeled steps.\n\n"
        "Curriculum notes:\n"
        f"{joined_summaries}\n\n"
        "Start by greeting me as my live tutor and asking whether I want concept review, targeted practice, or a live exam."
    )


def extract_record_summary_text(record: DocumentRecord) -> str:
    for prompt_output in record.prompt_outputs:
        if prompt_output.slug != "study-guide":
            continue
        if prompt_output.response_html_path and prompt_output.response_html_path.exists():
            content = prompt_output.response_html_path.read_text(encoding="utf-8")
            m = re.search(
                r'<h[2-4][^>]*>.*?[Ss]hort\s+[Ss]ummary.*?</h[2-4]>(.*?)(?=<h[2-4]|<hr\s*/?>)',
                content,
                re.DOTALL,
            )
            if m:
                raw_html = m.group(1).strip()
                plain = re.sub(r'<li[^>]*>(.*?)</li>', lambda mo: f"- {mo.group(1).strip()}\n", raw_html, flags=re.DOTALL)
                plain = re.sub(r'<[^>]+>', ' ', plain)
                plain = html.unescape(plain)
                plain = re.sub(r'[ \t]+', ' ', plain)
                plain = re.sub(r'\n{3,}', '\n\n', plain).strip()
                if plain:
                    return normalize_summary_text(plain)
        if prompt_output.response_markdown:
            summary_lines = extract_study_guide_summary_lines(prompt_output.response_markdown)
            if summary_lines:
                return normalize_summary_text("\n".join(summary_lines))
    return ""


def render_record_summary(record: DocumentRecord) -> str:
    summary_html = extract_record_summary_html(record)
    if not summary_html:
        return ""
    return f"""
      <section class="guided-card">
        <h3>Summary</h3>
        {summary_html}
      </section>
    """


def extract_record_summary_html(record: DocumentRecord) -> str:
    """Extract the Short Summary section from the study-guide HTML response file.

    Reads directly from the HTML file to preserve bullet points, math notation,
    and other rich formatting that would be lost going through the markdown stub.
    Falls back to the markdown-based extraction if no HTML file is available.
    """
    for prompt_output in record.prompt_outputs:
        if prompt_output.slug != "study-guide":
            continue
        # Prefer reading directly from the HTML response file
        if prompt_output.response_html_path and prompt_output.response_html_path.exists():
            content = prompt_output.response_html_path.read_text(encoding="utf-8")
            # Find the Short Summary heading (may have nested tags like <strong>)
            m = re.search(
                r'<h[2-4][^>]*>.*?[Ss]hort\s+[Ss]ummary.*?</h[2-4]>(.*?)(?=<h[2-4]|<hr\s*/?>)',
                content,
                re.DOTALL,
            )
            if m:
                return m.group(1).strip()
        # Fallback: derive from markdown stub
        if prompt_output.response_markdown:
            return extract_study_guide_summary_html(prompt_output.response_markdown, include_heading=False)
    return ""


_MODEL_DISPLAY_NAMES: dict[str, str] = {
    "gpt-4.1": "GPT-4.1",
    "gpt-5.4": "GPT-5.4",
    "gemini-3.1-pro-preview": "Gemini 3.1 Pro",
    "gemini-3.1-pro": "Gemini 3.1 Pro",
}


def _model_label(prompt_spec: PromptSpec) -> str:
    raw = prompt_spec.model or DEFAULT_MODEL
    return _MODEL_DISPLAY_NAMES.get(raw, raw.replace("-preview", ""))


def _prompt_output_links(
    prompt_output: PromptOutputRecord,
    prompt_spec: PromptSpec,
    model_label: str,
    output_dir: Path,
    site_dir: Path,
    base_path: str,
) -> list[str]:
    links = []
    if prompt_output.response_html_path and prompt_output.response_html_path.exists():
        links.append(link_tag(prompt_output.response_html_path, output_dir, site_dir, f"{model_label} HTML", base_path))
    if (
        prompt_spec.generate_response_pdf
        and prompt_output.response_pdf_path
        and prompt_output.response_pdf_path.exists()
    ):
        links.append(link_tag(prompt_output.response_pdf_path, output_dir, site_dir, f"{model_label} PDF", base_path))
    return links


def render_prompt_group(
    base_output: PromptOutputRecord | None,
    gpt5_output: PromptOutputRecord | None,
    gemini_output: PromptOutputRecord | None,
    base_spec: PromptSpec,
    output_dir: Path,
    site_dir: Path,
    base_path: str,
) -> str:
    gpt5_spec = PROMPTS_BY_SLUG.get(gpt5_output.slug) if gpt5_output else None
    gemini_spec = PROMPTS_BY_SLUG.get(gemini_output.slug) if gemini_output else None

    base_label = _model_label(base_spec)
    gpt5_label = _model_label(gpt5_spec) if gpt5_spec else "gpt-5.4"
    gemini_label = _model_label(gemini_spec) if gemini_spec else "gemini"

    links: list[str] = []
    if base_output:
        links += _prompt_output_links(base_output, base_spec, base_label, output_dir, site_dir, base_path)
    if gpt5_output and gpt5_spec:
        links += _prompt_output_links(gpt5_output, gpt5_spec, gpt5_label, output_dir, site_dir, base_path)
    if gemini_output and gemini_spec:
        links += _prompt_output_links(gemini_output, gemini_spec, gemini_label, output_dir, site_dir, base_path)

    chips: list[str] = []
    if base_output and base_output.processed_at:
        chips.append(f'<span class="chip">{html.escape(base_label)} generated {html.escape(base_output.processed_at)}</span>')
    if gpt5_output and gpt5_output.processed_at:
        chips.append(f'<span class="chip chip-model">{html.escape(gpt5_label)} generated {html.escape(gpt5_output.processed_at)}</span>')
    if gemini_output and gemini_output.processed_at:
        chips.append(f'<span class="chip chip-gemini">{html.escape(gemini_label)} generated {html.escape(gemini_output.processed_at)}</span>')
    if not chips:
        chips.append('<span class="chip">No AI response yet</span>')

    no_links_note = "" if links else '<span class="chip">No output files yet</span>'

    return f"""
      <section class="prompt-card">
        <h3>{html.escape(base_spec.title)}</h3>
        <div class="chip-row">
          {' '.join(chips)}
        </div>
        <div class="link-row">
          {' '.join(links)}{no_links_note}
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
    if prompt_spec is not None and prompt_spec.model:
        chips.append(f'<span class="chip chip-model">{html.escape(prompt_spec.model)}</span>')
    if prompt_output.processed_at:
        chips.append(f'<span class="chip">Generated by AI {html.escape(prompt_output.processed_at)}</span>')
    else:
        chips.append('<span class="chip">No OpenAI response yet</span>')

    return f"""
      <section class="prompt-card">
        <h3>{html.escape(prompt_output.title)}</h3>
        <div class="chip-row">
          {' '.join(chips)}
        </div>
        <div class="link-row">
          {' '.join(links)}
        </div>
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
    return ""


def normalize_base_path(value: str) -> str:
    if not value:
        return ""
    stripped = value.strip().strip("/")
    if not stripped:
        return ""
    return f"/{stripped}/"


def is_deploy_site_dir(*, output_dir: Path, site_dir: Path) -> bool:
    if not site_dir.is_relative_to(output_dir):
        return True
    try:
        relative_parts = site_dir.relative_to(output_dir).parts
    except ValueError:
        return False
    return "deploy" in relative_parts


def should_copy_site_assets(*, output_dir: Path, site_dir: Path, base_path: str) -> bool:
    return bool(base_path) or is_deploy_site_dir(output_dir=output_dir, site_dir=site_dir)


def extract_study_guide_summary_html(markdown_text: str, *, include_heading: bool = True) -> str:
    summary_lines = extract_study_guide_summary_lines(markdown_text)
    if not summary_lines:
        return ""

    summary_html = markdown_to_html(normalize_summary_text("\n".join(summary_lines)))
    heading_html = "<h4>Summary</h4>" if include_heading else ""
    return f"""
        <div class="response">
          {heading_html}
          {summary_html}
        </div>
    """


def normalize_summary_text(text: str) -> str:
    return re.sub(r"^This document\b", "This chapter", text.strip(), count=1, flags=re.IGNORECASE)


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
