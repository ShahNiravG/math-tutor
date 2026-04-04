"""Prompt catalog and selection rules for tutoring artifact generation."""

from __future__ import annotations

from dataclasses import dataclass


DEFAULT_MODEL = "gpt-5.4"


@dataclass(frozen=True)
class PromptSpec:
    slug: str
    title: str
    text: str
    source_prompt_slug: str | None = None
    source_placeholder: str = "{{previous_output}}"
    include_source_pdf_link: bool = True
    generate_response_pdf: bool = True
    model: str | None = None
    reasoning_effort: str | None = None
    generate: bool = True
    use_google_search: bool = False
    assignment_only: bool = False
    required_filename_substrings: tuple[str, ...] = ()
    explicit_only: bool = False


@dataclass(frozen=True)
class PromptTemplate:
    slug: str
    title: str
    text: str
    source_template_slug: str | None = None
    include_source_pdf_link: bool = True
    generate_response_pdf: bool = True
    slug_suffix: str = ""
    generate_models: tuple[str, ...] | None = None
    model: str | None = None
    assignment_only: bool = False
    required_filename_substrings: tuple[str, ...] = ()
    explicit_only: bool = False


@dataclass(frozen=True)
class ModelConfig:
    slug: str
    label: str
    model: str


MODEL_CONFIGS: tuple[ModelConfig, ...] = (
    ModelConfig(slug="", label="", model=DEFAULT_MODEL),
    ModelConfig(slug="gpt5", label="GPT-5.4", model="gpt-5.4"),
    ModelConfig(slug="gemini", label="Gemini", model="gemini-3.1-pro-preview"),
)

