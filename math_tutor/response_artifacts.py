"""Shared rendering helpers for generated tutoring response artifacts."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, sync_playwright

from math_tutor.video_recommendations import normalize_inspiring_videos_markdown


MATHJAX_SCRIPT = "https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"
COPY_BUTTON_SLUGS = {
    "mental-math",
    "mental-math-gpt5",
    "mental-math-gemini",
    "olympiad-problems",
    "olympiad-problems-gpt5",
    "olympiad-problems-gemini",
    "olympiad-solutions",
    "olympiad-solutions-gpt5",
    "olympiad-solutions-gemini",
}


def build_response_html(
    *,
    title: str,
    prompt_title: str,
    markdown_text: str,
    pdf_label: str | None,
    pdf_href: str | None,
    prompt_slug: str = "",
) -> str:
    if prompt_slug.startswith("inspiring-videos"):
        markdown_text = normalize_inspiring_videos_markdown(markdown_text)
    rendered = markdown_to_html(markdown_text)
    pdf_name = html_escape(response_document_title(title))
    prompt_name = html_escape(prompt_title)

    if pdf_label and pdf_href:
        pdf_note = (
            f'<p>Saved tutoring response with MathJax rendering. Original PDF file: '
            f'<a href="{html_escape(pdf_href)}">{html_escape(pdf_label)}</a></p>'
        )
    else:
        pdf_note = "<p>Saved tutoring response with MathJax rendering.</p>"

    show_copy = prompt_slug in COPY_BUTTON_SLUGS
    copy_block = """    /* ── Question copy buttons ── */
    .q-heading {
      display: flex;
      align-items: baseline;
      gap: 10px;
    }
    .copy-q-btn {
      appearance: none;
      border: 1px solid var(--line);
      background: rgba(255,255,255,.7);
      color: var(--muted);
      border-radius: 6px;
      cursor: pointer;
      padding: 2px 7px;
      font-size: .85rem;
      white-space: nowrap;
      transition: all .15s;
      flex-shrink: 0;
      margin-left: 10px;
    }
    .copy-q-btn:hover { border-color: var(--accent); color: var(--accent); }
    .copy-q-btn.copied { border-color: #166534; color: #166534; background: #dcfce7; }
    @media print { .copy-q-btn { display: none; } }""" if show_copy else ""
    copy_script = """  <script>
  function rawTextOf(node) {
    if (node.nodeType === Node.TEXT_NODE) return node.textContent;
    if (node.dataset && node.dataset.mjxTexstring) return node.dataset.mjxTexstring;
    var mjx = node.querySelector && node.querySelector('[data-mjx-texstring]');
    if (mjx) {
      var tex = mjx.getAttribute('data-mjx-texstring');
      return node.classList && node.classList.contains('MJX-TEX') ? tex
           : (node.getAttribute('display') === 'true' ? '\\\\[' + tex + '\\\\]' : '$' + tex + '$');
    }
    var out = '';
    node.childNodes.forEach(function(c) { out += rawTextOf(c); });
    return out;
  }
  function copyRawBlock(btn, blockEl) {
    var text = rawTextOf(blockEl).trim();
    function flash() {
      var orig = btn.innerHTML;
      btn.innerHTML = '\\u2713';
      btn.classList.add('copied');
      setTimeout(function() { btn.innerHTML = orig; btn.classList.remove('copied'); }, 2000);
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(flash).catch(function() { fallbackCopy(text); flash(); });
    } else { fallbackCopy(text); flash(); }
  }
  function fallbackCopy(text) {
    var ta = document.createElement('textarea');
    ta.value = text; ta.style.cssText = 'position:fixed;opacity:0;top:0;left:0';
    document.body.appendChild(ta); ta.select(); document.execCommand('copy');
    document.body.removeChild(ta);
  }
  document.addEventListener('DOMContentLoaded', function() {
    function isNumbered(text) {
      return /^[0-9]+[.)][ \\t]/.test(text.trim()) || /^[0-9]+[.)]$/.test(text.trim());
    }
    function attachCopyButtons() {
      var main = document.querySelector('main');
      if (!main) return;
      var children = Array.from(main.children);
      children.forEach(function(el) {
        if (el.tagName !== 'H4' || !isNumbered(el.textContent)) return;
        var block = document.createElement('div');
        var sib = el.nextElementSibling;
        while (sib && sib.tagName !== 'HR' && !/^H[234]$/.test(sib.tagName)) {
          block.appendChild(sib.cloneNode(true));
          sib = sib.nextElementSibling;
        }
        var headingClone = el.cloneNode(true);
        block.insertBefore(headingClone, block.firstChild);
        var btn = document.createElement('button');
        btn.className = 'copy-q-btn';
        btn.innerHTML = '\\u{1F4CB}';
        btn.addEventListener('click', function() { copyRawBlock(btn, block); });
        var wrapper = document.createElement('div');
        wrapper.className = 'q-heading';
        while (el.firstChild) wrapper.appendChild(el.firstChild);
        wrapper.appendChild(btn);
        el.appendChild(wrapper);
      });
      children.forEach(function(el) {
        if (el.tagName !== 'P' || !isNumbered(el.textContent)) return;
        var pClone = el.cloneNode(true);
        var btn = document.createElement('button');
        btn.className = 'copy-q-btn';
        btn.innerHTML = '\\u{1F4CB}';
        btn.addEventListener('click', function() { copyRawBlock(btn, pClone); });
        el.appendChild(btn);
      });
    }
    if (window.MathJax && MathJax.startup) {
      MathJax.startup.promise.then(attachCopyButtons);
    } else {
      attachCopyButtons();
    }
  });
  </script>""" if show_copy else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{pdf_name} - {prompt_name}</title>
  <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
      }}
    }};
  </script>
  <script defer src="{MATHJAX_SCRIPT}"></script>
  <style>
    :root {{
      --bg: #f6f1e8;
      --paper: #fffdf8;
      --ink: #1d2833;
      --muted: #667784;
      --line: #dfd5c8;
      --accent: #0f6a73;
      --code: #f1ebe2;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #f4d7c4 0, transparent 24%),
        linear-gradient(180deg, #f8f3eb 0%, var(--bg) 100%);
    }}
    .page {{
      width: min(920px, calc(100vw - 32px));
      margin: 24px auto 48px;
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 20px;
      box-shadow: 0 16px 36px rgba(48, 36, 23, 0.08);
      overflow: hidden;
    }}
    header {{
      padding: 24px 28px 18px;
      border-bottom: 1px solid var(--line);
      background: linear-gradient(180deg, #fffaf3 0%, #fbf6ee 100%);
    }}
    header h1 {{
      margin: 0 0 8px;
      font-size: 2rem;
      line-height: 1.08;
    }}
    header p {{
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
    }}
    main {{
      padding: 24px 28px 32px;
    }}
    a {{ color: var(--accent); }}
    h2, h3, h4 {{
      color: #213647;
      margin-top: 1.25em;
      margin-bottom: 0.45em;
    }}
    p, li {{
      line-height: 1.7;
    }}
    ul {{
      padding-left: 24px;
    }}
    hr {{
      border: 0;
      border-top: 1px solid var(--line);
      margin: 22px 0;
    }}
    code {{
      background: var(--code);
      padding: 0.1em 0.35em;
      border-radius: 6px;
      font-size: 0.95em;
    }}
{copy_block}
  </style>
{copy_script}
</head>
<body>
  <article class="page">
    <header>
      <h1>{pdf_name}</h1>
      <p><strong>{prompt_name}</strong></p>
      {pdf_note}
    </header>
    <main>
      {rendered}
    </main>
  </article>
</body>
</html>
"""


