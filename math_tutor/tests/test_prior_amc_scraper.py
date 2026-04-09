from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from math_tutor.challenge_builder import sync_curated_exam_bundle
from math_tutor.prior_amc_scraper import _ParagraphParser, scrape_prior_amc_exam_from_html


MAIN_PAGE_HTML = """
<div id="mw-content-text" class="mw-body-content"><div class="mw-content-ltr mw-parser-output" lang="en" dir="ltr">
<p><b>2025 AMC 10A</b> problems and solutions. The test was administered on Wednesday, November 5, 2025. The first link contains the full set of test problems. The second link contains the answer key. The rest contain each individual problem and its solution.</p>
<ul>
  <li><a href="/wiki/index.php?title=2025_AMC_10A_Problems" title="2025 AMC 10A Problems">2025 AMC 10A Problems</a></li>
  <li><a href="/wiki/index.php?title=2025_AMC_10A_Answer_Key" title="2025 AMC 10A Answer Key">2025 AMC 10A Answer Key</a>
    <ul>
      <li><a href="/wiki/index.php?title=2025_AMC_10A_Problems/Problem_1" title="2025 AMC 10A Problems/Problem 1">Problem 1</a></li>
      <li><a href="/wiki/index.php?title=2025_AMC_10A_Problems/Problem_2" title="2025 AMC 10A Problems/Problem 2">Problem 2</a></li>
      <li><a href="/wiki/index.php?title=2025_AMC_10A_Problems/Problem_3" title="2025 AMC 10A Problems/Problem 3">Problem 3</a></li>
    </ul>
  </li>
</ul>
</div></div>
"""


PROBLEMS_PAGE_HTML = """
<div id="mw-content-text" class="mw-body-content"><div class="mw-content-ltr mw-parser-output" lang="en" dir="ltr">
<h2><span class="mw-headline" id="Problem_1">Problem 1</span></h2>
<p>Andy leaves at <img src="//latex.artofproblemsolving.com/time1.png" class="latex" alt="$1:30$" /> and rides north.</p>
<p><img src="//latex.artofproblemsolving.com/options1.png" class="latex" alt="$\\textbf{(A) } 3:30\\qquad\\textbf{(B) } 3:45\\qquad\\textbf{(C) } 4:00\\qquad\\textbf{(D) } 4:15\\qquad\\textbf{(E) } 4:30$" /></p>
<p><a href="/wiki/index.php?title=2025_AMC_10A_Problems/Problem_1" title="2025 AMC 10A Problems/Problem 1">Solution</a></p>
<h2><span class="mw-headline" id="Problem_2">Problem 2</span></h2>
<p>What is the area of the shaded figure below?</p>
<p><img src="//latex.artofproblemsolving.com/diagram2.png" class="latexcenter" alt="[asy] draw((0,0)--(1,0)--(1,1)--cycle); [/asy]" width="300" height="180" /></p>
<p><img src="//latex.artofproblemsolving.com/options2.png" class="latex" alt="$\\textbf{(A)}~2\\qquad\\textbf{(B)}~4\\qquad\\textbf{(C)}~6\\qquad\\textbf{(D)}~8\\qquad\\textbf{(E)}~10$" /></p>
<p><a href="/wiki/index.php?title=2025_AMC_10A_Problems/Problem_2" title="2025 AMC 10A Problems/Problem 2">Solution</a></p>
<h2><span class="mw-headline" id="Problem_3">Problem 3</span></h2>
<p>The array below is part of the question.</p>
<p><img src="//latex.artofproblemsolving.com/table3.png" class="latexcenter" alt="$\\begin{tabular}{ccc}1&amp;2&amp;3\\\\4&amp;5&amp;6\\end{tabular}$" width="180" height="60" /></p>
<p>What number is in the center?</p>
<p><img src="//latex.artofproblemsolving.com/options3.png" class="latex" alt="$\\textbf{(A)}~1\\qquad\\textbf{(B)}~2\\qquad\\textbf{(C)}~3\\qquad\\textbf{(D)}~4\\qquad\\textbf{(E)}~5$" /></p>
<p><a href="/wiki/index.php?title=2025_AMC_10A_Problems/Problem_3" title="2025 AMC 10A Problems/Problem 3">Solution</a></p>
</div></div>
"""


ANSWER_KEY_HTML = """
<div id="mw-content-text" class="mw-body-content"><div class="mw-content-ltr mw-parser-output" lang="en" dir="ltr">
<ol><li>E</li><li>C</li><li>E</li></ol>
</div></div>
"""


