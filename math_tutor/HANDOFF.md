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

## Output Locations

Default output root:

- [math_tutor/output](/home/nshah/projects/SimpleRadixSort/math_tutor/output)

Subdirectories:

- [downloads](/home/nshah/projects/SimpleRadixSort/math_tutor/output/downloads)
- [responses](/home/nshah/projects/SimpleRadixSort/math_tutor/output/responses)
- [metadata](/home/nshah/projects/SimpleRadixSort/math_tutor/output/metadata)

## Most Important Files

- [math_tutor/cli.py](/home/nshah/projects/SimpleRadixSort/math_tutor/cli.py)
- [math_tutor/README.md](/home/nshah/projects/SimpleRadixSort/math_tutor/README.md)
- [math_tutor/TASK_HISTORY.md](/home/nshah/projects/SimpleRadixSort/math_tutor/TASK_HISTORY.md)

## Last Verified State

Live verification with `--limit 1` confirmed:

- login reached the real course flow
- one PDF was discovered from Modules
- the PDF downloaded successfully
- the OpenAI request was formed correctly enough to execute

The remaining blocker was external:

- OpenAI returned `429 insufficient_quota`

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
