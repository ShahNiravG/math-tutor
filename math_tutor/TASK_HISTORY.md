# Math Tutor Task History

This file is a working log of what we changed while building and debugging the `math_tutor` project. It is intended as a practical reference, not a verbatim transcript. Sensitive values such as login credentials and API keys are intentionally omitted.

## Original Goal

Build a Python project named `math tutor` that:

1. Logs into the school's Canvas course site
2. Fetches PDF documents from the course
3. Uploads each PDF to OpenAI with a fixed prompt stored in code
4. Saves the output for each document to disk
5. Accepts login credentials on the command line

## Initial Project Setup

We added a new standalone Python package alongside the existing Java project:

- `pyproject.toml`
- `math_tutor/__init__.py`
- `math_tutor/cli.py`
- `math_tutor/README.md`

Initial dependencies:

- `playwright`
- `httpx`
- `openai`

The first version of the CLI included:

- command-line parsing
- output directory creation
- a fixed `PROMPT` constant
- Canvas login automation
- Canvas files API enumeration
- PDF download
- OpenAI upload and response generation
- saving model output and metadata

## Early Runtime Issues

### 1. Missing `OPENAI_API_KEY`

The first live run failed before login because the environment variable `OPENAI_API_KEY` was not set.

What we learned:

- this was a configuration issue, not a code bug
- we needed a real key to continue testing end to end

### 2. Canvas login selectors failed

The first login automation targeted `https://mitty.instructure.com/login/canvas` and expected the older Canvas-native login form immediately.

Observed failure:

- the script could not find the username field

Root cause:

- the login page is React-rendered
- the script queried the page too early
- the form selectors were too narrow

Fixes made:

- switched to `networkidle` on login-page load
- broadened selectors to include newer field variants
- added shared selector waiting instead of serial full-timeout waiting for each selector

### 3. Custom checkbox interaction bug

The Canvas/OneLogin login UIs include custom-styled checkboxes.

Observed failure:

- Playwright `check()` could hang because the visual facade intercepted pointer events

Fix made:

- replaced checkbox interaction with `set_checked(True, force=True)`

### 4. Poor login failure handling

Observed behavior:

- on bad credentials the script would wait too long or fail indirectly later

Fixes made:

- added explicit login-error extraction
- surfaced messages like "Please verify your login or password and try again."
- improved timeout behavior so auth failures are reported directly

## Browser vs Script Login Mismatch

You noticed that manual browser debugging went to OneLogin, while the script went to Canvas-local login.

We investigated the redirect chain for:

- `https://mitty.instructure.com/courses/4187`
- `https://mitty.instructure.com/login/canvas`

Finding:

- the course URL redirects through `/login`, `/login/saml`, and the school's SSO/OneLogin flow
- the script was hardcoding `/login/canvas`, which forced the wrong login entry point

Fixes made:

- changed the default login entry to start from the course URL
- kept `--login-url` as an override only
- added OneLogin-specific handling

## OneLogin Support

We inspected the live OneLogin flow and found:

- first page: username only, then `Continue`
- second page: password, optional checkbox, then `Continue`

Fixes made:

- added a dedicated `perform_onelogin()` flow
- preserved `perform_canvas_login()` for fallback cases where Canvas-native login is still used

## Headful Debugging Support

You asked for the browser to stay open while debugging.

Fix made:

- added a prompt before exit for `--headful` runs
- this allows manual inspection before the browser closes

## Canvas Files API Problem

After login was improved, the script reached Canvas but failed here:

- `GET /api/v1/courses/4187/files`
- response: `403 Forbidden`

Conclusion:

- the account/session could not use the files API for this course
- file discovery needed to use the authenticated web UI instead of the API

## Switching Discovery to the Web UI

### Attempt 1: Course Files page

We replaced API-based discovery with HTML-based discovery from the course Files area.

Observed result:

- no PDFs were found

Investigation showed:

- the Files page is disabled for this course
- navigating to `/courses/4187/files` lands back on the course page with a message saying the page is disabled

### Attempt 2: Modules page

We inspected the authenticated course page and found that PDFs appear as attachment items in Modules.

Examples seen:

- `alg 2trig_h chp 5.1 note.docx.pdf`
- other chapter note PDFs

Important detail:

- module attachment links use URLs like `/courses/4187/modules/items/...`
- these resolve to Canvas file pages, not directly to PDF bytes

Fixes made:

- added a fallback to scrape module attachment links from `/courses/4187/modules`
- filtered links by visible text ending in `.pdf`
- resolved module item URLs to their corresponding Canvas file pages using the authenticated `httpx` client
- converted those file-page URLs into direct downloadable URLs by adding `download=1`

This successfully found and downloaded a real PDF.

## OpenAI Request Payload Fixes

Once the download path worked, the next failures were in the OpenAI request shape.

### Failure 1: unsupported `mime_type`

Observed error:

- `Unknown parameter: 'input[0].content[1].mime_type'`

Fix made:

- removed `mime_type` from the `input_file` content item

### Failure 2: mutually exclusive `file_id` and `filename`

Observed error:

- `Mutually exclusive parameters: ... only providing one of: 'file_id' or 'filename'`

Fix made:

- removed `filename`
- kept only `file_id`

At that point the Responses API request structure was valid.

## End-to-End Verification Status

We verified live with `--limit 1`:

1. login started from the correct course URL
2. login followed the OneLogin flow
3. module-based PDF discovery found one PDF
4. the PDF downloaded successfully
5. the OpenAI call was attempted

The final live blocker was external:

- OpenAI returned `429 insufficient_quota`

Conclusion:

- the current code path gets all the way through login, discovery, and download
- the remaining issue is account/billing/quota on the OpenAI side, not the Canvas automation

## Downloaded Test File

During live verification with `--limit 1`, the first downloaded PDF was saved to:

- `math_tutor/output/downloads/4401267_alg-2trig-h-chp-5-1-note-docx.pdf`

## Key Design Decisions

### Why start from the course URL?

Because that matches the real user/browser flow and lets the institution-controlled redirect chain decide whether to use SAML, OneLogin, or Canvas-native login.

### Why keep Playwright and `httpx` together?

- Playwright handles the real browser/SSO flow
- `httpx` reuses the authenticated cookies for predictable file downloads

### Why use Modules scraping instead of the Files API?

Because:

- the Files page is disabled
- the Files API returned `403`
- the module attachments are visible and accessible in the authenticated UI

## Current State of the Project

As of this log, `math_tutor/cli.py` supports:

- course-based login entry
- OneLogin flow handling
- optional headful debugging with pause-before-exit
- module-based PDF discovery
- authenticated PDF download
- OpenAI file upload and response generation
- writing outputs and metadata locally

## Remaining External Requirements

To run the project successfully end to end, you still need:

- valid school login credentials
- a working OpenAI API key with available quota
- Playwright browser binaries installed

## Recommended Next Steps

1. Rotate any API key that was pasted into chat or logs.
2. Use an OpenAI project/key with available quota.
3. Re-run:

```bash
math-tutor --username YOUR_USERNAME --password YOUR_PASSWORD --limit 1
```

4. If needed, run with `--headful` to inspect the auth flow manually.