class PriorAmcScraperTests(unittest.TestCase):
    def test_scrape_prior_amc_exam_from_html_builds_explicit_exam_with_metadata_images_and_links(self) -> None:
        exam = scrape_prior_amc_exam_from_html(
            main_page_html=MAIN_PAGE_HTML,
            problems_page_html=PROBLEMS_PAGE_HTML,
            answer_key_html=ANSWER_KEY_HTML,
            source_url="https://artofproblemsolving.com/wiki/index.php?title=2025_AMC_10A",
        )

        self.assertEqual(exam["bank"], "prior-amc")
        self.assertEqual(exam["bank_title"], "Prior AMC")
        self.assertEqual(exam["id"], "prior-amc-2025-amc-10a")
        self.assertEqual(exam["title"], "2025 AMC 10A")
        self.assertEqual(exam["question_count"], 3)
        self.assertEqual(exam["curated_metadata"]["year"], 2025)
        self.assertEqual(exam["curated_metadata"]["contest"], "AMC 10A")
        self.assertEqual(exam["curated_metadata"]["administered_on"], "2025-11-05")
        self.assertEqual(
            exam["curated_metadata"]["problems_page"],
            "https://artofproblemsolving.com/wiki/index.php?title=2025_AMC_10A_Problems",
        )
        self.assertEqual(
            exam["curated_metadata"]["answer_key_page"],
            "https://artofproblemsolving.com/wiki/index.php?title=2025_AMC_10A_Answer_Key",
        )

        first_question = exam["questions"][0]
        self.assertEqual(first_question["id"], "prior-amc-2025-amc-10a-q01")
        self.assertEqual(first_question["correct"], "E")
        self.assertIn("$1:30$", first_question["text"])
        self.assertEqual(first_question["options"], ["(A) 3:30", "(B) 3:45", "(C) 4:00", "(D) 4:15", "(E) 4:30"])
        self.assertEqual(
            first_question["curated_source_link"],
            "https://artofproblemsolving.com/wiki/index.php?title=2025_AMC_10A_Problems/Problem_1",
        )
        self.assertEqual(
            first_question["curated_problem_link"],
            "https://artofproblemsolving.com/wiki/index.php?title=2025_AMC_10A_Problems#Problem_1",
        )
        self.assertEqual(first_question["question_images"], [])

        second_question = exam["questions"][1]
        self.assertEqual(second_question["id"], "prior-amc-2025-amc-10a-q02")
        self.assertEqual(second_question["correct"], "C")
        self.assertEqual(second_question["options"], ["(A) 2", "(B) 4", "(C) 6", "(D) 8", "(E) 10"])
        self.assertEqual(len(second_question["question_images"]), 1)
        self.assertEqual(
            second_question["question_images"][0]["url"],
            "https://latex.artofproblemsolving.com/diagram2.png",
        )

        third_question = exam["questions"][2]
        self.assertEqual(third_question["id"], "prior-amc-2025-amc-10a-q03")
        self.assertEqual(third_question["correct"], "E")
        self.assertEqual(third_question["options"], ["(A) 1", "(B) 2", "(C) 3", "(D) 4", "(E) 5"])
        self.assertNotIn("\\begin{tabular}", third_question["text"])
        self.assertEqual(len(third_question["question_images"]), 1)
        self.assertEqual(
            third_question["question_images"][0]["url"],
            "https://latex.artofproblemsolving.com/table3.png",
        )

    def test_sync_curated_exam_bundle_preserves_explicit_prior_amc_exam_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            exams_dir = temp_root / "exams"
            exams_dir.mkdir()
            canonical_path = temp_root / "curated_exams.json"

            exam = scrape_prior_amc_exam_from_html(
                main_page_html=MAIN_PAGE_HTML,
                problems_page_html=PROBLEMS_PAGE_HTML,
                answer_key_html=ANSWER_KEY_HTML,
                source_url="https://artofproblemsolving.com/wiki/index.php?title=2025_AMC_10A",
            )
            (exams_dir / "prior_amc_2025_amc_10a.json").write_text(
                json.dumps({"format": "explicit_curated_exam", "exam": exam}),
                encoding="utf-8",
            )

            bundle = sync_curated_exam_bundle(
                exams_dir=exams_dir,
                canonical_curated_exams_json=canonical_path,
            )

            self.assertEqual([item["id"] for item in bundle["exams"]], ["prior-amc-2025-amc-10a"])
            self.assertEqual(bundle["exams"][0]["questions"][0]["id"], "prior-amc-2025-amc-10a-q01")
            self.assertEqual(bundle["exams"][0]["questions"][1]["id"], "prior-amc-2025-amc-10a-q02")
            self.assertEqual(bundle["exams"][0]["questions"][2]["id"], "prior-amc-2025-amc-10a-q03")
            self.assertEqual(bundle["exams"][0]["question_count"], 3)

    def test_sync_curated_exam_bundle_skip_existing_explicit_leaves_existing_entry_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            exams_dir = temp_root / "exams"
            exams_dir.mkdir()
            canonical_path = temp_root / "curated_exams.json"

            exam = scrape_prior_amc_exam_from_html(
                main_page_html=MAIN_PAGE_HTML,
                problems_page_html=PROBLEMS_PAGE_HTML,
                answer_key_html=ANSWER_KEY_HTML,
                source_url="https://artofproblemsolving.com/wiki/index.php?title=2025_AMC_10A",
            )
            exam_json = {"format": "explicit_curated_exam", "exam": exam}
            (exams_dir / "prior_amc_2025_amc_10a.json").write_text(
                json.dumps(exam_json), encoding="utf-8"
            )

            # First sync seeds the bundle
            sync_curated_exam_bundle(exams_dir=exams_dir, canonical_curated_exams_json=canonical_path)

            # Manually edit the bundle entry to mark it as "already customised"
            bundle_data = json.loads(canonical_path.read_text())
            bundle_data["exams"][0]["_custom_flag"] = "preserved"
            canonical_path.write_text(json.dumps(bundle_data))

            # Second sync with skip_existing_explicit=True must NOT overwrite the edited entry
            bundle = sync_curated_exam_bundle(
                exams_dir=exams_dir,
                canonical_curated_exams_json=canonical_path,
                skip_existing_explicit=True,
            )
            self.assertEqual(bundle["exams"][0].get("_custom_flag"), "preserved")


