# Security Notes

## Secrets

Do not commit real secrets to this repository.

This includes:

- OpenAI API keys
- school login usernames and passwords
- session cookies
- copied command history that contains secrets
- browser export files containing authenticated state

Use local environment variables or a local `.env` file that is not committed.

## Recommended Local Setup

1. Copy `.env.example` to `.env`
2. Fill in real values only on your local machine
3. Load those values into your shell before running the CLI

Example:

```bash
cp .env.example .env
set -a
source .env
set +a
```

Then run:

```bash
math-tutor --username "$MATH_TUTOR_USERNAME" --password "$MATH_TUTOR_PASSWORD" --limit 1
```

## If A Secret Was Exposed

If a secret was pasted into chat, committed locally, or pushed to a remote:

1. Rotate or revoke it immediately
2. Remove it from tracked files
3. If it was committed, rewrite history if needed
4. Recheck the repo with a targeted search before pushing again

## Generated Files That Contain Secrets

`challenge_config.py` writes `challenges/config.php` at build time, injecting the database
credentials from `DBNAME`, `DBUSER`, `DBPASSWORD`, and `MySQL_HOST`. **That file is a build
artifact containing live secrets and must never be tracked.**

This has gone wrong once. See the "OPEN SECURITY ACTION" section of
`math_tutor/HANDOFF.md` for the incident and the outstanding remediation.

The lesson generalizes: the risk here is not a developer pasting a password into source, it is
a *generated* file landing in a path that happens not to be ignored. `.gitignore` covered
`math_tutor/output/` while the build wrote a repo-root `output/` tree. Both are now ignored,
along with bare `output/` at any level.

Before adding a new generated-output location, confirm it is ignored:

```bash
git check-ignore -v <path>
```

If that prints nothing, the path is committable and must be added to `.gitignore` first.

## Auditing History For Exposure

To check whether a secret ever reached a commit, searching the working tree is not enough —
deleting a file from HEAD leaves the blob reachable by commit SHA.

```bash
# every path ever added, filtered to sensitive-looking names
git log --all --pretty=format: --name-only --diff-filter=A | sort -u \
  | grep -iE 'sftp|\.env|secret|credential|\.pem$|\.key$|id_rsa|config\.php'
```

When inspecting a suspected file, check whether values are populated rather than printing
them. Never echo a secret into terminal output, logs, or a commit message.

## Current Repo Practice

This project is designed so that:

- credentials are passed at runtime
- the OpenAI key is read from `OPENAI_API_KEY`
- generated output is stored under `math_tutor/output/` and is git-ignored
- local `.env` files are ignored by git; only `.env.example` is tracked
- `.vscode/sftp.json` is ignored at both the repository root and under `math_tutor/`; only
  `sftp.example.json` is tracked

That keeps the working code and the secret material separate.
