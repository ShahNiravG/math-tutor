"""Question extraction and exam-catalog assembly for challenge generation."""

from __future__ import annotations

import json
import random
import re
from pathlib import Path

from math_tutor.amc10_scraper import _normalize_option_text
from math_tutor.chaptering import chapter_slug, chapter_sort_key, parse_response_stem_chapter


SHUFFLE_SEED = 42
MAX_EXAM_SIZE = 10
MAX_OP_PER_EXAM = 3
TARGET_MM_PER_EXAM = MAX_EXAM_SIZE - MAX_OP_PER_EXAM  # 7
CURATED_BANK_EXAM_SIZE = 5
# The internal "classic" slug refers to the AI-generated challenge bank shown in the UI.
CLASSIC_BANK_ID = "classic"
CLASSIC_BANK_TITLE = "AI-Generated"
SOURCE_SUFFIXES = [
    ("__mental-math-gpt5.md", "mm", "gpt54", "GPT-5.4", "__mental-math-gpt5-mcq.md"),
    ("__mental-math-gemini.md", "mm", "gem", "Gemini 3.1 Pro", "__mental-math-gemini-mcq.md"),
    ("__olympiad-problems-gpt5.md", "op", "gpt54", "GPT-5.4", "__olympiad-problems-gpt5-mcq.md"),
    ("__olympiad-problems-gemini.md", "op", "gem", "Gemini 3.1 Pro", "__olympiad-problems-gemini-mcq.md"),
]


def _candidate_mcq_paths(*, responses_dir: Path, base: str, mcq_suffix: str) -> list[Path]:
    candidates = [responses_dir / f"{base}{mcq_suffix}"]
    stem = Path(mcq_suffix).stem
    extension = Path(mcq_suffix).suffix
    if stem.endswith("-mcq"):
        candidates.append(responses_dir / f"{base}{stem}-{_model_suffix_for_mcq(stem)}{extension}")
    return candidates


def _model_suffix_for_mcq(stem: str) -> str:
    if stem.endswith("gpt5-mcq"):
        return "gpt5"
    if stem.endswith("gemini-mcq"):
        return "gemini"
    return ""


def _extract_numbered_questions(text: str) -> list[str]:
    matches = list(re.finditer(r"(?m)^(\d+)\.\s+", text))
    questions: list[str] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        question_text = text[start:end].strip()
        if question_text:
            questions.append(question_text)
    return questions


def _extract_bold_titled_questions(text: str) -> list[str]:
    matches = list(re.finditer(r"(?m)^\*\*([^*\n]+)\*\*\s*\n", text))
    questions: list[str] = []
    for i, match in enumerate(matches):
        title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            questions.append(f"**{title}**\n{body}")
    return questions


def _extract_from_file(path: Path) -> list[str]:
    text = path.read_text(encoding="utf-8")
    stem = path.stem
    if "__mental-math-gpt5" in stem:
        return _extract_numbered_questions(text)
    if "__mental-math-gemini" in stem:
        return _extract_bold_titled_questions(text)
    if "__olympiad-problems" in stem:
        text = re.sub(r"(?m)^#+\s*Problems\s*$", "", text)
        text = re.sub(r"(?m)^Problems\s*$", "", text)
        return _extract_numbered_questions(text)
    return []


def _parse_mcq_file(path: Path) -> dict[int, dict]:
    text = path.read_text(encoding="utf-8")
    result: dict[int, dict] = {}
    blocks = re.split(r"(?m)^(\d+)[.\s]*$", text)
    index = 1
    while index + 1 < len(blocks):
        question_number = int(blocks[index])
        block = blocks[index + 1]
        options = re.findall(r"^\(([A-D])\)\s*(.+)$", block, re.MULTILINE)
        answer_match = re.search(r"^Answer:\s*([A-D])", block, re.MULTILINE)
        if options and answer_match:
            result[question_number] = {
                "options": [f"({letter}) {option_text.strip()}" for letter, option_text in options],
                "correct": answer_match.group(1),
            }
        index += 2
    return result


