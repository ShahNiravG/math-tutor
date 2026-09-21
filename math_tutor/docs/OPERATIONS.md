# Operations Guide

## Purpose

This guide documents the supported operator workflows for `math_tutor` using
the current canonical state and artifact conventions.

## Canonical State Files

Algebra II / Trigonometry retains its existing state paths:

- `math_tutor/output/fetch_state.json`
- `math_tutor/output/generated_output_state.json`

AP Calculus AB uses isolated state and artifacts:

- `math_tutor/output/courses/ap-calculus-ab/fetch_state.json`
- `math_tutor/output/courses/ap-calculus-ab/downloads/`
- `math_tutor/output/courses/ap-calculus-ab/generated_output_state.json`
- `math_tutor/output/courses/ap-calculus-ab/responses/`
- `math_tutor/output/courses/ap-calculus-ab/metadata/`

Generated metadata files live under:

- `math_tutor/output/metadata/`

Generated response artifacts live under:

- `math_tutor/output/responses/`

## Environment

The CLI loads `.env` from the repository root automatically. `export KEY=value` entries are supported.

Typical variables:

- `MATH_TUTOR_USERNAME`
- `MATH_TUTOR_PASSWORD`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`

## Standard Commands

### Fetch and generate all class-note outputs

```bash
.venv/bin/math-tutor --course algebra-2-trig
```

### Fetch only, without generation

```bash
.venv/bin/math-tutor --course algebra-2-trig --fetch-only
```

### Skip Canvas login and process already-fetched notes

```bash
.venv/bin/math-tutor --course algebra-2-trig --skip-fetch
```

### Limit processing to a chapter

```bash
.venv/bin/math-tutor --course algebra-2-trig --skip-fetch --chapter 5.1
```

### Run only selected prompts

```bash
.venv/bin/math-tutor --course algebra-2-trig --skip-fetch --prompt study-guide --prompt mental-math-gpt5
```

### Force regeneration for already-saved prompt outputs

```bash
.venv/bin/math-tutor --course algebra-2-trig --skip-fetch --force-generation
```

### Fetch assignments only

```bash
.venv/bin/math-tutor --course algebra-2-trig --fetch-assignments
```

### Fetch AP Calculus AB Chapter 2 only

```bash
.venv/bin/math-tutor --course ap-calculus-ab --chapter 2 --fetch-only
```

Other Calculus chapters and assignment mode remain disabled.

### Preview the AP Calculus AB Chapter 2 study guide

```bash
.venv/bin/math-tutor --course ap-calculus-ab --skip-fetch --chapter 2 --prompt study-guide --dry-run
```

Dry-run mode does not resolve model credentials, initialize provider clients, launch Chromium,
or call Canvas. Remove `--dry-run` only after explicit approval for the model cost. The normal
non-force command is idempotent and skips the saved guide. Do not pass `--force`,
`--force-generation`, or `--force-prompt study-guide` without separate approval.

The Calculus response is validated before persistence. Invalid title, mastery headings,
section order, coverage fields, supplemental-aid disclosures, not-covered topic leakage,
incomplete 1–10 practice/answer sets, empty content, or provider-error output leaves prior
artifacts and generated state unchanged.

### Build the tutoring site

```bash
.venv/bin/math-tutor-build-site
```

This now defaults to the styled `staging` experience.
For the older pre-refresh look, use `--experience archived`.

This general command writes a disposable local preview under `math_tutor/output/site/`. That
preview directory is currently absent after an explicitly approved cleanup and is recreated on
demand. It is not read by the guarded production build or deployment commands.

### Build the deploy tree used by SFTP

```bash
.venv/bin/math-tutor-build-production
```

This command writes the canonical site directly to `math_tutor/output/deploy/math_tutor/`
with an empty base path and validates the production tree. It fails closed if an obsolete
nested `site/` directory or `/site/` HTML link remains, or if the tree contains the known
orphan-MathJax list delimiter defect.

### Deploy and verify production

```bash
.venv/bin/math-tutor-deploy-production --confirm-production
```

The confirmation flag is mandatory. The command rebuilds and validates before synchronizing the
canonical `math_tutor/output/deploy/math_tutor/` tree once to `public_html/math_tutor/`. Live
verification uses domain-root URLs only, including the Calculus Chapter 2 AI challenge, Calculus
guide, and Algebra II site. A failed step returns a nonzero exit and the idempotent command can
be retried. The obsolete remote `site/` directory is a one-time migration cleanup, not part of
normal deployment.

### Rebuild response HTML from saved Markdown only

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m math_tutor.backfill_response_html
```

### Validate before and after refactors

```bash
.venv/bin/python math_tutor/scripts/validate_project.py
```

## Recovery From Saved Markdown Only

If you preserved:

- `.env`
- `math_tutor/output/generated_output_state.json`
- `math_tutor/output/responses/*.md`

you can recover the generated HTML site without new OpenAI or Gemini calls:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m math_tutor.backfill_response_html
.venv/bin/math-tutor-build-production
```

## Deploy Notes

The active deploy tree is:

- `math_tutor/output/deploy/math_tutor/`

The current SFTP setup syncs from:

- `math_tutor/output/deploy/math_tutor/`

to the remote hosting tree configured in:

- `.vscode/sftp.json`

The build publishes the saved Calculus Chapter 2 source note under:

- `courses/ap-calculus-ab/doc-4839635.html`
- `courses/ap-calculus-ab/downloads/4839635_chapter-2-notetakers.pdf`

The Calculus site is built from `output/courses/ap-calculus-ab/`; no model call or Canvas login is needed for a rebuild. Site builds must reuse the saved study guide and must never regenerate it.

The Chapter 2 page also publishes non-secret Cengage navigation from
`math_tutor/site_textbook.py`. Students use `Open Chapter 2 through Canvas`, then choose
`Read It` inside WebAssign. Do not add a direct MindTap reader link or replace the Canvas URL
with a captured `gateway.cengage.com` LTI/OIDC authorization URL; both depend on protected
session state and the authorization request may contain sensitive launch data.

## Safe Expectations

- Validation must pass before structural refactors are considered complete.
- Internal refactors should not require new OpenAI or Gemini calls.
- Site rebuilds should be run when page-rendering or generated-site behavior changes.
- Pure CLI/state contract changes do not require a deploy rebuild.
