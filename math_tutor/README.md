# Math Tutor

`math_tutor` is a standalone Python CLI that:

1. Starts from the Canvas course at `https://mitty.instructure.com/courses/4187`
2. Follows the school's configured login redirect flow, including OneLogin if Canvas sends the browser there
3. Finds only PDFs whose names contain `note.docx`
4. Uses the authenticated course pages to discover those PDFs
5. Downloads each PDF locally and remembers which files were fetched successfully
6. Uploads each PDF to the OpenAI Responses API with a fixed prompt embedded in code
7. Saves the model output and run metadata to disk
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
export OPENAI_API_KEY=your_key_here
math-tutor \
  --username your_canvas_username \
  --password your_canvas_password
```

Useful flags:

- `--headful`: opens the browser so you can watch or debug login
- `--limit 3`: process only the first three PDFs
- `--fetch-only`: only download matching PDFs and update fetch state
- `--force`: reprocess files even if output already exists
- `--force-openai`: rerun the OpenAI step even for files already processed successfully
- `--output-dir custom/path`: choose a different output directory
- `--login-url URL`: override the initial login entry URL if you need to bypass the course redirect flow

Outputs are written under the selected output directory:

- `downloads/`: fetched PDFs
- `responses/`: ChatGPT/OpenAI markdown output for each PDF
- `metadata/`: JSON metadata for traceability
- `fetch_state.json`: remembers which PDFs were fetched successfully
- `openai_state.json`: remembers which PDFs completed the OpenAI step successfully
- `site/index.html`: a browsable tutoring page built from saved local files

## Build The Tutoring Page

```bash
math-tutor-build-site
```

This reads the existing saved PDFs, responses, and state files and generates:

- `math_tutor/output/site/index.html`

Useful flag:

- `--site-dir custom/path`: write the generated HTML page to a different directory

## Notes

- The prompt is stored as the `PROMPT` constant in `math_tutor/cli.py`.
- The CLI expects the school login credentials on the command line, as requested.
- The CLI only processes PDFs whose visible names contain `note.docx`.
- The HTML tutoring page is built from already saved files, so it does not need to refetch PDFs or rerun OpenAI.
- If login does not complete, rerun with `--headful` and inspect whether the site is using a different auth flow or MFA.