def load_all_questions(output_dir: Path) -> list[dict]:
    responses_dir = output_dir / "responses"
    if not responses_dir.exists():
        return []
    questions: list[dict] = []
    for suffix, question_type, model, model_label, mcq_suffix in SOURCE_SUFFIXES:
        type_label = "Mental Math" if question_type == "mm" else "Olympiad Problems"
        for path in sorted(responses_dir.glob(f"*{suffix}")):
            chapter = parse_response_stem_chapter(path.stem)
            base = path.stem[: path.stem.rfind("__")]
            mcq_data: dict[int, dict] = {}
            for mcq_path in _candidate_mcq_paths(responses_dir=responses_dir, base=base, mcq_suffix=mcq_suffix):
                if mcq_path.exists():
                    mcq_data = _parse_mcq_file(mcq_path)
                    break
            for question_number, question_text in enumerate(_extract_from_file(path), 1):
                question_id = f"chp{chapter.replace(' & ', '-').replace('.', '')}-{question_type}-{model}-q{question_number}"
                question: dict = {
                    "id": question_id,
                    "chapter": parse_response_stem_chapter(path.stem),
                    "type": question_type,
                    "model": model,
                    "model_label": model_label,
                    "source_label": f"Chapter {chapter} / {type_label} / {model_label} / Q{question_number}",
                    "question_number": question_number,
                    "text": question_text,
                }
                if question_number in mcq_data:
                    question["options"] = mcq_data[question_number]["options"]
                    question["correct"] = mcq_data[question_number]["correct"]
                questions.append(question)
    return questions


def load_curated_question_sources(exams_dir: Path) -> list[dict]:
    if not exams_dir.exists():
        return []

    sources: list[dict] = []
    for path in sorted(exams_dir.glob("*.json"), key=_natural_path_sort_key):
        questions = _load_curated_questions(path)
        if not questions:
            continue
        bank_id, bank_title = _curated_bank_identity(path)
        source_stem = path.stem.lower()
        sources.append(
            {
                "source_stem": source_stem,
                "source_file": path.name,
                "exam_title": _humanize_bank_title(path.stem),
                "bank": bank_id,
                "bank_title": bank_title,
                "questions": questions,
            }
        )
    return sources


def load_explicit_curated_exams(exams_dir: Path) -> list[dict]:
    if not exams_dir.exists():
        return []

    exams: list[dict] = []
    for path in sorted(exams_dir.glob("*.json"), key=_natural_path_sort_key):
        payload = _load_explicit_curated_exam_payload(path)
        if payload is None:
            continue
        exams.append(payload)
    return exams


def load_curated_exam_banks(exams_dir: Path) -> list[dict]:
    exams: list[dict] = []
    questions_by_bank: dict[str, list[dict]] = {}
    bank_titles: dict[str, str] = {}

    for source in load_curated_question_sources(exams_dir):
        bank_id = source["bank"]
        bank_titles[bank_id] = source["bank_title"]
        questions_by_bank.setdefault(bank_id, []).extend(dict(question) for question in source["questions"])

    for bank_id in sorted(questions_by_bank):
        bank_title = bank_titles[bank_id]
        bank_questions = questions_by_bank[bank_id]
        for question_number, question in enumerate(bank_questions, 1):
            question["id"] = f"{bank_id}-q{question_number:03d}"
            question["type"] = bank_id
        for exam_number, start in enumerate(range(0, len(bank_questions), CURATED_BANK_EXAM_SIZE), 1):
            exam_questions = bank_questions[start : start + CURATED_BANK_EXAM_SIZE]
            exams.append(
                {
                    "id": f"{bank_id}-{exam_number:02d}",
                    "title": f"{bank_title} Exam {exam_number}",
                    "bank": bank_id,
                    "bank_title": bank_title,
                    "questions": exam_questions,
                }
            )
    exams.extend(load_explicit_curated_exams(exams_dir))
    return exams


