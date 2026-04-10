"""Scrape one official AMC 10 exam from AoPS into an explicit curated-exam record."""

from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen

from math_tutor.atomic_io import atomic_write_json


AMC10_BANK_ID = "amc10"
AMC10_BANK_TITLE = "AMC 10"
OFFICIAL_MODEL_ID = "official"
OFFICIAL_MODEL_LABEL = "Official AMC"


def fetch_html(url: str) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    with urlopen(request) as response:  # noqa: S310 - used for trusted AoPS wiki URLs
        return response.read().decode("utf-8")


def scrape_amc10_exam(source_url: str) -> dict[str, Any]:
    main_page_html = fetch_html(source_url)
    main_page = _parse_main_page(main_page_html=main_page_html, source_url=source_url)
    problems_page_html = fetch_html(main_page["problems_page"])
    answer_key_html = fetch_html(main_page["answer_key_page"])
    return scrape_amc10_exam_from_html(
        main_page_html=main_page_html,
        problems_page_html=problems_page_html,
        answer_key_html=answer_key_html,
        source_url=source_url,
    )


def scrape_amc10_exam_from_html(
    *,
    main_page_html: str,
    problems_page_html: str,
    answer_key_html: str,
    source_url: str,
) -> dict[str, Any]:
    main_page = _parse_main_page(main_page_html=main_page_html, source_url=source_url)
    answers = _parse_answer_key(answer_key_html)
    problems = _parse_problems_page(problems_page_html, base_url=source_url)
    if len(problems) != len(answers):
        raise ValueError(
            f"Expected the problems page and answer key to have the same length, got "
            f"{len(problems)} problems and {len(answers)} answers."
        )

    exam_id = f"{AMC10_BANK_ID}-{_slugify(main_page['title'])}"
    questions: list[dict[str, Any]] = []
    for index, (problem, answer) in enumerate(zip(problems, answers, strict=True), 1):
        problem_link = f"{main_page['problems_page']}#Problem_{index}"
        questions.append(
            {
                "id": f"{exam_id}-q{index:02d}",
                "source_stem": exam_id,
                "curated_source": main_page["title"],
                "curated_concept": "",
                "curated_problem_link": problem_link,
                "curated_source_link": problem["solution_link"],
                "curated_problem_number": index,
                "curated_metadata": {
                    "problem_link": problem_link,
                    "solution_link": problem["solution_link"],
                    "question_images": problem["question_images"],
                },
                "chapter": "",
                "type": AMC10_BANK_ID,
                "model": OFFICIAL_MODEL_ID,
                "model_label": OFFICIAL_MODEL_LABEL,
                "source_label": f"{main_page['title']} / Problem {index}",
                "question_number": index,
                "text": problem["text"],
                "question_images": problem["question_images"],
                "options": problem["options"],
                "correct": answer,
            }
        )

    return {
        "format": "explicit_curated_exam",
        "source_type": "explicit_curated_exam",
        "id": exam_id,
        "title": main_page["title"],
        "bank": AMC10_BANK_ID,
        "bank_title": AMC10_BANK_TITLE,
        "question_count": len(questions),
        "questions": questions,
        "curated_metadata": {
            "year": main_page["year"],
            "contest": main_page["contest"],
            "administered_on": main_page["administered_on"],
            "source_page": source_url,
            "problems_page": main_page["problems_page"],
            "answer_key_page": main_page["answer_key_page"],
        },
    }


def _parse_main_page(*, main_page_html: str, source_url: str) -> dict[str, Any]:
    # Replace inline LaTeX images (e.g. <img alt="$16$">) with their numeric values so date
    # strings like "November <img alt="$16$">, <img alt="$2022$">." parse correctly.
    processed_html = re.sub(
        r'<img\s[^>]*alt="\$([^$<>]+)\$"[^>]*/?>',
        lambda m: m.group(1),
        main_page_html,
    )

    title_match = re.search(r"<p><b>([^<]+)</b>\s+problems and solutions\.", processed_html)
    date_match = re.search(
        r"(?:administered|held|will be held) on ([^.<]+)\.",
        processed_html,
    )
    problems_page_match = re.search(
        r'href="([^"]+)"[^>]*title="[^"]+Problems"[^>]*>\s*[^<]*Problems\s*</a>',
        processed_html,
    )
    answer_key_match = re.search(
        r'href="([^"]+)"[^>]*title="[^"]+Answer Key"[^>]*>\s*[^<]*Answer Key\s*</a>',
        processed_html,
    )
    if not title_match or not problems_page_match or not answer_key_match:
        raise ValueError("Could not find the expected title/problem-key links on the AoPS main page.")

    title = unescape(title_match.group(1)).strip()

    administered_on = None
    if date_match:
        date_str = re.sub(r"\s+", " ", unescape(date_match.group(1))).strip()
        for fmt in ("%A, %B %d, %Y", "%B %d, %Y"):
            try:
                administered_on = datetime.strptime(date_str, fmt).date().isoformat()
                break
            except ValueError:
                continue

    return {
        "title": title,
        "contest": re.sub(r"^\d+\s+", "", title).strip(),
        "year": int(title.split()[0]),
        "administered_on": administered_on,
        "problems_page": urljoin(source_url, unescape(problems_page_match.group(1))),
        "answer_key_page": urljoin(source_url, unescape(answer_key_match.group(1))),
    }


