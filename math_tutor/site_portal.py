"""Render the multi-course portal and empty course experiences."""

from __future__ import annotations

import html

from math_tutor.site_courses import CourseConfig


PORTAL_STYLES = """
    :root {
      --paper: #f4efe4;
      --paper-deep: #e7dece;
      --ink: #17252c;
      --muted: #5d696c;
      --line: rgba(23, 37, 44, 0.18);
      --algebra: #9d4c2f;
      --calculus: #12606b;
      --white: #fffdf7;
    }
    * { box-sizing: border-box; }
    html { min-height: 100%; }
    body {
      min-height: 100vh;
      margin: 0;
      color: var(--ink);
      background:
        linear-gradient(rgba(23, 37, 44, 0.035) 1px, transparent 1px),
        linear-gradient(90deg, rgba(23, 37, 44, 0.035) 1px, transparent 1px),
        radial-gradient(circle at 12% 8%, rgba(202, 135, 84, 0.28), transparent 28rem),
        radial-gradient(circle at 88% 92%, rgba(18, 96, 107, 0.18), transparent 30rem),
        var(--paper);
      background-size: 28px 28px, 28px 28px, auto, auto, auto;
      font-family: Georgia, "Times New Roman", serif;
    }
    a { color: inherit; }
    a:focus-visible {
      outline: 3px solid #e4a853;
      outline-offset: 5px;
    }
    .portal-shell {
      width: min(1120px, calc(100vw - 36px));
      margin: 0 auto;
      padding: 42px 0 64px;
    }
    .masthead {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 24px;
      padding-bottom: 24px;
      border-bottom: 1px solid var(--line);
    }
    .wordmark {
      display: flex;
      align-items: center;
      gap: 13px;
      text-decoration: none;
    }
    .wordmark-symbol {
      display: grid;
      width: 48px;
      height: 48px;
      place-items: center;
      border: 1px solid var(--line);
      border-radius: 50%;
      background: rgba(255, 253, 247, 0.78);
      color: var(--algebra);
      font-size: 1.55rem;
      box-shadow: 0 8px 30px rgba(58, 43, 27, 0.09);
    }
    .wordmark-copy { display: grid; gap: 2px; }
    .wordmark-copy strong { font-size: 1.13rem; letter-spacing: 0.01em; }
    .wordmark-copy span,
    .masthead-note,
    .eyebrow,
    .course-status,
    .course-action {
      font-family: "Trebuchet MS", "Gill Sans", sans-serif;
    }
    .wordmark-copy span,
    .masthead-note { color: var(--muted); font-size: 0.78rem; letter-spacing: 0.08em; text-transform: uppercase; }
    .portal-hero {
      display: grid;
      grid-template-columns: minmax(0, 1.45fr) minmax(240px, 0.55fr);
      gap: clamp(36px, 8vw, 100px);
      align-items: end;
      padding: clamp(58px, 9vw, 106px) 0 44px;
    }
    .eyebrow {
      display: inline-block;
      color: var(--algebra);
      font-size: 0.77rem;
      font-weight: 700;
      letter-spacing: 0.18em;
      text-transform: uppercase;
    }
    h1 {
      max-width: 760px;
      margin: 14px 0 0;
      font-size: clamp(3.25rem, 8vw, 6.8rem);
      font-weight: 500;
      letter-spacing: -0.065em;
      line-height: 0.88;
    }
    .hero-note {
      margin: 0 0 5px;
      padding-left: 22px;
      border-left: 2px solid var(--calculus);
      color: var(--muted);
      font-size: 1.06rem;
      line-height: 1.65;
    }
    .course-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 20px;
    }
    .course-card {
      position: relative;
      min-height: 330px;
      overflow: hidden;
      padding: clamp(28px, 4vw, 44px);
      border: 1px solid var(--line);
      border-radius: 3px 34px 3px 3px;
      background: rgba(255, 253, 247, 0.8);
      box-shadow: 0 18px 50px rgba(58, 43, 27, 0.09);
      text-decoration: none;
      transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
    }
    .course-card::after {
      position: absolute;
      right: -45px;
      bottom: -76px;
      width: 210px;
      height: 210px;
      border: 1px solid currentColor;
      border-radius: 50%;
      content: "";
      opacity: 0.14;
    }
    .course-card:hover {
      transform: translateY(-5px);
      border-color: currentColor;
      box-shadow: 0 26px 64px rgba(58, 43, 27, 0.15);
    }
    .course-card-algebra-2-trig { color: var(--algebra); }
    .course-card-ap-calculus-ab { color: var(--calculus); }
    .course-number {
      position: absolute;
      top: 30px;
      right: 34px;
      color: currentColor;
      font-size: 4.7rem;
      line-height: 1;
      opacity: 0.1;
    }
    .course-status {
      display: inline-flex;
      padding: 7px 10px;
      border: 1px solid currentColor;
      border-radius: 999px;
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }
    .course-card h2 {
      max-width: 12ch;
      margin: 58px 0 16px;
      color: var(--ink);
      font-size: clamp(2rem, 4vw, 3.4rem);
      font-weight: 500;
      letter-spacing: -0.045em;
      line-height: 0.98;
    }
    .course-card p {
      max-width: 42ch;
      margin: 0 0 30px;
      color: var(--muted);
      line-height: 1.55;
    }
    .course-action {
      position: absolute;
      bottom: 34px;
      left: clamp(28px, 4vw, 44px);
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .course-action::after { content: "  →"; }
    .empty-layout {
      display: grid;
      min-height: calc(100vh - 180px);
      place-items: center;
      padding: 50px 0;
    }
    .empty-panel {
      width: min(760px, 100%);
      padding: clamp(38px, 7vw, 76px);
      border: 1px solid var(--line);
      border-radius: 3px 46px 3px 3px;
      background: rgba(255, 253, 247, 0.84);
      box-shadow: 0 24px 70px rgba(58, 43, 27, 0.12);
    }
    .empty-panel h1 {
      margin: 18px 0 26px;
      font-size: clamp(3rem, 9vw, 6rem);
    }
    .empty-message {
      margin: 0 0 14px;
      color: var(--calculus);
      font-size: clamp(1.45rem, 4vw, 2.1rem);
    }
    .empty-detail {
      max-width: 52ch;
      margin: 0;
      color: var(--muted);
      font-size: 1.05rem;
      line-height: 1.65;
    }
    .back-link {
      display: inline-flex;
      margin-top: 34px;
      padding: 12px 17px;
      border: 1px solid var(--calculus);
      border-radius: 999px;
      color: var(--calculus);
      font-family: "Trebuchet MS", "Gill Sans", sans-serif;
      font-size: 0.78rem;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-decoration: none;
      text-transform: uppercase;
    }
    .back-link:hover { background: var(--calculus); color: var(--white); }
    @media (max-width: 760px) {
      .portal-shell { width: min(100% - 24px, 1120px); padding-top: 20px; }
      .masthead-note { display: none; }
      .portal-hero { grid-template-columns: 1fr; gap: 28px; padding: 52px 0 34px; }
      .course-grid { grid-template-columns: 1fr; }
      .course-card { min-height: 300px; }
    }
    @media (prefers-reduced-motion: reduce) {
      .course-card { transition: none; }
    }
"""


