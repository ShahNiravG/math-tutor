"""Chapter challenge card rendering for generated document pages."""

from __future__ import annotations

import html
import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable
from urllib.parse import quote

from math_tutor.chaptering import parse_display_name_chapter
from math_tutor.challenge_builder import CHALLENGES_SRC_DIR
from math_tutor.site_cards import record_page_filename
from math_tutor.site_models import DocumentRecord


def render_chapter_challenge_card(
    record: DocumentRecord,
    base_path: str,
    site_page_href: Callable[[str, str], str],
    experience_variant: str = "default",
) -> str:
    chapter = parse_display_name_chapter(record.display_name)
    if not chapter:
        return ""
    chapter_exam_index = load_chapter_exam_index().get(chapter, [])
    if not chapter_exam_index:
        return ""
    return_target = (
        quote(site_page_href(record_page_filename(record), base_path), safe="")
        if base_path
        else f"../{record_page_filename(record)}"
    )
    return_label = quote("Back to Chapter", safe="")
    reports_href = f"{base_path}challenges/reports.php" if base_path else "challenges/reports.php"
    completed_href = f"{base_path}challenges/completed.php" if base_path else "challenges/completed.php"
    option_html_blocks: list[str] = []

    for exam in chapter_exam_index:
        exam_id = exam["id"]
        exam_href = (
            f"{base_path}challenges/exam.html?id={quote(exam_id, safe='')}&return={return_target}&return_label={return_label}"
            if base_path
            else f"challenges/exam.html?id={exam_id}&return=../{record_page_filename(record)}&return_label=Back%20to%20Chapter"
        )
        progress_href = (
            f"{base_path}challenges/get_progress.php?exam_id={quote(exam_id, safe='')}"
            if base_path
            else f"challenges/get_progress.php?exam_id={exam_id}"
        )
        is_mental_math = exam.get("challenge_type", "") == "mm"
        type_class = "chapter-challenge-tag-mm" if is_mental_math else "chapter-challenge-tag-op"
        action_class = "button-quick-practice" if is_mental_math else "button-olympiad"
        type_label = "Mental Math" if is_mental_math else "Olympiad"
        title = "Mental Math Challenge" if is_mental_math else "Olympiad Challenge"
        description = (
            "Practice fast, focused multiple-choice questions built from both Gemini and GPT-5.4 mental math sets."
            if is_mental_math
            else "Work through olympiad-style multiple-choice problems drawn from both Gemini and GPT-5.4 challenge sets."
        )
        models = " + ".join(exam.get("models", []))
        question_count = exam.get("question_count", 0)
        initial_status = (
            '<span class="chapter-challenge-status chapter-challenge-status-loading">Checking progress</span>'
            if experience_variant == "staging"
            else '<span class="chapter-challenge-status"></span>'
        )
        option_html_blocks.append(
            f"""
          <div class="chapter-challenge-option" data-challenge-exam="{html.escape(exam_id, quote=True)}" data-question-count="{question_count}" data-exam-href="{html.escape(exam_href, quote=True)}" data-progress-href="{html.escape(progress_href, quote=True)}">
            <div class="chapter-challenge-row">
              <div class="chapter-challenge-title">{title}</div>
              {initial_status}
            </div>
            <div class="chapter-challenge-meta">
              <span class="chapter-challenge-tag {type_class}">{type_label}</span>
              <span class="chapter-challenge-tag chapter-challenge-tag-model">{html.escape(models)}</span>
              <span class="chapter-challenge-tag chapter-challenge-tag-model">{question_count} questions</span>
            </div>
            <p>{html.escape(description)}</p>
            <div class="chapter-challenge-row">
              <div class="button-row">
                <a class="chapter-challenge-action {action_class}" href="{html.escape(exam_href, quote=True)}">Start Challenge</a>
              </div>
            </div>
          </div>
        """
        )

    return f"""
      <section class="prompt-card chapter-challenge-card{' chapter-challenge-card-staging' if experience_variant == 'staging' else ''}">
        <h3>Challenge Exams</h3>
        <p class="chapter-challenge-intro">{'Take this after review and practice. Challenge mode stays clean and assessment-focused for now.' if experience_variant == 'staging' else 'Choose a mental math or olympiad challenge and continue in the full challenge page.'}</p>
        <div class="chapter-challenge-options">
          {''.join(option_html_blocks)}
        </div>
        <script>
        (function () {{
          const SESSION_KEY = 'math_tutor_challenge_session';
          const reportsHref = {json.dumps(reports_href)};
          const completedHref = {json.dumps(completed_href)};
          const options = Array.from(document.querySelectorAll('[data-challenge-exam]'));

          function getLocalSession(examId) {{
            try {{
              const saved = JSON.parse(localStorage.getItem(SESSION_KEY) || 'null');
              return saved && saved.exam_id === examId ? saved : null;
            }} catch (e) {{
              return null;
            }}
          }}

          function answeredCount(progress, local) {{
            if (progress && typeof progress.answered_count === 'number') {{
              return progress.answered_count;
            }}
            if (local && local.answers) {{
              return Object.values(local.answers).filter(Boolean).length;
            }}
            return 0;
          }}

          function setStatus(el, text, className) {{
            if (!el) return;
            el.className = 'chapter-challenge-status chapter-challenge-tag ' + className;
            el.textContent = text;
          }}

          async function fetchJson(url) {{
            try {{
              const res = await fetch(url, {{cache: 'no-store'}});
              if (!res.ok) return null;
              return await res.json();
            }} catch (e) {{
              return null;
            }}
          }}

          Promise.all([
            fetchJson(completedHref),
            Promise.all(options.map(function (option) {{
              return fetchJson(option.getAttribute('data-progress-href'));
            }})),
          ]).then(function (results) {{
            const completedData = results[0] || {{}};
            const progressResults = results[1] || [];
            const completed = new Set(completedData.completed || []);

            options.forEach(function (option, index) {{
              const examId = option.getAttribute('data-challenge-exam');
              const questionCount = Number(option.getAttribute('data-question-count') || '0');
              const progressData = progressResults[index];
              const progress = progressData && progressData.progress ? progressData.progress : null;
              const local = getLocalSession(examId);
              const action = option.querySelector('.chapter-challenge-action');
              const status = option.querySelector('.chapter-challenge-status');
              const answered = answeredCount(progress, local);

              if (completed.has(examId)) {{
                setStatus(status, 'All answered', 'chapter-challenge-tag-done');
                if (action) {{
                  action.textContent = 'View Reports';
                  action.href = reportsHref;
                }}
                return;
              }}

              if (progress || local) {{
                setStatus(status, answered + '/' + questionCount + ' answered', 'chapter-challenge-tag-resume');
                if (action) {{
                  action.textContent = 'Resume Challenge';
                }}
                return;
              }}

              if (status) {{
                status.className = 'chapter-challenge-status';
                status.textContent = '';
              }}
              if (action) {{
                action.textContent = 'Start Challenge';
              }}
            }});
          }});
        }})();
        </script>
      </section>
    """


@lru_cache(maxsize=1)
def load_chapter_exam_index() -> dict[str, list[dict[str, Any]]]:
    chapter_json = CHALLENGES_SRC_DIR / "chapter_exams.json"
    if not chapter_json.exists():
        return {}
    payload = json.loads(chapter_json.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict[str, Any]]] = {}
    for exam in payload.get("exams", []):
        grouped.setdefault(exam.get("chapter", ""), []).append(
            {
                "id": exam.get("id", ""),
                "title": exam.get("title", ""),
                "chapter": exam.get("chapter", ""),
                "challenge_type": exam.get("challenge_type", ""),
                "question_count": len(exam.get("questions", [])),
                "models": sorted(
                    {
                        question.get("model_label", "")
                        for question in exam.get("questions", [])
                        if question.get("model_label")
                    }
                ),
            }
        )
    for exams in grouped.values():
        exams.sort(key=lambda item: (0 if item.get("challenge_type") == "mm" else 1, item.get("id", "")))
    return grouped
