"""Shared CSS and helper scripts for generated site pages."""

from __future__ import annotations


BASE_SITE_PAGE_STYLES = """
    :root {
      --bg: #f5f1e8;
      --panel: #fffaf2;
      --ink: #1f2a33;
      --muted: #5b6a74;
      --accent: #a14d2e;
      --accent-soft: #ead2c5;
      --line: #d8cfc2;
      --line-strong: #cabaa4;
      --code: #f0e7db;
      --prompt-bg: #fffef9;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: Georgia, "Times New Roman", serif;
      color: var(--ink);
      background:
        radial-gradient(circle at top left, #f8dfc8 0, transparent 28%),
        linear-gradient(180deg, #f6efe3 0%, var(--bg) 100%);
    }
    a { color: var(--accent); }
    .page {
      width: min(1240px, calc(100vw - 32px));
      margin: 24px auto 48px;
      display: grid;
      grid-template-columns: 236px 1fr;
      gap: 24px;
    }
    .page-home {
      width: min(1240px, calc(100vw - 32px));
      display: block;
    }
    .sidebar, .content-card {
      background: color-mix(in srgb, var(--panel) 94%, white);
      border: 1px solid var(--line);
      border-radius: 18px;
      box-shadow: 0 12px 30px rgba(78, 55, 32, 0.08);
    }
    .sidebar {
      padding: 18px;
      position: sticky;
      top: 20px;
      align-self: start;
      max-height: calc(100vh - 40px);
      overflow: auto;
    }
    .sidebar-library {
      padding: 22px 18px 18px;
    }
    .sidebar h1 {
      margin: 0 0 8px;
      font-size: 1.66rem;
      line-height: 1.04;
    }
    .brand-keep {
      white-space: nowrap;
    }
    .brand-head {
      display: flex;
      align-items: flex-start;
      gap: 10px;
      margin-bottom: 10px;
    }
    .brand-mark {
      width: 56px;
      height: 56px;
      flex: 0 0 56px;
      border-radius: 16px;
      overflow: hidden;
      box-shadow: 0 10px 24px rgba(78, 55, 32, 0.12);
    }
    .brand-mark svg {
      display: block;
      width: 100%;
      height: 100%;
    }
    .sidebar p {
      color: var(--muted);
      margin: 0 0 18px;
      line-height: 1.45;
    }
    .sidebar-compact-head {
      margin-bottom: 14px;
    }
    .sidebar-compact-head h2 {
      margin: 6px 0 8px;
      font-size: 1.45rem;
      line-height: 1.05;
    }
    .sidebar-compact-head p {
      margin: 0;
      color: var(--muted);
      line-height: 1.45;
    }
    .sidebar-home {
      display: inline-block;
      margin-bottom: 14px;
      font-weight: 600;
      text-decoration: none;
    }
    .global-nav {
      display: grid;
      gap: 8px;
      margin: 0 0 16px;
    }
    .nav-pill {
      display: block;
      text-decoration: none;
      padding: 10px 12px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.72);
      color: var(--ink);
      font-weight: 600;
    }
    .nav-pill.active {
      background: var(--accent-soft);
      border-color: var(--line-strong);
      color: #6a2e16;
    }
    .toc {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 8px;
    }
    .toc a {
      display: block;
      text-decoration: none;
      padding: 10px 12px;
      border-radius: 12px;
      border: 1px solid transparent;
      color: var(--ink);
    }
    .toc a:hover {
      border-color: var(--line);
      background: rgba(255, 255, 255, 0.6);
    }
    .toc a.active {
      background: var(--accent-soft);
      border-color: var(--line-strong);
      color: #6a2e16;
      font-weight: 700;
    }
    .meta {
      margin-top: 18px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
      color: var(--muted);
      font-size: 0.92rem;
    }
    .sidebar-challenges {
      margin-top: 14px;
      padding-top: 14px;
      border-top: 1px solid var(--line);
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    .challenges-nav-link {
      font-weight: 700;
      text-decoration: none;
      color: var(--accent);
      font-size: 0.95rem;
    }
    .challenges-nav-link:hover { text-decoration: underline; }
    .main {
      display: grid;
      gap: 18px;
    }
    .content-card {
      padding: 24px;
    }
    .surface-header {
      background: color-mix(in srgb, var(--panel) 94%, white);
      border: 1px solid var(--line);
      border-radius: 22px;
      box-shadow: 0 12px 30px rgba(78, 55, 32, 0.08);
      padding: 24px;
    }
    .surface-nav {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 18px;
    }
    .surface-brand {
      display: flex;
      align-items: center;
      gap: 14px;
    }
    .surface-brand-copy h2 {
      margin: 4px 0 0;
      font-size: 1.65rem;
      line-height: 1.02;
    }
    .landing-hero {
      position: relative;
      overflow: hidden;
      background:
        radial-gradient(circle at top right, rgba(243, 201, 143, 0.42), transparent 30%),
        linear-gradient(135deg, rgba(255, 248, 238, 0.96), rgba(253, 245, 232, 0.96));
      border: 1px solid var(--line);
      border-radius: 28px;
      padding: 38px 34px;
      box-shadow: 0 16px 34px rgba(78, 55, 32, 0.1);
    }
    .home-brand {
      display: flex;
      align-items: center;
      gap: 14px;
      margin-bottom: 22px;
    }
    .home-brand-title {
      margin: 4px 0 0;
      font-size: clamp(1.45rem, 3vw, 2rem);
      line-height: 1.02;
    }
    .landing-copy h2 {
      margin: 8px 0 14px;
      font-size: clamp(2.3rem, 6vw, 4rem);
      line-height: 0.98;
      max-width: 10ch;
    }
    .eyebrow {
      display: inline-block;
      font-size: 0.78rem;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--muted);
      font-family: system-ui, sans-serif;
      font-weight: 700;
    }
    .landing-stats {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin-top: 22px;
    }
    .stat-pill {
      min-width: 148px;
      padding: 14px 16px;
      border-radius: 18px;
      border: 1px solid rgba(202, 186, 164, 0.9);
      background: rgba(255,255,255,0.72);
      display: grid;
      gap: 4px;
    }
    .stat-pill strong {
      font-size: 1.05rem;
      color: #243645;
    }
    .stat-pill span {
      color: var(--muted);
      font-size: 0.88rem;
    }
    .landing-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px;
    }
    .destination-card {
      position: relative;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      gap: 14px;
      min-height: 260px;
      padding: 26px;
      border-radius: 24px;
      border: 1px solid var(--line);
      text-decoration: none;
      color: var(--ink);
      box-shadow: 0 16px 34px rgba(78, 55, 32, 0.08);
      transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
    }
    .destination-card:hover {
      transform: translateY(-4px);
      box-shadow: 0 22px 38px rgba(78, 55, 32, 0.13);
      border-color: var(--line-strong);
    }
    .destination-library {
      background: linear-gradient(160deg, #fffaf2 0%, #f8efe2 100%);
    }
    .destination-challenges {
      background: linear-gradient(160deg, #eef7f7 0%, #e4f0ef 100%);
    }
    .destination-live {
      background: linear-gradient(160deg, #f8f0e7 0%, #f3e4d6 100%);
    }
    .destination-kicker {
      font-family: system-ui, sans-serif;
      font-size: 0.82rem;
      font-weight: 800;
      letter-spacing: 0.12em;
      color: var(--muted);
    }
    .destination-card h3 {
      margin: 0;
      font-size: 1.75rem;
      line-height: 1.05;
    }
    .destination-card p {
      margin: 0;
      color: var(--muted);
      line-height: 1.55;
      max-width: 30ch;
    }
    .destination-link,
    .destination-soon {
      margin-top: auto;
      align-self: flex-start;
      padding: 10px 14px;
      border-radius: 999px;
      font-family: system-ui, sans-serif;
      font-size: 0.92rem;
      font-weight: 700;
    }
    .destination-link {
      background: rgba(255,255,255,0.82);
      border: 1px solid rgba(202, 186, 164, 0.9);
    }
    .destination-soon {
      background: rgba(255,255,255,0.58);
      border: 1px dashed rgba(161, 77, 46, 0.45);
      color: var(--accent);
    }
    .section-card {
      padding: 28px;
    }
    .section-head {
      display: flex;
      flex-wrap: wrap;
      align-items: end;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
    }
    .section-head h3 {
      margin: 6px 0 0;
      font-size: 1.5rem;
    }
    .section-link {
      text-decoration: none;
      font-weight: 700;
    }
    .library-preview-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
    }
    .doc-header {
      display: flex;
      flex-wrap: wrap;
      align-items: baseline;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 14px;
    }
    .doc-header h2 {
      margin: 0;
      font-size: 1.7rem;
      line-height: 1.1;
    }
    .page-intro {
      color: var(--muted);
      line-height: 1.5;
      margin: 0 0 18px;
    }
    .chip-row {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 16px;
    }
    .chip {
      display: inline-block;
      padding: 6px 10px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: #6a2e16;
      font-size: 0.88rem;
      font-weight: 600;
    }
    .chip-model {
      background: #dbeafe;
      color: #1e40af;
      font-weight: 600;
    }
    .chip-gemini {
      background: #dcfce7;
      color: #166534;
      font-weight: 600;
    }
    .chip-ai {
      background: #e2e8f0;
      color: #334155;
      font-weight: 400;
    }
    .chip-lock {
      background: #fef9c3;
      color: #854d0e;
      font-weight: 600;
    }
    .auth-icon {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.35rem;
      height: 1.35rem;
      margin-right: 0.45rem;
      border-radius: 999px;
      background: #854d0e;
      color: #fffdf4;
      font-size: 0.9rem;
      font-weight: 700;
      line-height: 1;
      box-shadow: inset 0 -1px 0 rgba(0, 0, 0, 0.16);
    }
    .olympiad-model-row {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      margin-bottom: 10px;
    }
    .olympiad-model-row .chip {
      white-space: nowrap;
      min-width: 120px;
      text-align: center;
    }
    .olympiad-links {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }
    .olympiad-links a {
      text-decoration: none;
      font-weight: 600;
      border: 1px solid var(--line);
      background: #fff;
      padding: 9px 12px;
      border-radius: 999px;
    }
    .olympiad-links a.pdf-link {
      font-weight: 500;
      font-size: 0.78rem;
      padding: 5px 10px;
      border-color: var(--line);
      background: #f5f5f5;
      color: #555;
      letter-spacing: 0.03em;
    }
    .link-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 18px;
    }
    .link-row a {
      text-decoration: none;
      font-weight: 600;
      border: 1px solid var(--line);
      background: #fff;
      padding: 9px 12px;
      border-radius: 999px;
    }
    .prompt-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
    }
    .guided-card {
      border: 1px solid var(--line-strong);
      background: linear-gradient(180deg, #fff7ec 0%, #fffdf8 100%);
      border-radius: 16px;
      padding: 18px;
      margin-bottom: 18px;
    }
    .guided-card h3 {
      margin: 0 0 10px;
      font-size: 1.25rem;
      color: #243645;
    }
    .guided-card p {
      margin: 0 0 12px;
      line-height: 1.5;
      color: var(--muted);
    }
    .button-row {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-bottom: 12px;
    }
    .button-row button,
    .button-row a {
      appearance: none;
      border: 1px solid var(--line);
      background: #fff;
      color: var(--accent);
      text-decoration: none;
      font: inherit;
      font-weight: 600;
      padding: 9px 12px;
      border-radius: 999px;
      cursor: pointer;
    }
    .guided-note {
      font-size: 0.95rem;
      color: var(--muted);
    }
    .chapter-challenge-copy {
      color: var(--muted);
      line-height: 1.55;
      margin: 0 0 14px;
    }
    .chapter-challenge-card {
      margin-top: 24px;
    }
    .chapter-challenge-intro {
      color: var(--muted);
      line-height: 1.55;
      margin: 0 0 14px;
    }
    .chapter-challenge-options {
      display: grid;
      gap: 14px;
    }
    .chapter-challenge-option {
      display: flex;
      flex-direction: column;
      gap: 8px;
      padding: 14px 0;
      border-top: 1px solid var(--line);
    }
    .chapter-challenge-option:first-of-type {
      border-top: 0;
      padding-top: 0;
    }
    .chapter-challenge-option p {
      margin: 0;
      color: var(--muted);
      line-height: 1.55;
    }
    .chapter-challenge-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      flex-wrap: wrap;
    }
    .chapter-challenge-title {
      font-size: 1rem;
      font-weight: 700;
      color: #243645;
    }
    .chapter-challenge-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 4px 0 0;
    }
    .chapter-challenge-tag {
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      font-size: 0.8rem;
      font-weight: 700;
      font-family: system-ui, sans-serif;
    }
    .chapter-challenge-tag-mm {
      background: #dbeafe;
      color: #1e40af;
    }
    .chapter-challenge-tag-op {
      background: #dcfce7;
      color: #166534;
    }
    .chapter-challenge-tag-model {
      background: var(--soft);
      color: var(--accent);
    }
    .chapter-challenge-tag-resume {
      background: #fef9c3;
      color: #854d0e;
    }
    .chapter-challenge-tag-done {
      background: #dcfce7;
      color: #166534;
    }
    .chapter-challenge-small {
      color: var(--muted);
      font-family: system-ui, sans-serif;
      font-size: 0.82rem;
    }
    details pre {
      white-space: pre-wrap;
      word-break: break-word;
      overflow-wrap: break-word;
      max-width: 100%;
      overflow: hidden;
    }
    .prompt-card {
      border: 1px solid var(--line-strong);
      background: var(--prompt-bg);
      border-radius: 16px;
      padding: 18px;
    }
    .prompt-card h3 {
      margin: 0 0 10px;
      font-size: 1.25rem;
      color: #243645;
    }
    .prompt-card .link-row {
      margin-bottom: 14px;
    }
    .assignment-list {
      display: grid;
      gap: 14px;
    }
    .assignment-row {
      display: grid;
      gap: 8px;
      padding-top: 12px;
      border-top: 1px solid var(--line);
    }
    .assignment-row:first-child {
      padding-top: 0;
      border-top: 0;
    }
    .assignment-row-label {
      font-size: 0.98rem;
      font-weight: 700;
      color: #243645;
    }
    .assignment-row .link-row {
      margin-bottom: 0;
    }
    .card-summary {
      color: #0d1b24;
      font-size: 1.03rem;
      font-weight: 500;
      line-height: 1.72;
      background: linear-gradient(180deg, #fffaf4 0%, #f7e6d2 100%);
      border: 1px solid #d6ab7d;
      border-left: 5px solid #a14d2e;
      border-radius: 14px;
      padding: 16px 18px;
      box-shadow: 0 8px 20px rgba(78,55,32,.08);
      margin: 0 0 8px;
    }
    .card-summary p,
    .card-summary li,
    .card-summary ul,
    .card-summary ol {
      color: #0d1b24;
    }
    .card-summary p {
      margin: 0;
    }
    .card-summary p + p,
    .card-summary ul,
    .card-summary ol {
      margin-top: 10px;
    }
    .card-summary strong {
      color: #081118;
    }
    .card-summary li {
      margin-bottom: 6px;
    }
    .guided-card h3 {
      color: #243645;
    }
    .summary-card .card-summary {
      color: #0d1b24;
      font-size: 1.1rem;
      font-weight: 500;
      line-height: 1.78;
      background: linear-gradient(180deg, #fffaf4 0%, #f4e0c8 100%);
      border: 2px solid #d6ab7d;
      border-left: 8px solid #a14d2e;
      border-radius: 18px;
      padding: 22px 24px;
      box-shadow: 0 14px 32px rgba(78,55,32,.1);
      margin: 0 0 22px;
    }
    .summary-card .card-summary p,
    .summary-card .card-summary li,
    .summary-card .card-summary ul,
    .summary-card .card-summary ol {
      color: #0d1b24;
    }
    .summary-card .card-summary p {
      margin: 0;
    }
    .summary-card .card-summary p + p,
    .summary-card .card-summary ul,
    .summary-card .card-summary ol {
      margin-top: 12px;
    }
    .summary-card .card-summary strong {
      color: #081118;
    }
    .summary-card .card-summary li {
      margin-bottom: 8px;
    }
    @media (max-width: 960px) {
      .page { grid-template-columns: 1fr; }
      .sidebar { position: static; max-height: none; }
      .landing-grid { grid-template-columns: 1fr; }
      .home-brand { margin-bottom: 18px; }
    }
"""