def ensure_classic_bank_metadata(exams: list[dict]) -> list[dict]:
    normalized: list[dict] = []
    for exam in exams:
        normalized_exam = dict(exam)
        normalized_exam.setdefault("bank", CLASSIC_BANK_ID)
        if normalized_exam.get("bank") == CLASSIC_BANK_ID:
            normalized_exam["bank_title"] = CLASSIC_BANK_TITLE
        normalized.append(normalized_exam)
    return normalized


def _stratified_shuffle(questions: list[dict], seed: int) -> list[dict]:
    if not questions:
        return []
    rng = random.Random(seed)
    by_chapter: dict[str, list[dict]] = {}
    for question in questions:
        by_chapter.setdefault(question["chapter"], []).append(question)
    for chapter_questions in by_chapter.values():
        rng.shuffle(chapter_questions)
    chapters = sorted(by_chapter.keys(), key=chapter_sort_key)
    result: list[dict] = []
    max_len = max(len(items) for items in by_chapter.values())
    for index in range(max_len):
        for chapter in chapters:
            if index < len(by_chapter[chapter]):
                result.append(by_chapter[chapter][index])
    return result


def find_unassigned_questions(all_questions: list[dict], existing_exams: list[dict]) -> list[dict]:
    """Return questions from all_questions whose IDs are not in any existing exam."""
    assigned_ids: set[str] = set()
    for exam in existing_exams:
        for q in exam.get("questions", []):
            assigned_ids.add(q["id"])
    return [q for q in all_questions if q["id"] not in assigned_ids]


def append_classic_exams(new_questions: list[dict], *, last_exam_number: int) -> list[dict]:
    """Build new classic exams from new_questions, numbering from last_exam_number + 1.

    Uses the same stratified-shuffle + packing logic as build_exam_sets().
    Existing exams are never touched — only new exams are returned.
    """
    mm_questions = _stratified_shuffle(
        [q for q in new_questions if q["type"] == "mm" and "correct" in q],
        SHUFFLE_SEED,
    )
    op_questions = _stratified_shuffle(
        [q for q in new_questions if q["type"] == "op" and "correct" in q],
        SHUFFLE_SEED + 1,
    )

    exams: list[dict] = []
    mm_index = 0
    op_index = 0
    exam_number = last_exam_number + 1

    while mm_index < len(mm_questions) or op_index < len(op_questions):
        mm_take = min(TARGET_MM_PER_EXAM, len(mm_questions) - mm_index)
        op_take = min(MAX_OP_PER_EXAM, len(op_questions) - op_index, MAX_EXAM_SIZE - mm_take)
        total = mm_take + op_take
        if total == 0:
            break
        exam_questions = (
            mm_questions[mm_index : mm_index + mm_take]
            + op_questions[op_index : op_index + op_take]
        )
        exams.append(
            {
                "id": f"exam-{exam_number:02d}",
                "title": f"Challenge Exam {exam_number}",
                "bank": CLASSIC_BANK_ID,
                "bank_title": CLASSIC_BANK_TITLE,
                "questions": exam_questions,
            }
        )
        mm_index += mm_take
        op_index += op_take
        exam_number += 1

    return exams


def build_exam_sets(questions: list[dict]) -> list[dict]:
    mm_questions = _stratified_shuffle(
        [question for question in questions if question["type"] == "mm" and "correct" in question],
        SHUFFLE_SEED,
    )
    op_questions = _stratified_shuffle(
        [question for question in questions if question["type"] == "op" and "correct" in question],
        SHUFFLE_SEED + 1,
    )

    exams: list[dict] = []
    mm_index = 0
    op_index = 0
    exam_number = 1

    while mm_index < len(mm_questions) or op_index < len(op_questions):
        mm_take = min(TARGET_MM_PER_EXAM, len(mm_questions) - mm_index)
        op_take = min(MAX_OP_PER_EXAM, len(op_questions) - op_index, MAX_EXAM_SIZE - mm_take)
        total = mm_take + op_take
        if total == 0:
            break
        exam_questions = (
            mm_questions[mm_index : mm_index + mm_take]
            + op_questions[op_index : op_index + op_take]
        )
        exams.append(
            {
                "id": f"exam-{exam_number:02d}",
                "title": f"Challenge Exam {exam_number}",
                "bank": CLASSIC_BANK_ID,
                "bank_title": CLASSIC_BANK_TITLE,
                "questions": exam_questions,
            }
        )
        mm_index += mm_take
        op_index += op_take
        exam_number += 1

    return exams


