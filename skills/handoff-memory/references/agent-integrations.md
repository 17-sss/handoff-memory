# Agent Integrations

Keep the shared HANDOFF data inside the repository even when the skill itself is installed in an agent-specific location.

## Shared Data Rule

- Repo default shared file: `docs/HANDOFF.md`
- Workspace default shared file: `_memory/HANDOFF.md`
- Optional snapshots: `docs/handoffs/*.md` or `_memory/handoffs/*.md`
- Reuse an existing shared file if the project already uses `docs/HANDOFF.md`, `memories/HANDOFF.md`, or `HANDOFF.md`
- Use `_memory/WORKSPACE.md`, `_memory/DECISIONS.md`, and `_memory/PATTERNS.md` for cross-repo workspace context
- Do not make `.codex`, `.claude`, `.windsurf`, or `.agents` the default shared mutable store
- Most sessions should still update only the canonical handoff document

## Codex

- Global install: `$CODEX_HOME/skills/handoff-memory` or `~/.codex/skills/handoff-memory`
- Project-local install: `<repo>/.codex/skills/handoff-memory`
- Agent-specific files such as `<repo>/.codex/README.md` or `<repo>/AGENTS.md` can point the agent at `docs/HANDOFF.md`

## Claude Code

- Keep agent instructions in `CLAUDE.md` or `.claude/`
- Reference the shared HANDOFF document from those files instead of duplicating mutable state there

## Windsurf

- Keep rules in `.windsurf/rules/`
- Reference the shared HANDOFF document from those rules instead of making `.windsurf` the primary mutable store

## Generic Fallback

- If another agent supports repo-local skills or rules, install there
- If no standard location exists, `.agents/skills/handoff-memory` is an acceptable neutral fallback for installation
- The installation location does not change the shared HANDOFF file location
