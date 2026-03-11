# handoff-memory

Agent-neutral workflow for maintaining a shared repo-local HANDOFF document.

## Use When

- Ending a work session and leaving a reliable checkpoint
- Resuming a project from prior notes
- Standardizing a Git-trackable handoff file across contributors or machines
- Keeping mutable state out of `.codex`, `.claude`, `.windsurf`, or `.agents`

## What It Does

- Resolves a shared handoff file inside the repository
- Reuses an existing handoff at `docs/HANDOFF.md`, `memories/HANDOFF.md`, or `HANDOFF.md`
- Defaults to `docs/HANDOFF.md` when no handoff file exists
- Keeps agent-specific files as references to the shared handoff, not as the primary mutable state

## Workflow Summary

1. Resolve the canonical handoff path with `scripts/resolve_handoff_path.py`
2. Read the existing handoff if present
3. Refresh it using `references/handoff-template.md`
4. Commit the shared handoff with the repository when appropriate

## Install Scope

The skill itself can be installed globally or per-project. The shared HANDOFF data should still live inside the target repository.

### Codex

- Global install: `$CODEX_HOME/skills/handoff-memory` or `~/.codex/skills/handoff-memory`
- Project-local install: `<repo>/.codex/skills/handoff-memory`

### Other Agents

- Claude Code: keep agent-specific instructions in `CLAUDE.md` or `.claude/`, but point them at the shared repo-local HANDOFF
- Windsurf: keep rules in `.windsurf/rules/`, but point them at the shared repo-local HANDOFF
- Generic fallback: if no standard install path exists, `.agents/skills/handoff-memory` is an acceptable neutral install location

## Shared Data Rule

The primary handoff file should stay inside the repository so it can be reviewed and synchronized with Git when appropriate. Installation location and data location are separate concerns.

## Package Layout

- `SKILL.md` - Main skill definition
- `AGENTS.md` - Maintainer guidance for this skill package
- `metadata.json` - Catalog metadata
- `scripts/resolve_handoff_path.py` - Path resolver and initializer
- `references/handoff-template.md` - HANDOFF template
- `references/agent-integrations.md` - Agent-specific install notes
