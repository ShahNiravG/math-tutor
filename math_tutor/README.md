# Math Tutor

`math_tutor` is a standalone Python CLI that:

1. Starts from the Canvas course at `https://mitty.instructure.com/courses/4187`
2. Follows the school's configured login redirect flow, including OneLogin if Canvas sends the browser there
3. Finds only PDFs whose names contain `note.docx` or `note.pdf`
4. Uses the authenticated course pages to discover those PDFs
5. Downloads each PDF locally and remembers which files were fetched successfully
6. Uploads each PDF to OpenAI or Gemini once per prompt, with the prompts embedded in code
7. Saves each prompt-specific model output in Markdown, MathJax-enabled HTML, and PDF
8. Saves run metadata to disk
9. Can build a readable HTML tutoring site, privacy policy page, and challenge-exam app from the already-saved PDFs and responses

## Requirements

- Python 3.10+
- Playwright browser binaries installed
- `OPENAI_API_KEY` environment variable — required only when running OpenAI (GPT-4.1 or GPT-5.4) prompts
- `GEMINI_API_KEY` environment variable — required only when running Gemini prompts

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
playwright install chromium
```

## Usage

```bash
cp ../.env.example ../.env
math-tutor \
  --username your_canvas_username \
  --password your_canvas_password
```

The CLI automatically loads environment variables from `../.env` when present, so you usually do not need to `export OPENAI_API_KEY` or `export GEMINI_API_KEY` manually first.

For exact operator workflows, recovery steps, and deploy commands, see [docs/OPERATIONS.md](/home/nshah/projects/math-tutor/math_tutor/docs/OPERATIONS.md).

### Prompt slugs

Each prompt generates a separate output file. Supported slugs:

| Slug | Model | Description |
|---|---|---|
| `study-guide` | GPT-4.1 | Study guide with short summary, key concepts, and practice problems |
| `study-guide-gemini` | Gemini 3.1 Pro | Same study guide prompt via Gemini (display-only — no new API calls) |
| `inspiring-videos` | GPT-4.1 | Curated YouTube search suggestions |
| `inspiring-videos-gemini` | Gemini 3.1 Pro | Gemini-grounded YouTube search suggestions |
| `mental-math-gpt5` | GPT-5.4 | Mental math drill set |
| `mental-math-gpt5-mcq` | GPT-5.4 | Multiple-choice options for the GPT-5.4 mental math questions |
| `mental-math-gemini` | Gemini 3.1 Pro | Mental math drill set via Gemini |
| `mental-math-gemini-mcq` | Gemini 3.1 Pro | Multiple-choice options for the Gemini mental math questions |
| `olympiad-problems-gpt5` | GPT-5.4 | Olympiad-style hard problem set |
| `olympiad-solutions-gpt5` | GPT-5.4 | Step-by-step solutions for the saved GPT-5.4 olympiad problem set |
| `olympiad-problems-gpt5-mcq` | GPT-5.4 | Multiple-choice options for the GPT-5.4 olympiad problems |
| `olympiad-problems-gemini` | Gemini 3.1 Pro | Olympiad-style hard problem set via Gemini |
| `olympiad-solutions-gemini` | Gemini 3.1 Pro | Step-by-step solutions for the saved Gemini olympiad problem set |
| `olympiad-problems-gemini-mcq` | Gemini 3.1 Pro | Multiple-choice options for the Gemini olympiad problems |

### Useful flags

- `--headful`: opens the browser so you can watch or debug login
- `--limit 3`: process only the first three PDFs
- `--prompt mental-math-gpt5`: run only that prompt slug for each matched PDF (repeatable; auto-includes dependent MCQ prompts)
- `--force-prompt inspiring-videos`: rerun just that prompt while leaving other prompts alone
- `--fetch-only`: only download matching PDFs and update fetch state
- `--skip-fetch`: skip Canvas login and use already-downloaded PDFs from `fetch_state.json`
- `--fetch-assignments`: fetch assignment PDFs instead of class notes
- `--assignment-limit 10`: cap assignment fetches when `--fetch-assignments` is used
- `--chapter 11.4`: filter to a specific chapter (repeatable; works with `--skip-fetch`)
- `--force`: reprocess files even if output already exists
- `--force-generation`: rerun the generation step even for files already processed successfully
- `--list-files`: print all discovered course PDFs and exit
- `--print-prompt study-guide`: print saved prompt PDFs without rerunning fetch or generation
- `--print-all --chapter 7.4`: print class notes, assignments, and generated PDFs for a chapter
- `--dry-run`: preview what `--print-prompt` or `--print-all` would print
- `--output-dir custom/path`: choose a different output directory
- `--login-url URL`: override the initial login entry URL if the auth flow has changed
- `--site-dir custom/path`: choose where the generated tutoring page is written
- `--site-base-path /subpath/`: generate subpath-aware links when deploying below the domain root

### Gemini-only runs

When all selected prompts use Gemini, `OPENAI_API_KEY` is not required:

```bash
math-tutor \
  --username ... --password ... \
  --prompt mental-math-gemini \
  --prompt olympiad-problems-gemini \
  --prompt olympiad-solutions-gemini