def build_response_pdf(*, response_html_path: Path, response_pdf_path: Path, browser: Any | None = None) -> None:
    if browser is None:
        with sync_playwright() as playwright:
            owned_browser = playwright.chromium.launch(headless=True)
            try:
                render_response_pdf(
                    browser=owned_browser,
                    response_html_path=response_html_path,
                    response_pdf_path=response_pdf_path,
                )
            finally:
                owned_browser.close()
        return

    render_response_pdf(
        browser=browser,
        response_html_path=response_html_path,
        response_pdf_path=response_pdf_path,
    )


def render_response_pdf(*, browser: Any, response_html_path: Path, response_pdf_path: Path) -> None:
    page = browser.new_page()
    try:
        page.goto(response_html_path.resolve().as_uri(), wait_until="networkidle")
        try:
            page.wait_for_function("window.MathJax && window.MathJax.typesetPromise")
            page.evaluate("() => window.MathJax.typesetPromise()")
        except PlaywrightTimeoutError:
            pass
        page.pdf(
            path=str(response_pdf_path),
            format="Letter",
            print_background=True,
            margin={"top": "0.5in", "right": "0.5in", "bottom": "0.6in", "left": "0.5in"},
        )
    finally:
        page.close()


def markdown_to_html(markdown_text: str) -> str:
    lines = markdown_text.splitlines()
    parts: list[str] = []
    paragraph: list[str] = []
    in_list = False
    blockquote: list[str] = []

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

    def flush_blockquote() -> None:
        nonlocal blockquote
        if blockquote:
            parts.append(f"<blockquote><p>{render_inline(' '.join(blockquote).strip())}</p></blockquote>")
            blockquote = []

    for raw_line in lines:
        stripped = raw_line.strip()
        if not stripped:
            flush_paragraph()
            close_list()
            flush_blockquote()
            continue
        if re.fullmatch(r"(?:-{3,}|\*{3,})", stripped):
            flush_paragraph()
            close_list()
            flush_blockquote()
            parts.append("<hr>")
            continue
        heading_match = re.match(r"^(#{1,4})\s+(.*)$", stripped)
        if heading_match:
            flush_paragraph()
            close_list()
            flush_blockquote()
            level = min(len(heading_match.group(1)) + 1, 4)
            parts.append(f"<h{level}>{render_inline(heading_match.group(2))}</h{level}>")
            continue
        if stripped.startswith(("- ", "* ")):
            flush_paragraph()
            flush_blockquote()
            if not in_list:
                parts.append("<ul>")
                in_list = True
            parts.append(f"<li>{render_inline(stripped[2:].strip())}</li>")
            continue
        if stripped.startswith(">"):
            flush_paragraph()
            close_list()
            blockquote.append(stripped[1:].strip())
            continue
        flush_blockquote()
        close_list()
        paragraph.append(stripped)

    flush_paragraph()
    close_list()
    flush_blockquote()
    return "\n".join(parts)


