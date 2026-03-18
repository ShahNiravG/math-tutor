# Math Tutor

`math_tutor` is a standalone Python CLI that:

1. Starts from the Canvas course at `https://mitty.instructure.com/courses/4187`
2. Follows the school's configured login redirect flow, including OneLogin if Canvas sends the browser there
3. Uses the authenticated course files pages to find PDF documents in that course
4. Downloads each PDF locally
5. Uploads each PDF to the OpenAI Responses API with a fixed prompt embedded in code
6. Saves the model output and run metadata to disk

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
- `--force`: reprocess files even if output already exists
- `--output-dir custom/path`: choose a different output directory
- `--login-url URL`: override the initial login entry URL if you need to bypass the course redirect flow

Outputs are written under the selected output directory:

- `downloads/`: fetched PDFs
- `responses/`: ChatGPT/OpenAI markdown output for each PDF
- `metadata/`: JSON metadata for traceability

## Notes

- The prompt is stored as the `PROMPT` constant in `math_tutor/cli.py`.
- The CLI expects the school login credentials on the command line, as requested.
- If login does not complete, rerun with `--headful` and inspect whether the site is using a different auth flow or MFA.
