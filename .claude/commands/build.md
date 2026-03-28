Build the math tutor site using the correct venv command from the project root.

Run the following from `/home/nshah/projects/math-tutor`:

```
.venv/bin/math-tutor-build-site --site-dir math_tutor/output/deploy/math_tutor/site $ARGUMENTS
```

Where `$ARGUMENTS` is passed through as-is (e.g. `--force-challenges` to force regenerate exams).

After the build completes, report what was built and any warnings. If the build fails, diagnose the error and fix it.
