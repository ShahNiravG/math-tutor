"""Page-level HTML builders for generated site pages."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

from math_tutor.site_cards import document_label
from math_tutor.site_content import build_curriculum_guided_learning_prompt
from math_tutor.site_models import DocumentRecord
from math_tutor.site_records import render_document_overview_card, render_document_page_content
from math_tutor.site_sections import render_guided_learning_card, render_surface_header
from math_tutor.site_shell import render_page_shell


SITE_TITLE = "Algebra II with Trigonometry Tutor"


def build_index_html(
    *,
    records: list[DocumentRecord],
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    include_guided_learning: bool,
    site_page_href,
) -> str:
    del output_dir, site_dir, include_guided_learning
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_prompt_outputs = sum(
        1 for record in records for prompt_output in record.prompt_outputs if prompt_output.processed_at
    )
    library_href = site_page_href("library.html", base_path)
    challenges_href = f"{base_path}challenges/index.html" if base_path else "challenges/index.html"
    live_tutor_href = site_page_href("live-tutor.html", base_path)
    privacy_policy_href = "https://mathdelight.com/site/privacy-policy.html"
    body_html = f"""
    <section class="landing-hero">
      <div class="home-brand">
        <div class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 72 72" role="img" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <linearGradient id="homeBrandGlow" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stop-color="#fff5da"/>
                <stop offset="55%" stop-color="#f3c98f"/>
                <stop offset="100%" stop-color="#cf7c43"/>
              </linearGradient>
            </defs>
            <rect width="72" height="72" rx="16" fill="url(#homeBrandGlow)"/>
            <circle cx="36" cy="36" r="22" fill="none" stroke="#8b4a2c" stroke-width="2.4" opacity="0.35"/>
            <circle cx="36" cy="36" r="14" fill="none" stroke="#8b4a2c" stroke-width="1.7" opacity="0.22"/>
            <path d="M12 43 C21 28, 28 52, 37 37 S53 21, 60 33" fill="none" stroke="#134f59" stroke-width="3.2" stroke-linecap="round"/>
            <circle cx="24" cy="25" r="3.4" fill="#fff7f0" stroke="#8b4a2c" stroke-width="1.4"/>
            <circle cx="51" cy="21" r="2.8" fill="#fff7f0" stroke="#8b4a2c" stroke-width="1.2"/>
            <text x="36" y="53" text-anchor="middle" font-size="21" font-family="Georgia, serif" font-weight="700" fill="#8b4a2c">π</text>
          </svg>
        </div>
        <div>
          <span class="eyebrow">Math Delight</span>
          <h1 class="home-brand-title">Algebra II Trig Tutor</h1>
        </div>
      </div>
      <div class="landing-copy">
        <span class="eyebrow">Algebra II with Trigonometry</span>
        <h2>Choose how you want to study today.</h2>
        <p class="page-intro">Start in the class-note library, jump into a timed challenge exam, or use the future live tutor once it is ready.</p>
      </div>
      <div class="landing-stats">
        <div class="stat-pill"><strong>{len(records)}</strong><span>chapters</span></div>
        <div class="stat-pill"><strong>{total_prompt_outputs}</strong><span>saved outputs</span></div>
        <div class="stat-pill"><strong>{generated_at}</strong><span>last build</span></div>
      </div>
    </section>
    <section class="landing-grid">
      <a class="destination-card destination-library" href="{html.escape(library_href)}">
        <span class="destination-kicker">01</span>
        <h3>Library</h3>
        <p>Browse chapter notes, summaries, guided study prompts, and AI-generated practice resources.</p>
        <span class="destination-link">Open library</span>
      </a>
      <a class="destination-card destination-challenges" href="{html.escape(challenges_href)}">
        <span class="destination-kicker">02</span>
        <h3>Challenge Exams</h3>
        <p>Work through mixed mental-math and olympiad sets with the focused exam flow already built into the site.</p>
        <span class="destination-link">Start an exam</span>
      </a>
      <a class="destination-card destination-live" href="{html.escape(live_tutor_href)}">
        <span class="destination-kicker">03</span>
        <h3>Live Tutor</h3>
        <p>Launch a full-curriculum guided learning session with one prompt that covers every chapter and can generate custom exams on demand.</p>
        <span class="destination-link">Open live tutor</span>
      </a>
    </section>
    <section class="landing-footer-note">
      <a href="{html.escape(privacy_policy_href)}">Privacy Policy</a>
    </section>
    """
    return render_page_shell(
        title=SITE_TITLE,
        records=records,
        active_record=None,
        body_html=body_html,
        total_prompt_outputs=total_prompt_outputs,
        generated_at=generated_at,
        base_path=base_path,
        site_page_href=site_page_href,
        page_kind="home",
    )


def build_record_page_html(
    *,
    record: DocumentRecord,
    records: list[DocumentRecord],
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    include_guided_learning: bool,
    assignments: list[Path] | None = None,
    site_page_href=None,
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_prompt_outputs = sum(
        1 for doc in records for prompt_output in doc.prompt_outputs if prompt_output.processed_at
    )
    header_html = render_surface_header(
        active="library",
        base_path=base_path,
        eyebrow="Math Delight",
        title="Algebra II Trig Tutor",
        site_page_href=site_page_href,
    )
    record_html = render_document_page_content(
        record,
        output_dir,
        site_dir,
        base_path,
        include_guided_learning=include_guided_learning,
        assignments=assignments or [],
        site_page_href=site_page_href,
    )
    body_html = f"""
    {header_html}
    {record_html}
    """
    return render_page_shell(
        title=f"{document_label(record)} - {SITE_TITLE}",
        records=records,
        active_record=record,
        body_html=body_html,
        total_prompt_outputs=total_prompt_outputs,
        generated_at=generated_at,
        base_path=base_path,
        site_page_href=site_page_href,
        page_kind="record",
    )


def build_library_page_html(
    *,
    records: list[DocumentRecord],
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    include_guided_learning: bool,
    site_page_href,
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_prompt_outputs = sum(
        1 for record in records for prompt_output in record.prompt_outputs if prompt_output.processed_at
    )
    overview_cards = "\n".join(
        render_document_overview_card(
            record,
            output_dir,
            site_dir,
            base_path,
            include_guided_learning=include_guided_learning,
            site_page_href=site_page_href,
        )
        for record in records
    )
    header_html = render_surface_header(
        active="library",
        base_path=base_path,
        eyebrow="Math Delight",
        title="Algebra II Trig Tutor",
        site_page_href=site_page_href,
    )
    body_html = f"""
    {header_html}
    <section class="content-card section-card">
      <div class="section-head">
        <div>
          <span class="eyebrow">Library</span>
          <h3>Chapter collection</h3>
        </div>
      </div>
      <p class="page-intro">Choose a chapter to open its study guide, practice tools, assignments, and guided learning links.</p>
      <div class="prompt-grid">
        {overview_cards}
      </div>
    </section>
    """
    return render_page_shell(
        title=f"Library - {SITE_TITLE}",
        records=records,
        active_record=None,
        body_html=body_html,
        total_prompt_outputs=total_prompt_outputs,
        generated_at=generated_at,
        base_path=base_path,
        site_page_href=site_page_href,
        page_kind="library",
    )


def build_live_tutor_page_html(
    *,
    records: list[DocumentRecord],
    base_path: str,
    site_page_href,
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_prompt_outputs = sum(
        1 for record in records for prompt_output in record.prompt_outputs if prompt_output.processed_at
    )
    curriculum_prompt = build_curriculum_guided_learning_prompt(records)
    header_html = render_surface_header(
        active="live-tutor",
        base_path=base_path,
        eyebrow="Math Delight",
        title="Algebra II Trig Tutor",
        site_page_href=site_page_href,
    )
    body_html = f"""
    {header_html}
    <section class="content-card section-card">
      <div class="section-head">
        <div>
          <span class="eyebrow">Live Tutor</span>
          <h3>Whole-course guided learning</h3>
        </div>
      </div>
      <p class="page-intro">This uses the same guided-learning launch pattern as the chapter pages, but with a single prompt covering the full Algebra II with Trigonometry curriculum.</p>
      {render_guided_learning_card(
          title="Live Tutor",
          description="Open Gemini or ChatGPT Study Mode, then use the curriculum-wide prompt below. Students can ask for a live exam at any difficulty after the session starts.",
          prompt_text=curriculum_prompt,
          extra_links=[],
      )}
    </section>
    """
    return render_page_shell(
        title=f"Live Tutor - {SITE_TITLE}",
        records=records,
        active_record=None,
        body_html=body_html,
        total_prompt_outputs=total_prompt_outputs,
        generated_at=generated_at,
        base_path=base_path,
        site_page_href=site_page_href,
        page_kind="live-tutor",
    )


def build_privacy_policy_page_html(
    *,
    records: list[DocumentRecord],
    base_path: str,
    site_page_href,
) -> str:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_prompt_outputs = sum(
        1 for record in records for prompt_output in record.prompt_outputs if prompt_output.processed_at
    )
    header_html = render_surface_header(
        active="home",
        base_path=base_path,
        eyebrow="Math Delight",
        title="Privacy Policy",
        site_page_href=site_page_href,
    )
    body_html = f"""
    {header_html}
    <section class="content-card section-card">
      <div class="section-head">
        <div>
          <span class="eyebrow">Legal</span>
          <h3>Privacy Policy</h3>
        </div>
      </div>
      <p class="page-intro">This privacy policy explains how Algebra II Trig Tutor collects, uses, and protects information when students or families use the website and related Google OAuth sign-in flow.</p>

      <h3>Information We Collect</h3>
      <p>We collect only the user's email address from Google Sign-In, along with app data needed to operate the service such as challenge exam progress, submitted answers, timestamps, and saved learning activity.</p>

      <h3>How We Use Information</h3>
      <p>We use collected information to authenticate users, provide access to tutoring and challenge features, save progress, display reports, improve the learning experience, maintain security, and communicate essential updates related to the service.</p>

      <h3>Google User Data</h3>
      <p>If you sign in with Google, we use only the user's email address to identify the account within the app and support the requested educational features. We do not sell Google user data, and we do not use it for advertising.</p>

      <h3>Data Sharing</h3>
      <p>We do not sell personal information. Data may be shared only with service providers or hosting platforms that help operate the application, or when required by law, security needs, or protection of rights.</p>

      <h3>Data Retention</h3>
      <p>We keep information only as long as reasonably necessary to operate the tutoring service, maintain saved progress, review challenge results, meet legal obligations, or resolve disputes.</p>

      <h3>Security</h3>
      <p>We use reasonable administrative and technical safeguards to protect stored information. However, no method of transmission or storage is completely secure, so we cannot guarantee absolute security.</p>

      <h3>Your Choices</h3>
      <p>You may stop using the service at any time. If you would like your stored data reviewed or deleted, you can contact us using the contact method associated with this application or site.</p>

      <h3>Children and Education</h3>
      <p>This site is intended to support educational use. Parents, guardians, schools, or authorized users should ensure that use of the app complies with their local policies and requirements.</p>

      <h3>Changes to This Policy</h3>
      <p>We may update this privacy policy from time to time. Any updated version will be posted on this page with the current effective build date shown in the site footer.</p>

      <h3>Contact</h3>
      <p>For privacy-related questions about this application, please use the contact details associated with the website, school, or app administrator managing this deployment.</p>
    </section>
    """
    return render_page_shell(
        title=f"Privacy Policy - {SITE_TITLE}",
        records=records,
        active_record=None,
        body_html=body_html,
        total_prompt_outputs=total_prompt_outputs,
        generated_at=generated_at,
        base_path=base_path,
        site_page_href=site_page_href,
        page_kind="live-tutor",
    )