```

The skip logic works the same way for Gemini as for OpenAI: if a prompt output already exists for a given PDF it is not regenerated unless `--force-generation` is passed.

### Output files

Outputs are written under the selected output directory (default: `math_tutor/output/`):

- `downloads/`: fetched PDFs
- `responses/`: AI output for each PDF and prompt in `.md`, `.html`, and `.pdf`
- `metadata/`: JSON metadata for traceability
- `fetch_state.json`: remembers which PDFs were fetched successfully
- `generated_output_state.json`: remembers which PDFs completed each prompt step successfully across OpenAI and Gemini
- `site/index.html`: a browsable tutoring library landing page
- `site/doc-<file_id>.html`: per-document pages with shared left navigation

## Build the Tutoring Site

```bash
math-tutor-build-site
```

This reads the existing saved PDFs, responses, and state files and generates the full HTML site under `math_tutor/output/site/`. The build also writes the challenge-exam assets and `privacy-policy.html`, and regenerates challenge `config.php` from the current `.env`.
The styled `staging` experience is now the default for builds. If you need the older pre-refresh look, use `--experience archived`.

Useful flags:

- `--site-dir custom/path`: write the generated HTML to a different directory
- `--base-path /subpath/`: generate deploy-ready links when deploying below the domain root
- `--limit 1`: build for only the first saved PDF (useful for testing layout changes)

### Site layout

**Home page (`index.html`)** — a top-level landing page with three primary destinations:

- **Library** — chapter browsing
- **Challenge Exams** — the timed exam app
- **Live Tutor** — curriculum-wide guided learning launch page

**Library page (`library.html`)** — one card per document, each showing a summary row. The chapter list stays in the left rail only on this page.

**Live Tutor page (`live-tutor.html`)** — a full-curriculum guided learning page with one combined prompt assembled from all chapter summaries, plus Gemini/ChatGPT Study Mode launch actions.

**Per-document pages (`doc-<id>.html`)** — four prompt cards per document:

- **Study Guide** — one row per model (GPT-4.1, Gemini 3.1 Pro), with an HTML link and a `[PDF]` link
- **Inspiring Videos** — same model-row layout
- **Mental Math** — same model-row layout
- **Olympiad Problems & Solutions** — one card combining both prompts; rows are grouped by model, each showing `Problems [PDF]   Solutions [PDF]`

Each per-document page also includes a **Guided Learning** section with Gemini and ChatGPT Study Mode helper links and a copy button for the short summary from the Study Guide.

**Challenge Exams (`challenges/index.html`)** — branded challenge landing page with random exam picker. Exam runner at `challenges/exam.html` presents MCQ questions (mental math first, then up to 3 olympiad problems) with immediate correct/wrong feedback after each selection. Results page shows score and per-question MCQ review. Cloudflare Access protected.

The challenge area also includes:

- resume support from saved local state plus server-side progress saves for authenticated users
- `completed.php` and `reports.php` so the picker can hide completed exams and show submission history
- duplicate-submission protection so re-submitting the same exam returns the saved result instead of creating a second row
- a generated `privacy-policy.html` page used by the Google-authenticated challenge flow

### Deploy path

The current production site is deployed under `/site/`, while the SFTP sync root is `math_tutor/output/deploy/math_tutor/` as configured in `.vscode/sftp.json`. Build the site into that deploy tree with:

```bash
.venv/bin/math-tutor-build-site \
  --site-dir math_tutor/output/deploy/math_tutor/site \
  --base-path /site/