def render_inline(text: str) -> str:
    escaped = html_escape(text)
    math_tokens: list[str] = []

    def replace_math(match: re.Match[str]) -> str:
        math_tokens.append(match.group(0))
        return f"@@MATH{len(math_tokens) - 1}@@"

    escaped = _MATH_PATTERN.sub(replace_math, escaped)
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
    for index, token in enumerate(math_tokens):
        escaped = escaped.replace(f"@@MATH{index}@@", token)
    return escaped


_MATH_PATTERN = re.compile(
    r"(\\\[(?:.*?)\\\]|\\\((?:.*?)\\\)|\$\$(?:.*?)\$\$|(?<!\\)\$(?:\\.|[^$\n])+\$)",
    flags=re.DOTALL,
)


def pretty_title(display_name: str) -> str:
    cleaned = display_name.removesuffix(".pdf").replace(".docx", "")
    cleaned = re.sub(r"\s+\(\d+\)$", "", cleaned)
    cleaned = cleaned.replace("_", " ")
    return cleaned


def response_document_title(display_name: str) -> str:
    match = re.search(r"chp[.\s]+(\d+(?:\.\d+)?(?:\s*&\s*\d+(?:\.\d+)?)*)", display_name.lower())
    if match:
        chapter = re.sub(r"\s+", " ", match.group(1).strip())
        return f"Algebra II with Trigonometry Chapter {chapter}"
    return pretty_title(display_name)


def html_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def slugify(value: str) -> str:
    lowered = value.lower().strip()
    return re.sub(r"[^a-z0-9]+", "-", lowered).strip("-") or "document"
