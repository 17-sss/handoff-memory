# GitHub CLI PR Create Notes

Use this reference when maintaining the `github-pr-publish` command builder.

Official `gh pr create` behavior that shapes this skill:

- `gh pr create` creates a pull request and prints the URL on success.
- If the current branch is not fully pushed, the CLI can prompt where to push and can offer fork-based behavior.
- Supplying an explicit `--head` selects the PR head and avoids relying on implicit push/fork prompts.
- Supplying `--title` and `--body` or `--body-file` avoids title/body prompts.
- `--fill`, `--fill-first`, and `--fill-verbose` can derive content from commits; explicit title/body values take precedence.
- The CLI preview-style flag is not treated as safe by this skill because official documentation says it may still push git changes.

Skill policy:

- Always build an explicit `--head` argument before create.
- Never rely on interactive prompts or editor flows.
- Preview mode is implemented by this package without calling the GitHub creation command.
