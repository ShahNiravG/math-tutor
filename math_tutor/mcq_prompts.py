"""MCQ generation prompt contracts and source-file mappings."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MCQSourceConfig:
    source_suffix: str
    mcq_suffix: str
    provider: str
    prompt_type: str


SOURCE_CONFIGS = [
    MCQSourceConfig("__mental-math-gpt5.md", "__mental-math-gpt5-mcq", "gpt", "mental_math"),
    MCQSourceConfig("__mental-math-gemini.md", "__mental-math-gemini-mcq", "gemini", "mental_math"),
    MCQSourceConfig("__olympiad-problems-gpt5.md", "__olympiad-problems-gpt5-mcq", "gpt", "olympiad"),
    MCQSourceConfig("__olympiad-problems-gemini.md", "__olympiad-problems-gemini-mcq", "gemini", "olympiad"),
]

GPT_MODEL = "gpt-5.4"
GEMINI_MODEL = "gemini-3.1-pro-preview"

MENTAL_MATH_PROMPT = """\
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

{questions}
"""

OLYMPIAD_PROMPT = """\
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

{questions}
"""


def build_mcq_prompt(*, prompt_type: str, questions_text: str) -> str:
    template = MENTAL_MATH_PROMPT if prompt_type == "mental_math" else OLYMPIAD_PROMPT
    return template.format(questions=questions_text)
