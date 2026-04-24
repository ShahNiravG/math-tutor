from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from math_tutor.canvas_course import CanvasFile
from math_tutor.prompt_catalog import PROMPTS_BY_SLUG
from math_tutor.prompt_saved_outputs import (
    evaluate_generation_decision,
    print_saved_prompt_pdfs,
    should_skip_generation,
)
from math_tutor.state_store import GeneratedOutputState


def _stub_canvas_file() -> CanvasFile:
    return CanvasFile(
        file_id=4401267,
        display_name="Alg 2 Trig H Chp 5.1 Note.docx",
        download_url="https://example.com/x",
        content_type="application/pdf",
        size=None,
        updated_at=None,
    )


def _empty_state(tmp_dir: Path) -> GeneratedOutputState:
    return GeneratedOutputState(path=tmp_dir / "generated_output_state.json", processed={})


def _call_skip(
    *,
    responses_dir: Path,
    slug: str,
    requested_prompt_slugs: set[str] | None = None,
) -> bool:
    stem = "4401267_alg-2trig-h-chp-5-1-note-docx"
    response_path = responses_dir / f"{stem}__{slug}.md"
    return should_skip_generation(
        canvas_file=_stub_canvas_file(),
        prompt_spec=PROMPTS_BY_SLUG[slug],
        response_path=response_path,
        response_html_path=response_path.with_suffix(".html"),
        response_pdf_path=response_path.with_suffix(".pdf"),
        generated_output_state=_empty_state(responses_dir.parent),
        force=False,
        force_generation=False,
        index=1,
        total=1,
        requested_prompt_slugs=requested_prompt_slugs or set(),
    )


class EvaluateGenerationDecisionTests(unittest.TestCase):
    def test_returns_none_when_no_artifacts_and_no_family_sibling(self) -> None:
        with TemporaryDirectory() as tmp:
            responses_dir = Path(tmp) / "responses"
            responses_dir.mkdir()
            stem = "4401267_alg-2trig-h-chp-5-1-note-docx"
            response_path = responses_dir / f"{stem}__study-guide-gpt5.md"
            self.assertIsNone(
                evaluate_generation_decision(
                    prompt_spec=PROMPTS_BY_SLUG["study-guide-gpt5"],
                    response_path=response_path,
                    response_html_path=response_path.with_suffix(".html"),
                    response_pdf_path=response_path.with_suffix(".pdf"),
                )
            )

    def test_returns_already_exists_reason(self) -> None:
        with TemporaryDirectory() as tmp:
            responses_dir = Path(tmp) / "responses"
            responses_dir.mkdir()
            stem = "4401267_alg-2trig-h-chp-5-1-note-docx"
            response_path = responses_dir / f"{stem}__inspiring-videos-gpt5.md"
            response_path.write_text("x")
            response_path.with_suffix(".html").write_text("x")
            reason = evaluate_generation_decision(
                prompt_spec=PROMPTS_BY_SLUG["inspiring-videos-gpt5"],
                response_path=response_path,
                response_html_path=response_path.with_suffix(".html"),
                response_pdf_path=response_path.with_suffix(".pdf"),
            )
            self.assertEqual(reason, "output files already exist")

    def test_returns_family_sibling_reason(self) -> None:
        with TemporaryDirectory() as tmp:
            responses_dir = Path(tmp) / "responses"
            responses_dir.mkdir()
            stem = "4401267_alg-2trig-h-chp-5-1-note-docx"
            (responses_dir / f"{stem}__study-guide-gemini.md").write_text("x")
            response_path = responses_dir / f"{stem}__study-guide-gpt5.md"
            reason = evaluate_generation_decision(
                prompt_spec=PROMPTS_BY_SLUG["study-guide-gpt5"],
                response_path=response_path,
                response_html_path=response_path.with_suffix(".html"),
                response_pdf_path=response_path.with_suffix(".pdf"),
            )
            assert reason is not None
            self.assertIn("study-guide variant already exists", reason)
            self.assertIn("--prompt study-guide-gpt5", reason)


class FamilySkipTests(unittest.TestCase):
    def test_skip_when_family_sibling_md_exists(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            responses_dir = tmp_dir / "responses"
            responses_dir.mkdir()
            stem = "4401267_alg-2trig-h-chp-5-1-note-docx"
            (responses_dir / f"{stem}__study-guide-gemini.md").write_text("x")
            self.assertTrue(_call_skip(responses_dir=responses_dir, slug="study-guide-gpt5"))

    def test_no_skip_when_slug_explicitly_requested(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            responses_dir = tmp_dir / "responses"
            responses_dir.mkdir()
            stem = "4401267_alg-2trig-h-chp-5-1-note-docx"
            (responses_dir / f"{stem}__study-guide-gemini.md").write_text("x")
            self.assertFalse(
                _call_skip(
                    responses_dir=responses_dir,
                    slug="study-guide-gpt5",
                    requested_prompt_slugs={"study-guide-gpt5"},
                )
            )

    def test_no_skip_for_non_family_prompts(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            responses_dir = tmp_dir / "responses"
            responses_dir.mkdir()
            stem = "4401267_alg-2trig-h-chp-5-1-note-docx"
            (responses_dir / f"{stem}__mental-math-gemini.md").write_text("x")
            self.assertFalse(_call_skip(responses_dir=responses_dir, slug="mental-math-gpt5"))

    def test_inspiring_videos_family_skip(self) -> None:
        with TemporaryDirectory() as tmp:
            tmp_dir = Path(tmp)
            responses_dir = tmp_dir / "responses"
            responses_dir.mkdir()
            stem = "4401267_alg-2trig-h-chp-5-1-note-docx"
            (responses_dir / f"{stem}__inspiring-videos-gpt4.md").write_text("x")
            self.assertTrue(_call_skip(responses_dir=responses_dir, slug="inspiring-videos-gpt5"))


class PromptSavedOutputsTests(unittest.TestCase):
    def test_print_saved_prompt_pdfs_dry_run_reports_matching_targets(self) -> None:
        with TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir)
            responses_dir = output_dir / "responses"
            responses_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = responses_dir / "study-guide.pdf"
            pdf_path.write_text("pdf", encoding="utf-8")

            (output_dir / "fetch_state.json").write_text(
                json.dumps(
                    {
                        "fetched": {
                            "1": {
                                "display_name": "Alg 2 Trig H Chp 5.1 Note.docx",
                                "pdf_path": str(output_dir / "downloads" / "note.pdf"),
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )
            (output_dir / "generated_output_state.json").write_text(
                json.dumps(
                    {
                        "processed": {
                            "1": {
                                "study-guide": {
                                    "display_name": "Alg 2 Trig H Chp 5.1 Note.docx",
                                    "prompt_title": "Study Guide",
                                    "response_pdf_path": str(pdf_path),
                                }
                            }
                        }
                    }
                ),
                encoding="utf-8",
            )

            with patch("builtins.print") as print_mock:
                print_saved_prompt_pdfs(
                    output_dir=output_dir,
                    prompt_slugs=("study-guide",),
                    chapter_filters=["5.1"],
                    printer="Brother",
                    dry_run=True,
                )

        printed_text = "\n".join(
            " ".join(str(arg) for arg in call.args)
            for call in print_mock.call_args_list
        )
        self.assertIn("Dry run", printed_text)
        self.assertIn("study-guide.pdf", printed_text)


if __name__ == "__main__":
    unittest.main()
