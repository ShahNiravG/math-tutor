"""Helpers for validating and rendering inspiring-video recommendations."""

from __future__ import annotations

import json
import re
from typing import Any, TypedDict
from urllib.parse import parse_qs, quote, urlparse

import httpx


class InspiringVideoRecommendation(TypedDict):
    title: str
    creator: str
    url: str
    why_it_inspires: str
    topics_matched: list[str]


def normalize_youtube_url(url: str) -> str | None:
    parsed = urlparse(url.strip())
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]

    video_id = ""
    if host == "youtu.be":
        video_id = parsed.path.strip("/").split("/", 1)[0]
    elif host == "youtube.com":
        if parsed.path == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        elif parsed.path.startswith("/shorts/"):
            video_id = parsed.path.split("/", 2)[2]

    video_id = re.sub(r"[^A-Za-z0-9_-].*$", "", video_id)
    if not video_id:
        return None
    return f"https://www.youtube.com/watch?v={video_id}"


def validate_youtube_url(url: str) -> tuple[str, dict[str, Any]] | None:
    normalized = normalize_youtube_url(url)
    if not normalized:
        return None

    oembed_url = f"https://www.youtube.com/oembed?url={quote(normalized, safe='')}&format=json"
    try:
        response = httpx.get(oembed_url, timeout=15.0, follow_redirects=True)
        response.raise_for_status()
        payload = response.json()
    except Exception:
        return None

    if not isinstance(payload, dict):
        return None
    if not payload.get("title") or not payload.get("author_name"):
        return None
    return normalized, payload


def parse_gemini_video_recommendations(
    *,
    output_text: str,
    prompt_slug: str,
) -> list[InspiringVideoRecommendation]:
    try:
        raw_items = json.loads(output_text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Gemini returned invalid JSON for {prompt_slug}.") from exc
    if not isinstance(raw_items, list):
        raise RuntimeError(f"Gemini returned an unexpected payload for {prompt_slug}.")

    validated: list[InspiringVideoRecommendation] = []
    seen_urls: set[str] = set()
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            continue
        url = str(raw_item.get("url") or "").strip()
        validated_result = validate_youtube_url(url)
        if not validated_result:
            continue
        normalized_url, oembed_payload = validated_result
        if normalized_url in seen_urls:
            continue
        seen_urls.add(normalized_url)
        validated.append(
            {
                "title": str(raw_item.get("title") or oembed_payload["title"]).strip()
                or str(oembed_payload["title"]).strip(),
                "creator": str(raw_item.get("creator") or oembed_payload["author_name"]).strip()
                or str(oembed_payload["author_name"]).strip(),
                "url": normalized_url,
                "why_it_inspires": str(raw_item.get("why_it_inspires") or "").strip(),
                "topics_matched": [
                    str(topic).strip()
                    for topic in raw_item.get("topics_matched") or []
                    if str(topic).strip()
                ],
            }
        )

    if not validated:
        raise RuntimeError("Gemini did not return any valid public YouTube links.")
    return validated


def render_inspiring_videos_markdown(recommendations: list[InspiringVideoRecommendation]) -> str:
    blocks: list[str] = []
    for index, item in enumerate(recommendations, start=1):
        topics = ", ".join(item.get("topics_matched") or [])
        blocks.append(
            "\n".join(
                [
                    f"### {index}. {item['title']}",
                    f"**Creator:** {item['creator']}",
                    f"**URL:** {item['url']}",
                    f"**Why it inspires:** {item['why_it_inspires']}",
                    f"**Topics matched:** {topics}",
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)
