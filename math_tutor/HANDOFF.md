# Math Tutor Handoff

## What This Project Does

`math_tutor` logs into the Canvas course, finds PDF attachments, downloads them, sends them through the prompt-generation pipeline with OpenAI/Gemini as needed, and saves the generated output plus metadata locally. It also builds a browsable HTML tutoring site from those outputs.

## Current Login Flow

- The CLI starts from the course URL, not `/login/canvas`
- The site redirects through the school's real SSO flow
- The implementation supports OneLogin's two-step username/password flow
- `--headful` keeps the browser open until you press Enter
- `--skip-fetch` bypasses Canvas entirely and uses already-downloaded PDFs from `fetch_state.json`

## Current Document Discovery Flow

The course Files page is disabled and the Canvas Files API returned `403`, so discovery now uses the authenticated UI:

1. Try the course Files area
2. If that yields nothing, scrape PDF attachments from the Modules page
3. Resolve module item links to Canvas file URLs
4. Add `download=1` and fetch the PDF bytes with the authenticated HTTP client

The CLI only keeps PDFs whose names contain `note.docx` or `note.pdf`.

## Prompt Architecture

Prompts are defined in [math_tutor/prompt_catalog.py](/home/nshah/projects/math-tutor/math_tutor/prompt_catalog.py):

- **`PromptTemplate`** captures the prompt family, shared text, and any source-prompt dependency
- **`ModelConfig`** declares the available model variants for generated prompts
- **`PromptSpec`** is the fully expanded generation contract used by the pipeline

The catalog expands template × model combinations into concrete prompt specs, and dependency ordering is resolved before execution so source prompts always run before derived prompts like MCQ generation.

**Bundled generation**: mental-math and olympiad prompts include MCQ as part of their bundle. Specifying `--prompt mental-math-gpt5` automatically includes `mental-math-gpt5-mcq`.

**Display-only prompts**: `study-guide-gemini` has `generate=False` — it is shown in the site but no API calls are made for it.

## Current Processing Rules

- `fetch_state.json` prevents refetching files that were already downloaded successfully
- `generated_output_state.json` tracks generated-output completion state (used for display, not for skip logic)
- Skip logic is **file-existence only**: if all output artifacts (`.md`, `.html`, optionally `.pdf`) exist, the prompt is skipped
- `--fetch-only` stops after download/state update
- `--skip-fetch` uses `fetch_state.json` directly; no Canvas login needed
- `--force-generation` reruns the generation step for already processed files

## Output Locations

Default output root: `math_tutor/output/`

- `downloads/` — fetched PDFs
- `responses/` — AI output per PDF per prompt (`.md`, `.html`, `.pdf`)
- `metadata/` — JSON metadata for traceability
- `fetch_state.json` — remembers fetched PDFs
- `generated_output_state.json` — remembers completed prompt steps across providers
- `site/` — local browsable HTML site (default build target)

Deploy root: `math_tutor/output/deploy/math_tutor/`

Generated production pages live directly under: `math_tutor/output/deploy/math_tutor/`

The disposable local preview tree `math_tutor/output/site/` was explicitly deleted on
2026-09-20. It is not a production input and can be recreated with `math-tutor-build-site`.
The 18 files in `math_tutor/output/deploy/math_tutor/downloads/` are retained legacy Algebra
copies; each was verified byte-for-byte against both `output/downloads/` and the active
`deploy/math_tutor/courses/algebra-2-trig/downloads/` copy. Current pages use the course-scoped
copies, but the legacy directory has not been deleted.

- `responses/` — copied from `output/responses/` during build
- `.htaccess` and other hosting-level assets can live at the deploy root
- `index.html` — course-selection portal
- `courses/algebra-2-trig/index.html` — Algebra course home
- `courses/algebra-2-trig/library.html` — Algebra chapter overview
- `courses/algebra-2-trig/live-tutor.html` — Algebra curriculum-wide guided learning
- `courses/algebra-2-trig/privacy-policy.html` — generated legal page linked from the auth flow
- `courses/algebra-2-trig/doc-<file_id>.html` — Algebra per-document pages
- `courses/algebra-2-trig/challenges/` — Algebra challenge exam app (Cloudflare Access protected)
- `courses/ap-calculus-ab/index.html` — AP Calculus AB course home with the available school chapters
- `courses/ap-calculus-ab/library.html` — Calculus chapter library
- `courses/ap-calculus-ab/doc-4839635.html` — Chapter 2 source-note page
- `courses/ap-calculus-ab/downloads/4839635_chapter-2-notetakers.pdf` — deployed school PDF
- `courses/ap-calculus-ab/doc-4839646.html` — Chapter 3 source-note, AI Challenge, and Cengage page
- `courses/ap-calculus-ab/downloads/4839646_chapter-3-notetakers.pdf` — deployed school PDF

