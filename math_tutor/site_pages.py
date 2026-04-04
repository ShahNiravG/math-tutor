"""Page-level HTML builders for generated site pages."""

from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

from math_tutor.site_cards import document_label, record_page_filename
from math_tutor.site_content import build_curriculum_guided_learning_prompt
from math_tutor.site_models import DocumentRecord
from math_tutor.site_records import render_document_overview_card, render_document_page_content
from math_tutor.site_sections import render_guided_learning_card, render_surface_header
from math_tutor.site_shell import render_page_shell


SITE_TITLE = "Algebra II with Trigonometry Tutor"


def _featured_record(records: list[DocumentRecord]) -> DocumentRecord | None:
    return records[0] if records else None


def build_index_html(
    *,
    records: list[DocumentRecord],
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    include_guided_learning: bool,
    site_page_href,
    experience_variant: str = "default",
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
    featured_record = _featured_record(records)
    if experience_variant == "staging":
        header_html = render_surface_header(
            active="home",
            base_path=base_path,
            eyebrow="Math Delight",
            title="Algebra II Trig Tutor",
            site_page_href=site_page_href,
            experience_variant=experience_variant,
        )
        featured_practice_href = (
            f"{site_page_href(record_page_filename(featured_record), base_path)}#practice"
            if featured_record
            else library_href
        )
        featured_learn_href = (
            f"{site_page_href(record_page_filename(featured_record), base_path)}#learn"
            if featured_record
            else library_href
        )
        featured_title = document_label(featured_record) if featured_record else "Your next chapter"
        body_html = f"""
        {header_html}
        <section class="landing-hero landing-hero-staging">
          <div class="landing-hero-copy">
            <span class="eyebrow">Today&apos;s Best Path</span>
            <h1 class="hero-title">Build confidence, one chapter at a time.</h1>
            <p class="page-intro">Review the chapter idea, practice with short questions, then test yourself. The site keeps each step visible so students never have to guess where to go next.</p>
            <div class="hero-action-grid">
              <a class="hero-action primary" href="{html.escape(featured_practice_href)}">Start Practice</a>
              <a class="hero-action" href="{html.escape(featured_learn_href)}">Review a Chapter</a>
              <a class="hero-action" href="{html.escape(challenges_href)}">Open Challenges</a>
            </div>
            <div class="landing-stats">
              <div class="stat-pill"><strong>{len(records)}</strong><span>chapters ready</span></div>
              <div class="stat-pill"><strong>{total_prompt_outputs}</strong><span>study outputs</span></div>
              <div class="stat-pill"><strong>{generated_at}</strong><span>latest update</span></div>
            </div>
          </div>
          <aside class="continue-card" data-continue-card>
            <span class="task-kicker">Continue</span>
            <h3 data-continue-title>{html.escape(featured_title)}</h3>
            <p class="continue-copy" data-continue-copy>Ready to pick up where you left off.</p>
            <a class="hero-action primary" data-continue-link href="{html.escape(featured_practice_href)}">Continue Learning</a>
          </aside>
        </section>
        <section class="content-card section-card section-surface">
          <div class="section-head">
            <div>
              <span class="eyebrow">Quick Start</span>
              <h3>Three steps, one direction</h3>
            </div>
          </div>
          <div class="quick-start-grid">
            <section class="prompt-card prompt-card-staging">
              <span class="task-kicker">1. Learn</span>
              <h3>Read the chapter idea</h3>
              <p class="task-copy">Students get the big picture first, so formulas and terms feel familiar before they solve anything.</p>
            </section>
            <section class="prompt-card prompt-card-staging">
              <span class="task-kicker">2. Practice</span>
              <h3>Do quick problems</h3>
              <p class="task-copy">Short practice builds confidence and lowers math anxiety before stretch work or timed work begins.</p>
            </section>
            <section class="prompt-card prompt-card-staging">
              <span class="task-kicker">3. Challenge</span>
              <h3>Test without extra hints</h3>
              <p class="task-copy">Challenge mode stays clean and focused so it feels like a real check for understanding.</p>
            </section>
          </div>
        </section>
        <section class="landing-grid landing-grid-staging">
          <a class="destination-card destination-library" href="{html.escape(library_href)}">
            <span class="destination-kicker">Learn</span>
            <h3>Chapter Library</h3>
            <p>Go straight to a chapter and jump into its learn, practice, or challenge section.</p>
            <span class="destination-link">Browse chapters</span>
          </a>
          <a class="destination-card destination-challenges" href="{html.escape(challenges_href)}">
            <span class="destination-kicker">Check</span>
            <h3>Challenge Exams</h3>
            <p>Take focused mental math or olympiad-style challenge sets with clear progress and resume support.</p>
            <span class="destination-link">Open challenge mode</span>
          </a>
          <a class="destination-card destination-live" href="{html.escape(live_tutor_href)}">
            <span class="destination-kicker">Coach</span>
            <h3>Live Tutor</h3>
            <p>Use an optional AI coaching setup when a student wants more help after their own first try.</p>
            <span class="destination-link">Set up AI coach</span>
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
            experience_variant=experience_variant,
        )
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
        experience_variant=experience_variant,
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
    experience_variant: str = "default",
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
        experience_variant=experience_variant,
    )
    record_html = render_document_page_content(
        record,
        output_dir,
        site_dir,
        base_path,
        include_guided_learning=include_guided_learning,
        assignments=assignments or [],
        site_page_href=site_page_href,
        experience_variant=experience_variant,
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
        experience_variant=experience_variant,
    )


def build_library_page_html(
    *,
    records: list[DocumentRecord],
    output_dir: Path,
    site_dir: Path,
    base_path: str,
    include_guided_learning: bool,
    site_page_href,
    experience_variant: str = "default",
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
            experience_variant=experience_variant,
        )
        for record in records
    )
    header_html = render_surface_header(
        active="library",
        base_path=base_path,
        eyebrow="Math Delight",
        title="Algebra II Trig Tutor",
        site_page_href=site_page_href,
        experience_variant=experience_variant,
    )
    if experience_variant == "staging":
        featured_record = _featured_record(records)
        featured_practice_href = (
            f"{site_page_href(record_page_filename(featured_record), base_path)}#practice"
            if featured_record
            else site_page_href("index.html", base_path)
        )
        body_html = f"""
        {header_html}
        <section class="content-card section-card section-surface">
          <div class="section-head">
            <div>
              <span class="eyebrow">Library</span>
              <h3>Choose a chapter, then pick your mode</h3>
            </div>
            <a class="section-link" href="{html.escape(featured_practice_href)}">Jump straight into practice</a>
          </div>
          <p class="page-intro">Every chapter now gives students three clear paths: learn the idea, practice with quick wins, or test themselves in challenge mode.</p>
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
            experience_variant=experience_variant,
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
        experience_variant=experience_variant,
    )