STAGING_SITE_PAGE_OVERRIDES = """
    :root {
      --stage-neutral-0: #ffffff;
      --stage-neutral-25: #f8fafc;
      --stage-neutral-50: #eef2f7;
      --stage-neutral-100: #dde5f0;
      --stage-ink: #10233b;
      --stage-muted: #516173;
      --stage-blue-600: #1d4ed8;
      --stage-blue-700: #1e3a8a;
      --stage-blue-50: #dbeafe;
      --stage-orange-500: #f97316;
      --stage-orange-50: #ffedd5;
      --stage-success: #15803d;
      --stage-success-bg: #dcfce7;
      --stage-amber: #d97706;
      --stage-amber-bg: #fef3c7;
      --stage-soft-red: #ef4444;
      --stage-soft-red-bg: #fff1f2;
    }
    body.experience-staging {
      font-family: "Inter", "Segoe UI", sans-serif;
      color: var(--stage-ink);
      background:
        radial-gradient(circle at top left, rgba(249, 115, 22, 0.08), transparent 24%),
        radial-gradient(circle at top right, rgba(29, 78, 216, 0.08), transparent 26%),
        linear-gradient(180deg, #f8fafc 0%, #eef4fb 100%);
    }
    body.experience-staging .page,
    body.experience-staging .page-home {
      width: min(1280px, calc(100vw - 32px));
    }
    body.experience-staging .content-card,
    body.experience-staging .sidebar,
    body.experience-staging .surface-header,
    body.experience-staging .landing-hero,
    body.experience-staging .prompt-card,
    body.experience-staging .guided-card {
      border-radius: 24px;
      border-color: rgba(148, 163, 184, 0.24);
      box-shadow: 0 18px 42px rgba(15, 23, 42, 0.08);
    }
    body.experience-staging .sidebar,
    body.experience-staging .content-card,
    body.experience-staging .surface-header,
    body.experience-staging .prompt-card,
    body.experience-staging .guided-card {
      background: rgba(255, 255, 255, 0.92);
      backdrop-filter: blur(10px);
    }
    body.experience-staging .surface-header {
      padding: 28px;
      background:
        linear-gradient(180deg, rgba(255,255,255,0.98), rgba(247,250,255,0.96));
    }
    body.experience-staging .surface-brand-copy h2,
    body.experience-staging .section-head h3,
    body.experience-staging .doc-header h2,
    body.experience-staging .prompt-card h3,
    body.experience-staging .destination-card h3 {
      letter-spacing: -0.03em;
    }
    body.experience-staging .surface-subtitle {
      margin: 14px 0 0;
      max-width: 60ch;
      color: var(--stage-muted);
      line-height: 1.6;
    }
    body.experience-staging .nav-pill {
      background: var(--stage-neutral-0);
      border-color: rgba(148, 163, 184, 0.28);
      color: var(--stage-ink);
      font-weight: 700;
    }
    body.experience-staging .nav-pill.active {
      background: var(--stage-blue-50);
      border-color: rgba(29, 78, 216, 0.24);
      color: var(--stage-blue-700);
    }
    body.experience-staging .landing-hero-staging {
      display: grid;
      grid-template-columns: minmax(0, 1.35fr) minmax(280px, 0.85fr);
      gap: 22px;
      padding: 32px;
      background:
        radial-gradient(circle at top left, rgba(249, 115, 22, 0.11), transparent 28%),
        radial-gradient(circle at bottom right, rgba(29, 78, 216, 0.12), transparent 30%),
        linear-gradient(145deg, rgba(255,255,255,0.98), rgba(241,245,249,0.98));
    }
    body.experience-staging .hero-title {
      margin: 0 0 16px;
      font-size: clamp(2.5rem, 6vw, 4.7rem);
      line-height: 0.94;
      max-width: 20ch;
    }
    body.experience-staging .page-intro,
    body.experience-staging .task-copy,
    body.experience-staging .continue-copy {
      color: var(--stage-muted);
      line-height: 1.7;
      font-size: 1rem;
    }
    body.experience-staging .hero-action-grid {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      margin: 22px 0 0;
    }
    body.experience-staging .hero-action,
    body.experience-staging .link-row a,
    body.experience-staging .button-row a,
    body.experience-staging .button-row button,
    body.experience-staging .olympiad-links a {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      min-height: 42px;
      padding: 10px 16px;
      border-radius: 999px;
      border: 1px solid rgba(148, 163, 184, 0.28);
      background: var(--stage-neutral-0);
      color: var(--stage-ink);
      font-weight: 700;
      text-decoration: none;
      transition: transform 160ms ease, box-shadow 160ms ease, border-color 160ms ease;
    }
    body.experience-staging .hero-action.primary,
    body.experience-staging .destination-link,
    body.experience-staging .chapter-challenge-action {
      background: linear-gradient(180deg, #f97316 0%, #ea580c 100%);
      color: #fff;
      border-color: transparent;
      box-shadow: 0 14px 28px rgba(249, 115, 22, 0.25);
    }
    body.experience-staging .hero-action:hover,
    body.experience-staging .link-row a:hover,
    body.experience-staging .button-row a:hover,
    body.experience-staging .button-row button:hover,
    body.experience-staging .olympiad-links a:hover {
      transform: translateY(-1px);
      border-color: rgba(29, 78, 216, 0.24);
    }
    body.experience-staging .link-row a.button-class-note,
    body.experience-staging .resource-chip-row a.button-class-note,
    body.experience-staging .olympiad-links a.button-class-note,
    body.experience-staging .link-row a.button-study-guide,
    body.experience-staging .resource-chip-row a.button-study-guide,
    body.experience-staging .olympiad-links a.button-study-guide {
      background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%);
      border-color: rgba(59, 130, 246, 0.28);
      color: #1d4ed8;
      box-shadow: 0 10px 22px rgba(59, 130, 246, 0.16);
    }
    body.experience-staging .link-row a.button-watch-picks,
    body.experience-staging .resource-chip-row a.button-watch-picks,
    body.experience-staging .olympiad-links a.button-watch-picks {
      background: linear-gradient(180deg, #f0fdfa 0%, #ccfbf1 100%);
      border-color: rgba(13, 148, 136, 0.28);
      color: #0f766e;
      box-shadow: 0 10px 22px rgba(20, 184, 166, 0.16);
    }
    body.experience-staging .link-row a.button-quick-practice,
    body.experience-staging .resource-chip-row a.button-quick-practice,
    body.experience-staging .olympiad-links a.button-quick-practice,
    body.experience-staging .chapter-challenge-action.button-quick-practice {
      background: linear-gradient(180deg, #fff7ed 0%, #ffedd5 100%);
      border-color: rgba(249, 115, 22, 0.28);
      color: #c2410c;
      box-shadow: 0 10px 22px rgba(249, 115, 22, 0.16);
    }
    body.experience-staging .link-row a.button-olympiad,
    body.experience-staging .resource-chip-row a.button-olympiad,
    body.experience-staging .olympiad-links a.button-olympiad,
    body.experience-staging .chapter-challenge-action.button-olympiad {
      background: linear-gradient(180deg, #fffbeb 0%, #fef3c7 100%);
      border-color: rgba(217, 119, 6, 0.28);
      color: #b45309;
      box-shadow: 0 10px 22px rgba(245, 158, 11, 0.16);
    }
    body.experience-staging .continue-card {
      padding: 22px;
      border-radius: 24px;
      border: 1px solid rgba(148, 163, 184, 0.24);
      background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
      display: grid;
      gap: 14px;
      align-content: start;
    }
    body.experience-staging .continue-card h3 {
      margin: 0;
      font-size: 1.45rem;
      letter-spacing: -0.03em;
    }
    body.experience-staging .continue-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 12px;
      align-items: center;
    }
    body.experience-staging .task-kicker,
    body.experience-staging .chapter-kicker {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      align-self: flex-start;
      padding: 7px 12px;
      border-radius: 999px;
      background: var(--stage-blue-50);
      color: var(--stage-blue-700);
      font-size: 0.78rem;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      font-weight: 800;
    }
    body.experience-staging .landing-grid-staging,
    body.experience-staging .quick-start-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 18px;
    }
    body.experience-staging .destination-card {
      min-height: 250px;
      padding: 24px;
    }
    body.experience-staging .destination-card h3 {
      font-size: 1.85rem;
    }
    body.experience-staging .destination-link {
      margin-top: auto;
      align-self: flex-start;
      padding: 10px 14px;
      border-radius: 999px;
    }
    body.experience-staging .section-surface {
      padding: 28px;
    }
    body.experience-staging .overview-card-staging,
    body.experience-staging .prompt-card-staging {
      background: linear-gradient(180deg, #ffffff 0%, #f9fbfd 100%);
    }
    body.experience-staging .task-head {
      display: grid;
      gap: 6px;
      margin-bottom: 12px;
    }
    body.experience-staging .task-head h3,
    body.experience-staging .prompt-card h3 {
      font-size: 1.3rem;
      margin: 0;
    }
    body.experience-staging .chip {
      background: #eef2ff;
      color: #3730a3;
      font-family: "Inter", "Segoe UI", sans-serif;
    }
    body.experience-staging .chip-ai {
      background: #e2e8f0;
      color: #334155;
    }
    body.experience-staging .chip-model {
      background: var(--stage-blue-50);
      color: var(--stage-blue-700);
    }
    body.experience-staging .chip-gemini {
      background: var(--stage-success-bg);
      color: var(--stage-success);
    }
    body.experience-staging .card-summary {
      background: linear-gradient(180deg, #ffffff 0%, #f9fbff 100%);
      border: 1px solid rgba(148, 163, 184, 0.24);
      border-left: 6px solid var(--stage-blue-600);
      border-radius: 18px;
      color: var(--stage-ink);
      line-height: 1.8;
    }
    body.experience-staging .chapter-hero-card {
      padding: 30px;
      background:
        radial-gradient(circle at top right, rgba(29, 78, 216, 0.08), transparent 28%),
        radial-gradient(circle at bottom left, rgba(249, 115, 22, 0.08), transparent 28%),
        linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
    }
    body.experience-staging .chapter-hero-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.45fr) minmax(280px, 0.75fr);
      gap: 20px;
      align-items: start;
    }
    body.experience-staging .chapter-hero-main {
      display: grid;
      gap: 16px;
    }
    body.experience-staging .chapter-summary-panel h3 {
      margin: 0 0 10px;
      font-size: 1.15rem;
    }
    body.experience-staging .chapter-support-card {
      display: grid;
      gap: 16px;
      padding: 20px;
      border-radius: 22px;
      background: linear-gradient(180deg, rgba(255,255,255,0.98), rgba(245,248,255,0.92));
      border: 1px solid rgba(148, 163, 184, 0.24);
    }
    body.experience-staging .chapter-support-card h3 {
      margin: 0;
      font-size: 1.18rem;
    }
    body.experience-staging .chapter-support-list {
      list-style: none;
      margin: 0;
      padding: 0;
      display: grid;
      gap: 12px;
    }
    body.experience-staging .chapter-support-list li {
      display: flex;
      gap: 10px;
      line-height: 1.6;
      color: var(--stage-muted);
    }
    body.experience-staging .chapter-support-index {
      width: 28px;
      height: 28px;
      flex: 0 0 28px;
      border-radius: 999px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      background: var(--stage-orange-50);
      color: var(--stage-orange-500);
      font-weight: 800;
    }
    body.experience-staging .resource-chip-row,
    body.experience-staging .resource-chip-row a {
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
    }
    body.experience-staging .resource-chip-row a {
      text-decoration: none;
    }
    body.experience-staging .prompt-grid {
      gap: 18px;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }
    body.experience-staging .prompt-grid-compact {
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
    }
    body.experience-staging .prompt-card-stack {
      display: grid;
      gap: 16px;
    }
    body.experience-staging .prompt-card-subsection {
      margin-top: 18px;
      padding: 16px 16px 6px;
      border-radius: 18px;
      border: 1px solid rgba(59, 130, 246, 0.16);
      background: linear-gradient(180deg, rgba(239, 246, 255, 0.96), rgba(248, 250, 252, 0.98));
    }
    body.experience-staging .prompt-card-stack .prompt-card-subsection {
      margin-top: 0;
    }
    body.experience-staging .prompt-card-subsection-head {
      display: grid;
      gap: 6px;
      margin-bottom: 10px;
    }
    body.experience-staging .prompt-card-subsection h4 {
      margin: 0;
      font-size: 1rem;
      letter-spacing: -0.01em;
    }
    body.experience-staging .prompt-card-subsection-video .task-kicker {
      background: #e0f2fe;
      color: #0369a1;
    }
    body.experience-staging .guided-card-staging {
      background: linear-gradient(180deg, #fffaf5 0%, #ffffff 100%);
      border-color: rgba(249, 115, 22, 0.2);
    }
    body.experience-staging .chapter-challenge-card-staging {
      margin-top: 0;
      background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
      border: 0;
      padding: 0;
      box-shadow: none;
    }
    body.experience-staging .chapter-challenge-option {
      border-top: 0;
      padding: 18px;
      border-radius: 18px;
      background: rgba(248, 250, 252, 0.88);
      border: 1px solid rgba(148, 163, 184, 0.22);
    }
    body.experience-staging .chapter-challenge-options {
      gap: 16px;
    }
    body.experience-staging .chapter-challenge-status-loading {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 5px 10px;
      border-radius: 999px;
      background: #e2e8f0;
      color: #475569;
      font-family: "Inter", "Segoe UI", sans-serif;
      font-size: 0.78rem;
      font-weight: 700;
    }
    body.experience-staging .chapter-challenge-status-loading::before {
      content: "";
      width: 8px;
      height: 8px;
      border-radius: 999px;
      background: currentColor;
      opacity: 0.5;
      animation: stagePulse 1s ease-in-out infinite;
    }
    body.experience-staging .chapter-challenge-tag-resume {
      background: var(--stage-amber-bg);
      color: var(--stage-amber);
    }
    body.experience-staging .chapter-challenge-tag-done {
      background: var(--stage-success-bg);
      color: var(--stage-success);
    }
    @keyframes stageShimmer {
      100% {
        transform: translateX(100%);
      }
    }
    @keyframes stagePulse {
      0%, 100% {
        opacity: 0.35;
      }
      50% {
        opacity: 1;
      }
    }
    @media (max-width: 1100px) {
      body.experience-staging .landing-hero-staging,
      body.experience-staging .chapter-hero-grid {
        grid-template-columns: 1fr;
      }
    }
    @media (max-width: 960px) {
      body.experience-staging .landing-grid-staging,
      body.experience-staging .quick-start-grid {
        grid-template-columns: 1fr;
      }
    }
"""