## Current Site UX

- Public deploy base path is the domain root; canonical course URLs begin with `/courses/`
- `.vscode/sftp.json` currently syncs from local `output/deploy/math_tutor/` to remote `public_html/math_tutor/`
- `index.html` is a course selector for Algebra II / Trigonometry and AP Calculus AB
- Algebra pages live under `courses/algebra-2-trig/` and include a persistent `Switch Course` action
- AP Calculus AB lives under `courses/ap-calculus-ab/`; Chapters 2 and 3 are published from its isolated output and no Algebra content is inherited
- The Calculus Chapter 2 page includes a validated Cengage textbook map: students launch through a normal Canvas homework link and choose `Read It` in WebAssign; no direct MindTap or transient LTI/OIDC link is published
- Calculus exposes verified class notes for Chapters 2 and 3 and one reviewed GPT-5.4 study guide for Chapter 2 only. Both chapters retain their reviewed Cengage maps and expose no Live Tutor, generated mental math, olympiad content, or internal challenge-exam bank.
- Chapters 2 and 3 have deployed external AI Challenge sections with manifest-scoped Medium and Hard prompt cards. Each card copies a ten-question prompt and opens Gemini or ChatGPT; no API call, saved score, internal question bank, or provider model selection is involved. Canonical deployed locations use domain-root `/courses/...` URLs.
- One brand mark per page, all rendered from
  [math_tutor/site_brand.py](/home/nshah/projects/math-tutor/math_tutor/site_brand.py): the
  long-standing detailed π mark for the site and portal, a θ mark for Algebra, an ∫ mark for
  Calculus. Course pages carry their own course mark plus a `Math Delight` eyebrow, never two
  marks. The portal's former one-off circled glyph is retired.
- Every generated site page emits an inline percent-encoded SVG favicon. Documents under
  `responses/` do not; they come from `response_artifacts.py`, not the site shell.
- Course accent is the only color signal. Algebra keeps its shipped `#a14d2e`; Calculus uses
  `#12606b`. There is deliberately no per-chapter color.
- The library sidebar names no course and carries no brand mark. Course identity and the
  capability-aware nav belong to `site_sections.render_surface_header`; the sidebar's old
  hardcoded `Algebra II Trig Tutor` branch was unreachable dead code and was deleted.
- The Algebra library keeps the chapter list in the left rail and moves the branded nav header into the main panel
- The Algebra Live Tutor is a no-sidebar page with the same branded top header as the library overview
- Per-document pages keep a slim left rail without the full chapter list
- Challenge exam pages now use the same brand identity and top navigation language as the main site
- The challenge landing page tracks completed exams, hides already-finished picks, and links to `reports.php`

## Most Important Files

- [math_tutor/cli.py](/home/nshah/projects/math-tutor/math_tutor/cli.py)
- [math_tutor/site_builder.py](/home/nshah/projects/math-tutor/math_tutor/site_builder.py)
- [math_tutor/atomic_io.py](/home/nshah/projects/math-tutor/math_tutor/atomic_io.py)
- [math_tutor/README.md](/home/nshah/projects/math-tutor/math_tutor/README.md)
- [math_tutor/TASK_HISTORY.md](/home/nshah/projects/math-tutor/math_tutor/TASK_HISTORY.md)

## Refactor Checkpoint

The codebase is no longer organized around one large CLI file and one large site-builder file.

Current important module boundaries:

- CLI orchestration:
  - [math_tutor/cli.py](/home/nshah/projects/math-tutor/math_tutor/cli.py)
  - [math_tutor/cli_commands.py](/home/nshah/projects/math-tutor/math_tutor/cli_commands.py)
  - [math_tutor/cli_context.py](/home/nshah/projects/math-tutor/math_tutor/cli_context.py)
  - [math_tutor/cli_runtime.py](/home/nshah/projects/math-tutor/math_tutor/cli_runtime.py)
  - [math_tutor/cli_generation.py](/home/nshah/projects/math-tutor/math_tutor/cli_generation.py)
- Canvas logic:
  - [math_tutor/canvas_course.py](/home/nshah/projects/math-tutor/math_tutor/canvas_course.py)
  - [math_tutor/canvas_files.py](/home/nshah/projects/math-tutor/math_tutor/canvas_files.py)
  - [math_tutor/canvas_login.py](/home/nshah/projects/math-tutor/math_tutor/canvas_login.py)