MAIN_PAGE_HTML_HELD_ON = MAIN_PAGE_HTML.replace(
    "The test was administered on Wednesday, November 5, 2025.",
    "The test was held on Thursday, November 10, 2022.",
)

MAIN_PAGE_HTML_NO_WEEKDAY = MAIN_PAGE_HTML.replace(
    "The test was administered on Wednesday, November 5, 2025.",
    "This test was held on January 30, 2020.",
)

MAIN_PAGE_HTML_LATEX_DATE = MAIN_PAGE_HTML.replace(
    "The test was administered on Wednesday, November 5, 2025.",
    'The test was held on Wednesday, November <img src="//latex.artofproblemsolving.com/a.png" class="latex" alt="$16$" width="20" height="14" />, <img src="//latex.artofproblemsolving.com/b.png" class="latex" alt="$2022$" width="38" height="14" />.',
)

MAIN_PAGE_HTML_FUTURE_LATEX_DATE = MAIN_PAGE_HTML.replace(
    "The test was administered on Wednesday, November 5, 2025.",
    'The test will be held on Thursday, February <img src="//latex.artofproblemsolving.com/c.png" class="latex" alt="$4$" width="11" height="14" />, <img src="//latex.artofproblemsolving.com/d.png" class="latex" alt="$2021$" width="35" height="13" />.',
)

MAIN_PAGE_HTML_NO_DATE = MAIN_PAGE_HTML.replace(
    "The test was administered on Wednesday, November 5, 2025.",
    "The test date has not been announced.",
)

MAIN_PAGE_HTML_DATE_NO_WEEKDAY_HELD = MAIN_PAGE_HTML.replace(
    "The test was administered on Wednesday, November 5, 2025.",
    "The test was held on November 14, 2023.",
)


def _scrape(main_page_html: str) -> dict:
    return scrape_prior_amc_exam_from_html(
        main_page_html=main_page_html,
        problems_page_html=PROBLEMS_PAGE_HTML,
        answer_key_html=ANSWER_KEY_HTML,
        source_url="https://artofproblemsolving.com/wiki/index.php?title=2025_AMC_10A",
    )


