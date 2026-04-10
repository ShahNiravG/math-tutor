Backfill MCQ variants for existing class notes that don't have them yet. Skips notes that already have MCQ outputs. Run from `/home/nshah/projects/math-tutor`.

Usage examples:
- Full backfill: `/generate-mcq`
- Limit to N notes (for testing): `/generate-mcq --limit 3`
- Dry-run (see what would be processed): `/generate-mcq --dry-run`

Run:
```
PYTHONUNBUFFERED=1 .venv/bin/math-tutor-generate-mcq $ARGUMENTS 2>&1 | tee /tmp/math-tutor-mcq.log
```

Report how many notes were processed and any errors.
