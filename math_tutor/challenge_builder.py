"""Build interactive challenge exams from saved AI-generated question files."""
from __future__ import annotations

import json
import os
import random
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path

from math_tutor.cli import load_dotenv_if_present

PACKAGE_DIR = Path(__file__).resolve().parent

CHALLENGES_SRC_DIR = PACKAGE_DIR / "challenges_src"
SHUFFLE_SEED = 42
MM_PER_EXAM = 5
OP_PER_EXAM = 5

SOURCE_SUFFIXES = [
    ("__mental-math-gpt5.md",         "mm", "gpt54", "GPT-5.4"),
    ("__mental-math-gemini.md",        "mm", "gem",   "Gemini 3.1 Pro"),
    ("__olympiad-problems-gpt5.md",    "op", "gpt54", "GPT-5.4"),
    ("__olympiad-problems-gemini.md",  "op", "gem",   "Gemini 3.1 Pro"),
]


# ---------------------------------------------------------------------------
# Question extraction
# ---------------------------------------------------------------------------

def _chapter_from_stem(stem: str) -> str:
    base = stem.split("__")[0]
    m = re.search(r"chp-(\d+(?:-\d+)*)", base)
    if not m:
        return "?"
    parts = m.group(1).split("-")
    chapters: list[str] = []
    i = 0
    while i + 1 < len(parts):
        chapters.append(f"{parts[i]}.{parts[i + 1]}")
        i += 2
    return " & ".join(chapters)


def _extract_numbered_questions(text: str) -> list[str]:
    matches = list(re.finditer(r"(?m)^(\d+)\.\s+", text))
    questions: list[str] = []
    for i, match in enumerate(matches):
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        q = text[start:end].strip()
        if q:
            questions.append(q)
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


def load_all_questions(output_dir: Path) -> list[dict]:
    responses_dir = output_dir / "responses"
    if not responses_dir.exists():
        return []
    questions: list[dict] = []
    for suffix, q_type, model, model_label in SOURCE_SUFFIXES:
        type_label = "Mental Math" if q_type == "mm" else "Olympiad Problems"
        for path in sorted(responses_dir.glob(f"*{suffix}")):
            chapter = _chapter_from_stem(path.stem)
            for i, text in enumerate(_extract_from_file(path), 1):
                q_id = f"chp{chapter.replace(' & ', '-').replace('.', '')}-{q_type}-{model}-q{i}"
                questions.append({
                    "id": q_id,
                    "chapter": chapter,
                    "type": q_type,
                    "model": model,
                    "model_label": model_label,
                    "source_label": f"Chapter {chapter} / {type_label} / {model_label} / Q{i}",
                    "question_number": i,
                    "text": text,
                })
    return questions


# ---------------------------------------------------------------------------
# Exam set generation
# ---------------------------------------------------------------------------

def _chapter_sort_key(chapter: str) -> float:
    m = re.match(r"^(\d+(?:\.\d+)?)", chapter)
    return float(m.group(1)) if m else 9999.0


def _stratified_shuffle(questions: list[dict], seed: int) -> list[dict]:
    rng = random.Random(seed)
    by_chapter: dict[str, list[dict]] = {}
    for q in questions:
        by_chapter.setdefault(q["chapter"], []).append(q)
    for qs in by_chapter.values():
        rng.shuffle(qs)
    chapters = sorted(by_chapter.keys(), key=_chapter_sort_key)
    result: list[dict] = []
    max_len = max(len(v) for v in by_chapter.values())
    for i in range(max_len):
        for chap in chapters:
            if i < len(by_chapter[chap]):
                result.append(by_chapter[chap][i])
    return result


def build_exam_sets(questions: list[dict]) -> list[dict]:
    mm = _stratified_shuffle([q for q in questions if q["type"] == "mm"], SHUFFLE_SEED)
    op = _stratified_shuffle([q for q in questions if q["type"] == "op"], SHUFFLE_SEED + 1)

    exams: list[dict] = []
    mm_idx = op_idx = 0
    num = 1

    while mm_idx + MM_PER_EXAM <= len(mm) and op_idx + OP_PER_EXAM <= len(op):
        mm_batch = mm[mm_idx: mm_idx + MM_PER_EXAM]
        op_batch = op[op_idx: op_idx + OP_PER_EXAM]
        interleaved: list[dict] = []
        for j in range(max(MM_PER_EXAM, OP_PER_EXAM)):
            if j < MM_PER_EXAM:
                interleaved.append(mm_batch[j])
            if j < OP_PER_EXAM:
                interleaved.append(op_batch[j])
        exams.append({"id": f"exam-{num:02d}", "title": f"Challenge Exam {num}", "questions": interleaved})
        mm_idx += MM_PER_EXAM
        op_idx += OP_PER_EXAM
        num += 1

    return exams


# ---------------------------------------------------------------------------
# Config PHP generation
# ---------------------------------------------------------------------------

def _php_str(value: str) -> str:
    escaped = value.replace("\\", "\\\\").replace("'", "\\'")
    return f"'{escaped}'"


