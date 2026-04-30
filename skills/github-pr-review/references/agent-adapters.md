# Agent Adapters

This package is intentionally agent-neutral. The core workflow is `SKILL.md` plus shell scripts that use `gh`, GitHub APIs, local `git`, and repository test commands.

## Codex

Install under a discoverable skills directory such as `$CODEX_HOME/skills/github-pr-review`, `~/.codex/skills/github-pr-review`, or a project-local skill path. `agents/openai.yaml` is only UI metadata; it does not define the workflow.

`gh` commands that contact GitHub may need sandbox/network escalation in Codex environments. If a required `gh` command fails with a likely sandbox or network error, rerun it through the environment's approval path, for example with `sandbox_permissions: "require_escalated"` on Codex shell tool calls, rather than switching to browser automation.

Useful scoped approval prefixes:

- `["gh", "auth", "status"]`
- `["gh", "pr", "view"]`
- `["gh", "pr", "diff"]`
- `["gh", "api"]`

Keep tokens out of prompts, logs, and files. Prefer the authenticated `gh` session.

## Claude Code

Place the folder where Claude Code loads skills or reference `SKILL.md` from project instructions. Keep GitHub authentication in `gh`, not in `CLAUDE.md` or project files.

## Cursor

Reference `SKILL.md` from Cursor rules or commands. Invoke the bundled scripts from the workspace terminal when collecting context or posting a confirmed review.

## Generic Agents

Load `SKILL.md` as procedural instructions. Use the scripts as optional helpers. If the agent has proprietary GitHub connectors, treat them as conveniences only; the baseline path remains `gh` and GitHub REST or GraphQL APIs.
