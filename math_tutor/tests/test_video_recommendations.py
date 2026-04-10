from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from math_tutor.video_recommendations import (
    normalize_youtube_url,
    parse_gemini_video_recommendations,
    render_inspiring_videos_markdown,
    validate_youtube_url,
)


class ValidateYoutubeUrlTests(unittest.TestCase):
    """Contract: returns ``None`` for network/HTTP/parse failures only.

    Programming errors (``AttributeError``, ``KeyError``, etc.) must not be
    swallowed — they indicate bugs we want to see, not transient failures.
    """

    def test_returns_none_on_http_error(self) -> None:
        import httpx
        with patch("math_tutor.video_recommendations.httpx.get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("refused")
            self.assertIsNone(validate_youtube_url("https://youtu.be/abc123_DEF"))

    def test_returns_none_on_http_status_error(self) -> None:
        import httpx
        with patch("math_tutor.video_recommendations.httpx.get") as mock_get:
            response = mock_get.return_value
            response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "404", request=None, response=None  # type: ignore[arg-type]
            )
            self.assertIsNone(validate_youtube_url("https://youtu.be/abc123_DEF"))

    def test_returns_none_on_invalid_json(self) -> None:
        with patch("math_tutor.video_recommendations.httpx.get") as mock_get:
            response = mock_get.return_value
            response.raise_for_status = lambda: None
            response.json.side_effect = json.JSONDecodeError("bad", "", 0)
            self.assertIsNone(validate_youtube_url("https://youtu.be/abc123_DEF"))

    def test_does_not_swallow_programming_errors(self) -> None:
        with patch("math_tutor.video_recommendations.httpx.get") as mock_get:
            response = mock_get.return_value
            response.raise_for_status = lambda: None
            response.json.side_effect = AttributeError("typo in code")
            with self.assertRaises(AttributeError):
                validate_youtube_url("https://youtu.be/abc123_DEF")


class VideoRecommendationsTests(unittest.TestCase):
    def test_normalize_youtube_url_accepts_watch_and_short_urls(self) -> None:
        self.assertEqual(
            normalize_youtube_url("https://www.youtube.com/watch?v=abc123_DEF"),
            "https://www.youtube.com/watch?v=abc123_DEF",
        )
        self.assertEqual(
            normalize_youtube_url("https://youtu.be/abc123_DEF?t=12"),
            "https://www.youtube.com/watch?v=abc123_DEF",
        )
        self.assertIsNone(normalize_youtube_url("https://example.com/video"))

    def test_parse_gemini_video_recommendations_validates_and_deduplicates(self) -> None:
        payload = """
        [
          {"url": "https://youtu.be/abc123_DEF", "title": "Video A", "creator": "Teacher", "why_it_inspires": "Good", "topics_matched": ["Angles"]},
          {"url": "https://www.youtube.com/watch?v=abc123_DEF", "title": "Video A2", "creator": "Teacher", "why_it_inspires": "Duplicate", "topics_matched": ["Angles"]}
        ]
        """
        with patch("math_tutor.video_recommendations.validate_youtube_url") as validate:
            validate.return_value = (
                "https://www.youtube.com/watch?v=abc123_DEF",
                {"title": "Fallback", "author_name": "Fallback Author"},
            )
            recommendations = parse_gemini_video_recommendations(
                output_text=payload,
                prompt_slug="inspiring-videos-gemini",
            )

        self.assertEqual(len(recommendations), 1)
        self.assertEqual(recommendations[0]["title"], "Video A")

    def test_render_inspiring_videos_markdown_formats_sections(self) -> None:
        markdown = render_inspiring_videos_markdown(
            [
                {
                    "title": "Video A",
                    "creator": "Teacher",
                    "url": "https://www.youtube.com/watch?v=abc123_DEF",
                    "why_it_inspires": "Good",
                    "topics_matched": ["Angles", "Radians"],
                }
            ]
        )

        self.assertIn("### 1. Video A", markdown)
        self.assertIn("**Google Search Link:** [Video A Teacher YouTube]", markdown)
        self.assertIn(
            "(https://www.google.com/search?q=Video+A+Teacher+YouTube)",
            markdown,
        )
        self.assertIn("**Topics matched:** Angles, Radians", markdown)
