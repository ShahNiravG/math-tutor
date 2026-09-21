from __future__ import annotations

import unittest
from pathlib import Path

from math_tutor.site_brand import (
    render_favicon_link_tag,
    render_favicon_svg,
    SITE_MARK_ID,
    brand_mark_id_for_course,
    get_brand_mark,
    render_brand_mark,
)
from math_tutor.site_courses import COURSE_REGISTRY, get_course
from math_tutor.site_pages import build_index_html
from math_tutor.site_portal import build_empty_course_html, build_portal_html
from math_tutor.site_sections import render_surface_header
from math_tutor.site_theme import get_site_page_styles


# The historic Math Delight mark. These fragments have been on the deployed site
# since before the multi-course split; pinning them here means an accidental
# redraw of the site logo fails the suite instead of shipping.
HISTORIC_WAVE_PATH = "M12 43 C21 28, 28 52, 37 37 S53 21, 60 33"
HISTORIC_OUTER_RING = '<circle cx="36" cy="36" r="22" fill="none" stroke="#8b4a2c" stroke-width="2.4" opacity="0.35"/>'


class SiteMarkTests(unittest.TestCase):
    def test_site_mark_renders_the_long_standing_detailed_pi_mark(self) -> None:
        svg = render_brand_mark(mark_id="site", variant_id="header")

        self.assertIn('viewBox="0 0 72 72"', svg)
        self.assertIn(HISTORIC_WAVE_PATH, svg)
        self.assertIn(HISTORIC_OUTER_RING, svg)
        self.assertIn(">π</text>", svg)

    def test_mark_scopes_its_gradient_id_to_the_caller_supplied_variant(self) -> None:
        header = render_brand_mark(mark_id="site", variant_id="header")
        hero = render_brand_mark(mark_id="site", variant_id="hero")

        self.assertIn('id="brandGradient-header"', header)
        self.assertIn("url(#brandGradient-header)", header)
        self.assertNotIn("brandGradient-hero", header)
        self.assertIn('id="brandGradient-hero"', hero)
        self.assertIn("url(#brandGradient-hero)", hero)


class CourseMarkTests(unittest.TestCase):
    def test_each_course_has_its_own_glyph(self) -> None:
        self.assertEqual(get_brand_mark("site").glyph, "π")
        self.assertEqual(get_brand_mark("algebra-2-trig").glyph, "θ")
        self.assertEqual(get_brand_mark("ap-calculus-ab").glyph, "∫")

    def test_course_marks_keep_the_shared_family_geometry(self) -> None:
        for mark_id in ("site", "algebra-2-trig", "ap-calculus-ab"):
            svg = render_brand_mark(mark_id=mark_id, variant_id="header")
            with self.subTest(mark_id=mark_id):
                self.assertIn('viewBox="0 0 72 72"', svg)
                self.assertIn('<rect width="72" height="72" rx="16"', svg)
                self.assertIn('r="22"', svg)
                self.assertIn('r="14"', svg)

    def test_course_marks_are_visually_distinct_from_each_other(self) -> None:
        algebra = get_brand_mark("algebra-2-trig")
        calculus = get_brand_mark("ap-calculus-ab")
        site = get_brand_mark(SITE_MARK_ID)

        gradients = {mark.gradient_stops for mark in (site, algebra, calculus)}
        self.assertEqual(len(gradients), 3, "each mark needs its own gradient")

        motifs = {mark.motif_svg for mark in (site, algebra, calculus)}
        self.assertEqual(len(motifs), 3, "each mark needs its own motif")

    def test_unknown_mark_is_rejected_rather_than_silently_falling_back(self) -> None:
        with self.assertRaises(ValueError):
            get_brand_mark("trigonometry-ii")

    def test_course_ids_resolve_to_their_mark_and_anything_else_to_the_site_mark(self) -> None:
        self.assertEqual(brand_mark_id_for_course("algebra-2-trig"), "algebra-2-trig")
        self.assertEqual(brand_mark_id_for_course("ap-calculus-ab"), "ap-calculus-ab")
        self.assertEqual(brand_mark_id_for_course(None), SITE_MARK_ID)

    def test_every_registered_course_has_a_mark(self) -> None:
        for course in COURSE_REGISTRY:
            with self.subTest(course=course.course_id):
                mark = get_brand_mark(brand_mark_id_for_course(course.course_id))
                self.assertEqual(mark.label, course.display_name)