class OptionParsingTests(unittest.TestCase):
    def test_parse_option_alt_handles_space_before_brace(self) -> None:
        # Some exams use \textbf {(A) } (space before {) instead of \textbf{(A) }
        alt = r"$\textbf {(A) } 6\sqrt{3}-3\pi \qquad \textbf {(B) } \frac{9\sqrt{3}}{2} - 2\pi \qquad \textbf {(C) } \frac{3\sqrt{3}}{2} - \frac{\pi}{3} \qquad \textbf {(D) } 3\sqrt{3} - \pi \qquad \textbf {(E) } 4\sqrt{3} - \frac{4\pi}{3}$"
        from math_tutor.prior_amc_scraper import _parse_option_alt
        options = _parse_option_alt(alt)
        self.assertEqual(len(options), 5)
        self.assertTrue(options[0].startswith("(A)"))
        self.assertTrue(options[4].startswith("(E)"))

    def test_problem_with_spaced_textbf_options_is_detected_as_option_block(self) -> None:
        # _looks_like_option_block must match \textbf {(A)} (space before {)
        # so it gets routed through option parsing, not appended as question text
        spaced_options_html = (
            '<img src="//latex.artofproblemsolving.com/x.png" class="latex" '
            r'alt="$\textbf {(A) } 6\sqrt{3}-3\pi \qquad \textbf {(B) } \frac{9}{2}$" />'
        )
        p = _ParagraphParser(base_url="https://artofproblemsolving.com/")
        p.feed(spaced_options_html)
        p.close()
        self.assertNotEqual(p.option_alt, "", "option_alt should be set for spaced \\textbf {(A)} format")
        self.assertEqual(p.text, "")

    def test_parse_option_alt_handles_paren_textbf_format(self) -> None:
        # 2021 Fall exams use (\textbf{A})\: text instead of \textbf{(A) } text
        from math_tutor.prior_amc_scraper import _parse_option_alt
        alt = r"$(\textbf{A})\: 10{,}000\qquad(\textbf{B}) \: 10{,}010\qquad(\textbf{C}) \: 10{,}110\qquad(\textbf{D}) \: 11{,}000\qquad(\textbf{E}) \: 11{,}110$"
        options = _parse_option_alt(alt)
        self.assertEqual(len(options), 5)
        self.assertTrue(options[0].startswith("(A)"), options[0])
        self.assertTrue(options[4].startswith("(E)"), options[4])

    def test_paren_textbf_options_are_detected_as_option_block(self) -> None:
        # _looks_like_option_block must match (\textbf{A}) format (parens outside \textbf)
        html = (
            '<img src="//latex.artofproblemsolving.com/x.png" class="latex" '
            r'alt="$(\textbf{A})\: 8\qquad(\textbf{B}) \: 9$" />'
        )
        p = _ParagraphParser(base_url="https://artofproblemsolving.com/")
        p.feed(html)
        p.close()
        self.assertNotEqual(p.option_alt, "", "option_alt should be set for (\\textbf{A}) format")
        self.assertEqual(p.text, "")

    def test_split_options_across_two_images_in_one_paragraph(self) -> None:
        # P17 of 2021 Fall 10B has options (A)-(C) in one image and (D)-(E) in another
        from math_tutor.prior_amc_scraper import _parse_option_alt
        html = (
            '<img src="//latex.artofproblemsolving.com/x.png" class="latex" '
            r'alt="$(\textbf{A})\: 5x+2y=0\qquad(\textbf{B}) \: 3x+2y=0\qquad(\textbf{C}) \: x-3y=0$" />'
            "\n"
            '<img src="//latex.artofproblemsolving.com/y.png" class="latex" '
            r'alt="$(\textbf{D}) \: 2x-3y=0\qquad(\textbf{E}) \: 7x+y=0$" />'
        )
        p = _ParagraphParser(base_url="https://artofproblemsolving.com/")
        p.feed(html)
        p.close()
        self.assertEqual(len(p.option_alts), 2, "both option images should be collected")
        all_options: list[str] = []
        for alt in p.option_alts:
            all_options.extend(_parse_option_alt(alt))
        self.assertEqual(len(all_options), 5)
        self.assertTrue(all_options[0].startswith("(A)"))
        self.assertTrue(all_options[4].startswith("(E)"))

    def test_options_and_text_in_same_paragraph(self) -> None:
        # P19 of 2021 Fall 10B has question text and options in a single <p>
        from math_tutor.prior_amc_scraper import _parse_option_alt
        html = (
            "<p>"
            'Question text here. '
            '<img src="//latex.artofproblemsolving.com/x.png" class="latexcenter" '
            r'alt="\[f(2)+f(3)?\]" width="200" height="18" />'
            '<img src="//latex.artofproblemsolving.com/y.png" class="latex" '
            r'alt="$(\textbf{A})\: 8\qquad(\textbf{B}) \: 9\qquad(\textbf{C}) \: 11\qquad(\textbf{D}) \: 22\qquad(\textbf{E}) \: 29$" />'
            "</p>"
        )
        p = _ParagraphParser(base_url="https://artofproblemsolving.com/")
        p.feed(html)
        p.close()
        self.assertIn("Question text", p.text)
        self.assertNotEqual(p.option_alt, "")
        options = _parse_option_alt(p.option_alt)
        self.assertEqual(len(options), 5)


