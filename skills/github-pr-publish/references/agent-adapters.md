# Agent Adapters

This package is intentionally agent-neutral. The baseline workflow is `SKILL.md` plus shell scripts that use `gh`, local `git`, and GitHub REST APIs.

## Codex

Install under a discoverable skills directory such as `$CODEX_HOME/skills/github-pr-publish`, `~/.codex/skills/github-pr-publish`, or a project-local skill path. `agents/openai.yaml` is UI metadata only.

`gh` commands that contact GitHub may need network access in sandboxed environments. Prefer the authenticated `gh` session and never ask the user to paste token values into prompts or files.

## Claude Code / Cursor / Generic Agents

Load `SKILL.md` as procedural instructions and use bundled scripts as optional helpers. Proprietary GitHub connectors may be conveniences, but the portable baseline remains `gh`, local `git`, and GitHub REST APIs.