PROMPT_TEMPLATES: tuple[PromptTemplate, ...] = (
    PromptTemplate(
        slug="study-guide",
        title="Study Guide",
        text="""You are a careful math tutor.

Read the attached PDF and produce the following sections using these exact headings:

## Title
Provide a concise student-friendly chapter title in 3 to 10 words. Use the math topic name only. Do not repeat the chapter number in the title.

## Short Summary
Write a short summary of the document.

## Core Definitions, Theorems, and Formulas
List the core definitions, theorems, and formulas.

## Study Guide
Write a worked study guide that explains the important ideas step by step.

## Practice Problems
Give five practice problems with answers, based only on the document.

## Assumptions or Ambiguities
List any assumptions or ambiguities you had to resolve.

Keep the response self-contained and preserve those exact section headings.
""",
        generate_models=("",),
    ),
    PromptTemplate(
        slug="auto-grading-assignment",
        title="Auto Grading Assignment",
        text="""Role: You are an expert academic grader. Since no answer key is provided, you must first solve each problem independently to establish the correct answers before grading the student's work.

Grading Rubric:
- Standard unit: assign 1 point per problem.
- Sub-problems: treat every sub-part (for example a, b, i, ii) as an individual 1-point item.
- Final answers: the student has placed a box around their final answers. Prioritize these boxed values for the final result.
- Partial credit:
  - 1.0 point: correct boxed answer with supporting work.
  - 0.5 points: incorrect boxed answer, but the work shows the correct setup or only a minor carry-over error.
  - 0 points: incorrect answer with no work or fundamentally wrong logic.

Task Instructions:
1. Solve: for every problem identified in the PDF, show your own brief step-by-step solution first.
2. Evaluate: compare your solution to the student's boxed answer and their shown work.
3. Correct: if the student is wrong, clearly explain the error in their logic or calculation.

Output Format:
Start with this exact summary block at the top of the response:

Final Summary:

Final Score: [Sum of points] / [Total possible points]

Total Correct Answers: [Count of fully correct items] / [Total items]

Questions Less Than Perfect: [Comma-separated list of question numbers that received less than 1.0 point. If none, write "None".]

Then, for each question, use this exact structure:

[Question Number]

AI Solution: [Briefly show the correct steps and answer]

Student Result: [Correct/Incorrect/Partial] - [Points]/1

Feedback: [Brief explanation of errors found]
""",
        model="gemini-3.1-pro-preview",
        assignment_only=True,
        required_filename_substrings=("work",),
        explicit_only=True,
        generate_models=("",),
    ),
    PromptTemplate(
        slug="inspiring-videos",
        title="Inspiring Videos",
        text="""I have a 14-year-old student studying the math topics in the attached PDF.

For the topics in the PDF, recommend exactly 2 highly engaging and visually intuitive YouTube videos from reputable math creators that inspire curiosity rather than focus on procedural problem solving.

Requirements:
1. Prefer videos that build deep conceptual understanding, such as geometric or visual intuition.
2. Keep the recommendations appropriate for a motivated beginner.
3. Avoid overly technical, competition-focused, or Olympiad-level content.
4. Use grounded web search to find the exact public YouTube video page.
5. Provide a direct, working YouTube watch URL for each recommendation.
6. Do not invent or guess URLs. Only include a URL if you found that exact video page.
7. Prefer standard watch links like https://www.youtube.com/watch?v=... over channel or search pages.
8. For each recommendation, briefly explain why it is inspiring and why it matches the topics in the PDF.
9. If the PDF spans several distinct topics, choose the 2 videos that best cover the most central ideas.

Format the response exactly as:
- Title: ...
- Creator: ...
- URL: https://www.youtube.com/watch?v=...
- Why it inspires: ...
- Topics matched: ...

Output only the two recommendations.
""",
        include_source_pdf_link=False,
        generate_response_pdf=False,
        generate_models=("", "gemini"),
    ),
    PromptTemplate(
        slug="mental-math",
        title="Mental Math",
        text=(
            "Generate 10 mental math questions based on this math pdf. "
            "These question should be answerable without paper and pencil. "
            "The questions should test the understanding of the core concepts. "
            "Give only the questions, with short titles if helpful."
        ),
        generate_models=("gpt5", "gemini"),
    ),
    PromptTemplate(
        slug="mental-math-mcq",
        title="Mental Math MCQ",
        text="""\
Below are mental math questions on a math topic. For each question, provide exactly 4 \
multiple-choice options (A, B, C, D). One must be the mathematically correct answer; \
the other three must be plausible but incorrect — use common errors such as sign mistakes, \
degree/radian confusion, off-by-one errors, or arithmetic slips.

Rules:
- Options must be concise: a single number, fraction, expression, or short phrase.
- The correct answer must be verified.
- Distractors must reflect realistic student mistakes, not random values.
- Randomly vary which letter (A/B/C/D) holds the correct answer across questions.
- Number the blocks to match the question numbers in the input.
- Output ONLY the answer blocks below — no explanations, no restating questions, no extra text.

Format (one block per question):

1.
(A) ...
(B) ...
(C) ...
(D) ...
Answer: [letter]

2.
...

Here are the questions:

{{previous_output}}
""",
        source_template_slug="mental-math",
        slug_suffix="mcq",
        generate_models=("gpt5", "gemini"),
    ),
    PromptTemplate(
        slug="olympiad-problems",
        title="Olympiad Problems",
        text="""You are designing elegant Olympiad-style mental math problems from the attached PDF.

Generate 6 challenging problems inspired by the core ideas in the PDF.

Requirements:
1. The problems should be harder than the normal mental math set.
2. They should reward insight, pattern recognition, symmetry, invariants, estimation, or clever algebraic/trigonometric manipulation.
3. They should still be solvable mentally or with very light scratch work.
4. Do not provide solutions yet.
5. Keep the statements concise and polished.
6. Output only a numbered list of problems under the heading "Problems".
""",
        generate_models=("gpt5", "gemini"),
    ),
    PromptTemplate(
        slug="olympiad-solutions",
        title="Olympiad Solutions",
        text="""You are writing elegant Olympiad-style solutions.

Use the exact problem list below and provide step-by-step solutions for each problem.

Requirements:
1. Preserve the original numbering and wording of the problems.
2. Give concise but rigorous reasoning.
3. Prefer elegant observations over brute force.
4. Make each solution self-contained.
5. Format the response under the heading "Solutions".

Problem list to solve:
{{previous_output}}
""",
        source_template_slug="olympiad-problems",
        generate_models=("gpt5", "gemini"),
    ),
    PromptTemplate(
        slug="olympiad-problems-mcq",
        title="Olympiad Problems MCQ",
        text="""\
Below are Olympiad-style math problems. For each problem, provide exactly 4 multiple-choice \
options (A, B, C, D). One must be the mathematically correct answer; the other three should \
be plausible — use values that arise from partial progress, sign errors, missing factors, \
or near-correct approaches.

Rules:
- Options must be concise: a single value, expression, angle measure, or short result. \
LaTeX is fine for mathematical expressions.
- The correct answer must be mathematically verified.
- Distractors should reflect genuine mathematical mistakes, not arbitrary values.
- Randomly vary which letter (A/B/C/D) holds the correct answer across problems.
- Number the blocks to match the problem numbers in the input.
- Output ONLY the answer blocks below — no explanations, no restating problems, no extra text.

Format (one block per problem):

1.
(A) ...
(B) ...
(C) ...
(D) ...
Answer: [letter]

2.
...

Here are the problems:

{{previous_output}}
""",
        source_template_slug="olympiad-problems",
        slug_suffix="mcq",
        generate_models=("gpt5", "gemini"),
    ),
)