class FaviconTests(unittest.TestCase):
    def test_favicon_drops_the_detail_that_turns_to_mud_at_tab_size(self) -> None:
        svg = render_favicon_svg(mark_id=SITE_MARK_ID)

        self.assertIn('<rect width="72" height="72" rx="16"', svg)
        self.assertIn(">π</text>", svg)
        self.assertNotIn('r="22"', svg)
        self.assertNotIn('r="14"', svg)
        self.assertNotIn(HISTORIC_WAVE_PATH, svg)

    def test_favicon_enlarges_the_glyph_relative_to_the_full_mark(self) -> None:
        mark = get_brand_mark(SITE_MARK_ID)

        self.assertGreater(mark.favicon_glyph_font_size, mark.glyph_font_size)

    def test_favicon_link_percent_encodes_hashes_so_the_uri_is_not_truncated(self) -> None:
        tag = render_favicon_link_tag(mark_id=SITE_MARK_ID)

        self.assertIn('rel="icon"', tag)
        self.assertIn('type="image/svg+xml"', tag)
        self.assertIn("data:image/svg+xml,", tag)
        # A literal '#' would start a fragment and drop every colour after it.
        href = tag.split('href="', 1)[1].rsplit('"', 1)[0]
        self.assertNotIn("#", href)
        self.assertIn("%23", href)

    def test_every_mark_produces_a_usable_favicon(self) -> None:
        for mark_id in (SITE_MARK_ID, "algebra-2-trig", "ap-calculus-ab"):
            with self.subTest(mark_id=mark_id):
                tag = render_favicon_link_tag(mark_id=mark_id)
                self.assertIn("data:image/svg+xml,", tag)
                self.assertNotIn("#", tag.split('href="', 1)[1].rsplit('"', 1)[0])


class SingleSourceOfTruthTests(unittest.TestCase):
    """The mark lived in five pasted copies before site_brand.py existed.

    These tests are the thing that keeps it from drifting back apart.
    """

    def test_no_other_python_module_defines_the_mark_geometry(self) -> None:
        package_dir = Path(__file__).resolve().parents[1]

        offenders = [
            path.name
            for path in sorted(package_dir.glob("*.py"))
            if path.name != "site_brand.py" and HISTORIC_WAVE_PATH in path.read_text(encoding="utf-8")
        ]

        self.assertEqual(offenders, [], "brand SVG must only live in site_brand.py")

    def test_no_module_hand_rolls_a_brand_gradient(self) -> None:
        package_dir = Path(__file__).resolve().parents[1]

        offenders = [
            path.name
            for path in sorted(package_dir.glob("*.py"))
            if path.name != "site_brand.py" and "BrandGlow" in path.read_text(encoding="utf-8")
        ]

        self.assertEqual(offenders, [], "gradients are scoped by site_brand.render_brand_mark")


class CourseSurfaceMarkTests(unittest.TestCase):
    def test_surface_header_carries_the_mark_of_its_own_course(self) -> None:
        calculus = render_surface_header(
            active="home",
            base_path="/site/courses/ap-calculus-ab/",
            eyebrow="Math Delight",
            title="AP Calculus AB Tutor",
            site_page_href=lambda filename, base_path: f"{base_path}{filename}",
            course=get_course("ap-calculus-ab"),
            portal_href="/site/index.html",
        )
        algebra = render_surface_header(
            active="home",
            base_path="/site/courses/algebra-2-trig/",
            eyebrow="Math Delight",
            title="Algebra II Trig Tutor",
            site_page_href=lambda filename, base_path: f"{base_path}{filename}",
            course=get_course("algebra-2-trig"),
            portal_href="/site/index.html",
        )

        self.assertIn(">∫</text>", calculus)
        self.assertNotIn(">π</text>", calculus)
        self.assertIn(">θ</text>", algebra)
        self.assertNotIn(">π</text>", algebra)


class FaviconWiringTests(unittest.TestCase):
    def test_course_pages_carry_their_own_course_favicon(self) -> None:
        page = build_index_html(
            records=[],
            output_dir=Path("/tmp/out"),
            site_dir=Path("/tmp/out/site"),
            base_path="/site/courses/ap-calculus-ab/",
            course=get_course("ap-calculus-ab"),
            portal_href="/site/index.html",
            include_guided_learning=False,
            site_page_href=lambda filename, base_path: f"{base_path}{filename}",
        )

        self.assertIn('rel="icon"', page)
        self.assertIn(render_favicon_link_tag(mark_id="ap-calculus-ab"), page)

    def test_portal_carries_the_site_favicon(self) -> None:
        page = build_portal_html(courses=COURSE_REGISTRY, base_path="/site/")

        self.assertIn('rel="icon"', page)
        self.assertIn(render_favicon_link_tag(mark_id=SITE_MARK_ID), page)


