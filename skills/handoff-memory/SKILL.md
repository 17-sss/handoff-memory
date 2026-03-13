---
name: handoff-memory
description: Create, refresh, validate, and resume shared HANDOFF and memory documents for either a single repository or a multi-repository workspace. Use when asked to write a handoff, checkpoint progress, resume prior work, or standardize project-state notes in Git-trackable files such as `docs/HANDOFF.md` for a repo or `_memory/HANDOFF.md` for a workspace root.
---

# Handoff Memory

## Overview

Keep shared memory documents close to the work they describe. For a single repository, keep the canonical handoff in the repo. For a multi-repository workspace, keep cross-repo memory in the workspace root.

This skill keeps one canonical handoff per scope and adds lightweight operational tooling:

- resolve the right document path
- create or refresh the canonical file
- validate that the document is structurally usable
- check whether the document is stale before trusting it
- optionally write timestamped session snapshots without making them the primary state

## Default Workflow

Use this as the default flow unless the user already has a stronger convention:

1. Resolve or initialize the canonical document.
   Run `scripts/create_handoff.py --project-root <path> --scope auto --document handoff --format json`.

2. Read the canonical document before changing it.
   Preserve still-valid context. Remove stale claims that would mislead the next session.

3. Update the canonical document with the current state.
   Keep it short, explicit, and action-oriented.

4. Validate it before ending the session.
   Run `scripts/validate_handoff.py --project-root <path> --scope auto --document handoff`.

5. When resuming, check staleness before trusting old notes.
   Run `scripts/check_staleness.py --project-root <path> --scope auto --document handoff`.

Use `--snapshot` with `create_handoff.py` when the user wants a timestamped session archive. Do not make snapshots the default shared state.

## Path Rules

- Prefer an explicit `--handoff-path` when the project already defines a canonical location.
- In repo scope, reuse an existing shared handoff file in a recognized location such as `docs/HANDOFF.md`, `memories/HANDOFF.md`, or `HANDOFF.md`.
- In workspace scope, keep cross-repo memory under `_memory/`.
- If no repo handoff exists, create `docs/HANDOFF.md`.
- If no workspace handoff exists, create `_memory/HANDOFF.md`.
- For workspace memory, use these defaults:
  - `_memory/HANDOFF.md` for current cross-repo status
  - `_memory/WORKSPACE.md` for durable workspace structure
  - `_memory/DECISIONS.md` for cross-repo architecture or policy choices
  - `_memory/PATTERNS.md` for repeatable conventions
- Most sessions should only update the canonical handoff. Touch the companion workspace documents only when durable shared context changed.
- Optional snapshots live under `docs/handoffs/` for repos or `_memory/handoffs/` for workspaces.
- Avoid `.codex`, `.claude`, `.windsurf`, or `.agents` as the default shared mutable handoff location.

## Scope Guidance

### Repo Scope

Use repo scope when the task belongs to one repository.

- Canonical file: `docs/HANDOFF.md`
- Session snapshots: `docs/handoffs/*.md`
- Keep implementation-level detail here

### Workspace Scope

Use workspace scope when the agent session starts from a parent folder that coordinates multiple repositories and the task spans more than one of them.

- Canonical file: `_memory/HANDOFF.md`
- Session snapshots: `_memory/handoffs/*.md`
- Keep only cross-repo coordination and durable shared context here
- Leave repo-specific implementation detail in each repo's own `docs/HANDOFF.md`

## Content Rules

- Keep the document scan-friendly. The next session should understand it in under a minute.
- Start with a strong `TL;DR`.
- Prefer exact paths, commands, branch names, dates, and repo names over vague prose.
- Record what is true now, not a transcript of the full chat.
- Note what changed recently, what is risky, and what should happen next.
- Include a quick reference section with the few files, commands, dashboards, or docs that matter most.
- Keep a short resume checklist so the next session can verify the notes before acting on them.
- Note when a claim is unverified.
- Do not store secrets, tokens, private keys, raw credentials, or long confidential logs.

## Document Model

The canonical handoff is the shared source of truth. Optional session snapshots are secondary artifacts for traceability.

- Canonical handoff:
  - repo: `docs/HANDOFF.md`
  - workspace: `_memory/HANDOFF.md`
- Snapshot archive:
  - repo: `docs/handoffs/*.md`
  - workspace: `_memory/handoffs/*.md`

This model keeps the current state easy to find while still allowing point-in-time captures when they are useful.

## Resume Workflow

When asked to continue work from a prior session:

1. Resolve the canonical handoff path.
2. Read the canonical handoff before planning or editing code.
3. Run the staleness check if the document might be old.
4. If working in workspace scope, read companion memory files only when they are directly relevant.
5. Compare the document against the current repo or workspace state and call out drift.
6. Continue the work.
7. Refresh and validate the canonical handoff again before ending the session if anything material changed.

## Scripts

### `scripts/resolve_handoff_path.py`

Resolve the canonical repo-local or workspace-local memory path. Use `--scope repo|workspace|auto`, `--document handoff|workspace|decisions|patterns`, or `--handoff-path` to honor an explicit override. Use `--ensure` to create the file when it does not exist.

### `scripts/create_handoff.py`

Initialize or refresh the canonical file and sync metadata such as project root, branch, and update timestamp. Use `--snapshot` to write a timestamped archive copy before the canonical file is refreshed.

### `scripts/validate_handoff.py`

Check that the document has the required sections, does not leave obvious placeholders behind, and stays short enough to be useful. Use `--strict` when placeholders or empty sections should fail validation.

### `scripts/check_staleness.py`

Compare the handoff timestamp against recent repo activity. This helps catch cases where commits or dirty working tree changes made the handoff untrustworthy.

## References

### `references/handoff-template.md`

Use this to understand the expected handoff structure and section intent.

### `references/workspace-memory-guide.md`

Use this when the task spans multiple repositories and you need to decide whether the canonical workspace handoff is enough or whether a durable companion document should also change.

### `references/agent-integrations.md`

Use this when the user asks where to install the skill for Codex or another agent. Keep install notes separate from the handoff workflow itself.

## Notes

- Installation scope and data location are separate concerns.
- The skill may be installed globally or per-project, but the shared mutable documents should stay inside the repository or workspace root they describe.
- Agent-specific files such as `AGENTS.md`, `CLAUDE.md`, `.codex/*`, or `.windsurf/rules/*` may reference the shared handoff, but should not become the primary mutable store.