def _course_href(course: CourseConfig, base_path: str) -> str:
    prefix = f"/{base_path.strip('/')}/" if base_path.strip("/") else ""
    return f"{prefix}courses/{course.course_id}/index.html"


def _document(*, title: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>
{PORTAL_STYLES}
  </style>
</head>
<body>
{body}
</body>
</html>
"""


def build_portal_html(*, courses: tuple[CourseConfig, ...], base_path: str) -> str:
    cards = "\n".join(
        f"""
        <a class="course-card course-card-{html.escape(course.course_id)}" href="{html.escape(_course_href(course, base_path))}">
          <span class="course-number" aria-hidden="true">{index:02d}</span>
          <span class="course-status">{'Ready' if course.content_ready else 'Opening soon'}</span>
          <h2>{html.escape(course.display_name)}</h2>
          <p>{html.escape(course.description)}</p>
          <span class="course-action">{'Enter course' if course.content_ready else 'View course'}</span>
        </a>
        """
        for index, course in enumerate(courses, 1)
    )
    body = f"""
  <div class="portal-shell">
    <header class="masthead">
      <a class="wordmark" href="#courses" aria-label="Math Delight course portal">
        <span class="wordmark-symbol" aria-hidden="true">π</span>
        <span class="wordmark-copy"><strong>Math Delight</strong><span>Learning Studio</span></span>
      </a>
      <span class="masthead-note">One place · every course</span>
    </header>
    <main>
      <section class="portal-hero">
        <div>
          <span class="eyebrow">Course Portal</span>
          <h1>Choose your course.</h1>
        </div>
        <p class="hero-note">Each course keeps its own lessons, practice, and progress together—so the next step is always clear.</p>
      </section>
      <nav id="courses" class="course-grid" aria-label="Available courses">
{cards}
      </nav>
    </main>
  </div>
    """
    return _document(title="Math Delight | Choose a Course", body=body)


def build_empty_course_html(*, course: CourseConfig, portal_href: str) -> str:
    empty_section_label = f"{course.section_label.lower()}s"
    body = f"""
  <div class="portal-shell">
    <header class="masthead">
      <a class="wordmark" href="{html.escape(portal_href)}" aria-label="Return to Math Delight course portal">
        <span class="wordmark-symbol" aria-hidden="true">∫</span>
        <span class="wordmark-copy"><strong>Math Delight</strong><span>Learning Studio</span></span>
      </a>
      <span class="masthead-note">{html.escape(course.short_name)}</span>
    </header>
    <main class="empty-layout">
      <section class="empty-panel" aria-labelledby="course-title">
        <span class="eyebrow">New Course</span>
        <h1 id="course-title">{html.escape(course.display_name)}</h1>
        <p class="empty-message">Course setup in progress</p>
        <p class="empty-detail">No {html.escape(empty_section_label)} have been published yet. This course space is ready for the new school year and will grow as class materials become available.</p>
        <a class="back-link" href="{html.escape(portal_href)}">← Switch Course</a>
      </section>
    </main>
  </div>
    """
    return _document(title=f"{course.display_name} | Math Delight", body=body)
