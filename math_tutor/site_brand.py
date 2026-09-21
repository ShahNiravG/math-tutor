"""Canonical brand marks for the generated multi-course site.

This module is the single source of truth for the Math Delight site mark and
each course mark. Page generators must render marks through here rather than
pasting SVG, so that a logo change is one edit instead of five.

Each mark shares the same geometry -- a rounded square on a diagonal gradient,
two concentric orbit rings, a mathematical motif, and a serif glyph -- so the
course marks read as siblings of the site mark rather than unrelated logos.
"""

from __future__ import annotations

import html
from dataclasses import dataclass
from urllib.parse import quote


@dataclass(frozen=True)
class BrandMark:
    """An immutable brand mark definition.

    ``motif_svg`` carries the parts unique to this mark (the curve, any accent
    line, and the floating dots). Everything else is shared geometry rendered
    by :func:`render_brand_mark`.
    """

    mark_id: str
    label: str
    glyph: str
    accent: str
    accent_soft: str
    glyph_font_size: int
    glyph_baseline: int
    gradient_stops: tuple[tuple[str, str], ...]
    ring_color: str
    outer_ring_opacity: str
    inner_ring_opacity: str
    glyph_color: str
    motif_svg: str
    favicon_glyph_font_size: int
    favicon_glyph_baseline: int
    favicon_glyph_color: str


SITE_MARK_ID = "site"


# Freeform wave with two floating points: the long-standing site mark.
_SITE_MOTIF = (
    '<path d="M12 43 C21 28, 28 52, 37 37 S53 21, 60 33" fill="none" '
    'stroke="#134f59" stroke-width="3.2" stroke-linecap="round"/>'
    '<circle cx="24" cy="25" r="3.4" fill="#fff7f0" stroke="#8b4a2c" stroke-width="1.4"/>'
    '<circle cx="51" cy="21" r="2.8" fill="#fff7f0" stroke="#8b4a2c" stroke-width="1.2"/>'
)

# A clean sine wave for trigonometry, in indigo for cool-against-warm contrast.
_ALGEBRA_MOTIF = (
    '<path d="M12 34 Q20 18, 28 34 T44 34 T60 34" fill="none" '
    'stroke="#23324f" stroke-width="3.2" stroke-linecap="round"/>'
    '<circle cx="16" cy="49" r="3.0" fill="#fff4ee" stroke="#7d3420" stroke-width="1.4"/>'
    '<circle cx="57" cy="47" r="2.4" fill="#fff4ee" stroke="#7d3420" stroke-width="1.2"/>'
)

# A parabola with a tangent line and a marked point of tangency: the derivative.
# The tangent is the one warm accent in a cool mark, which is what makes the
# tangency legible at 48px.
_CALCULUS_MOTIF = (
    '<path d="M12 18 Q36 46, 60 18" fill="none" '
    'stroke="#0b3d46" stroke-width="3.2" stroke-linecap="round"/>'
    '<path d="M13 22.1 L38 36.7" fill="none" '
    'stroke="#b4532c" stroke-width="2.4" stroke-linecap="round"/>'
    '<circle cx="24" cy="28.5" r="2.8" fill="#f2fbfb" stroke="#0b3d46" stroke-width="1.4"/>'
)


_BRAND_MARKS: tuple[BrandMark, ...] = (
    BrandMark(
        mark_id=SITE_MARK_ID,
        label="Math Delight",
        glyph="π",
        accent="#a14d2e",
        accent_soft="#ead2c5",
        glyph_font_size=21,
        glyph_baseline=53,
        gradient_stops=(("0%", "#fff5da"), ("55%", "#f3c98f"), ("100%", "#cf7c43")),
        ring_color="#8b4a2c",
        outer_ring_opacity="0.35",
        inner_ring_opacity="0.22",
        glyph_color="#8b4a2c",
        motif_svg=_SITE_MOTIF,
        favicon_glyph_font_size=46,
        favicon_glyph_baseline=54,
        favicon_glyph_color="#7d3f22",
    ),
    BrandMark(
        mark_id="algebra-2-trig",
        label="Algebra II / Trigonometry",
        glyph="θ",
        # The value Algebra already ships; keeping it means no colour shift.
        accent="#a14d2e",
        accent_soft="#ead2c5",
        glyph_font_size=21,
        glyph_baseline=55,
        # Pushed rosier than the site mark so the two are not confusable.
        gradient_stops=(("0%", "#ffeee8"), ("55%", "#e3a288"), ("100%", "#9d4c2f")),
        ring_color="#7d3420",
        outer_ring_opacity="0.32",
        inner_ring_opacity="0.2",
        glyph_color="#7d3420",
        motif_svg=_ALGEBRA_MOTIF,
        favicon_glyph_font_size=46,
        favicon_glyph_baseline=55,
        favicon_glyph_color="#6d2c1a",
    ),
    BrandMark(
        mark_id="ap-calculus-ab",
        label="AP Calculus AB",
        glyph="∫",
        accent="#12606b",
        accent_soft="#d3e6e8",
        glyph_font_size=24,
        glyph_baseline=57,
        gradient_stops=(("0%", "#e9f7f7"), ("55%", "#69b4b9"), ("100%", "#12606b")),
        ring_color="#0b4a54",
        outer_ring_opacity="0.3",
        inner_ring_opacity="0.18",
        glyph_color="#0b4a54",
        motif_svg=_CALCULUS_MOTIF,
        favicon_glyph_font_size=52,
        favicon_glyph_baseline=58,
        favicon_glyph_color="#08333b",
    ),
)


