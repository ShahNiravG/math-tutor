"""MCQ artifact path and HTML rendering helpers."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from math_tutor.response_artifacts import markdown_to_html


@dataclass(frozen=True)
class MCQOutputPaths:
    output_stem: str
    markdown_path: Path
    html_path: Path
    pdf_path: Path


def build_mcq_output_paths(*, source_md: Path, mcq_slug: str, responses_dir: Path) -> MCQOutputPaths:
    stem = source_md.stem
    base_stem = stem[: stem.rfind("__")]
    output_stem = base_stem + mcq_slug
    return MCQOutputPaths(
        output_stem=output_stem,
        markdown_path=responses_dir / f"{output_stem}.md",
        html_path=responses_dir / f"{output_stem}.html",
        pdf_path=responses_dir / f"{output_stem}.pdf",
    )


def build_mcq_html(stem: str, mcq_markdown: str) -> str:
    title = re.sub(r"^\d+_", "", stem)
    rendered = markdown_to_html(mcq_markdown)
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
    .q-row {{ display: flex; align-items: baseline; gap: 10px; }}
    .copy-q-btn {{
      appearance: none; border: 1px solid var(--line); background: rgba(255,255,255,.7);
      color: var(--muted); border-radius: 6px; cursor: pointer;
      padding: 2px 7px; font-size: .85rem;
      white-space: nowrap; transition: all .15s; flex-shrink: 0; margin-left: 10px;
    }}
    .copy-q-btn:hover {{ border-color: var(--accent); color: var(--accent); }}
    .copy-q-btn.copied {{ border-color: #166534; color: #166534; background: #dcfce7; }}
    @media print {{ .copy-q-btn {{ display: none; }} }}
  </style>
  <script>
  function rawTextOf(node) {{
    if (node.nodeType === Node.TEXT_NODE) return node.textContent;
    var mjx = node.querySelector && node.querySelector('[data-mjx-texstring]');
    if (mjx) {{
      var tex = mjx.getAttribute('data-mjx-texstring');
      return (node.getAttribute && node.getAttribute('display') === 'true') ? '\\\\[' + tex + '\\\\]' : '$' + tex + '$';
    }}
    var out = '';
    node.childNodes.forEach(function(c) {{ out += rawTextOf(c); }});
    return out;
  }}
  function copyText(btn, text) {{
    function flash() {{
      var orig = btn.innerHTML;
      btn.innerHTML = '\\u2713'; btn.classList.add('copied');
      setTimeout(function() {{ btn.innerHTML = orig; btn.classList.remove('copied'); }}, 2000);
    }}
    if (navigator.clipboard && navigator.clipboard.writeText) {{
      navigator.clipboard.writeText(text).then(flash).catch(function() {{ fallbackCopy(text); flash(); }});
    }} else {{ fallbackCopy(text); flash(); }}
  }}
  function fallbackCopy(text) {{
    var ta = document.createElement('textarea');
    ta.value = text; ta.style.cssText = 'position:fixed;opacity:0;top:0;left:0';
    document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
  }}
  document.addEventListener('DOMContentLoaded', function() {{
    function attach() {{
      document.querySelectorAll('main p').forEach(function(p) {{
        if (!/^[0-9]+[.]/.test(p.textContent.trim())) return;
        var btn = document.createElement('button');
        btn.className = 'copy-q-btn'; btn.innerHTML = '&#128203;';
        var pClone = p.cloneNode(true);
        btn.addEventListener('click', function() {{ copyText(btn, rawTextOf(pClone).trim()); }});
        var row = document.createElement('span');
        row.className = 'q-row';
        while (p.firstChild) row.appendChild(p.firstChild);
        row.appendChild(btn);
        p.appendChild(row);
      }});
    }}
    if (window.MathJax && MathJax.startup) {{ MathJax.startup.promise.then(attach); }}
    else {{ attach(); }}
  }});
  </script>
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