def _parse_answer_key(answer_key_html: str) -> list[str]:
    list_match = re.search(r"<ol>(.*?)</ol>", answer_key_html, flags=re.DOTALL)
    if not list_match:
        raise ValueError("Could not locate the answer key list on the AoPS answer key page.")
    answers = re.findall(r"<li>\s*([A-E])\s*</li>", list_match.group(1))
    if not answers:
        raise ValueError("Could not parse any answer letters from the AoPS answer key page.")
    return answers


def _parse_problems_page(problems_page_html: str, *, base_url: str) -> list[dict[str, Any]]:
    pieces = re.split(
        r'<h2><span class="mw-headline" id="Problem_(\d+)">Problem \d+</span></h2>',
        problems_page_html,
        flags=re.DOTALL,
    )
    if len(pieces) < 3:
        raise ValueError("Could not find any problem sections on the AoPS problems page.")

    problems: list[dict[str, Any]] = []
    for index in range(1, len(pieces), 2):
        block = pieces[index + 1]
        paragraphs = re.findall(r"<p>(.*?)</p>", block, flags=re.DOTALL)
        text_paragraphs: list[str] = []
        question_images: list[dict[str, Any]] = []
        options: list[str] = []
        solution_link = ""

        for paragraph_html in paragraphs:
            if ">Solution<" in paragraph_html:
                link_match = re.search(r'href="([^"]+)"', paragraph_html)
                if link_match:
                    solution_link = urljoin(base_url, unescape(link_match.group(1)))
                break

            paragraph = _ParagraphParser(base_url=base_url)
            paragraph.feed(paragraph_html)
            paragraph.close()

            if paragraph.option_alts:
                for alt in paragraph.option_alts:
                    options.extend(_parse_option_alt(alt))

            if paragraph.text:
                text_paragraphs.append(paragraph.text)
            question_images.extend(paragraph.question_images)

        if not text_paragraphs or not options or not solution_link:
            raise ValueError("A problem section was missing question text, options, or a solution link.")

        problems.append(
            {
                "text": "\n\n".join(text_paragraphs).strip(),
                "question_images": question_images,
                "options": options,
                "solution_link": solution_link,
            }
        )

    return problems


def _parse_option_alt(option_alt: str) -> list[str]:
    latex = option_alt.strip()
    if latex.startswith("$") and latex.endswith("$"):
        latex = latex[1:-1]

    # Standard format: \textbf{(A) } or \textbf {(A) }
    matches = list(
        re.finditer(
            r"\\textbf\s*\{\(([A-E])\)\s*\}\s*~?\s*(.*?)(?=(?:\\qquad\s*\\textbf\s*\{\([A-E]\)\s*\})|$)",
            latex,
            flags=re.DOTALL,
        )
    )
    if not matches:
        # Alternate format: (\textbf{A})\: text  (used in 2021 Fall exams)
        matches = list(
            re.finditer(
                r"\(\\textbf\{([A-E])\}\)\s*\\?\s*:\s*(.*?)(?=(?:\\qquad\s*\(\\textbf\{[A-E]\})|$)",
                latex,
                flags=re.DOTALL,
            )
        )
    if not matches:
        raise ValueError(f"Could not parse MCQ options from option block: {option_alt!r}")

    options: list[str] = []
    for match in matches:
        letter = match.group(1)
        text = re.sub(r"\s+", " ", match.group(2).replace("~", " ")).strip()
        text = re.sub(r"\s+([,.;:?])", r"\1", text)
        options.append(f"({letter}) {text}")
    return options


class _ParagraphParser(HTMLParser):
    def __init__(self, *, base_url: str) -> None:
        super().__init__(convert_charrefs=True)
        self._base_url = base_url
        self._parts: list[str] = []
        self.question_images: list[dict[str, Any]] = []
        self.option_alts: list[str] = []

    @property
    def option_alt(self) -> str:
        return self.option_alts[0] if self.option_alts else ""

    @property
    def text(self) -> str:
        joined = "".join(self._parts)
        joined = joined.replace("\xa0", " ")
        joined = re.sub(r"[ \t\r\f\v]+", " ", joined)
        joined = re.sub(r" *\n *", "\n", joined)
        return joined.strip()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr_map = {key: value or "" for key, value in attrs}
        if tag == "img":
            alt = unescape(attr_map.get("alt", "")).strip()
            src = attr_map.get("src", "").strip()
            class_name = attr_map.get("class", "")
            if self._looks_like_option_block(alt):
                self.option_alts.append(alt)
                return
            if _should_preserve_as_image(alt=alt, class_name=class_name):
                self.question_images.append(
                    {
                        "url": urljoin(self._base_url, unescape(src)),
                        "alt": alt,
                        "width": _parse_optional_int(attr_map.get("width")),
                        "height": _parse_optional_int(attr_map.get("height")),
                    }
                )
                return
            self._parts.append(alt)
            return
        if tag == "br":
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    @staticmethod
    def _looks_like_option_block(alt: str) -> bool:
        # Matches \textbf{(A)} / \textbf {(A)} style AND (\textbf{A}) style
        return bool(re.search(r"\\textbf\s*\{\([A-E]\)\s*\}|\(\\textbf\{[A-E]\}\)", alt))