def get_brand_mark(mark_id: str) -> BrandMark:
    for mark in _BRAND_MARKS:
        if mark.mark_id == mark_id:
            return mark
    raise ValueError(f"Unknown brand mark: {mark_id}")


def render_favicon_svg(*, mark_id: str) -> str:
    """Return a simplified mark for tab-size rendering.

    At 16px the orbit rings, motif, and floating dots collapse into noise, so
    the favicon keeps only the gradient ground and an enlarged glyph.
    """

    mark = get_brand_mark(mark_id)
    gradient_id = "brandFavicon"
    stops = "".join(
        f'<stop offset="{offset}" stop-color="{color}"/>' for offset, color in mark.gradient_stops
    )
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 72 72">'
        f'<defs><linearGradient id="{gradient_id}" x1="0%" y1="0%" x2="100%" y2="100%">'
        f"{stops}</linearGradient></defs>"
        f'<rect width="72" height="72" rx="16" fill="url(#{gradient_id})"/>'
        f'<text x="36" y="{mark.favicon_glyph_baseline}" text-anchor="middle" '
        f'font-size="{mark.favicon_glyph_font_size}" font-family="Georgia, serif" '
        f'font-weight="700" fill="{mark.favicon_glyph_color}">{mark.glyph}</text>'
        "</svg>"
    )


def render_favicon_link_tag(*, mark_id: str) -> str:
    """Return an inline ``<link rel="icon">`` carrying the simplified mark.

    The SVG is fully percent-encoded. Hex colours contain ``#``, which would
    otherwise start a URI fragment and silently drop the rest of the document.
    """

    encoded = quote(render_favicon_svg(mark_id=mark_id), safe="")
    return f'<link rel="icon" type="image/svg+xml" href="data:image/svg+xml,{encoded}">'


def brand_mark_id_for_course(course_id: str | None) -> str:
    """Return the mark for ``course_id``, falling back to the site mark.

    Pages that are not owned by a course -- the portal above all -- carry the
    site mark, so an unknown or absent course is a fallback rather than an error.
    """

    if course_id is None:
        return SITE_MARK_ID
    for mark in _BRAND_MARKS:
        if mark.mark_id == course_id:
            return mark.mark_id
    return SITE_MARK_ID


def render_brand_mark(*, mark_id: str, variant_id: str) -> str:
    """Return the full SVG for ``mark_id``.

    ``variant_id`` scopes the gradient element id so that several marks can
    appear in one document without their gradients colliding.
    """

    mark = get_brand_mark(mark_id)
    gradient_id = f"brandGradient-{variant_id}"
    stops = "".join(
        f'<stop offset="{offset}" stop-color="{color}"/>' for offset, color in mark.gradient_stops
    )
    return (
        '<svg viewBox="0 0 72 72" role="img" xmlns="http://www.w3.org/2000/svg" '
        f'aria-label="{html.escape(mark.label)}">'
        f'<defs><linearGradient id="{gradient_id}" x1="0%" y1="0%" x2="100%" y2="100%">'
        f"{stops}</linearGradient></defs>"
        f'<rect width="72" height="72" rx="16" fill="url(#{gradient_id})"/>'
        f'<circle cx="36" cy="36" r="22" fill="none" stroke="{mark.ring_color}" '
        f'stroke-width="2.4" opacity="{mark.outer_ring_opacity}"/>'
        f'<circle cx="36" cy="36" r="14" fill="none" stroke="{mark.ring_color}" '
        f'stroke-width="1.7" opacity="{mark.inner_ring_opacity}"/>'
        f"{mark.motif_svg}"
        f'<text x="36" y="{mark.glyph_baseline}" text-anchor="middle" '
        f'font-size="{mark.glyph_font_size}" font-family="Georgia, serif" '
        f'font-weight="700" fill="{mark.glyph_color}">{mark.glyph}</text>'
        "</svg>"
    )


def render_course_accent_css(course_id: str | None) -> str:
    """Return a ``:root`` block binding the accent tokens to ``course_id``.

    Appended after the base stylesheet so the course value wins over the
    default token. Course identity is the only colour signal on the site;
    there is deliberately no per-chapter colour.
    """

    mark = get_brand_mark(brand_mark_id_for_course(course_id))
    return (
        "\n    :root {\n"
        f"      --accent: {mark.accent};\n"
        f"      --accent-soft: {mark.accent_soft};\n"
        "    }\n"
    )
