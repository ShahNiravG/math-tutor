# Math Tutor

`math_tutor` is a standalone Python CLI that:

1. Starts from the Canvas course at `https://mitty.instructure.com/courses/4187`
2. Follows the school's configured login redirect flow, including OneLogin if Canvas sends the browser there
3. Finds only PDFs whose names contain `note.docx` or `note.pdf`
4. Uses the authenticated course pages to discover those PDFs
5. Downloads each PDF locally and remembers which files were fetched successfully
6. Uploads each PDF to the OpenAI Responses API once per prompt, with the prompts embedded in code
7. Saves each prompt-specific model output in Markdown, MathJax-enabled HTML, and PDF
8. Saves run metadata to disk
8. Can build a readable HTML tutoring page from the already-saved PDFs and responses

## Requirements

- Python 3.10+
- An `OPENAI_API_KEY` environment variable
- Playwright browser binaries installed

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

The CLI automatically loads environment variables from `../.env` when present, so you usually do not need to `export OPENAI_API_KEY` manually first.

Useful flags:

- `--headful`: opens the browser so you can watch or debug login
- `--limit 3`: process only the first three PDFs
- `--prompt study-guide`: run only the Study Guide prompt for each matched PDF
- `--prompt mental-math`: run only the Mental Math prompt for each matched PDF
- `--prompt olympiad-problems`: generate the harder Olympiad-style problem set
- `--prompt olympiad-solutions`: generate step-by-step solutions for the exact saved Olympiad problem set
- `--force-prompt inspiring-videos`: rerun OpenAI for just that prompt while leaving other prompts alone
- `--fetch-only`: only download matching PDFs and update fetch state
- `--force`: reprocess files even if output already exists
- `--force-openai`: rerun the OpenAI step even for files already processed successfully
- `--output-dir custom/path`: choose a different output directory
- `--login-url URL`: override the initial login entry URL if you need to bypass the course redirect flow
- `--build-site-guided-learning`: after processing, build the tutoring page with a `Guided Learning` section for each PDF processed in that run
- `--site-dir custom/path`: choose where that generated tutoring page is written
- `--site-base-path /subpath/`: optionally generate subpath-aware links for the auto-built tutoring page when deploying below the domain root

Outputs are written under the selected output directory:

- `downloads/`: fetched PDFs
- `responses/`: ChatGPT/OpenAI output for each PDF and prompt in `.md`, `.html`, and `.pdf`
- `metadata/`: JSON metadata for traceability
- `fetch_state.json`: remembers which PDFs were fetched successfully
- `openai_state.json`: remembers which PDFs completed each prompt's OpenAI step successfully
- `site/index.html`: a browsable tutoring library landing page built from saved local files
- `site/doc-<file_id>.html`: per-document pages with shared left navigation

## Build The Tutoring Page

```bash
math-tutor-build-site
```

This reads the existing saved PDFs, responses, and state files and generates:

- `math_tutor/output/site/index.html`

Useful flag:

- `--site-dir custom/path`: write the generated HTML page to a different directory
- `--base-path /subpath/`: generate deploy-ready links such as `/subpath/downloads/...` when deploying below the domain root
- `--limit 1`: build the page for only the first saved PDF so you can test changes safely
- `--include-guided-learning`: add a `Guided Learning` section for each PDF with Gemini and ChatGPT helper buttons

If you build into a deploy directory such as `~/public_html` or another publish target, the site builder copies the referenced PDFs and response files into that directory. By default it keeps links relative, which works well for root-domain deployments like `https://mathdelight.com/`. Use `--base-path` only when the site will live under a subpath.

The `Guided Learning` helper adds plain buttons for Gemini and ChatGPT Study Mode, plus a copy button for the `Short Summary` text from the document's Study Guide so it can be pasted into either tool.

## Backfill HTML Responses

If you already have saved Study Guide Markdown responses from earlier runs, you can generate matching HTML and PDF response files and normalize the saved state without rerunning OpenAI:

```bash
math-tutor-backfill-response-html
```

## Notes

 - The prompts are stored in [cli.py](/home/nshah/projects/math-tutor/math_tutor/cli.py), including Study Guide, Mental Math, Olympiad Problems, and Olympiad Solutions.
- The CLI expects the school login credentials on the command line, as requested.
- The CLI only processes PDFs whose visible names contain `note.docx` or `note.pdf`.
- The Study Guide prompt keeps the original legacy filenames, so already completed Study Guide runs are preserved and not repeated.
- The CLI tracks OpenAI success per PDF and per prompt, so it only calls OpenAI again when that specific prompt output is missing or forced.
- You can target one or more prompts with repeated `--prompt` flags, and `--force-openai` applies to the selected prompts only.
- You can also target reruns more explicitly with repeated `--force-prompt` flags, such as `--prompt inspiring-videos --force-prompt inspiring-videos --limit 1`.
- `Olympiad Solutions` depends on the exact saved `Olympiad Problems` output for that PDF. If the problems do not exist yet, the CLI generates them first and then saves the solutions separately.
- The HTML tutoring site is built from already saved files, so it does not need to refetch PDFs or rerun OpenAI.
- Math formulas render better in the saved `.html` response files than in plain Markdown viewers, and the generated PDF responses are convenient for printing or sharing.
- The tutoring site uses a multi-page layout so each document opens on its own page while the left navigation remains available throughout.
- `math-tutor --build-site-guided-learning --limit 1` builds the page for exactly the PDF processed in that run, which makes Guided Learning easy to test before generating the full library.
- If login does not complete, rerun with `--headful` and inspect whether the site is using a different auth flow or MFA.