def build_chapter_exam_sets(
    questions: list[dict],
    *,
    chapters: tuple[str, ...] | None = None,
) -> list[dict]:
    if chapters is None:
        chapters = tuple(
            sorted(
                {question["chapter"] for question in questions if question.get("chapter") and "correct" in question},
                key=chapter_sort_key,
            )
        )
    exams: list[dict] = []
    for chapter in chapters:
        chapter_key = chapter_slug(chapter)
        chapter_questions = [question for question in questions if question["chapter"] == chapter and "correct" in question]
        mm_questions = sorted(
            [question for question in chapter_questions if question["type"] == "mm"],
            key=lambda question: (question["model_label"], question["question_number"]),
        )
        op_questions = sorted(
            [question for question in chapter_questions if question["type"] == "op"],
            key=lambda question: (question["model_label"], question["question_number"]),
        )
        if mm_questions:
            exams.append(
                {
                    "id": f"chp{chapter_key}-mm",
                    "title": f"Chapter {chapter} Mental Math Challenge",
                    "chapter": chapter,
                    "challenge_type": "mm",
                    "questions": mm_questions,
                }
            )
        if op_questions:
            exams.append(
                {
                    "id": f"chp{chapter_key}-op",
                    "title": f"Chapter {chapter} Olympiad Challenge",
                    "chapter": chapter,
                    "challenge_type": "op",
                    "questions": op_questions,
                }
            )
    return exams


def _load_curated_questions(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        return []

    bank = path.stem.lower()
    bank_id, bank_title = _curated_bank_identity(path)
    questions: list[dict] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        question_number = int(entry.get("problem_number", len(questions) + 1))
        question_text = str(entry.get("question", "")).strip()
        options_map = entry.get("options", {})
        correct_option = str(entry.get("correct_option", "")).strip().upper()
        if not question_text or not isinstance(options_map, dict) or not correct_option:
            continue

        option_lines = [
            f"({letter}) {str(options_map[letter]).strip()}"
            for letter in sorted(options_map)
            if str(letter).strip()
        ]
        if not option_lines:
            continue

        source = str(entry.get("source", bank_title)).strip() or bank_title
        concept = str(entry.get("concept", "")).strip()
        source_link = str(entry.get("link", "")).strip()
        source_parts = [bank_title, source]
        if concept:
            source_parts.append(concept)
        source_parts.append(f"Q{question_number}")
        curated_metadata = {
            key: value
            for key, value in entry.items()
            if key not in {"question", "options", "correct_option"}
        }
        questions.append(
            {
                "id": f"{bank}-q{question_number}",
                "source_stem": bank,
                "source_file": path.name,
                "curated_source": source,
                "curated_concept": concept,
                "curated_source_link": source_link,
                "curated_problem_number": question_number,
                "curated_metadata": curated_metadata,
                "chapter": "",
                "type": bank_id,
                "model": "gem",
                "model_label": "Gemini 3.1 Pro",
                "source_label": " / ".join(source_parts),
                "question_number": question_number,
                "text": question_text,
                "options": option_lines,
                "correct": correct_option,
            }
        )
    return questions


def _load_explicit_curated_exam_payload(path: Path) -> dict | None:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict) or payload.get("format") != "explicit_curated_exam":
        return None
    exam = payload.get("exam")
    if not isinstance(exam, dict):
        return None
    return _normalize_explicit_curated_exam(exam, source_path=path)


