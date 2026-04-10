# Handoff Templates

Use one canonical handoff per scope. Optional timestamped snapshots are secondary archives, not the primary shared state.

## Path Style

- Keep canonical filenames stable: `HANDOFF.md`, `WORKSTREAM.md`, `WORKSPACE.md`, `DECISIONS.md`, and `PATTERNS.md` should not get timestamp prefixes.
- Use workspace-relative paths and repo names in the body whenever possible, for example `frontend/src/app.tsx` or `backend:services/payments.py`.
- Avoid machine-specific absolute paths such as `/Users/...` or old workstation roots unless they are genuinely required.
- Reserve timestamped naming for snapshot archives only, using `YYYYMMDD_HHMMSS[-n]-<kind>-<label>.md`.

## Repo Handoff

```md
# HANDOFF

## Metadata

- Project:
- Project ID:
- Repo Root:
- Branch:
- Last Updated:
- Updated By:

## TL;DR

- Summarize the current situation in 2-3 bullets.

## Current Objective

- State the immediate goal for the next session.

## Current State

- What is done:
- What is in progress:
- What still needs confirmation:

## Recent Changes

- Change:
- Validation:
- Impact:

## Known Issues / Watch List

- Issue:
- Risk:
- Workaround:

## Quick Reference

- Key files:
- Commands:
- Links / dashboards:

## Validation

- Checks run:
- Results:
- Not run yet:

## Next Actions

1. Put the first concrete step the next session should execute here, not a broad exploration topic.
2. Add the second step only if it is already justified by the current state.

## Resume Checklist

- Re-open the files most relevant to the active task.
- Re-run the most relevant check before making more changes.
- Confirm the first next action still matches the repo state.

## Resume Prompt

Continue this project from the shared HANDOFF document. First verify the repo still matches the notes, then execute the first unfinished next action. Do not reopen already-settled design direction unless the user or current repo state invalidates it.
```

## Workspace Handoff

```md
# HANDOFF

## Metadata

- Workspace:
- Root:
- Last Updated:
- Updated By:

## Active Workstreams

- Workstream:
- Status:
- Repositories:

## Current Coordination State

- What is stable:
- What is in progress:
- What needs handoff:

## Shared Watch List

- Issue:
- Risk:
- Owner:

## Quick Reference

- Key repositories:
- Shared commands:
- Dashboards / docs:

## Next Actions

1. Put the first coordination step the next session should execute here, not a brainstorming prompt.
2. Add the next step only if it is already justified by the current state.

## Resume Prompt

Continue this workspace from the shared HANDOFF document. First identify the active workstream or active repo set, then verify only those related repositories before editing. After verification, execute the first unfinished next action instead of reopening already-settled direction unless the user or repo state invalidates it. Use a workspace-wide scan only when the task truly spans the whole workspace.
```

## Workstream Handoff

```md
# HANDOFF

## Metadata

- Workspace:
- Workstream:
- Root:
- Workstream Root:
- Last Updated:
- Updated By:

## TL;DR

- Summarize the workstream state in 2-3 bullets.

## Current Objective

- State the shared goal for the next session.

## Current State

- What is stable:
- What is in progress:
- What still needs confirmation:

## Repo Impact

- Repositories involved:
- Cross-repo dependencies:
- Shared blockers:

## Recent Changes

- Change:
- Validation:
- Impact:

## Known Issues / Watch List

- Issue:
- Risk:
- Workaround:

## Quick Reference

- Key repositories:
- Shared commands:
- Dashboards / docs:

## Validation

- Checks run:
- Results:
- Not run yet:

## Next Actions

1. Put the first coordination step the next session should execute here, not a brainstorming prompt.
2. Add the next step only if it is already justified by the current state.

## Resume Checklist

- Verify each impacted repo still matches the notes.
- Re-run the highest-signal shared check before editing further.
- Confirm the first next action still matches the workstream state.

## Resume Prompt

Continue this workstream from the shared HANDOFF document. First verify the involved repositories still match the notes, then execute the first unfinished next action. Do not reopen already-settled design direction unless the user or current repo state invalidates it.
```

## Workstream Overview

```md
# WORKSTREAM

## Overview

- Workstream:
- Workspace Root:
- Workstream Root:
- Purpose:

## Repositories

- Repo:
- Repo:

## Shared Goal

- Outcome:
- Non-goals:

## Ownership / Boundaries

- Primary owner:
- Repo boundaries:

## Entry Points / Commands

- Key paths:
- Commands:

## Notes

- Constraints:
- Coordination notes:
```
