# AGENTS.md

This package defines the `handoff-memory` skill.

## Package Intent

- Keep the shared mutable memory files inside the target repository or workspace root
- Support multiple agent environments without making any one agent folder the default data store
- Preserve one canonical handoff path per scope and document type
- Add lightweight operational tooling without turning session snapshots into the primary state

## Resolver Rules

- Honor `--handoff-path` when the caller gives one
- Support `repo`, `workspace`, and `auto` scope detection
- In repo scope prefer existing files in this order:
  - `docs/HANDOFF.md`
  - `memories/HANDOFF.md`
  - `HANDOFF.md`
- In workspace scope default to:
  - `_memory/HANDOFF.md`
  - `_memory/WORKSPACE.md`
  - `_memory/DECISIONS.md`
  - `_memory/PATTERNS.md`
- Optional snapshots live under `docs/handoffs/` or `_memory/handoffs/`
- If the path does not exist, create the default file for the chosen scope and document

## Editing Guidance

- Keep `SKILL.md`, `README.md`, and `metadata.json` aligned
- Update templates if the expected memory sections change
- Keep the scripts in `scripts/` aligned with the documented workflow
- Keep `references/agent-usage-best-practices.md` aligned with the actual recommended agent flow
- Most sessions should still update only the canonical handoff document
- Do not reintroduce global machine-local storage as the default behavior
