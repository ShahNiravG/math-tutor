from __future__ import annotations

import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ChallengeTemplateTests(unittest.TestCase):
    def test_exam_template_uses_per_exam_session_storage(self) -> None:
        template = (ROOT / "challenges_src" / "exam.html").read_text(encoding="utf-8")

        self.assertIn("const SESSION_KEY_PREFIX = 'math_tutor_challenge_session:';", template)
        self.assertIn("function sessionKeyForExam(examId)", template)
        self.assertIn("questionCount: S.exam.questions.length,", template)

    def test_index_template_lists_multiple_saved_sessions(self) -> None:
        template = (ROOT / "challenges_src" / "index.html").read_text(encoding="utf-8")

        self.assertIn("const SESSION_KEY_PREFIX = 'math_tutor_challenge_session:';", template)
        self.assertIn("localStorage.key(i)", template)
        self.assertIn("renderResumeCards(completedSet, examIndexById);", template)
        self.assertIn("data-discard-key", template)

    def test_index_template_supports_bank_selection(self) -> None:
        template = (ROOT / "challenges_src" / "index.html").read_text(encoding="utf-8")

        self.assertIn("bank-picker", template)
        self.assertIn("selectedBank", template)
        self.assertIn("bank_title", template)
        self.assertIn("Choose a challenge bank", template)
        self.assertIn("cache: 'no-store'", template)

    def test_exam_and_result_templates_support_five_choice_mcq(self) -> None:
        exam_template = (ROOT / "challenges_src" / "exam.html").read_text(encoding="utf-8")
        result_template = (ROOT / "challenges_src" / "result.php").read_text(encoding="utf-8")
        partial_template = (ROOT / "challenges_src" / "partial_result.php").read_text(encoding="utf-8")

        self.assertIn("[A-E]", exam_template)
        self.assertIn("[A-E]", result_template)
        self.assertIn("[A-E]", partial_template)

    def test_exam_and_partial_result_templates_preserve_curated_source_metadata(self) -> None:
        exam_template = (ROOT / "challenges_src" / "exam.html").read_text(encoding="utf-8")
        partial_template = (ROOT / "challenges_src" / "partial_result.php").read_text(encoding="utf-8")

        self.assertIn("curated_source: q.curated_source || ''", exam_template)
        self.assertIn("curated_concept: q.curated_concept || ''", exam_template)
        self.assertIn("curated_source_link: q.curated_source_link || ''", exam_template)
        self.assertIn("Review Source", partial_template)
        self.assertIn("curated_source_link", partial_template)

    def test_progress_views_use_saved_question_counts(self) -> None:
        reports = (ROOT / "challenges_src" / "reports.php").read_text(encoding="utf-8")
        admin_delete = (ROOT / "challenges_src" / "admin" / "delete.php").read_text(encoding="utf-8")

        self.assertIn("answers_json", reports)
        self.assertIn("<?= $p['answered'] ?>/<?= $total_questions ?: '?' ?> answered", reports)
        self.assertIn("answers_json", admin_delete)
        self.assertIn("<?= (int)$record['answered_count'] ?>/<?= $progress_total ?: '?' ?>", admin_delete)

    def test_reports_template_allows_logged_in_user_to_resume_progress(self) -> None:
        reports = (ROOT / "challenges_src" / "reports.php").read_text(encoding="utf-8")

        self.assertIn("HTTP_CF_ACCESS_AUTHENTICATED_USER_EMAIL", reports)
        self.assertIn("'can_resume'    =>", reports)
        self.assertIn("Resume Challenge &rarr;", reports)
        self.assertIn("exam.html?id=", reports)
        self.assertIn("return_label", reports)

    def test_result_template_uses_hidden_copy_payload_instead_of_inline_json(self) -> None:
        template = (ROOT / "challenges_src" / "result.php").read_text(encoding="utf-8")

        self.assertIn('class="copy-payload"', template)
        self.assertIn('onclick="copyRawText(this)"', template)
        self.assertNotIn('onclick="copyRawText(this,<?= json_encode($copy_text) ?>)"', template)

    def test_partial_result_template_uses_hidden_copy_payload_instead_of_inline_json(self) -> None:
        template = (ROOT / "challenges_src" / "partial_result.php").read_text(encoding="utf-8")

        self.assertIn('class="copy-payload"', template)
        self.assertIn('onclick="copyRawText(this)"', template)
        self.assertNotIn('onclick="copyRawText(this,<?= json_encode($copy_text) ?>)"', template)


if __name__ == "__main__":
    unittest.main()