def _normalize_explicit_curated_exam(exam: dict, *, source_path: Path) -> dict:
    normalized_exam = dict(exam)
    normalized_exam["source_type"] = "explicit_curated_exam"
    normalized_exam.setdefault("bank", "amc10")
    normalized_exam.setdefault("bank_title", "AMC 10")
    normalized_exam.setdefault("source_stem", normalized_exam.get("id", source_path.stem))
    normalized_exam.setdefault("source_file", source_path.name)

    normalized_questions: list[dict] = []
    for index, question in enumerate(normalized_exam.get("questions", []), 1):
        normalized_question = _repair_explicit_curated_question(dict(question))
        normalized_question.setdefault("id", f"{normalized_exam['id']}-q{index:02d}")
        normalized_question.setdefault("source_stem", normalized_exam["source_stem"])
        normalized_question.setdefault("source_file", source_path.name)
        normalized_question.setdefault("type", normalized_exam["bank"])
        normalized_question.setdefault("chapter", "")
        normalized_question.setdefault("question_number", index)
        normalized_question.setdefault("curated_problem_number", index)
        normalized_question.setdefault("model", "official")
        normalized_question.setdefault("model_label", "Official AMC")
        normalized_question.setdefault("curated_problem_link", "")
        normalized_question.setdefault("question_images", [])
        normalized_questions.append(normalized_question)

    normalized_exam["questions"] = normalized_questions
    normalized_exam["question_count"] = len(normalized_questions)
    return normalized_exam


def _repair_explicit_curated_question(question: dict) -> dict:
    options = question.get("options")
    if isinstance(options, list):
        cleaned_options = []
        for option in options:
            option_text = str(option).strip()
            match = re.match(r"^\(([A-E])\)\s*(.*)$", option_text)
            if match:
                cleaned_options.append(f"({match.group(1)}) {_normalize_option_text(match.group(2))}".rstrip())
            elif option_text:
                cleaned_options.append(_normalize_option_text(option_text))
        question["options"] = cleaned_options

        if _options_are_effectively_empty(cleaned_options):
            repaired_text, repaired_options = _extract_embedded_choice_lines(str(question.get("text", "")))
            if repaired_options:
                question["text"] = repaired_text
                question["options"] = repaired_options
    return question


def _options_are_effectively_empty(options: list[str]) -> bool:
    if not options:
        return True
    return all(re.fullmatch(r"\([A-E]\)\s*", option) for option in options)


def _extract_embedded_choice_lines(text: str) -> tuple[str, list[str]]:
    parts = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    if len(parts) < 6:
        return text, []

    candidate_choices = parts[-5:]
    if any(len(choice) < 2 for choice in candidate_choices):
        return text, []

    prompt_text = "\n\n".join(parts[:-5]).strip()
    if not prompt_text:
        return text, []

    options = [f"({chr(65 + index)}) {choice}" for index, choice in enumerate(candidate_choices)]
    return prompt_text, options


def _curated_bank_identity(path: Path) -> tuple[str, str]:
    stem = path.stem
    if stem.lower().startswith(("amc", "aime", "aimi")):
        return ("amc", "AIME")
    return (stem.lower(), _humanize_bank_title(stem))


def _natural_path_sort_key(path: Path) -> tuple[tuple[int, str | int], ...]:
    parts = re.split(r"(\d+)", path.stem.lower())
    key: list[tuple[int, str | int]] = []
    for part in parts:
        if not part:
            continue
        if part.isdigit():
            key.append((1, int(part)))
        else:
            key.append((0, part))
    return tuple(key)


def _humanize_bank_title(stem: str) -> str:
    words = []
    for token in stem.replace("_", "-").split("-"):
        if not token:
            continue
        words.append(token if token.isupper() else token.capitalize())
    return " ".join(words)
