Build the math tutor site using the correct venv command from the project root.
`staging` is now the default experience — no flag needed. Use `--experience archived` only when you intentionally want the older pre-refresh styling.

Run the following from `/home/nshah/projects/math-tutor`:

```
.venv/bin/math-tutor-build-site --site-dir math_tutor/output/deploy/math_tutor/site $ARGUMENTS
```

Where `$ARGUMENTS` is passed through as-is (e.g. `--experience archived` to use older styling).

After the build completes, report what was built and any warnings. If the build fails, diagnose the error and fix it.