- Prompt and artifact flow:
  - [math_tutor/prompt_catalog.py](/home/nshah/projects/math-tutor/math_tutor/prompt_catalog.py)
  - [math_tutor/prompt_pipeline.py](/home/nshah/projects/math-tutor/math_tutor/prompt_pipeline.py)
  - [math_tutor/prompt_generation.py](/home/nshah/projects/math-tutor/math_tutor/prompt_generation.py)
  - [math_tutor/prompt_output_store.py](/home/nshah/projects/math-tutor/math_tutor/prompt_output_store.py)
  - [math_tutor/study_guide_validation.py](/home/nshah/projects/math-tutor/math_tutor/study_guide_validation.py)
  - [math_tutor/course_curriculum.py](/home/nshah/projects/math-tutor/math_tutor/course_curriculum.py)
  - [math_tutor/response_artifacts.py](/home/nshah/projects/math-tutor/math_tutor/response_artifacts.py)
- Site generation:
  - [math_tutor/site_builder.py](/home/nshah/projects/math-tutor/math_tutor/site_builder.py)
  - [math_tutor/site_pages.py](/home/nshah/projects/math-tutor/math_tutor/site_pages.py)
  - [math_tutor/site_records.py](/home/nshah/projects/math-tutor/math_tutor/site_records.py)
  - [math_tutor/site_prompt_cards.py](/home/nshah/projects/math-tutor/math_tutor/site_prompt_cards.py)
  - [math_tutor/site_shell.py](/home/nshah/projects/math-tutor/math_tutor/site_shell.py)
  - [math_tutor/site_theme.py](/home/nshah/projects/math-tutor/math_tutor/site_theme.py)
  - [math_tutor/site_navigation.py](/home/nshah/projects/math-tutor/math_tutor/site_navigation.py)
  - [math_tutor/site_challenges.py](/home/nshah/projects/math-tutor/math_tutor/site_challenges.py)
  - [math_tutor/site_textbook.py](/home/nshah/projects/math-tutor/math_tutor/site_textbook.py)

This means future cleanup should usually target one focused module at a time instead of editing `cli.py` or `site_builder.py` as giant catch-all files.

## Common Commands

```bash
# Full run (fetch + generate all prompts)
.venv/bin/math-tutor --course algebra-2-trig

# Skip fetch, generate for a specific chapter
.venv/bin/math-tutor --course algebra-2-trig --skip-fetch --chapter 11.4

# Fetch only (no generation)
.venv/bin/math-tutor --course algebra-2-trig --fetch-only

# Fetch any AP Calculus AB chapter note without model calls
.venv/bin/math-tutor --course ap-calculus-ab --chapter 3 --fetch-only

# Discover review-only Canvas/Cengage metadata for a future chapter
.venv/bin/python -m math_tutor.calculus_onboarding --chapter 4

# Preview a reviewed Calculus chapter study guide without any model call
.venv/bin/math-tutor --course ap-calculus-ab --skip-fetch --chapter 3 --prompt study-guide --dry-run

# Build and validate the canonical production tree
.venv/bin/math-tutor-build-production

# Build, validate, deploy, and verify live content (explicit production mutation)
.venv/bin/math-tutor-deploy-production --confirm-production

# Backfill MCQ for existing notes (skips already-done)
.venv/bin/math-tutor-generate-mcq
```

For the current canonical operator runbook, including recovery from saved Markdown without new model calls, see [docs/OPERATIONS.md](/home/nshah/projects/math-tutor/math_tutor/docs/OPERATIONS.md).

## Safe Validation Before Refactors

From the repository root:

```bash
.venv/bin/python math_tutor/scripts/validate_project.py
```

This runs local unit tests and Python compilation checks without:

- fetching from Canvas
- calling model APIs
- rewriting the current deploy tree

Architecture and validation references:

- [docs/ARCHITECTURE.md](/home/nshah/projects/math-tutor/math_tutor/docs/ARCHITECTURE.md)
- [docs/VALIDATION.md](/home/nshah/projects/math-tutor/math_tutor/docs/VALIDATION.md)

## Challenge Exam Details