def generate_config_php(output_path: Path) -> None:
    host = os.environ.get("MYSQL_HOST", "localhost")
    dbname = os.environ.get("DBNAME", "")
    user = os.environ.get("DBUSER", "")
    password = os.environ.get("DBPASSWORD", "")
    output_path.write_text(
        f"<?php\n"
        f"define('DB_HOST', {_php_str(host)});\n"
        f"define('DB_NAME', {_php_str(dbname)});\n"
        f"define('DB_USER', {_php_str(user)});\n"
        f"define('DB_PASS', {_php_str(password)});\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# Main build
# ---------------------------------------------------------------------------

def build_challenges(
    output_dir: Path,
    site_dir: Path,
    force: bool = False,
) -> None:
    challenges_dir = site_dir / "challenges"
    challenges_dir.mkdir(parents=True, exist_ok=True)

    # Canonical exams.json lives in challenges_src/ so it is tracked in git
    canonical_exams_json = CHALLENGES_SRC_DIR / "exams.json"

    if not force and canonical_exams_json.exists():
        existing = json.loads(canonical_exams_json.read_text(encoding="utf-8"))
        generated_at = existing.get("generated_at", "unknown")
        exam_count = len(existing.get("exams", []))
        print(f"Challenge exams already generated ({exam_count} exams, bundle: {generated_at}). "
              f"Skipping regeneration. Use --force-challenges to regenerate.")
    else:
        if force and canonical_exams_json.exists():
            print("Force flag set — regenerating challenge exams...")
        else:
            print("Generating challenge exams for the first time...")
        questions = load_all_questions(output_dir)
        print(f"  Found {len(questions)} questions "
              f"({sum(1 for q in questions if q['type'] == 'mm')} mental math, "
              f"{sum(1 for q in questions if q['type'] == 'op')} olympiad)")

        exams = build_exam_sets(questions)
        generated_at = datetime.now(timezone.utc).isoformat()
        print(f"  Generated {len(exams)} challenge exams (bundle: {generated_at})")

        canonical_exams_json.write_text(
            json.dumps({"generated_at": generated_at, "exams": exams}, indent=2),
            encoding="utf-8",
        )
        print(f"  Wrote {canonical_exams_json}")

    # Always copy static PHP + HTML source files (picks up UI changes)
    # Skip exams.json — it's only needed to generate individual exam files, not served directly.
    for src_file in CHALLENGES_SRC_DIR.glob("*"):
        if src_file.name == "exams.json":
            continue
        dest = challenges_dir / src_file.name
        shutil.copy2(src_file, dest)
        print(f"  Copied {src_file.name}")

    # Always generate a lightweight exams-index.json for the picker page (no question text)
    # and individual per-exam JSON files so exam.html only fetches ~4KB instead of 194KB.
    full = json.loads(canonical_exams_json.read_text(encoding="utf-8"))
    generated_at = full.get("generated_at")
    index_entries = []
    exams_subdir = challenges_dir / "exams"
    exams_subdir.mkdir(exist_ok=True)
    total_individual_kb = 0
    for exam in full.get("exams", []):
        mm = sum(1 for q in exam["questions"] if q["type"] == "mm")
        op = sum(1 for q in exam["questions"] if q["type"] == "op")
        chapters = sorted(
            {q["chapter"] for q in exam["questions"]},
            key=lambda c: float(re.match(r"^[\d.]+", c).group()) if re.match(r"^[\d.]+", c) else 9999,
        )
        index_entries.append({
            "id": exam["id"],
            "title": exam["title"],
            "mm": mm,
            "op": op,
            "chapters": chapters,
        })
        # Write individual exam file: exams/{exam-id}.json
        individual_path = exams_subdir / f"{exam['id']}.json"
        individual_path.write_text(
            json.dumps({"generated_at": generated_at, **exam}),
            encoding="utf-8",
        )
        total_individual_kb += individual_path.stat().st_size
    index_json_path = challenges_dir / "exams-index.json"
    index_json_path.write_text(
        json.dumps({"generated_at": generated_at, "exams": index_entries}),
        encoding="utf-8",
    )
    full_kb = canonical_exams_json.stat().st_size // 1024
    avg_kb = (total_individual_kb // len(index_entries)) if index_entries else 0
    print(f"  Wrote exams-index.json ({len(index_entries)} exams, "
          f"{index_json_path.stat().st_size // 1024}KB vs {full_kb}KB full)")
    print(f"  Wrote {len(index_entries)} individual exam files to exams/ "
          f"(avg {avg_kb // 1024 if avg_kb >= 1024 else avg_kb}{'KB' if avg_kb >= 1024 else 'B'} each, "
          f"vs {full_kb}KB full bundle)")

    # Always regenerate config.php from current env vars
    config_path = challenges_dir / "config.php"
    generate_config_php(config_path)
    print(f"  Generated {config_path}")

    print(f"\nChallenge exams at: {challenges_dir}")


def main() -> None:
    load_dotenv_if_present()
    import argparse
    parser = argparse.ArgumentParser(description="Build challenge exam files from saved AI responses.")
    parser.add_argument("--output-dir", default=str(PACKAGE_DIR / "output"),
                        help="Directory containing responses/ and other outputs.")
    parser.add_argument("--site-dir", default=str(PACKAGE_DIR / "output" / "deploy" / "math_tutor" / "site"),
                        help="Site directory where challenges/ will be written.")
    parser.add_argument("--force", action="store_true",
                        help="Regenerate exams.json even if it already exists.")
    args = parser.parse_args()
    build_challenges(
        output_dir=Path(args.output_dir).resolve(),
        site_dir=Path(args.site_dir).resolve(),
        force=args.force,
    )
