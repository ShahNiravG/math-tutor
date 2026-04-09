from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from math_tutor.challenge_builder import sync_curated_exam_bundle
from math_tutor.prior_amc_scraper import scrape_prior_amc_exam_from_html


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


if __name__ == "__main__":
    unittest.main()
