# Workspace Memory Guide

Use workspace scope when the agent session starts from a parent folder that coordinates multiple repositories and the task spans more than one repo.

## Default Rule

Most sessions should update exactly one canonical handoff for the active context.

If the whole workspace shares one active cross-repo context, use `_memory/HANDOFF.md`.

If the same workspace contains multiple independent repo combinations or initiatives, create a dedicated workstream under `_memory/workstreams/<name>/`.

Only update the other workspace or workstream documents when durable shared context changed:

- `_memory/WORKSPACE.md` when the repo map, ownership, or operating model changed
- `_memory/DECISIONS.md` when a cross-repo decision was made or reversed
- `_memory/PATTERNS.md` when a convention should be reused later
- `_memory/workstreams/<name>/WORKSTREAM.md` when a workstream's involved repos, purpose, or boundaries changed
- `_memory/workstreams/<name>/DECISIONS.md` when a decision belongs to one workstream rather than the whole workspace
- `_memory/workstreams/<name>/PATTERNS.md` when a convention is specific to one workstream
- `_memory/handoffs/*.md` only when you explicitly want a timestamped session snapshot

## Recommended Files

- `_memory/HANDOFF.md`
  - Workspace-wide summary
  - Active workstream index
  - Shared blockers and next actions that affect the whole workspace

- `_memory/WORKSPACE.md`
  - Workspace purpose
  - Repo map and ownership
  - Shared run commands
  - Environment assumptions

- `_memory/DECISIONS.md`
  - Cross-repo architecture decisions
  - Interface contracts
  - Policies that affect more than one repo

- `_memory/PATTERNS.md`
  - Repeated implementation conventions
  - Naming, API, deployment, and release patterns

- `_memory/workstreams/<name>/HANDOFF.md`
  - Current status for one specific repo combination or initiative
  - Cross-repo blockers limited to that workstream
  - Next actions for that workstream only

- `_memory/workstreams/<name>/WORKSTREAM.md`
  - Workstream purpose
  - Repos involved
  - Boundaries and commands

- `_memory/workstreams/<name>/DECISIONS.md`
  - Decisions specific to one workstream

- `_memory/workstreams/<name>/PATTERNS.md`
  - Conventions specific to one workstream

- `_memory/handoffs/*.md`
  - Optional point-in-time session snapshots
  - Useful when a major transition or risky edit deserves a preserved checkpoint

## Update Rules

- Update `_memory/HANDOFF.md` when the active cross-repo task changes
- Update `_memory/WORKSPACE.md` when the workspace shape or shared operating model changes
- Update `_memory/DECISIONS.md` when a decision affects multiple repos
- Update `_memory/PATTERNS.md` when a convention should be reused in future work
- Update `_memory/workstreams/<name>/HANDOFF.md` when a task belongs to one specific initiative inside the workspace
- Update `_memory/workstreams/<name>/WORKSTREAM.md` when the workstream's repo set or mission changes
- Do not force a session snapshot for every handoff. Use snapshots when the extra history is worth the noise.

## Relationship to Repo-Level Handoffs

- Keep repo-specific implementation details in each repo's `docs/HANDOFF.md`
- Keep workspace-wide coordination at the workspace level
- Keep initiative-specific cross-repo coordination in workstream documents
- Avoid duplicating detailed repo-level notes in workspace memory unless they affect coordination
