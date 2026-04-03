# Validation Workflow

## Goal

Run local checks that improve confidence in refactors without:

- calling model APIs
- logging into Canvas
- rewriting the existing deploy output

## Recommended command

From the repository root:

```bash
.venv/bin/python math_tutor/scripts/validate_project.py
```

This runs:

1. unit tests under `math_tutor/tests`
2. Python bytecode compilation for the core modules

## When to run it

- before starting a refactor
- before committing architectural changes
- before pushing changes that affect challenge generation or site building

## What it intentionally does not do

- fetch PDFs
- regenerate model output
- rebuild the deploy site
- modify `output/responses/*.md`

## Additional safe verification

If you want to smoke-test the site builder without touching the live deploy tree,
build to a temporary directory:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m math_tutor.site_builder \
  --site-dir /tmp/math-tutor-site-check
```
