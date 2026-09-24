"""External AI challenge cards for narrowly approved course chapters."""

from __future__ import annotations

import html
from dataclasses import dataclass
from urllib.parse import urlparse

from math_tutor.calculus_chapters import (
    CalculusChapterManifest,
    get_calculus_chapter_manifest,
    validate_calculus_chapter_manifest,
)


@dataclass(frozen=True)
class AIChallengeProvider:
    provider_id: str
    label: str
    url: str


AI_CHALLENGE_PROVIDERS: tuple[AIChallengeProvider, ...] = (
    AIChallengeProvider("gemini", "Open Gemini", "https://gemini.google.com/app"),
    AIChallengeProvider("chatgpt", "Open ChatGPT", "https://chatgpt.com/"),
)

_ALLOWED_PROVIDER_TARGETS = {
    ("https", "gemini.google.com", "/app"),
    ("https", "chatgpt.com", "/"),
}

_SHARED_CHALLENGE_INSTRUCTIONS = """You are running a private AP Calculus AB-style practice challenge for one student.

Create and administer exactly 10 original multiple-choice questions for Chapter 2: Limits and Derivatives.

Allowed topics:
- 2.1 tangent and velocity problems
- 2.2 the limit of a function
- 2.3 calculating limits using the limit laws
- 2.5 continuity
- 2.6 infinite limits, limits at infinity, and horizontal asymptotes
- 2.7 derivatives and rates of change
- 2.8 introductory derivative-as-a-function concepts only

Do not test the formal epsilon-delta definition in section 2.4. Do not introduce product, quotient, or chain rules; implicit differentiation; related rates; optimization; integration; differential equations; or later AP Calculus topics.

Create every question from first principles. Do not quote, reproduce, paraphrase, imitate, or transform an actual College Board, AP Classroom, Bluebook, textbook, Khan Academy, or other published question. Describe this only as original AP Calculus AB-style practice.

Use the strongest reasoning model available in this account. Before presenting each question, privately solve it, verify all domain and endpoint conditions, verify that exactly one option is correct, and discard any ambiguous draft or draft with equivalent choices.

Ask one question at a time with exactly four choices labeled A through D. Do not reveal the answer before the student responds. After each response, say whether it is correct, give a concise but complete explanation, explain the likely misconception when incorrect, update the score, and then ask the next question. Use exact values unless approximation and rounding are explicitly requested. State every necessary domain, interval, unit, and assumption. Do not require an image or unstated graph. Do not repeat the same problem structure with only different numbers.

After question 10, show the score out of 10, percentage, performance by topic, and a short list of topics to review. Begin immediately with: "Chapter 2 Challenge — Question 1 of 10"."""

MEDIUM_CHALLENGE_PROMPT = f"""{_SHARED_CHALLENGE_INSTRUCTIONS}

Difficulty: MEDIUM.
Use a balanced mix of direct interpretation, foundational conceptual checks, standard representations, and one- or two-step calculations. Keep algebra clean and avoid trick wording. A prepared student who understands the chapter fundamentals should be able to solve each problem in roughly two to four minutes."""

HARD_CHALLENGE_PROMPT = f"""{_SHARED_CHALLENGE_INSTRUCTIONS}

Difficulty: HARD.
Use multi-step reasoning, connections among verbal, numerical, graphical descriptions expressed in words, and symbolic representations, plus meaningful domain, endpoint, one-sided-limit, and infinite-limit subtleties. Use plausible misconception-based distractors. Stay strictly within the allowed Chapter 2 scope; do not make a question hard by introducing a later calculus topic. A strong student should need careful reasoning, not obscure tricks."""


