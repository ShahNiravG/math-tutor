"""Shared site shell rendering for generated tutoring pages."""

from __future__ import annotations

import html
from typing import Callable

from math_tutor.response_artifacts import MATHJAX_SCRIPT
from math_tutor.site_cards import document_label, record_page_filename
from math_tutor.site_navigation import render_sidebar_html
from math_tutor.site_models import DocumentRecord
from math_tutor.site_theme import (
    COPY_PROMPT_SCRIPT,
    KATEX_AUTORENDER_SCRIPT,
    KATEX_AUTORENDER_SRC,
    KATEX_CSS_HREF,
    KATEX_JS_SRC,
    STAGING_SITE_SCRIPT,
    get_site_page_styles,
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
    site_page_href: Callable[[str, str], str],
    page_kind: str = "record",
    experience_variant: str = "default",
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

    body_classes = [f"page-kind-{page_kind}", f"experience-{experience_variant}"]
    body_attrs: list[str] = [f'class="{" ".join(body_classes)}"', f'data-page-kind="{html.escape(page_kind)}"']
    if active_record is not None:
        body_attrs.append(
            f'data-record-href="{html.escape(site_page_href(record_page_filename(active_record), base_path))}"'
        )
        body_attrs.append(f'data-record-title="{html.escape(document_label(active_record))}"')

    font_links = ""
    math_assets = f"""
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
    """
    math_render_script = ""
    if experience_variant == "staging":
        font_links = f"""
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="{html.escape(KATEX_CSS_HREF)}">
        """
        math_assets = f"""
  <script defer src="{html.escape(KATEX_JS_SRC)}"></script>
  <script defer src="{html.escape(KATEX_AUTORENDER_SRC)}"></script>
        """
        math_render_script = KATEX_AUTORENDER_SCRIPT + "\n" + STAGING_SITE_SCRIPT

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
{font_links}
{math_assets}
  <style>
{get_site_page_styles(experience_variant)}
  </style>
</head>
<body {' '.join(body_attrs)}>
{shell_html}
  <script>
{COPY_PROMPT_SCRIPT}
{math_render_script}
  </script>
</body>
</html>
"""
