# Math Tutor Handoff

## What This Project Does

`math_tutor` logs into the Canvas course, finds PDF attachments, downloads them, sends them to OpenAI with a fixed prompt, and saves the generated output plus metadata locally.

## Current Login Flow

- The CLI starts from the course URL, not `/login/canvas`
- The site redirects through the school's real SSO flow
- The implementation supports OneLogin's two-step username/password flow
- `--headful` keeps the browser open until you press Enter

## Current Document Discovery Flow

The course Files page is disabled and the Canvas Files API returned `403`, so discovery now uses the authenticated UI:

1. Try the course Files area
2. If that yields nothing, scrape PDF attachments from the Modules page
3. Resolve module item links to Canvas file URLs
4. Add `download=1` and fetch the PDF bytes with the authenticated HTTP client

The CLI only keeps PDFs whose names contain `note.docx` or `note.pdf`.

## Current Processing Rules

- `fetch_state.json` prevents refetching files that were already downloaded successfully
- `openai_state.json` prevents rerunning OpenAI for files that already completed successfully
- `--fetch-only` stops after download/state update
- `--force-openai` reruns the OpenAI step for already processed files

## Output Locations

Default output root:

- [math_tutor/output](/home/nshah/projects/math-tutor/math_tutor/output)

Subdirectories:

- [downloads](/home/nshah/projects/math-tutor/math_tutor/output/downloads)
- [responses](/home/nshah/projects/math-tutor/math_tutor/output/responses)
- [metadata](/home/nshah/projects/math-tutor/math_tutor/output/metadata)
- [fetch_state.json](/home/nshah/projects/math-tutor/math_tutor/output/fetch_state.json)
- [openai_state.json](/home/nshah/projects/math-tutor/math_tutor/output/openai_state.json)

## Most Important Files

- [math_tutor/cli.py](/home/nshah/projects/math-tutor/math_tutor/cli.py)
- [math_tutor/README.md](/home/nshah/projects/math-tutor/math_tutor/README.md)
- [math_tutor/TASK_HISTORY.md](/home/nshah/projects/math-tutor/math_tutor/TASK_HISTORY.md)
- [math_tutor/HANDOFF.md](/home/nshah/projects/math-tutor/math_tutor/HANDOFF.md)

## Last Verified State

Recent live verification confirmed:

- `--limit 1` completed end to end successfully
- `--fetch-only` skips OpenAI and remembers prior successful downloads
- normal reruns skip OpenAI for files already processed successfully
- `--force-openai` reruns the OpenAI step while reusing the downloaded PDF

## Known Risks

- The school SSO flow could change and require selector updates
- The Modules page structure could change
- OpenAI runs require a valid key with available quota

## Recommended Next Command

```bash
math-tutor --username YOUR_USERNAME --password YOUR_PASSWORD --limit 1
```

If the login flow changes or needs manual confirmation:

```bash
math-tutor --username YOUR_USERNAME --password YOUR_PASSWORD --limit 1 --headful
```
