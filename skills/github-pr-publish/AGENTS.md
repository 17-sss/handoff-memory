# AGENTS.md

This package defines the `github-pr-publish` skill.

## Package Intent

- Standardize safe GitHub pull request publishing through `gh`, local `git`, and GitHub REST APIs
- Support public and private repositories without assuming visibility from URLs
- Keep PR creation, pushing, and browser opening behind explicit user intent
- Prevent implicit `gh pr create` prompting, pushing, or fork creation

## Editing Guidance

- Keep `SKILL.md`, `README.md`, and `metadata.json` aligned when the workflow contract changes
- Do not store tokens, PATs, raw credentials, raw auth logs, or authorization headers in this package
- Keep scripts thin and auditable; workflow judgment belongs in `SKILL.md`
- Preserve preview-by-default behavior and explicit-only mutation flags
- Preserve explicit `--head` command construction for every create path
- Keep Codex-specific metadata in `agents/openai.yaml`, not in the core workflow
- Update fake `gh`/`git` tests whenever script safety rules change