def build_ai_challenge_prompts(manifest: CalculusChapterManifest) -> tuple[str, str]:
    validate_calculus_chapter_manifest(manifest)
    allowed_topics = "\n".join(
        f"- {section.section_id}: {section.title}"
        + (f" ({section.challenge_note})" if section.challenge_status == "limited" else "")
        for section in manifest.sections
        if section.challenge_status != "excluded"
    )
    restrictions = " ".join(
        section.challenge_note or ""
        for section in manifest.sections
        if section.challenge_status in {"limited", "excluded"}
    ).strip()
    shared = f"""You are running a private AP Calculus AB-style practice challenge for one student.

Create and administer exactly 10 original multiple-choice questions for Chapter {manifest.chapter}: {manifest.title}.

Allowed topics:
{allowed_topics}

{restrictions} Do not introduce topics outside this reviewed chapter scope or later AP Calculus topics.

Create every question from first principles. Do not quote, reproduce, paraphrase, imitate, or transform an actual College Board, AP Classroom, Bluebook, textbook, Khan Academy, or other published question. Describe this only as original AP Calculus AB-style practice.

Use the strongest reasoning model available in this account. Before presenting each question, privately solve it, verify all domain and endpoint conditions, verify that exactly one option is correct, and discard any ambiguous draft or draft with equivalent choices.

Ask one question at a time with exactly four choices labeled A through D. Do not reveal the answer before the student responds. After each response, say whether it is correct, give a concise but complete explanation, explain the likely misconception when incorrect, update the score, and then ask the next question. Use exact values unless approximation and rounding are explicitly requested. State every necessary domain, interval, unit, and assumption. Do not require an image or unstated graph. Do not repeat the same problem structure with only different numbers.

After question 10, show the score out of 10, percentage, performance by topic, and a short list of topics to review. Begin immediately with: "Chapter {manifest.chapter} Challenge — Question 1 of 10"."""
    medium = f"""{shared}

Difficulty: MEDIUM.
Use a balanced mix of direct interpretation, foundational conceptual checks, standard representations, and one- or two-step calculations. Keep algebra clean and avoid trick wording. A prepared student who understands the chapter fundamentals should be able to solve each problem in roughly two to four minutes."""
    hard = f"""{shared}

Difficulty: HARD.
Use multi-step reasoning, connections among verbal, numerical, graphical descriptions expressed in words, and symbolic representations, plus meaningful domain and endpoint subtleties. Use plausible misconception-based distractors. Stay strictly within the reviewed chapter scope; do not make a question hard by introducing a later calculus topic. A strong student should need careful reasoning, not obscure tricks."""
    return medium, hard


def has_ai_challenge(*, course_id: str | None, chapter: str | None) -> bool:
    if course_id is None or chapter is None:
        return False
    return get_calculus_chapter_manifest(course_id, chapter) is not None


def _validate_provider(provider: AIChallengeProvider) -> None:
    parsed = urlparse(provider.url)
    if (parsed.scheme, parsed.hostname, parsed.path) not in _ALLOWED_PROVIDER_TARGETS:
        raise ValueError(f"Unsafe AI challenge provider URL: {provider.url}")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(f"AI challenge provider URL must not contain credentials or parameters: {provider.url}")


