Commit all staged and unstaged changes, then push to GitHub. Run from `/home/nshah/projects/math-tutor`.

Steps:
1. Run `git status` and `git diff --stat` to summarize what changed
2. Stage all modified tracked files and any new `.claude/commands/` files (do not stage `.env`, output/, or other sensitive/generated files)
3. Write a concise commit message summarizing the changes — lead with the "why", not just the "what"
4. Commit and push to `origin/main`
5. Report what was committed and confirm the push succeeded

If there is nothing to commit, say so clearly.

If `$ARGUMENTS` is provided, use it as the commit message instead of generating one.
