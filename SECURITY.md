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

## Current Repo Practice

This project is designed so that:

- credentials are passed at runtime
- the OpenAI key is read from `OPENAI_API_KEY`
- generated output is stored under `math_tutor/output/`
- local `.env` files are ignored by git

That keeps the working code and the secret material separate.
