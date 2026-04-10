Fetch class notes from Canvas and run AI generation pipeline. Run from `/home/nshah/projects/math-tutor`.

Usage examples:
- Full run (fetch + all AI prompts): `/fetch --username EMAIL --password PASS`
- Dry-run (see what would be processed, no API calls): `/fetch --username EMAIL --password PASS --dry-run`
- Fetch only (no AI generation): `/fetch --username EMAIL --password PASS --fetch-only`
- Specific prompts only: `/fetch --username EMAIL --password PASS --prompt mental-math-gpt5-mcq --prompt olympiad-problems-gpt5-mcq`
- Fetch assignments too: `/fetch --username EMAIL --password PASS --fetch-assignments`

Run:
```
PYTHONUNBUFFERED=1 .venv/bin/math-tutor $ARGUMENTS 2>&1 | tee /tmp/math-tutor-fetch.log
```

Report what was fetched and generated, or any errors encountered.