def build_live_tutor_page_html(
    *,
    records: list[DocumentRecord],
    base_path: str,
    site_page_href,
    experience_variant: str = "default",
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
        experience_variant=experience_variant,
    )
    if experience_variant == "staging":
        body_html = f"""
        {header_html}
        <section class="content-card section-card section-surface">
          <div class="section-head">
            <div>
              <span class="eyebrow">Live Tutor</span>
              <h3>Optional AI coaching after the student&apos;s first try</h3>
            </div>
          </div>
          <p class="page-intro">This is the fallback path for students who still need support after they review a chapter and attempt practice. It is helpful, but it is no longer the main path through the product.</p>
          <div class="quick-start-grid">
            <section class="prompt-card prompt-card-staging">
              <span class="task-kicker">When to use it</span>
              <h3>After a first attempt</h3>
              <p class="task-copy">Students should try the chapter summary and at least one practice set before opening external AI help.</p>
            </section>
            <section class="prompt-card prompt-card-staging">
              <span class="task-kicker">What to ask for</span>
              <h3>One step at a time</h3>
              <p class="task-copy">Ask for the next move, not the whole answer. That keeps the learning flow active instead of passive.</p>
            </section>
            <section class="prompt-card prompt-card-staging">
              <span class="task-kicker">Best outcome</span>
              <h3>Return to Math Delight</h3>
              <p class="task-copy">Use the coach to get unstuck, then come back and finish practice or challenge mode here.</p>
            </section>
          </div>
          {render_guided_learning_card(
              title="AI Coach Setup",
              description="Open Gemini or ChatGPT Study Mode, then use the curriculum-wide prompt below. Keep the conversation focused on next steps, not full spoilers.",
              prompt_text=curriculum_prompt,
              extra_links=[],
              experience_variant=experience_variant,
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
            experience_variant=experience_variant,
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
          experience_variant=experience_variant,
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
        experience_variant=experience_variant,
    )


def build_privacy_policy_page_html(
    *,
    records: list[DocumentRecord],
    base_path: str,
    site_page_href,
    experience_variant: str = "default",
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
        experience_variant=experience_variant,
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
        experience_variant=experience_variant,
    )
