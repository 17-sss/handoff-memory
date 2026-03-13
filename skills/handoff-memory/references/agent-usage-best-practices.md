# Agent Usage Best Practices

Use this guide when an agent is actively relying on `handoff-memory` during normal work.

## Core Rule

Prefer one canonical handoff per active scope.

- Repo work: update `docs/HANDOFF.md`
- Cross-repo work: update `_memory/HANDOFF.md`
- Only touch `_memory/WORKSPACE.md`, `_memory/DECISIONS.md`, or `_memory/PATTERNS.md` when durable shared context changed
- Use snapshots only when the extra history is worth keeping

## Start-of-Session Flow

1. Detect the right scope before writing anything.
   - Single repo task: repo scope
   - Parent folder coordinating multiple repos: workspace scope

2. Resolve the canonical document first.

```bash
python3 scripts/resolve_handoff_path.py --project-root <path> --scope auto --document handoff --format json
```

3. Check whether the document is stale before trusting it.

```bash
python3 scripts/check_staleness.py --project-root <path> --scope auto --document handoff --format json
```

4. Read the canonical handoff before planning, searching, or editing.

5. Read companion workspace documents only when they are directly relevant.
   - `WORKSPACE.md` for repo map, ownership, or shared commands
   - `DECISIONS.md` for cross-repo decisions
   - `PATTERNS.md` for conventions worth reusing

6. If the codebase drifted from the handoff, call it out and correct the handoff before relying on it.

## During-Session Rules

- Keep the canonical handoff current enough that another agent could resume within a minute
- Keep `TL;DR`, `Current Objective`, and `Next Actions` especially fresh
- Prefer exact paths, commands, and repo names
- Keep implementation detail in repo handoffs, not in the workspace handoff
- Keep cross-repo coordination in the workspace handoff, not duplicated into every repo handoff
- When a task deeply changes one repo and lightly affects others, update the repo handoff in detail and keep the workspace handoff at the coordination level

## End-of-Session Flow

1. Refresh the canonical document metadata and structure.

```bash
python3 scripts/create_handoff.py --project-root <path> --scope auto --document handoff
```

2. Add a snapshot only when it buys real value.

```bash
python3 scripts/create_handoff.py --project-root <path> --scope auto --document handoff --snapshot
```

Good reasons to snapshot:

- A risky migration or deploy boundary
- A major context handoff between people or agents
- A large rewrite of the canonical handoff
- A debugging session whose intermediate state may matter later

3. Validate before you stop.

```bash
python3 scripts/validate_handoff.py --project-root <path> --scope auto --document handoff --strict
```

4. If the task touched multiple repos, also update the affected repo-local handoffs.

## Decision Matrix

- One repo, one task:
  - update that repo's `docs/HANDOFF.md`
- Multiple repos, one shared task:
  - update `_memory/HANDOFF.md`
  - update repo-local handoffs only for repos with meaningful implementation changes
- New cross-repo technical decision:
  - update `_memory/DECISIONS.md`
- New reusable convention:
  - update `_memory/PATTERNS.md`
- Workspace structure, ownership, or command changes:
  - update `_memory/WORKSPACE.md`

## Good Handoff Characteristics

- Starts with a strong `TL;DR`
- Names the real next action, not a vague intention
- Separates confirmed facts from unverified assumptions
- Includes the smallest useful set of file paths and commands
- Mentions validation status honestly
- Makes risks visible without turning into a chat transcript

## Anti-Patterns

- Appending the full conversation to the handoff
- Letting snapshots replace the canonical handoff
- Updating all workspace documents every session
- Copying repo-level detail into `_memory/HANDOFF.md` when it does not affect coordination
- Leaving template placeholders behind in a final handoff
- Treating agent-specific folders as the primary mutable store

## Suggested Agent Prompts

- "Resume from the canonical handoff, check for staleness, and call out any drift before editing."
- "Write or refresh the repo handoff using the current code state, then validate it strictly."
- "Update the workspace handoff only for cross-repo coordination and keep repo-specific detail in the repo handoffs."
