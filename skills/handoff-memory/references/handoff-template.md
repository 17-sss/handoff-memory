# Handoff Templates

Use one canonical handoff per scope. Optional timestamped snapshots are secondary archives, not the primary shared state.

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

1. Put the first concrete next step here.
2. Add the second step only if it is already justified by the current state.

## Resume Checklist

- Re-open the files most relevant to the active task.
- Re-run the most relevant check before making more changes.
- Confirm the first next action still matches the repo state.

## Resume Prompt

Continue this project from the shared HANDOFF document. First verify the repo still matches the notes, then complete the first unfinished next action.
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

1. Put the first coordination step here.
2. Add the next step only if it is already justified by the current state.

## Resume Prompt

Continue this workspace from the shared HANDOFF document. First identify the active workstream, then verify the related workstream notes before editing.
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

1. Put the first coordination step here.
2. Add the next step only if it is already justified by the current state.

## Resume Checklist

- Verify each impacted repo still matches the notes.
- Re-run the highest-signal shared check before editing further.
- Confirm the first next action still matches the workstream state.

## Resume Prompt

Continue this workstream from the shared HANDOFF document. First verify the involved repositories still match the notes, then complete the first unfinished next action.
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