def render_ai_challenge_section(*, course_id: str | None, chapter: str | None) -> str:
    if course_id is None or chapter is None:
        return ""
    manifest = get_calculus_chapter_manifest(course_id, chapter)
    if manifest is None:
        return ""
    medium_prompt, hard_prompt = build_ai_challenge_prompts(manifest)

    cards = (
        (
            "medium",
            "Medium Challenge",
            "Build confidence with clear conceptual checks and focused one- or two-step problems.",
            "Medium",
            medium_prompt,
        ),
        (
            "hard",
            "Hard Challenge",
            "Stretch your reasoning with multi-step questions and subtle domain or limit behavior.",
            "Hard",
            hard_prompt,
        ),
    )
    rendered_cards: list[str] = []
    for challenge_id, title, description, difficulty, prompt in cards:
        prompt_id = f"ai-challenge-prompt-{challenge_id}"
        status_id = f"ai-challenge-status-{challenge_id}"
        provider_links: list[str] = []
        for provider in AI_CHALLENGE_PROVIDERS:
            _validate_provider(provider)
            provider_links.append(
                f'<a class="chapter-challenge-action ai-challenge-provider" '
                f'href="{html.escape(provider.url, quote=True)}" target="_blank" '
                f'rel="noopener noreferrer" data-prompt-target="{prompt_id}" '
                f'data-status-target="{status_id}">{html.escape(provider.label)}</a>'
            )
        rendered_cards.append(
            f"""
          <article class="chapter-challenge-option ai-challenge-option ai-challenge-{challenge_id}">
            <div class="chapter-challenge-row">
              <div class="chapter-challenge-title">{html.escape(title)}</div>
            </div>
            <div class="chapter-challenge-meta">
              <span class="chapter-challenge-tag chapter-challenge-tag-model">{difficulty}</span>
              <span class="chapter-challenge-tag chapter-challenge-tag-model">10 questions</span>
              <span class="chapter-challenge-tag chapter-challenge-tag-model">External AI</span>
            </div>
            <p>{html.escape(description)}</p>
            <div class="button-row ai-challenge-actions">{''.join(provider_links)}</div>
            <p class="ai-challenge-status" id="{status_id}" role="status" aria-live="polite"></p>
            <details class="ai-challenge-fallback">
              <summary>View or copy the prompt manually</summary>
              <textarea id="{prompt_id}" rows="10" readonly>{html.escape(prompt)}</textarea>
              <button class="chapter-challenge-action ai-challenge-copy" type="button" data-copy-target="{prompt_id}" data-status-target="{status_id}">Copy prompt</button>
            </details>
          </article>
        """
        )

    return f"""
      <section class="content-card section-card section-surface" id="ai-challenge">
        <div class="section-head">
          <div>
            <span class="eyebrow">AI Challenge</span>
            <h3>Choose your difficulty</h3>
          </div>
        </div>
        <p class="page-intro">Choose a provider. Math Delight copies the selected prompt and opens the provider in a new tab; paste the prompt there to begin.</p>
        <div class="prompt-card chapter-challenge-card chapter-challenge-card-staging ai-challenge-card">
          <div class="chapter-challenge-options">{''.join(rendered_cards)}</div>
          <p class="chapter-challenge-small">Results are not saved in Math Delight. Questions and grading are generated by the external AI provider.</p>
        </div>
        <script>
        (function () {{
          function promptFor(id) {{
            const field = document.getElementById(id);
            return field ? field.value : '';
          }}

          function setStatus(id, message) {{
            const status = document.getElementById(id);
            if (status) status.textContent = message;
          }}

          function copyPrompt(promptId, statusId) {{
            const text = promptFor(promptId);
            if (!text) return Promise.reject(new Error('Prompt unavailable'));
            if (navigator.clipboard && window.isSecureContext) {{
              return navigator.clipboard.writeText(text);
            }}
            const field = document.getElementById(promptId);
            if (!field) return Promise.reject(new Error('Prompt unavailable'));
            field.focus();
            field.select();
            return document.execCommand('copy')
              ? Promise.resolve()
              : Promise.reject(new Error('Clipboard unavailable'));
          }}

          document.querySelectorAll('.ai-challenge-provider').forEach(function (link) {{
            link.addEventListener('click', function () {{
              copyPrompt(link.dataset.promptTarget, link.dataset.statusTarget).then(function () {{
                setStatus(link.dataset.statusTarget, 'Prompt copied — paste it into the new tab and press Enter.');
              }}).catch(function () {{
                const field = document.getElementById(link.dataset.promptTarget);
                const details = field ? field.closest('details') : null;
                if (details) details.open = true;
                setStatus(link.dataset.statusTarget, 'Automatic copy was blocked. Copy the prompt shown below, then paste it into the new tab.');
              }});
            }});
          }});

          document.querySelectorAll('.ai-challenge-copy').forEach(function (button) {{
            button.addEventListener('click', function () {{
              copyPrompt(button.dataset.copyTarget, button.dataset.statusTarget).then(function () {{
                setStatus(button.dataset.statusTarget, 'Prompt copied — paste it into Gemini or ChatGPT and press Enter.');
              }}).catch(function () {{
                setStatus(button.dataset.statusTarget, 'Copy was blocked. Select the prompt text and copy it manually.');
              }});
            }});
          }});
        }})();
        </script>
      </section>
    """


for _provider in AI_CHALLENGE_PROVIDERS:
    _validate_provider(_provider)
