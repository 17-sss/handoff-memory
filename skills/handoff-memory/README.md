# handoff-memory

Agent-neutral workflow for maintaining shared handoff and memory documents for either a single repository or a multi-repository workspace.

## Use When

- Ending a work session and leaving a reliable checkpoint
- Resuming a project from prior notes
- Standardizing a Git-trackable handoff file across contributors or machines
- Working from a parent folder that coordinates multiple repositories
- Keeping mutable state out of `.codex`, `.claude`, `.windsurf`, or `.agents`

## What It Does

- Resolves shared memory files in either repo scope or workspace scope
- Reuses an existing repo handoff at `docs/HANDOFF.md`, `memories/HANDOFF.md`, or `HANDOFF.md`
- Defaults to `docs/HANDOFF.md` for a repo and `_memory/HANDOFF.md` for a workspace
- Adds lightweight operational tooling for `create`, `validate`, and `check_staleness`
- Supports optional timestamped snapshots in `docs/handoffs/` or `_memory/handoffs/`
- Keeps agent-specific files as references to the shared handoff, not as the primary mutable state

## Workflow Summary

1. Create or refresh the canonical memory path with `scripts/create_handoff.py`
2. Read the canonical handoff before editing it
3. Refresh it using the matching structure in `references/`
4. Validate it with `scripts/validate_handoff.py`
5. Check staleness with `scripts/check_staleness.py` when resuming older notes

## Scope Model

### Repo Scope

Use repo scope when the task belongs to one repository.

- Preferred file: `docs/HANDOFF.md`
- Fallbacks: `memories/HANDOFF.md`, `HANDOFF.md`

### Workspace Scope

Use workspace scope when the prompt starts from a parent folder that coordinates multiple repositories.

- `_memory/HANDOFF.md` - current cross-repo status
- `_memory/WORKSPACE.md` - durable workspace overview
- `_memory/DECISIONS.md` - shared technical decisions
- `_memory/PATTERNS.md` - repeated conventions across repos
- `_memory/handoffs/*.md` - optional timestamped session snapshots

Most sessions should only update `_memory/HANDOFF.md`. Touch the companion files only when durable shared context changed.

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

The primary memory files should stay inside the repository or workspace root they describe so they can be reviewed and synchronized with Git when appropriate. Installation location and data location are separate concerns.

## Recommended Commands

Initialize or refresh the canonical file:

```bash
python3 scripts/create_handoff.py --project-root <path> --scope auto --document handoff
```

Write a timestamped snapshot before refreshing:

```bash
python3 scripts/create_handoff.py --project-root <path> --scope auto --document handoff --snapshot
```

Validate structure before ending the session:

```bash
python3 scripts/validate_handoff.py --project-root <path> --scope auto --document handoff
```

Check whether the current handoff is stale when resuming:

```bash
python3 scripts/check_staleness.py --project-root <path> --scope auto --document handoff
```

## Package Layout

- `SKILL.md` - Main skill definition
- `AGENTS.md` - Maintainer guidance for this skill package
- `metadata.json` - Catalog metadata
- `scripts/create_handoff.py` - Initializes or refreshes the canonical file
- `scripts/validate_handoff.py` - Validates structure and obvious placeholders
- `scripts/check_staleness.py` - Checks whether the notes lag behind repo activity
- `scripts/resolve_handoff_path.py` - Path resolver and initializer
- `references/handoff-template.md` - HANDOFF template
- `references/workspace-memory-guide.md` - Workspace memory structure guidance
- `references/agent-integrations.md` - Agent-specific install notes
