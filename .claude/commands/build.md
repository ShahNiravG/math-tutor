Build the math tutor site using the correct venv command from the project root.
The styled `staging` experience is the main default. Use `--experience archived` only when you intentionally want the older pre-refresh styling.

Run the following from `/home/nshah/projects/math-tutor`:

```
.venv/bin/math-tutor-build-site --site-dir math_tutor/output/deploy/math_tutor/site --experience staging $ARGUMENTS
```

Where `$ARGUMENTS` is passed through as-is (e.g. `--force-challenges` to force regenerate exams).

After the build completes, report what was built and any warnings. If the build fails, diagnose the error and fix it.