def build_prompt_spec(template: PromptTemplate, model_config: ModelConfig) -> PromptSpec:
    if template.slug_suffix and model_config.slug:
        base = template.slug[: -(len(template.slug_suffix) + 1)]
        slug = f"{base}-{model_config.slug}-{template.slug_suffix}"
    elif model_config.slug:
        slug = f"{template.slug}-{model_config.slug}"
    else:
        slug = template.slug

    title = template.title if not model_config.label else f"{template.title} ({model_config.label})"
    source_slug = None
    if template.source_template_slug:
        source_slug = (
            template.source_template_slug
            if not model_config.slug
            else f"{template.source_template_slug}-{model_config.slug}"
        )
    generate = template.generate_models is None or model_config.slug in template.generate_models
    return PromptSpec(
        slug=slug,
        title=title,
        text=template.text,
        source_prompt_slug=source_slug,
        include_source_pdf_link=template.include_source_pdf_link,
        generate_response_pdf=template.generate_response_pdf,
        model=template.model if template.model else (model_config.model if model_config.slug else None),
        generate=generate,
        use_google_search=(template.slug == "inspiring-videos" and model_config.slug == "gemini"),
        assignment_only=template.assignment_only,
        required_filename_substrings=template.required_filename_substrings,
        explicit_only=template.explicit_only,
    )


def order_prompts(prompts: tuple[PromptSpec, ...]) -> tuple[PromptSpec, ...]:
    by_slug = {prompt.slug: prompt for prompt in prompts}
    ordered: list[PromptSpec] = []
    seen: set[str] = set()

    def add(slug: str) -> None:
        if slug in seen:
            return
        seen.add(slug)
        ordered.append(by_slug[slug])
        for prompt in prompts:
            if prompt.source_prompt_slug == slug:
                add(prompt.slug)

    for prompt in prompts:
        if prompt.source_prompt_slug is None:
            add(prompt.slug)
    return tuple(ordered)


RAW_PROMPTS: tuple[PromptSpec, ...] = tuple(
    build_prompt_spec(template, model_config)
    for template in PROMPT_TEMPLATES
    for model_config in MODEL_CONFIGS
)
PROMPTS: tuple[PromptSpec, ...] = order_prompts(RAW_PROMPTS)
PROMPTS_BY_SLUG: dict[str, PromptSpec] = {prompt.slug: prompt for prompt in PROMPTS}
STUDY_GUIDE_PROMPT = PROMPTS_BY_SLUG["study-guide"]
CLASS_NOTE_PRINT_SLUG = "class-note"
ASSIGNMENT_PRINT_SLUG = "assignment"
PRINTABLE_PROMPT_SLUGS: tuple[str, ...] = (
    CLASS_NOTE_PRINT_SLUG,
    ASSIGNMENT_PRINT_SLUG,
    *(prompt.slug for prompt in PROMPTS),
)


def prompt_title_from_slug(prompt_slug: str) -> str:
    prompt_spec = PROMPTS_BY_SLUG.get(prompt_slug)
    if prompt_spec is not None:
        return prompt_spec.title
    return prompt_slug.replace("-", " ").title()


def resolve_selected_prompts(prompt_slugs: list[str] | None) -> tuple[PromptSpec, ...]:
    if not prompt_slugs:
        return tuple(prompt for prompt in PROMPTS if not prompt.explicit_only)

    selected: list[PromptSpec] = []
    seen: set[str] = set()

    def add(slug: str) -> None:
        if slug in seen:
            return
        prompt_spec = PROMPTS_BY_SLUG[slug]
        selected.append(prompt_spec)
        seen.add(slug)
        for prompt in PROMPTS:
            if prompt.source_prompt_slug == slug:
                add(prompt.slug)

    for prompt_slug in prompt_slugs:
        add(prompt_slug)

    return tuple(selected)


def resolve_prompt_slug_set(prompt_slugs: list[str] | None) -> set[str]:
    if not prompt_slugs:
        return set()
    return set(prompt_slugs)
