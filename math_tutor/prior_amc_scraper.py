"""Scrape one official AMC exam from AoPS into an explicit curated-exam record."""

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


PRIOR_AMC_BANK_ID = "prior-amc"
PRIOR_AMC_BANK_TITLE = "Prior AMC"
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


def scrape_prior_amc_exam(source_url: str) -> dict[str, Any]:
    main_page_html = fetch_html(source_url)
    main_page = _parse_main_page(main_page_html=main_page_html, source_url=source_url)
    problems_page_html = fetch_html(main_page["problems_page"])
    answer_key_html = fetch_html(main_page["answer_key_page"])
    return scrape_prior_amc_exam_from_html(
        main_page_html=main_page_html,
        problems_page_html=problems_page_html,
        answer_key_html=answer_key_html,
        source_url=source_url,
    )


def scrape_prior_amc_exam_from_html(
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

    exam_id = f"{PRIOR_AMC_BANK_ID}-{_slugify(main_page['title'])}"
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
                "type": PRIOR_AMC_BANK_ID,
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
        "bank": PRIOR_AMC_BANK_ID,
        "bank_title": PRIOR_AMC_BANK_TITLE,
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
    title_match = re.search(r"<p><b>([^<]+)</b>\s+problems and solutions\.", main_page_html)
    date_match = re.search(r"test was administered on ([^.]+)\.", main_page_html)
    problems_page_match = re.search(
        r'href="([^"]+)"[^>]*title="[^"]+Problems"[^>]*>\s*[^<]*Problems\s*</a>',
        main_page_html,
    )
    answer_key_match = re.search(
        r'href="([^"]+)"[^>]*title="[^"]+Answer Key"[^>]*>\s*[^<]*Answer Key\s*</a>',
        main_page_html,
    )
    if not title_match or not date_match or not problems_page_match or not answer_key_match:
        raise ValueError("Could not find the expected title/date/problem-key links on the AoPS main page.")

    title = unescape(title_match.group(1)).strip()
    return {
        "title": title,
        "contest": re.sub(r"^\d+\s+", "", title).strip(),
        "year": int(title.split()[0]),
        "administered_on": datetime.strptime(date_match.group(1).strip(), "%A, %B %d, %Y").date().isoformat(),
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

            if paragraph.option_alt:
                options = _parse_option_alt(paragraph.option_alt)

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

    matches = list(
        re.finditer(
            r"\\textbf\{\(([A-E])\)\s*\}\s*~?\s*(.*?)(?=(?:\\qquad\s*\\textbf\{\([A-E]\)\s*\})|$)",
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
        self.option_alt = ""

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
                self.option_alt = alt
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
        return bool(re.search(r"\\textbf\{\([A-E]\)\s*\}", alt))


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape an AoPS AMC exam into an explicit curated exam JSON file.")
    parser.add_argument("url", help="AoPS wiki URL such as https://artofproblemsolving.com/wiki/index.php?title=2025_AMC_10A")
    parser.add_argument("output", help="Output JSON path")
    args = parser.parse_args()

    exam = scrape_prior_amc_exam(args.url)
    output_path = Path(args.output)
    output_path.write_text(json.dumps({"format": "explicit_curated_exam", "exam": exam}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