```

Then sync the whole `math_tutor/output/deploy/math_tutor/` folder to Bluehost. The generated tutoring pages live under its `site/` subfolder, and the deploy root can also contain top-level files like `.htaccess`.

### Model display names

Prompt outputs are labeled by model. The `-preview` suffix is stripped from display labels, so `gemini-3.1-pro-preview` appears as `gemini-3.1-pro`.

## Backfill HTML Responses

If you already have saved Study Guide Markdown responses from earlier runs, you can generate matching HTML and PDF response files and normalize the saved state without rerunning the AI:

```bash
math-tutor-backfill-response-html
```

## Engineering Validation

Run the local validation workflow before refactoring core behavior:

```bash
.venv/bin/python math_tutor/scripts/validate_project.py
```

This validation path is intentionally safe for preserved artifacts:

- no OpenAI calls
- no Gemini calls
- no Canvas fetches
- no deploy-tree rewrites

## Architecture and Contracts

Reference docs:

- [docs/ARCHITECTURE.md](/home/nshah/projects/math-tutor/math_tutor/docs/ARCHITECTURE.md)
- [docs/VALIDATION.md](/home/nshah/projects/math-tutor/math_tutor/docs/VALIDATION.md)
- [docs/OPERATIONS.md](/home/nshah/projects/math-tutor/math_tutor/docs/OPERATIONS.md)

## Current Engineering State

The codebase has been split into smaller modules so the main entry points are no longer the source of truth for every behavior.

Examples:

- CLI/runtime orchestration:
  - [cli.py](/home/nshah/projects/math-tutor/math_tutor/cli.py)
  - [cli_commands.py](/home/nshah/projects/math-tutor/math_tutor/cli_commands.py)
  - [cli_context.py](/home/nshah/projects/math-tutor/math_tutor/cli_context.py)
  - [cli_runtime.py](/home/nshah/projects/math-tutor/math_tutor/cli_runtime.py)
  - [cli_generation.py](/home/nshah/projects/math-tutor/math_tutor/cli_generation.py)
- Canvas integration:
  - [canvas_course.py](/home/nshah/projects/math-tutor/math_tutor/canvas_course.py)
  - [canvas_files.py](/home/nshah/projects/math-tutor/math_tutor/canvas_files.py)
  - [canvas_login.py](/home/nshah/projects/math-tutor/math_tutor/canvas_login.py)
- Prompt generation/output:
  - [prompt_catalog.py](/home/nshah/projects/math-tutor/math_tutor/prompt_catalog.py)
  - [prompt_pipeline.py](/home/nshah/projects/math-tutor/math_tutor/prompt_pipeline.py)
  - [prompt_generation.py](/home/nshah/projects/math-tutor/math_tutor/prompt_generation.py)
  - [prompt_output_store.py](/home/nshah/projects/math-tutor/math_tutor/prompt_output_store.py)
  - [response_artifacts.py](/home/nshah/projects/math-tutor/math_tutor/response_artifacts.py)
- Site generation/rendering:
  - [site_builder.py](/home/nshah/projects/math-tutor/math_tutor/site_builder.py)
  - [site_pages.py](/home/nshah/projects/math-tutor/math_tutor/site_pages.py)
  - [site_records.py](/home/nshah/projects/math-tutor/math_tutor/site_records.py)
  - [site_prompt_cards.py](/home/nshah/projects/math-tutor/math_tutor/site_prompt_cards.py)
  - [site_shell.py](/home/nshah/projects/math-tutor/math_tutor/site_shell.py)
  - [site_theme.py](/home/nshah/projects/math-tutor/math_tutor/site_theme.py)
  - [site_navigation.py](/home/nshah/projects/math-tutor/math_tutor/site_navigation.py)
  - [site_challenges.py](/home/nshah/projects/math-tutor/math_tutor/site_challenges.py)

Current validation baseline:

- `195` unit tests pass through [scripts/validate_project.py](/home/nshah/projects/math-tutor/math_tutor/scripts/validate_project.py)
- core modules compile successfully with `py_compile`
- validation does not call model APIs, fetch from Canvas, or rewrite the current deploy tree

## Crash Safety

The generation pipeline is long-running and operator-interruptible, so expensive saved state must survive crashes, Ctrl-C, disk-full, and OOM cleanly.

- **JSON state writes**: every writer routes through [atomic_io.py](/home/nshah/projects/math-tutor/math_tutor/atomic_io.py). The helper writes to a sibling tempfile in the destination's own directory, `fsync`s it, then `os.replace`s it into place. A failure at any point leaves the previous file contents untouched and removes the tempfile. Covers `fetch_state.json`, `generated_output_state.json`, per-prompt metadata sidecars, challenge catalogs, AMC curated exams, and the artifact-name migration.
- **PDF downloads**: [canvas_course.download_pdf](/home/nshah/projects/math-tutor/math_tutor/canvas_course.py) streams to a sibling `.<name>.part` file and renames it into the destination only on full success. A dropped connection or HTTP error never leaves a truncated PDF on disk and never clobbers a previously fetched good file.
- **Narrow exception handlers**: helpers like `validate_youtube_url` catch only the specific failure modes they expect (`httpx.HTTPError`, `json.JSONDecodeError`, `ValueError`). Programming errors propagate so bugs stay visible.

See [docs/ARCHITECTURE.md](/home/nshah/projects/math-tutor/math_tutor/docs/ARCHITECTURE.md) "Crash Safety" for the full contract and rules for adding new persistent writers.

## Notes

- Prompts are defined in [prompt_catalog.py](/home/nshah/projects/math-tutor/math_tutor/prompt_catalog.py).
- The CLI only processes PDFs whose visible names contain `note.docx` or `note.pdf`.
- The Study Guide prompt keeps legacy filenames so already-completed Study Guide runs are preserved and not repeated.
- The CLI tracks success per PDF and per prompt slug, so it only reruns when that specific output is missing or forced.
- You can target one or more prompts with repeated `--prompt` flags, and `--force-generation` applies only to the selected prompts.
- `Olympiad Solutions` depends on the saved `Olympiad Problems` output for the same PDF. If the problems file does not exist yet, the CLI generates it first.
- The HTML tutoring site is built from already-saved files and does not need to refetch PDFs or rerun the AI.
- The Gemini inspiring-videos prompt uses Google Search grounding in the Gemini API.
- Math formulas render best in the saved `.html` response files (MathJax). The `.pdf` files are convenient for printing or sharing.
- If login does not complete, rerun with `--headful` and inspect whether the site is using a different auth flow or MFA.