- 76 exams built from 608 MCQ-equipped questions (380 MM + 228 OP across 19 chapters)
- Exam structure: up to 7 mental math questions first, then at most 3 olympiad questions; max 10 per exam
- `save_progress.php` writes authenticated in-progress challenge state to MySQL
- `completed.php` returns completed exam ids for the current authenticated user
- `reports.php` shows per-user submissions plus in-progress sessions
- `exam.html` presents MCQ buttons (A/B/C/D) with immediate correct/wrong feedback after each selection
- `submit.php` prevents duplicate submissions per user+exam and returns the existing result token when needed
- `result.php` shows score chip + per-question MCQ option review with correct/wrong highlighting
- `challenges_src/master_questions.json` — flat catalog of all 608 MCQ questions (git tracked, not served to site); use for external purposes
- Force-rebuild challenges when question pool changes: `--force-challenges`

## Last Verified State

- 19 class note chapters fully processed (through chapter 11.4)
- All prompts: study-guide, inspiring-videos, mental-math-gpt5 + MCQ, mental-math-gemini + MCQ, olympiad-problems/solutions-gpt5 + MCQ, olympiad-problems/solutions-gemini + MCQ
- 76 MCQ challenge exams deployed; master_questions.json committed to git
- Site reorganized around a root course portal, a complete course-scoped Algebra experience, and an isolated AP Calculus AB course with Chapters 2 and 3
- Privacy policy page and challenge auth/reporting pages are part of the generated deploy output
- Deploy base path is empty; canonical production URLs are rooted at `/courses/...`
- Response file deploy copying works correctly (fixed `is_deploy_site_dir` bug)
- CLI fetch logs now summarize already-fetched vs pending files before processing
- All JSON state writers route through `math_tutor/atomic_io.py` and PDF downloads stream via a `.part` rename — mid-operation crashes no longer corrupt state files or leave truncated PDFs on disk (see [docs/ARCHITECTURE.md](/home/nshah/projects/math-tutor/math_tutor/docs/ARCHITECTURE.md) "Crash Safety")
- AP Calculus AB Chapter 2 canonical metadata is course-scoped as `Limits and Derivatives`, with verified sections 2.1 through 2.8.
- AP Calculus AB Chapter 2 now has a deployed external-AI challenge component with Medium and Hard ten-question prompts, Gemini and ChatGPT launch actions, clipboard fallback, exact course/chapter isolation, and responsive desktop/mobile rendering.
- AP Calculus AB Chapter 3 is deployed as `Chapter 3: Differentiation Rules` from Canvas file
  `4839646`. Its ten reviewed sections map to normal Canvas assignments `299784` through
  `299793`; the page contains ten Cengage cards and manifest-scoped Medium and Hard AI
  Challenge cards. It has no generated study guide and no Chapter 3 model call has occurred.
- Future Calculus chapters use `calculus_onboarding.py` for read-only Canvas assignment
  discovery. It writes a non-secret `review-required` candidate; after review, one
  `CalculusChapterManifest` supplies curriculum, textbook navigation, AI Challenge scope, and
  study-guide scope without renderer changes. Fetch-only accepts one whole-number chapter,
  while generation accepts only a reviewed manifest plus explicit `--skip-fetch --prompt
  study-guide`.
- One validated mastery-oriented GPT-5.4 study guide is saved under the isolated Calculus output tree. It uses authoritative supplemental teaching only within PDF-established topics, includes 15 worked examples and ten fully solved mastery problems, marks section 2.4 `Not covered`, and marks section 2.8 `Partially covered`.
- Never regenerate the Calculus study guide without explicit approval; site builds and recovery must reuse the saved Markdown/HTML/PDF.
- Local validation baseline is `338` passing tests plus `git diff --check`.
  The brand/navigation pass added `tests/test_site_brand.py` and `tests/test_site_navigation.py`,
  including a drift guard that fails if `challenges_src/*.html` diverges from the canonical mark
  in `site_brand.py`.
- The approved mastery-oriented replacement is deployed at the production domain-root path. Its
  HTML/PDF were rebuilt from saved Markdown after fixing multiline display math inside list items;
  no additional model call occurred.
- Production builds use `.venv/bin/math-tutor-build-production`. Production deployment uses
  `.venv/bin/math-tutor-deploy-production --confirm-production`; it validates the domain-root
  layout, rejects nested `site/` output and stale `/site/` links, syncs the deploy tree once,
  and verifies domain-root Calculus and Algebra content.
- The 2026-09-23 Chapter 3 production build passed the guarded validator. A pre-sync check
  confirmed ten textbook cards, two AI Challenge modes, and no gateway/OIDC/token or stale
  `/site/` material. The first SSH connection reset during key exchange before transfer; one
  retry completed and the guarded command reported successful live verification.
