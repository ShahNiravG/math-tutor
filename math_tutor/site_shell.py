"""Shared site shell rendering for generated tutoring pages."""

from __future__ import annotations

import html
from typing import Callable

from math_tutor.response_artifacts import MATHJAX_SCRIPT
from math_tutor.site_navigation import render_sidebar_html
from math_tutor.site_models import DocumentRecord
from math_tutor.site_theme import COPY_PROMPT_SCRIPT, SITE_PAGE_STYLES


def render_page_shell(
    *,
    title: str,
    records: list[DocumentRecord],
    active_record: DocumentRecord | None,
    body_html: str,
    total_prompt_outputs: int,
    generated_at: str,
    base_path: str,
    site_page_href: Callable[[str, str], str],
    page_kind: str = "record",
) -> str:
    del total_prompt_outputs, generated_at

    page_class = "page-home" if page_kind == "home" else "page-doc"
    sidebar_html = render_sidebar_html(
        records=records,
        active_record=active_record,
        base_path=base_path,
        site_page_href=site_page_href,
        page_kind=page_kind,
    )

    shell_html = f"""
  <div class="page {page_class}">
    {sidebar_html}
    <main class="main">
      {body_html}
    </main>
  </div>
    """ if page_kind not in {"home", "live-tutor", "record"} else f"""
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
{SITE_PAGE_STYLES}
  </style>
</head>
<body>
{shell_html}
  <script>
{COPY_PROMPT_SCRIPT}
  </script>
</body>
</html>
"""
