# AGENTS.md

This package defines the `github-pr-review` skill.

## Package Intent

- Standardize GitHub PR review through `gh`, GitHub APIs, local `git`, and tests
- Support public and private repositories without making private repos the only target
- Post comments only through the user's authenticated GitHub account
- Keep browser automation as a last fallback, not the normal workflow

## Editing Guidance

- Keep `SKILL.md`, `README.md`, and `metadata.json` aligned when the workflow contract changes
- Do not store tokens, PATs, raw credentials, or auth logs in this package
- Keep scripts thin and auditable; the review judgment belongs in `SKILL.md`
- Preserve the default policy of drafting before posting
- Preserve explicit-only behavior for approve and request-changes review events
- Keep Codex-specific metadata in `agents/openai.yaml`, not in the core workflow