class ForceRescrapeTests(unittest.TestCase):
    def test_preserve_question_ids_reuses_existing_id_when_text_matches(self) -> None:
        from math_tutor.prior_amc_scraper import _preserve_question_ids

        existing = [
            {"id": "exam-q01", "text": "Question Alpha"},
            {"id": "exam-q02", "text": "Question Beta"},
            {"id": "exam-q03", "text": "Question Gamma"},
        ]
        # Simulate rescrape returning same questions in a different order
        new_questions = [
            {"id": "exam-q01", "text": "Question Beta"},   # positionally q01 but text = old q02
            {"id": "exam-q02", "text": "Question Alpha"},  # positionally q02 but text = old q01
            {"id": "exam-q03", "text": "Question Gamma"},  # unchanged
        ]
        result = _preserve_question_ids(existing, new_questions)
        self.assertEqual(result[0]["id"], "exam-q02")  # Beta → keeps its old id
        self.assertEqual(result[1]["id"], "exam-q01")  # Alpha → keeps its old id
        self.assertEqual(result[2]["id"], "exam-q03")  # Gamma → unchanged

    def test_preserve_question_ids_keeps_new_positional_id_when_text_has_no_match(self) -> None:
        from math_tutor.prior_amc_scraper import _preserve_question_ids

        existing = [
            {"id": "exam-q01", "text": "Question Alpha"},
        ]
        # Rescrape returns a completely different question (text changed)
        new_questions = [
            {"id": "exam-q01", "text": "A completely different question"},
        ]
        result = _preserve_question_ids(existing, new_questions)
        # No text match → keep the new positional id as-is
        self.assertEqual(result[0]["id"], "exam-q01")
        self.assertEqual(result[0]["text"], "A completely different question")

    def test_scrape_all_warns_when_force_overwriting_existing_file(self) -> None:
        import io
        import sys
        import unittest.mock as mock
        from math_tutor.prior_amc_scraper import scrape_all_amc_10_exams

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            # Pre-create one exam file to simulate existing data
            existing = {
                "format": "explicit_curated_exam",
                "exam": {
                    "id": "prior-amc-2024-amc-10b",
                    "title": "2024 AMC 10B",
                    "questions": [{"id": "prior-amc-2024-amc-10b-q01", "text": "Q1"}],
                },
            }
            (output_dir / "prior_amc_2024_amc_10b.json").write_text(
                json.dumps(existing), encoding="utf-8"
            )

            captured = io.StringIO()
            # stub out the actual network scrape so the test is fast and offline
            def fake_scrape(url):
                # Return a minimal valid exam so the loop can proceed to the file
                # that already exists (2024 AMC 10B) and emit the warning.
                return {
                    "id": "prior-amc-stub",
                    "title": "Stub",
                    "bank": "prior-amc",
                    "bank_title": "Prior AMC",
                    "questions": [],
                    "question_count": 0,
                }

            with mock.patch("math_tutor.prior_amc_scraper.scrape_prior_amc_exam", fake_scrape):
                scrape_all_amc_10_exams(output_dir, skip_existing=False, _out=captured)

            output = captured.getvalue()
            self.assertIn("WARNING", output.upper())
            self.assertIn("prior-amc-2024-amc-10b", output)


class DateParsingTests(unittest.TestCase):
    def test_held_on_date_format(self) -> None:
        exam = _scrape(MAIN_PAGE_HTML_HELD_ON)
        self.assertEqual(exam["curated_metadata"]["administered_on"], "2022-11-10")

    def test_no_weekday_date_format(self) -> None:
        exam = _scrape(MAIN_PAGE_HTML_NO_WEEKDAY)
        self.assertEqual(exam["curated_metadata"]["administered_on"], "2020-01-30")

    def test_latex_image_date(self) -> None:
        exam = _scrape(MAIN_PAGE_HTML_LATEX_DATE)
        self.assertEqual(exam["curated_metadata"]["administered_on"], "2022-11-16")

    def test_future_tense_with_latex_date(self) -> None:
        exam = _scrape(MAIN_PAGE_HTML_FUTURE_LATEX_DATE)
        self.assertEqual(exam["curated_metadata"]["administered_on"], "2021-02-04")

    def test_no_date_returns_none(self) -> None:
        exam = _scrape(MAIN_PAGE_HTML_NO_DATE)
        self.assertIsNone(exam["curated_metadata"]["administered_on"])

    def test_date_without_weekday_held(self) -> None:
        exam = _scrape(MAIN_PAGE_HTML_DATE_NO_WEEKDAY_HELD)
        self.assertEqual(exam["curated_metadata"]["administered_on"], "2023-11-14")


if __name__ == "__main__":
    unittest.main()