- Challenge exams were restored after generated public JSON was written as mode `0600` and
  `rsync -a` preserved that unreadable mode on production. Public challenge JSON is now created
  as `0644`, unchanged files have their mode repaired during builds, and production validation
  blocks JSON that is not web-readable. The static catalog now loads independently from optional
  `completed.php` progress data, so progress/database failure cannot block the picker. The fix was
  deployed, user-verified, committed as `3ebea09`, and pushed to `origin/main`.
- The obsolete local and remote `site/` trees were deleted after the root deployment passed live
  verification. The canonical Chapter 2 URL returns HTTP 200; the former `/site/` URL returns 404.
- A possible cumulative, subsection-oriented Calculus mental-math workflow was discussed but
  explicitly abandoned for now. It is not an approved phase or implementation plan. Do not add,
  expose, or generate Calculus mental-math content until the user provides new guidance and
  approves a new specification.
- The project `.env` contains updated Canvas credentials. Values must never be logged. The current
  shell may contain older inherited credential variables, so future authenticated fetches must
  clear `MATH_TUTOR_USERNAME`, `MATH_TUTOR_PASSWORD`, `CANVAS_USERNAME`, and `CANVAS_PASSWORD`
  for that command before the CLI reloads `.env`.

## OPEN SECURITY ACTION: Rotate The Database Password

Unresolved as of 2026-09-20. Do not consider this closed until the password is rotated.

A generated `challenges/config.php` containing live MySQL credentials was committed to this
**public** repository. `challenge_config.py` writes that file at build time from `DBNAME`,
`DBUSER`, `DBPASSWORD`, and `MySQL_HOST`. At the time, `.gitignore` covered
`math_tutor/output/` but the build had written a **repo-root** `output/` tree, which was not
ignored.

- Paths: `output/deploy/math_tutor/site/challenges/config.php` and
  `output/deploy/math_tutor/site/staging/challenges/config.php`
- Introduced: `ded60d6` (2026-04-09 18:49); removed from HEAD: `556fafc` (19:05)
- `DB_NAME`, `DB_USER`, `DB_PASS`, and `DB_HOST` were all populated
- The committed values are **identical to the credentials currently deployed**
- Publicly readable in history for roughly 5.4 months; deleting from HEAD did not remove the
  blob, which is still fetchable by commit SHA

Severity is reduced but not removed by `DB_HOST` being `localhost`: direct remote MySQL is
probably unavailable, but shared hosting often exposes phpMyAdmin or remote MySQL, and the
leaked `DB_USER` reveals the account naming convention.

Required, in order:

1. Rotate the MySQL password in the hosting control panel.
2. Update `DBPASSWORD` in `.env`.
3. Redeploy so `config.php` regenerates:
   `set -a && . ./.env && set +a && .venv/bin/math-tutor-deploy-production --confirm-production`
4. Review the challenge database and host access logs for unauthorized use.

History rewriting (`git filter-repo --path output/ --invert-paths` plus a force push) is
**optional hygiene and not remediation**. It rewrites every later commit SHA, breaks existing
clones including any a concurrent agent holds, and GitHub retains unreachable objects by SHA
until Support garbage-collects them. Rotate first; once rotated the leaked value is worthless.

A scan of full history found no other exposure: no OpenAI, Gemini, or GitHub tokens, no
private keys. `.env` and `sftp.json` were never committed, only their `.example` forms.

Recurrence is closed by `f6d9b12`, which ignores bare `output/` at any level.

## Known Risks

- The school SSO flow could change and require selector updates
- The Modules page structure could change
- OpenAI and Gemini runs require valid API keys with available quota
- Challenge exam app requires MySQL DB credentials in `.env`. These are injected into a
  generated `challenges/config.php` at build time; that file must never be tracked. See
  "OPEN SECURITY ACTION" above — the current credentials are exposed in public git history
  and rotation is still outstanding.
- `load_dotenv_if_present()` does not override an already-set non-empty environment variable,
  so a stale value inherited in the shell silently wins over `.env`. Source `.env` before
  deploying or `config.php` is generated with wrong credentials, breaking `reports.php`,
  `submit.php`, `result.php`, and `save_progress.php`.
- `challenge_builder.py` remains a larger orchestration module than the rest of the cleaned codebase, though its long function is procedural deploy wiring rather than mixed responsibility (lower priority than previously stated)
- `mcq_generator.py` was flagged in earlier handoffs but has since been split into `mcq_clients`, `mcq_workflow`, `mcq_artifacts`, and `mcq_prompts` — the remaining file is ~80 lines and no longer a refactor target
