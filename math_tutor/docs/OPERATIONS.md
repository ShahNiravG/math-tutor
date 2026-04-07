# Operations Guide

## Purpose

This guide documents the supported operator workflows for `math_tutor` using
the current canonical state and artifact conventions.

## Canonical State Files

- `math_tutor/output/fetch_state.json`
- `math_tutor/output/generated_output_state.json`

Generated metadata files live under:

- `math_tutor/output/metadata/`

Generated response artifacts live under:

- `math_tutor/output/responses/`

## Environment

The CLI loads `../.env` automatically when present.

Typical variables:

- `MATH_TUTOR_USERNAME`
- `MATH_TUTOR_PASSWORD`
- `OPENAI_API_KEY`
- `GEMINI_API_KEY`

## Standard Commands

### Fetch and generate all class-note outputs

```bash
.venv/bin/math-tutor --username EMAIL --password PASS
```

### Fetch only, without generation

```bash
.venv/bin/math-tutor --username EMAIL --password PASS --fetch-only
```

### Skip Canvas login and process already-fetched notes

```bash
.venv/bin/math-tutor --skip-fetch
```

### Limit processing to a chapter

```bash
.venv/bin/math-tutor --skip-fetch --chapter 5.1
```

### Run only selected prompts

```bash
.venv/bin/math-tutor --skip-fetch --prompt study-guide --prompt mental-math-gpt5
```

### Force regeneration for already-saved prompt outputs

```bash
.venv/bin/math-tutor --skip-fetch --force-generation
```

### Fetch assignments only

```bash
.venv/bin/math-tutor --username EMAIL --password PASS --fetch-assignments
```

### Build the tutoring site

```bash
.venv/bin/math-tutor-build-site
```

This now defaults to the styled `staging` experience.
For the older pre-refresh look, use `--experience archived`.

### Build the deploy tree used by SFTP

```bash
.venv/bin/math-tutor-build-site \
  --site-dir math_tutor/output/deploy/math_tutor/site \
  --base-path /site/
```

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
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m math_tutor.site_builder \
  --site-dir math_tutor/output/deploy/math_tutor/site \
  --force-challenges
```

## Deploy Notes

The active deploy tree is:

- `math_tutor/output/deploy/math_tutor/site/`

The current SFTP setup syncs from:

- `math_tutor/output/deploy/math_tutor/`

to the remote hosting tree configured in:

- `.vscode/sftp.json`

## Safe Expectations

- Validation must pass before structural refactors are considered complete.
- Internal refactors should not require new OpenAI or Gemini calls.
- Site rebuilds should be run when page-rendering or generated-site behavior changes.
- Pure CLI/state contract changes do not require a deploy rebuild.
