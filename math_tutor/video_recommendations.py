"""Helpers for validating and rendering inspiring-video recommendations."""

from __future__ import annotations

import json
import re
from typing import Any, TypedDict
from urllib.parse import parse_qs, quote, quote_plus, urlparse

import httpx


class InspiringVideoRecommendation(TypedDict):
    title: str
    creator: str
    url: str
    why_it_inspires: str
    topics_matched: list[str]


_SEARCH_QUERY_BLOCK_PATTERN = re.compile(
    r"\*\*Google Search Query:\*\*\s*\n\s*`(?P<query>[^`\n]+)`",
    re.MULTILINE,
)


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


def build_google_search_query(*, title: str, creator: str) -> str:
    parts = [title.strip(), creator.strip(), "YouTube"]
    return " ".join(part for part in parts if part)


def build_google_search_url(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}"


def normalize_inspiring_videos_markdown(markdown_text: str) -> str:
    normalized = _SEARCH_QUERY_BLOCK_PATTERN.sub(
        lambda match: (
            f"**Google Search Link:** "
            f"[{match.group('query')}]" f"({build_google_search_url(match.group('query'))})"
        ),
        markdown_text,
    )

    if "google.com/search" in normalized:
        return normalized

    blocks: list[str] = []
    changed = False
    for block in normalized.split("\n\n---\n\n"):
        lines = block.splitlines()
        if not lines:
            blocks.append(block)
            continue
        if any("google.com/search" in line or "Google Search" in line for line in lines):
            blocks.append(block)
            continue
        heading = lines[0].strip()
        if not heading.startswith("### "):
            blocks.append(block)
            continue
        title = re.sub(r"^###\s+\d+\.\s*", "", heading).strip()
        title = re.sub(r"[*_`]+", "", title).strip()

        creator_index = next((index for index, line in enumerate(lines) if line.startswith("**Creator:** ")), -1)
        if creator_index < 0:
            blocks.append(block)
            continue
        creator = lines[creator_index].split("**Creator:** ", 1)[1].strip()
        if not title or not creator:
            blocks.append(block)
            continue

        search_query = build_google_search_query(title=title, creator=creator)
        search_line = f"**Google Search Link:** [{search_query}]({build_google_search_url(search_query)})"

        insert_at = creator_index + 1
        if insert_at < len(lines) and lines[insert_at].startswith("**URL:** "):
            insert_at += 1
        lines.insert(insert_at, search_line)
        blocks.append("\n".join(lines))
        changed = True

    if changed:
        return "\n\n---\n\n".join(blocks)
    return normalized


def render_inspiring_videos_markdown(recommendations: list[InspiringVideoRecommendation]) -> str:
    blocks: list[str] = []
    for index, item in enumerate(recommendations, start=1):
        topics = ", ".join(item.get("topics_matched") or [])
        search_query = build_google_search_query(title=item["title"], creator=item["creator"])
        blocks.append(
            "\n".join(
                [
                    f"### {index}. {item['title']}",
                    f"**Creator:** {item['creator']}",
                    f"**URL:** {item['url']}",
                    f"**Google Search Link:** [{search_query}]({build_google_search_url(search_query)})",
                    f"**Why it inspires:** {item['why_it_inspires']}",
                    f"**Topics matched:** {topics}",
                ]
            )
        )
    return "\n\n---\n\n".join(blocks)
