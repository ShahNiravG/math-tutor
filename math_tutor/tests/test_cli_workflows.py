from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import Mock

from math_tutor.canvas_course import CanvasFile
from math_tutor.cli_workflows import FileBatchContext, process_file_batch
from math_tutor.prompt_catalog import PROMPTS_BY_SLUG
from math_tutor.state_store import FetchState, GeneratedOutputState


class CliWorkflowTests(unittest.TestCase):
    def test_process_file_batch_runs_each_file_with_stable_indexing(self) -> None:
        process_file_fn = Mock()
        files = [
            CanvasFile(
                file_id=1,
                display_name="Alg 2 Trig H Chp 5.1 Note.docx",
                download_url="https://example.com/1",
                content_type="application/pdf",
                size=None,
                updated_at=None,
            ),
            CanvasFile(
                file_id=2,
                display_name="Alg 2 Trig H Chp 5.2 Note.docx",
                download_url="https://example.com/2",
                content_type="application/pdf",
                size=None,
                updated_at=None,
            ),
        ]
        batch_context = FileBatchContext(
            canvas_client=None,
            openai_client=None,
            gemini_client=None,
            pdf_browser=None,
            downloads_dir=Path("/tmp/downloads"),
            responses_dir=Path("/tmp/responses"),
            metadata_dir=Path("/tmp/metadata"),
            fetch_state=FetchState(path=Path("/tmp/fetch_state.json"), fetched={}),
            generated_output_state=GeneratedOutputState(
                path=Path("/tmp/generated_output_state.json"),
                processed={},
            ),
            default_model="gpt-5.4",
            prompts=(PROMPTS_BY_SLUG["study-guide"],),
            forced_prompt_slugs=set(),
            force=False,
            fetch_only=False,
            force_generation=False,
        )

        processed_ids = process_file_batch(
            files=files,
            batch_context=batch_context,
            process_file_fn=process_file_fn,
        )

        self.assertEqual(processed_ids, {"1", "2"})
        self.assertEqual(process_file_fn.call_count, 2)
        first_call = process_file_fn.call_args_list[0].kwargs
        second_call = process_file_fn.call_args_list[1].kwargs
        self.assertEqual(first_call["index"], 1)
        self.assertEqual(first_call["total"], 2)
        self.assertEqual(second_call["index"], 2)
        self.assertEqual(second_call["total"], 2)


if __name__ == "__main__":
    unittest.main()
