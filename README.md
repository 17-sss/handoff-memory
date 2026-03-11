# Agent Skills

A collection of reusable skills for AI coding agents. Skills are packaged instructions and helper scripts that extend agent capabilities while keeping the workflow repository-friendly.

## Available Skills

### handoff-memory

Agent-neutral workflow for creating and maintaining shared repo-local HANDOFF documents.

**Use when:**
- Writing a project handoff before ending a session
- Resuming work from an existing handoff
- Standardizing shared project-state notes in Git-trackable files
- Keeping mutable handoff state out of `.codex`, `.claude`, `.windsurf`, or `.agents`

**Behavior:**
- Reuses an existing shared handoff file such as `docs/HANDOFF.md`, `memories/HANDOFF.md`, or `HANDOFF.md`
- Defaults to `docs/HANDOFF.md` when no shared handoff file exists
- Supports global or project-local skill installation, while keeping the shared data inside the repository

## Installation

Install a specific skill from this repository:

```bash
npx skills add https://github.com/17-sss/agent-skills --skill <skill-name>
```

Example:

```bash
npx skills add https://github.com/17-sss/agent-skills --skill handoff-memory
```

Install all skills only when you explicitly want the full collection:

```bash
npx skills add https://github.com/17-sss/agent-skills --all
```

## Usage

Once installed, agents can invoke the relevant skill when a task matches it. Detailed usage, install scope, and workflow notes live inside each skill package under `skills/<skill-name>/README.md`.

## Repository Structure

Each skill lives under `skills/<skill-name>/` and may contain:

- `SKILL.md` - Primary skill definition
- `README.md` - Human-facing documentation
- `AGENTS.md` - Agent-facing repo guidance for the skill package
- `metadata.json` - Catalog metadata
- `scripts/` - Helper scripts
- `references/` - Supporting docs and templates
- `agents/` - Optional agent-specific metadata such as `openai.yaml`