def _parse_optional_int(value: str | None) -> int | None:
    if value is None or value == "":
        return None
    return int(value)


def _should_preserve_as_image(*, alt: str, class_name: str) -> bool:
    stripped = alt.lstrip()
    if stripped.startswith("[asy]"):
        return True
    if "\\begin{tabular}" in alt or ("latexcenter" in class_name and "\\begin{array}" in alt):
        return True
    return False


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


# AMC 10 exams from 2020–2025 (excluding 2025 AMC 10A which is already scraped).
# Key: output filename stem, Value: AoPS wiki title parameter.
AMC_10_EXAMS_2020_2025: dict[str, str] = {
    "amc10_2020_amc_10a": "2020_AMC_10A",
    "amc10_2020_amc_10b": "2020_AMC_10B",
    "amc10_2021_amc_10a": "2021_AMC_10A",
    "amc10_2021_amc_10b": "2021_AMC_10B",
    "amc10_2021_fall_amc_10a": "2021_Fall_AMC_10A",
    "amc10_2021_fall_amc_10b": "2021_Fall_AMC_10B",
    "amc10_2022_amc_10a": "2022_AMC_10A",
    "amc10_2022_amc_10b": "2022_AMC_10B",
    "amc10_2023_amc_10a": "2023_AMC_10A",
    "amc10_2023_amc_10b": "2023_AMC_10B",
    "amc10_2024_amc_10a": "2024_AMC_10A",
    "amc10_2024_amc_10b": "2024_AMC_10B",
    "amc10_2025_amc_10b": "2025_AMC_10B",
}

AOPS_WIKI_BASE = "https://artofproblemsolving.com/wiki/index.php?title="


def _preserve_question_ids(
    existing: list[dict[str, Any]],
    new_questions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remap IDs in new_questions to match existing IDs wherever the question text is the same.

    This keeps question IDs stable across force-rescrapes so that existing DB submissions
    (which reference question_id) remain consistent. Questions whose text has no match in
    the existing list keep their new positional ID as-is.
    """
    text_to_id: dict[str, str] = {}
    for q in existing:
        text = q.get("text", "").strip()
        qid = q.get("id", "")
        if text and qid:
            text_to_id[text] = qid

    result: list[dict[str, Any]] = []
    for q in new_questions:
        remapped = dict(q)
        matched_id = text_to_id.get(q.get("text", "").strip())
        if matched_id:
            remapped["id"] = matched_id
        result.append(remapped)
    return result


def scrape_all_amc_10_exams(
    output_dir: Path,
    *,
    _out: Any = None,
) -> list[Path]:
    """Scrape all AMC 10 exams from 2020–2025 into output_dir.

    Existing files are always skipped — use the `scrape` subcommand to re-scrape a specific exam.
    Returns the list of paths written or skipped.
    _out: optional file-like for output (defaults to sys.stdout via print).
    """
    _print = (lambda msg: print(msg, file=_out)) if _out is not None else print

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for stem, title in AMC_10_EXAMS_2020_2025.items():
        output_path = output_dir / f"{stem}.json"
        if output_path.exists():
            _print(f"  skip (exists): {output_path.name}")
            written.append(output_path)
            continue

        url = f"{AOPS_WIKI_BASE}{title}"
        _print(f"  scraping: {title} → {output_path.name}")
        exam = scrape_amc10_exam(url)
        atomic_write_json(
            output_path,
            {"format": "explicit_curated_exam", "exam": exam},
            indent=2,
        )
        written.append(output_path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape AoPS AMC exam(s) into explicit curated exam JSON files.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    single = subparsers.add_parser("scrape", help="Scrape a single exam by URL.")
    single.add_argument("url", help="AoPS wiki URL, e.g. https://artofproblemsolving.com/wiki/index.php?title=2025_AMC_10A")
    single.add_argument("output", help="Output JSON path")

    batch = subparsers.add_parser("scrape-all", help="Scrape all AMC 10 exams 2020–2025 into a directory (skips existing files).")
    batch.add_argument("output_dir", help="Directory to write JSON files into")

    args = parser.parse_args()

    if args.command == "scrape":
        exam = scrape_amc10_exam(args.url)
        output_path = Path(args.output)
        atomic_write_json(output_path, {"format": "explicit_curated_exam", "exam": exam}, indent=2)
    elif args.command == "scrape-all":
        paths = scrape_all_amc_10_exams(Path(args.output_dir))
        print(f"Done: {len(paths)} exam(s) written to {args.output_dir}")


if __name__ == "__main__":
    main()
