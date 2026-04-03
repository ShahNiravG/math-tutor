from __future__ import annotations

import unittest

from math_tutor.response_artifacts import (
    build_response_html,
    markdown_to_html,
    response_document_title,
    slugify,
)


class ResponseArtifactsTests(unittest.TestCase):
    def test_markdown_to_html_renders_basic_blocks(self) -> None:
        html = markdown_to_html("# Title\n\nParagraph with **bold** text.\n\n- One\n- Two\n\n---")
        self.assertIn("<h2>Title</h2>", html)
        self.assertIn("<strong>bold</strong>", html)
        self.assertIn("<ul>", html)
        self.assertIn("<li>One</li>", html)
        self.assertIn("<hr>", html)

    def test_response_document_title_prefers_chapter_label(self) -> None:
        self.assertEqual(
            response_document_title("Alg 2 Trig H Chp 5.1 Note.docx"),
            "Algebra II with Trigonometry Chapter 5.1",
        )

    def test_build_response_html_includes_copy_button_only_for_supported_prompts(self) -> None:
        copy_html = build_response_html(
            title="Alg 2 Trig H Chp 5.1 Note.docx",
            prompt_title="Mental Math",
            markdown_text="1. Test question",
            pdf_label="note.pdf",
            pdf_href="note.pdf",
            prompt_slug="mental-math-gpt5",
        )
        study_html = build_response_html(
            title="Alg 2 Trig H Chp 5.1 Note.docx",
            prompt_title="Study Guide",
            markdown_text="Regular paragraph",
            pdf_label="note.pdf",
            pdf_href="note.pdf",
            prompt_slug="study-guide",
        )
        self.assertIn("copy-q-btn", copy_html)
        self.assertNotIn("copy-q-btn", study_html)

    def test_slugify_normalizes_document_names(self) -> None:
        self.assertEqual(slugify("Alg 2 Trig H Chp 5.1 Note"), "alg-2-trig-h-chp-5-1-note")


if __name__ == "__main__":
    unittest.main()
