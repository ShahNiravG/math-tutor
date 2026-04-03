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

Generated site pages live under: `math_tutor/output/deploy/math_tutor/site/`

- `responses/` — copied from `output/responses/` during build
- `.htaccess` and other hosting-level assets can live at the deploy root
- `index.html` — top-level landing page
- `library.html` — chapter overview page
- `live-tutor.html` — curriculum-wide guided learning page
- `privacy-policy.html` — generated legal page linked from the auth flow
- `doc-<file_id>.html` — per-document pages
- `challenges/` — challenge exam app (Cloudflare Access protected)
- `assignments/` — assignment PDFs (Cloudflare Access protected)

## Current Site UX

- Public deploy base path is `/site/`
- `.vscode/sftp.json` currently syncs from local `output/deploy/math_tutor/` to remote `public_html/math_tutor/`
- `index.html` is now a three-card landing page: Library, Challenge Exams, Live Tutor
- `library.html` keeps the chapter list in the left rail and moves the branded nav header into the main panel
- `live-tutor.html` is a no-sidebar page with the same branded top header as the library overview
- Per-document pages keep a slim left rail without the full chapter list
- Challenge exam pages now use the same brand identity and top navigation language as the main site
- The challenge landing page tracks completed exams, hides already-finished picks, and links to `reports.php`

## Most Important Files

- [math_tutor/cli.py](/home/nshah/projects/math-tutor/math_tutor/cli.py)
- [math_tutor/site_builder.py](/home/nshah/projects/math-tutor/math_tutor/site_builder.py)
- [math_tutor/mcq_generator.py](/home/nshah/projects/math-tutor/math_tutor/mcq_generator.py)
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

This means future cleanup should usually target one focused module at a time instead of editing `cli.py` or `site_builder.py` as giant catch-all files.

## Common Commands

```bash
# Full run (fetch + generate all prompts)
.venv/bin/math-tutor --username EMAIL --password PASS

# Skip fetch, generate for a specific chapter
.venv/bin/math-tutor --skip-fetch --chapter 11.4

# Fetch only (no generation)
.venv/bin/math-tutor --username EMAIL --password PASS --fetch-only

# Build and deploy site
.venv/bin/math-tutor-build-site --site-dir math_tutor/output/deploy/math_tutor/site --base-path /site/

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
- Site redesigned: index.html (landing), library.html, live-tutor.html pages added
- Privacy policy page and challenge auth/reporting pages are part of the generated deploy output
- Deploy base path is `/site/`; all build commands use `--base-path /site/`
- Response file deploy copying works correctly (fixed `is_deploy_site_dir` bug)
- CLI fetch logs now summarize already-fetched vs pending files before processing
- Local validation baseline is `78` passing tests via `math_tutor/scripts/validate_project.py`
- The current refactor checkpoint did not rerun model APIs and did not rebuild the deploy tree in place unless explicitly requested

## Known Risks

- The school SSO flow could change and require selector updates
- The Modules page structure could change
- OpenAI and Gemini runs require valid API keys with available quota
- Challenge exam app requires MySQL DB credentials in `.env`
- `challenge_builder.py` and `mcq_generator.py` are still larger mixed-responsibility modules than the rest of the cleaned codebase
