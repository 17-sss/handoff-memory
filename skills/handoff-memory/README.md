# handoff-memory

Agent-neutral workflow for maintaining shared handoff and memory documents for a single repository, a multi-repository workspace, or a workstream inside that workspace.

## Requirements

- `python3` in `PATH` for the bundled scripts
- `git` in `PATH` for branch metadata and staleness checks
- A writable repository or workspace folder where the shared documents live

Path resolution and validation still work outside Git, but freshness checks are most useful when the target lives in a Git repo or multi-repo workspace.

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
- Supports workstream-specific handoffs and memory under `_memory/workstreams/<name>/`
- Adds lightweight operational tooling for `create`, `validate`, and `check_staleness`
- Supports optional timestamped snapshots in `docs/handoffs/` or `_memory/handoffs/`
- Keeps agent-specific files as references to the shared handoff, not as the primary mutable state
- Narrows workspace stale checks to the active workstream or repo set named in `_memory/HANDOFF.md` before falling back to every child repository
- Treats `Next Actions` and `Resume Prompt` as authoritative resume-time execution guidance unless the user or repo state clearly invalidates them

## Workflow Summary

1. Create or refresh the canonical memory path with `scripts/create_handoff.py`
2. Read the canonical handoff before editing it
3. Refresh it using the matching structure in `references/`
4. Validate it with `scripts/validate_handoff.py`
5. Check staleness with `scripts/check_staleness.py` when resuming older notes

In mixed workspaces, `check_staleness.py` does not blindly scan every child repo by default. It first tries to infer the active workstream or active repo set from the workspace handoff. Use `--workspace-wide` only when you truly want the whole parent folder.

On resume requests, the intended flow is: verify, then execute the first unfinished next action. Fresh exploration is fine only when the handoff is stale, ambiguous, contradicted by the repo, or the user explicitly asks to rethink the plan.

## Scope Model

### Repo Scope

Use repo scope when the task belongs to one repository.

- Preferred file: `docs/HANDOFF.md`
- Fallbacks: `memories/HANDOFF.md`, `HANDOFF.md`

### Workspace Scope

Use workspace scope when the prompt starts from a parent folder that coordinates multiple repositories.

- `_memory/HANDOFF.md` - workspace-wide summary and active workstream index
- `_memory/WORKSPACE.md` - durable workspace overview
- `_memory/DECISIONS.md` - shared technical decisions
- `_memory/PATTERNS.md` - repeated conventions across repos
- `_memory/handoffs/*.md` - optional timestamped session snapshots

Use these files when the whole workspace shares one active cross-repo context. Touch the companion files only when durable shared context changed.

### Workstream Scope

Use workstream scope when the same workspace contains multiple independent repo combinations or initiatives.

- `_memory/workstreams/<name>/HANDOFF.md` - canonical handoff for that repo combination
- `_memory/workstreams/<name>/WORKSTREAM.md` - durable overview for that workstream
- `_memory/workstreams/<name>/DECISIONS.md` - workstream-specific decisions
- `_memory/workstreams/<name>/PATTERNS.md` - workstream-specific conventions
- `_memory/workstreams/<name>/handoffs/*.md` - optional timestamped snapshots

Use workstream names for actual initiatives or streams of work, not just raw repo lists. For example, prefer `checkout-flow` over `frontend-backend`.

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

## Best Practices

If an agent is using this skill continuously, follow [agent-usage-best-practices.md](references/agent-usage-best-practices.md). The short version:

- Start by resolving the canonical handoff and checking staleness
- On resume, treat `Next Actions` and `Resume Prompt` as the default execution plan
- Update only one canonical handoff per active scope
- Use a workstream when one workspace hosts multiple independent repo combinations
- Touch workspace or workstream companion files only when durable shared context changed
- Use snapshots only for meaningful transitions, with an explicit kind and reason
- Validate strictly before ending the session

## Recommended Commands

Initialize or refresh the canonical file:

```bash
python3 scripts/create_handoff.py --project-root <path> --scope auto --document handoff
```

Initialize a workstream-specific handoff:

```bash
python3 scripts/create_handoff.py --project-root <path> --scope workspace --workstream <name> --document handoff
```

Initialize a durable workstream overview and record the involved repos:

```bash
python3 scripts/create_handoff.py --project-root <path> --scope workspace --workstream <name> --document workstream --repository <repo-a> --repository <repo-b>
```

Write a timestamped snapshot before refreshing:

```bash
python3 scripts/create_handoff.py --project-root <path> --scope auto --document handoff --snapshot --snapshot-kind handoff --snapshot-reason "Context transfer before ending the session"
```

Validate structure before ending the session:

```bash
python3 scripts/validate_handoff.py --project-root <path> --scope auto --document handoff
```

Check whether the current handoff is stale when resuming:

```bash
python3 scripts/check_staleness.py --project-root <path> --scope auto --document handoff
```

Check staleness for one workstream only:

```bash
python3 scripts/check_staleness.py --project-root <path> --scope workspace --workstream <name> --document handoff
```

Force a true workspace-wide scan across every child repo:

```bash
python3 scripts/check_staleness.py --project-root <path> --scope workspace --document handoff --workspace-wide
```

## Package Layout

- `SKILL.md` - Main skill definition
- `AGENTS.md` - Maintainer guidance for this skill package
- `metadata.json` - Catalog metadata
- `evals/train_queries.json` - Starter should-trigger and should-not-trigger queries
- `evals/validation_queries.json` - Small holdout set for trigger sanity checks
- `scripts/create_handoff.py` - Initializes or refreshes the canonical file
- `scripts/validate_handoff.py` - Validates structure and obvious placeholders
- `scripts/check_staleness.py` - Checks whether the notes lag behind repo activity
- `scripts/resolve_handoff_path.py` - Path resolver and initializer
- `references/handoff-template.md` - HANDOFF template
- `references/agent-usage-best-practices.md` - Recommended agent workflow
- `references/snapshot-strategy.md` - When to snapshot and how to label it
- `references/workspace-memory-guide.md` - Workspace memory structure guidance
- `references/agent-integrations.md` - Agent-specific install notes

## Trigger Evals

The `evals/` folder contains a small starter set of realistic trigger queries inspired by the Agent Skills authoring guidance. Use them to sanity-check whether the `description` is specific enough to activate on handoff and resume tasks without firing on unrelated coding requests.

- `train_queries.json` is the working set for iterating on the description
- `validation_queries.json` is the holdout set for a quick regression check

These files are intentionally small. Expand them as you learn where the skill over-triggers or fails to activate.
