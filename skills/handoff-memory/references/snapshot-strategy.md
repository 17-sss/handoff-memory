# Snapshot Strategy

Snapshots are optional point-in-time checkpoints. They are useful when the history itself matters, but they should not replace the canonical handoff.

## Core Rule

Keep the current truth in the canonical handoff:

- repo: `docs/HANDOFF.md`
- workspace-wide: `_memory/HANDOFF.md`
- workstream: `_memory/workstreams/<name>/HANDOFF.md`

Use snapshots only when you want a preserved checkpoint that future sessions may need to inspect.

## When to Create a Snapshot

Create one before refreshing the canonical handoff when any of these are true:

- A risky migration or deploy is about to start
- You are handing off to a different person, machine, or agent
- A debugging session produced an intermediate state worth preserving
- A major decision, milestone, or rollback boundary was reached
- You are about to rewrite the canonical handoff substantially

## When Not to Create a Snapshot

Skip snapshots for routine updates such as:

- Small incremental code changes
- Normal progress inside the same workstream
- Canonical handoff edits that do not cross a meaningful boundary
- Short sessions where the canonical handoff already captures the latest truth well

## Snapshot Kinds

Use one of these kinds with `--snapshot-kind`:

- `handoff` - clean context transfer between sessions, people, or agents
- `risk` - before a risky edit, experiment, or irreversible step
- `deploy` - before or after a deploy or release step
- `migration` - before or after a schema, platform, or large refactor migration
- `debug` - preserve a debugging checkpoint with meaningful intermediate findings
- `decision` - capture state around an important technical decision
- `milestone` - mark a meaningful project or workstream milestone
- `other` - use only when none of the above fit

## Command Pattern

```bash
python3 scripts/create_handoff.py \
  --project-root <path> \
  --scope auto \
  --document handoff \
  --snapshot \
  --snapshot-kind handoff \
  --snapshot-reason "Context transfer before switching to another machine"
```

For a workstream:

```bash
python3 scripts/create_handoff.py \
  --project-root <path> \
  --scope workspace \
  --workstream checkout-flow \
  --document handoff \
  --snapshot \
  --snapshot-kind risk \
  --snapshot-reason "Checkpoint before touching frontend and backend payment paths"
```

## Naming Guidance

- Use `--snapshot-label` only when the default project or workstream name is too vague
- Prefer initiative names such as `checkout-flow` or `asset-delivery`
- Keep labels short and stable enough to scan later
- Snapshot filenames should use `YYYYMMDD_HHMMSS[-n]-<kind>-<label>.md`
- Keep canonical files unprefixed. Timestamp prefixes belong only in snapshot archives.

## Snapshot Content

Each snapshot should explain:

- when it was created
- what canonical file it came from
- which scope it belongs to
- why it exists

This makes snapshots worth keeping without turning them into the primary source of truth.
