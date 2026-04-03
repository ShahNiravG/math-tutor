from __future__ import annotations

import unittest
from pathlib import Path

from math_tutor.canvas_course import CanvasFile
from math_tutor.generated_metadata import (
    build_generated_metadata,
    normalize_metadata_payload,
    provider_name_for_model,
)
from math_tutor.prompt_catalog import PROMPTS_BY_SLUG


class GeneratedMetadataTests(unittest.TestCase):
    def test_provider_name_for_model(self) -> None:
        self.assertEqual(provider_name_for_model("gpt-5.4"), "openai")
        self.assertEqual(provider_name_for_model("gemini-3.1-pro-preview"), "gemini")

    def test_normalize_metadata_payload_infers_provider_from_model(self) -> None:
        payload = normalize_metadata_payload(
            {
                "model": "gemini-3.1-pro-preview",
                "response_id": None,
            }
        )

        self.assertEqual(payload["model"], "gemini-3.1-pro-preview")
        self.assertEqual(payload["provider"], "gemini")
        self.assertIn("response_id", payload)

    def test_build_generated_metadata_uses_neutral_keys(self) -> None:
        canvas_file = CanvasFile(
            file_id=123,
            display_name="Alg 2 Trig H Chp 5.1 Note.docx",
            download_url="https://example.com/file.pdf",
            content_type="application/pdf",
            size=None,
            updated_at=None,
        )

        payload = build_generated_metadata(
            canvas_file=canvas_file,
            prompt_spec=PROMPTS_BY_SLUG["mental-math-gpt5"],
            pdf_path=Path("/tmp/source.pdf"),
            response_path=Path("/tmp/response.md"),
            response_html_path=Path("/tmp/response.html"),
            response_pdf_path=Path("/tmp/response.pdf"),
            model_name="gpt-5.4",
            response_id="resp_123",
        )

        self.assertEqual(payload["provider"], "openai")
        self.assertEqual(payload["model"], "gpt-5.4")
        self.assertEqual(payload["response_id"], "resp_123")
        self.assertNotIn("openai_model", payload)
        self.assertNotIn("openai_response_id", payload)


if __name__ == "__main__":
    unittest.main()
