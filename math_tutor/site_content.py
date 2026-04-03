"""Shared study-guide content extraction and rendering helpers for site pages."""

from __future__ import annotations

import html
import re

from math_tutor.response_artifacts import pretty_title, render_inline
from math_tutor.site_cards import document_label
from math_tutor.site_models import DocumentRecord


def build_guided_learning_prompt(record: DocumentRecord) -> str:
    for prompt_output in record.prompt_outputs:
        if prompt_output.slug != "study-guide":
            continue
        html_summary = _extract_summary_from_response_html(prompt_output.response_html_path)
        if html_summary:
            return html_summary
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
        html_summary = _extract_summary_from_response_html(prompt_output.response_html_path)
        if html_summary:
            return html_summary
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
      <section class="guided-card summary-card">
        <h3>Summary</h3>
        <div class="card-summary">
          {summary_html}
        </div>
      </section>
    """


def extract_record_summary_html(record: DocumentRecord) -> str:
    for prompt_output in record.prompt_outputs:
        if prompt_output.slug != "study-guide":
            continue
        if prompt_output.response_html_path and prompt_output.response_html_path.exists():
            content = prompt_output.response_html_path.read_text(encoding="utf-8")
            match = re.search(
                r'<h[2-4][^>]*>.*?[Ss]hort\s+[Ss]ummary.*?</h[2-4]>(.*?)(?=<h[2-4]|<hr\s*/?>)',
                content,
                re.DOTALL,
            )
            if match:
                return match.group(1).strip()
        if prompt_output.response_markdown:
            return extract_study_guide_summary_html(prompt_output.response_markdown, include_heading=False)
    return ""


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
            if "short summary" in normalized and re.match(r"^#{1,6}\s*", stripped):
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


def _extract_summary_from_response_html(response_html_path) -> str:
    if not response_html_path or not response_html_path.exists():
        return ""
    content = response_html_path.read_text(encoding="utf-8")
    match = re.search(
        r'<h[2-4][^>]*>.*?[Ss]hort\s+[Ss]ummary.*?</h[2-4]>(.*?)(?=<h[2-4]|<hr\s*/?>)',
        content,
        re.DOTALL,
    )
    if not match:
        return ""
    raw_html = match.group(1).strip()
    plain = re.sub(r'<li[^>]*>(.*?)</li>', lambda mo: f"- {mo.group(1).strip()}\n", raw_html, flags=re.DOTALL)
    plain = re.sub(r"<[^>]+>", " ", plain)
    plain = html.unescape(plain)
    plain = re.sub(r"[ \t]+", " ", plain)
    plain = re.sub(r"\n{3,}", "\n\n", plain).strip()
    if not plain:
        return ""
    return normalize_summary_text(plain)
