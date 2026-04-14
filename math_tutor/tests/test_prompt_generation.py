from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import Mock, patch

from math_tutor.prompt_catalog import PROMPTS_BY_SLUG
from math_tutor.prompt_generation import generate_prompt_response, generate_tutor_response


class PromptGenerationTests(unittest.TestCase):
    def test_generate_tutor_response_sends_model_key(self) -> None:
        responses = Mock()
        files = Mock()
        files.create.return_value = SimpleNamespace(id="file_123")
        client = SimpleNamespace(files=files, responses=responses)
        responses.create.return_value = SimpleNamespace(output_text="done", id="resp_1")

        with TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "note.pdf"
            pdf_path.write_bytes(b"pdf")

            generate_tutor_response(
                client=client,
                pdf_path=pdf_path,
                model="gpt-5.4",
                prompt_text="Teach me",
            )

        kwargs = responses.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "gpt-5.4")
        self.assertNotIn("default_model", kwargs)

    def test_generate_prompt_response_routes_default_video_prompt_through_openai(self) -> None:
        openai_result = SimpleNamespace(output_text="videos", id="resp_2")
        with TemporaryDirectory() as temp_dir:
            pdf_path = Path(temp_dir) / "note.pdf"
            pdf_path.write_bytes(b"pdf")
            with patch("math_tutor.prompt_generation.generate_tutor_response") as generate_openai:
                generate_openai.return_value = openai_result

                result = generate_prompt_response(
                    client=object(),
                    gemini_client=None,
                    pdf_path=pdf_path,
                    default_model="gpt-5.4",
                    prompt_spec=PROMPTS_BY_SLUG["inspiring-videos"],
                    source_output=None,
                )

        self.assertEqual(result.output_text, "videos")
        self.assertEqual(result.response_id, "resp_2")
        generate_openai.assert_called_once()


if __name__ == "__main__":
    unittest.main()