class PortalMarkTests(unittest.TestCase):
    def test_portal_masthead_uses_the_real_site_mark(self) -> None:
        portal = build_portal_html(courses=COURSE_REGISTRY, base_path="/site/")

        self.assertIn(HISTORIC_WAVE_PATH, portal)

    def test_portal_no_longer_uses_the_one_off_circled_glyph(self) -> None:
        portal = build_portal_html(courses=COURSE_REGISTRY, base_path="/site/")

        self.assertNotIn('class="wordmark-symbol"', portal)

    def test_each_course_card_carries_that_course_mark(self) -> None:
        portal = build_portal_html(courses=COURSE_REGISTRY, base_path="/site/")

        self.assertIn(">θ</text>", portal)
        self.assertIn(">∫</text>", portal)

    def test_empty_course_page_uses_its_course_mark_not_a_page_specific_glyph(self) -> None:
        empty = build_empty_course_html(
            course=get_course("ap-calculus-ab"),
            portal_href="/site/index.html",
        )

        self.assertIn(">∫</text>", empty)
        self.assertNotIn('class="wordmark-symbol"', empty)


class CourseAccentTests(unittest.TestCase):
    # The value Algebra has shipped with. Algebra pages must not shift colour.
    HISTORIC_ALGEBRA_ACCENT = "#a14d2e"

    def test_algebra_keeps_the_accent_it_already_ships(self) -> None:
        self.assertEqual(get_brand_mark("algebra-2-trig").accent, self.HISTORIC_ALGEBRA_ACCENT)

    def test_calculus_uses_its_own_accent(self) -> None:
        calculus = get_brand_mark("ap-calculus-ab").accent

        self.assertEqual(calculus, "#12606b")
        self.assertNotEqual(calculus, self.HISTORIC_ALGEBRA_ACCENT)

    def test_page_styles_bind_the_accent_to_the_course(self) -> None:
        algebra_css = get_site_page_styles("default", course_id="algebra-2-trig")
        calculus_css = get_site_page_styles("default", course_id="ap-calculus-ab")

        self.assertIn(f"--accent: {self.HISTORIC_ALGEBRA_ACCENT}", algebra_css)
        self.assertIn("--accent: #12606b", calculus_css)

    def test_accent_override_is_the_last_definition_so_it_wins(self) -> None:
        calculus_css = get_site_page_styles("default", course_id="ap-calculus-ab")

        self.assertGreater(
            calculus_css.rindex("--accent: #12606b"),
            calculus_css.rindex("--accent: #a14d2e"),
            "course override must come after the base token to take effect",
        )

    def test_unknown_course_falls_back_without_raising(self) -> None:
        css = get_site_page_styles("default", course_id=None)

        self.assertIn("--accent:", css)


CHALLENGE_PAGES = ("index.html", "exam.html")


class ChallengeMarkDriftTests(unittest.TestCase):
    """challenges_src/*.html is byte-copied to the deploy tree.

    It cannot import site_brand, so the mark is necessarily duplicated there.
    These tests are what keeps that duplicate from drifting: if the canonical
    mark changes and the challenge pages are not updated, the suite fails.
    """

    def setUp(self) -> None:
        self.challenges_src = Path(__file__).resolve().parents[1] / "challenges_src"

    def test_challenge_pages_embed_the_canonical_challenge_mark(self) -> None:
        # Challenges belong to Algebra only, so they carry the Algebra mark.
        expected = render_brand_mark(mark_id="algebra-2-trig", variant_id="challenge")

        for page in CHALLENGE_PAGES:
            with self.subTest(page=page):
                markup = (self.challenges_src / page).read_text(encoding="utf-8")
                self.assertIn(expected, markup)

    def test_challenge_pages_carry_no_stale_hand_rolled_mark(self) -> None:
        for page in CHALLENGE_PAGES:
            with self.subTest(page=page):
                markup = (self.challenges_src / page).read_text(encoding="utf-8")
                self.assertNotIn("challengeBrandGlow", markup)
                self.assertNotIn(HISTORIC_WAVE_PATH, markup)

    def test_challenge_pages_carry_the_challenge_favicon(self) -> None:
        expected = render_favicon_link_tag(mark_id="algebra-2-trig")

        for page in CHALLENGE_PAGES:
            with self.subTest(page=page):
                markup = (self.challenges_src / page).read_text(encoding="utf-8")
                self.assertIn(expected, markup)

    def test_challenge_pages_name_the_course_that_owns_challenges(self) -> None:
        """Only Algebra supports challenges today.

        If another course ever enables them, this fails and forces the
        hardcoded title in challenges_src to become build-substituted.
        """

        challenge_courses = [course for course in COURSE_REGISTRY if course.supports_challenges]

        self.assertEqual([course.course_id for course in challenge_courses], ["algebra-2-trig"])
        for page in CHALLENGE_PAGES:
            with self.subTest(page=page):
                markup = (self.challenges_src / page).read_text(encoding="utf-8")
                self.assertIn("Algebra II Trig Tutor", markup)


if __name__ == "__main__":
    unittest.main()