KATEX_CSS_HREF = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.css"
KATEX_JS_SRC = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/katex.min.js"
KATEX_AUTORENDER_SRC = "https://cdn.jsdelivr.net/npm/katex@0.16.11/dist/contrib/auto-render.min.js"
KATEX_AUTORENDER_SCRIPT = """
    document.addEventListener("DOMContentLoaded", function () {
      if (window.renderMathInElement) {
        renderMathInElement(document.body, {
          delimiters: [
            {left: "$$", right: "$$", display: true},
            {left: "\\\\(", right: "\\\\)", display: false},
            {left: "\\\\[", right: "\\\\]", display: true},
            {left: "$", right: "$", display: false}
          ],
          throwOnError: false
        });
      }
    });
"""


STAGING_SITE_SCRIPT = """
    (function () {
      const LAST_RECORD_KEY = "math_tutor_last_record";
      const LEGACY_SESSION_KEY = "math_tutor_challenge_session";
      const SESSION_KEY_PREFIX = "math_tutor_challenge_session:";
      const body = document.body;
      const recordHref = body.dataset.recordHref;
      const recordTitle = body.dataset.recordTitle;
      const storage = {
        get(key) {
          try {
            return localStorage.getItem(key);
          } catch (error) {
            return null;
          }
        },
        set(key, value) {
          try {
            localStorage.setItem(key, value);
          } catch (error) {
            // Ignore blocked storage and fall back to the default continue card.
          }
        }
      };

      function readStoredSession(key) {
        try {
          const saved = JSON.parse(storage.get(key) || "null");
          if (!saved || !saved.exam_id) return null;
          return saved;
        } catch (error) {
          return null;
        }
      }

      function sessionSavedAtMs(saved) {
        const value = Date.parse(saved && saved.savedAt ? saved.savedAt : "");
        return Number.isNaN(value) ? 0 : value;
      }

      function getMostRecentChallengeSession() {
        const byExam = {};
        try {
          for (let i = 0; i < localStorage.length; i += 1) {
            const key = localStorage.key(i);
            if (!key || key.indexOf(SESSION_KEY_PREFIX) !== 0) continue;
            const saved = readStoredSession(key);
            if (!saved) continue;
            const existing = byExam[saved.exam_id];
            if (!existing || sessionSavedAtMs(saved) >= sessionSavedAtMs(existing)) {
              byExam[saved.exam_id] = saved;
            }
          }
        } catch (error) {
          // Ignore blocked storage and fall back to the legacy key below.
        }

        const legacySaved = readStoredSession(LEGACY_SESSION_KEY);
        if (legacySaved) {
          const current = byExam[legacySaved.exam_id];
          if (!current || sessionSavedAtMs(legacySaved) > sessionSavedAtMs(current)) {
            byExam[legacySaved.exam_id] = legacySaved;
          }
        }

        return Object.values(byExam).sort(function(a, b) {
          return sessionSavedAtMs(b) - sessionSavedAtMs(a);
        })[0] || null;
      }

      function persistLastRecord() {
        if (!recordHref || !recordTitle) return;
        const resumeHref = recordHref + (window.location.hash || "");
        storage.set(LAST_RECORD_KEY, JSON.stringify({
          href: recordHref,
          resumeHref: resumeHref,
          title: recordTitle,
          savedAt: new Date().toISOString()
        }));
      }

      if (recordHref && recordTitle) {
        persistLastRecord();
        window.addEventListener("hashchange", persistLastRecord);
      }

      function hydrateContinueCard() {
        const card = document.querySelector("[data-continue-card]");
        if (!card) return;
        const title = card.querySelector("[data-continue-title]");
        const link = card.querySelector("[data-continue-link]");
        const copy = card.querySelector("[data-continue-copy]");
        const challengeLink = card.querySelector("[data-challenge-link]");

        let heading = title ? title.textContent : "Your next chapter";
        let href = link ? link.getAttribute("href") : "";
        let text = "Continue with the recommended chapter path.";
        let actionLabel = "Continue Learning";

        try {
          const savedRecord = JSON.parse(storage.get(LAST_RECORD_KEY) || "null");
          if (savedRecord && (savedRecord.resumeHref || savedRecord.href)) {
            heading = savedRecord.title || heading;
            href = savedRecord.resumeHref || savedRecord.href;
            text = "Return to " + savedRecord.title + " and keep going where you left off.";
            actionLabel = "Resume Chapter";
          }

          const savedChallenge = getMostRecentChallengeSession();
          if (savedChallenge && savedChallenge.exam_id) {
            if (challengeLink) {
              challengeLink.hidden = false;
              challengeLink.setAttribute(
                "href",
                "challenges/exam.html?id=" + encodeURIComponent(savedChallenge.exam_id)
              );
              challengeLink.textContent = "Resume Challenge";
            }
            if (savedRecord && (savedRecord.resumeHref || savedRecord.href)) {
              text += " You can also jump back into your unfinished challenge.";
            }
          } else if (challengeLink) {
            challengeLink.hidden = true;
          }
        } catch (error) {
          text = "Continue with the recommended chapter path.";
          if (challengeLink) challengeLink.hidden = true;
        }

        if (title && heading) title.textContent = heading;
        if (copy) copy.textContent = text;
        if (link && href) {
          link.setAttribute("href", href);
          link.textContent = actionLabel;
        }
      }

      if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", hydrateContinueCard);
      } else {
        hydrateContinueCard();
      }
    })();
"""


def get_site_page_styles(experience_variant: str = "default") -> str:
    if experience_variant == "staging":
        return BASE_SITE_PAGE_STYLES + "\n" + STAGING_SITE_PAGE_OVERRIDES
    return BASE_SITE_PAGE_STYLES


COPY_PROMPT_SCRIPT = """
    async function copyChatgptPrompt(button) {
      const prompt = button.dataset.chatgptPrompt || "";
      const status = button.parentElement && button.parentElement.nextElementSibling;
      if (!prompt || !navigator.clipboard || !navigator.clipboard.writeText) {
        if (status) {
          status.textContent = "Copy failed in this browser. Use the prompt text shown below.";
        }
        return;
      }
      try {
        await navigator.clipboard.writeText(prompt);
        if (status) {
          status.textContent = "Prompt copied.";
        }
      } catch (error) {
        if (status) {
          status.textContent = "Copy failed in this browser. Use the prompt text shown below.";
        }
      }
    }
"""
