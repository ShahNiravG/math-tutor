from __future__ import annotations

import unittest
from unittest.mock import patch

from math_tutor.video_recommendations import (
    normalize_youtube_url,
    parse_gemini_video_recommendations,
    render_inspiring_videos_markdown,
)


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
        self.assertIn("**Topics matched:** Angles, Radians", markdown)
