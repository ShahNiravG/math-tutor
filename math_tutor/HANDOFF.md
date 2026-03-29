# Math Tutor Handoff

## What This Project Does

`math_tutor` logs into the Canvas course, finds PDF attachments, downloads them, sends them to OpenAI/Gemini with structured prompts, and saves the generated output plus metadata locally. It also builds a browsable HTML tutoring site from those outputs.

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

Prompts are defined via two dataclasses in `cli.py`:

- **`PromptTemplate`**: slug, title, prompt text, optional `source_template_slug` dependency, `generate_models` allowlist
- **`ModelConfig`**: slug (`""` = default/GPT-4.1, `"gpt5"` = GPT-5.4, `"gemini"` = Gemini 3.1 Pro)

`_build_prompt_spec()` creates `PromptSpec` instances from template × model cross-products. `_order_prompts()` topologically sorts them so dependents follow their source. PROMPTS has 21 entries.

**Bundled generation**: mental-math and olympiad prompts include MCQ as part of their bundle. Specifying `--prompt mental-math-gpt5` automatically includes `mental-math-gpt5-mcq`.

**Display-only prompts**: `study-guide-gemini` and `inspiring-videos-gemini` have `generate=False` — they are shown in the site but no API calls are made for them.

## Current Processing Rules

- `fetch_state.json` prevents refetching files that were already downloaded successfully
- `openai_state.json` tracks completion state (used for display, not for skip logic)
- Skip logic is **file-existence only**: if all output artifacts (`.md`, `.html`, optionally `.pdf`) exist, the prompt is skipped
- `--fetch-only` stops after download/state update
- `--skip-fetch` uses `fetch_state.json` directly; no Canvas login needed
- `--force-openai` reruns the AI step for already processed files

## Output Locations

Default output root: `math_tutor/output/`

- `downloads/` — fetched PDFs
- `responses/` — AI output per PDF per prompt (`.md`, `.html`, `.pdf`)
- `metadata/` — JSON metadata for traceability
- `fetch_state.json` — remembers fetched PDFs
- `openai_state.json` — remembers completed prompt steps
- `site/` — local browsable HTML site (default build target)

Deploy output: `math_tutor/output/deploy/math_tutor/site/`

- `responses/` — copied from `output/responses/` during build
- `index.html` — top-level landing page
- `library.html` — chapter overview page
- `live-tutor.html` — curriculum-wide guided learning page
- `doc-<file_id>.html` — per-document pages
- `challenges/` — challenge exam app (Cloudflare Access protected)
- `assignments/` — assignment PDFs (Cloudflare Access protected)

## Current Site UX

- Public deploy base path is `/site/`
- `index.html` is now a three-card landing page: Library, Challenge Exams, Live Tutor
- `library.html` keeps the chapter list in the left rail and moves the branded nav header into the main panel
- `live-tutor.html` is a no-sidebar page with the same branded top header as the library overview
- Per-document pages keep a slim left rail without the full chapter list
- Challenge exam pages now use the same brand identity and top navigation language as the main site

## Most Important Files

- [math_tutor/cli.py](/home/nshah/projects/math-tutor/math_tutor/cli.py)
- [math_tutor/site_builder.py](/home/nshah/projects/math-tutor/math_tutor/site_builder.py)
- [math_tutor/mcq_generator.py](/home/nshah/projects/math-tutor/math_tutor/mcq_generator.py)
- [math_tutor/README.md](/home/nshah/projects/math-tutor/math_tutor/README.md)
- [math_tutor/TASK_HISTORY.md](/home/nshah/projects/math-tutor/math_tutor/TASK_HISTORY.md)

## Common Commands

```bash
# Full run (fetch + generate all prompts)
.venv/bin/math-tutor --username EMAIL --password PASS

# Skip fetch, generate for a specific chapter
.venv/bin/math-tutor --skip-fetch --chapter 11.4

# Fetch only (no AI)
.venv/bin/math-tutor --username EMAIL --password PASS --fetch-only

# Build and deploy site
.venv/bin/math-tutor-build-site --site-dir math_tutor/output/deploy/math_tutor/site --base-path /site/

# Backfill MCQ for existing notes (skips already-done)
.venv/bin/math-tutor-generate-mcq
```

## Last Verified State

- 19 class note chapters fully processed (through chapter 11.4)
- All prompts: study-guide, inspiring-videos, mental-math-gpt5 + MCQ, mental-math-gemini + MCQ, olympiad-problems/solutions-gpt5 + MCQ, olympiad-problems/solutions-gemini + MCQ
- Deploy site at `output/deploy/math_tutor/site/` rebuilt and up to date
- Deploy links verified against `/site/` base path
- Response file deploy copying works correctly (fixed `is_deploy_site_dir` bug)

## Known Risks

- The school SSO flow could change and require selector updates
- The Modules page structure could change
- OpenAI and Gemini runs require valid API keys with available quota
- Challenge exam app requires MySQL DB credentials in `.env`
