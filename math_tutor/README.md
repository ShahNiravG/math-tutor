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
9. Can build a readable HTML tutoring site from the already-saved PDFs and responses

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

### Prompt slugs

Each prompt generates a separate output file. Supported slugs:

| Slug | Model | Description |
|---|---|---|
| `study-guide` | GPT-4.1 | Study guide with short summary, key concepts, and practice problems |
| `study-guide-gemini` | Gemini 3.1 Pro | Same study guide prompt via Gemini |
| `inspiring-videos` | GPT-4.1 | Curated YouTube search suggestions |
| `inspiring-videos-gemini` | Gemini 3.1 Pro | Same inspiring videos prompt via Gemini |
| `mental-math` | GPT-4.1 | Mental math drill set |
| `mental-math-gemini` | Gemini 3.1 Pro | Same mental math prompt via Gemini |
| `olympiad-problems` | GPT-5.4 | Olympiad-style hard problem set |
| `olympiad-problems-gemini` | Gemini 3.1 Pro | Same olympiad problems via Gemini |
| `olympiad-solutions` | GPT-5.4 | Step-by-step solutions for the saved olympiad problem set |
| `olympiad-solutions-gemini` | Gemini 3.1 Pro | Same olympiad solutions via Gemini |

### Useful flags

- `--headful`: opens the browser so you can watch or debug login
- `--limit 3`: process only the first three PDFs
- `--prompt mental-math`: run only that prompt slug for each matched PDF (repeatable)
- `--prompt mental-math-gemini --prompt olympiad-problems-gemini`: run multiple Gemini prompts in one pass
- `--force-prompt inspiring-videos`: rerun just that prompt while leaving other prompts alone
- `--fetch-only`: only download matching PDFs and update fetch state
- `--force`: reprocess files even if output already exists
- `--force-openai`: rerun the AI step even for files already processed successfully
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

The skip logic works the same way for Gemini as for OpenAI: if a prompt output already exists for a given PDF it is not regenerated unless `--force-openai` is passed.

### Output files

Outputs are written under the selected output directory (default: `math_tutor/output/`):

- `downloads/`: fetched PDFs
- `responses/`: AI output for each PDF and prompt in `.md`, `.html`, and `.pdf`
- `metadata/`: JSON metadata for traceability
- `fetch_state.json`: remembers which PDFs were fetched successfully
- `openai_state.json`: remembers which PDFs completed each prompt step successfully (used for both OpenAI and Gemini)
- `site/index.html`: a browsable tutoring library landing page
- `site/doc-<file_id>.html`: per-document pages with shared left navigation

## Build the Tutoring Site

```bash
math-tutor-build-site
```

This reads the existing saved PDFs, responses, and state files and generates the full HTML site under `math_tutor/output/site/`.

Useful flags:

- `--site-dir custom/path`: write the generated HTML to a different directory
- `--base-path /subpath/`: generate deploy-ready links when deploying below the domain root
- `--limit 1`: build for only the first saved PDF (useful for testing layout changes)

### Site layout

**Index page (`index.html`)** — one card per document, each showing a summary row.

**Per-document pages (`doc-<id>.html`)** — four prompt cards per document:

- **Study Guide** — one row per model (GPT-4.1, Gemini 3.1 Pro), with an HTML link and a `[PDF]` link
- **Inspiring Videos** — same model-row layout
- **Mental Math** — same model-row layout
- **Olympiad Problems & Solutions** — one card combining both prompts; rows are grouped by model, each showing `Problems [PDF]   Solutions [PDF]`

Each per-document page also includes a **Guided Learning** section with Gemini and ChatGPT Study Mode helper links and a copy button for the short summary from the Study Guide.

### Model display names

Prompt outputs are labeled by model. The `-preview` suffix is stripped from display labels, so `gemini-3.1-pro-preview` appears as `gemini-3.1-pro`.

## Backfill HTML Responses

If you already have saved Study Guide Markdown responses from earlier runs, you can generate matching HTML and PDF response files and normalize the saved state without rerunning the AI:

```bash
math-tutor-backfill-response-html
```

## Notes

- Prompts are defined in [cli.py](cli.py).
- The CLI only processes PDFs whose visible names contain `note.docx` or `note.pdf`.
- The Study Guide prompt keeps legacy filenames so already-completed Study Guide runs are preserved and not repeated.
- The CLI tracks success per PDF and per prompt slug, so it only reruns when that specific output is missing or forced.
- You can target one or more prompts with repeated `--prompt` flags, and `--force-openai` applies only to the selected prompts.
- `Olympiad Solutions` depends on the saved `Olympiad Problems` output for the same PDF. If the problems file does not exist yet, the CLI generates it first.
- The HTML tutoring site is built from already-saved files and does not need to refetch PDFs or rerun the AI.
- Math formulas render best in the saved `.html` response files (MathJax). The `.pdf` files are convenient for printing or sharing.
- If login does not complete, rerun with `--headful` and inspect whether the site is using a different auth flow or MFA.
