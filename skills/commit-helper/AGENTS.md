# AGENTS.md

This package defines the `commit-helper` skill.

## Package Intent

- Make commit drafting reproducible by inspecting explicit local rules and real local history
- Keep commit-style decisions explainable through a small set of common style families
- Avoid turning one repository's preferences into a universal global rule

## Editing Guidance

- Keep the skill generic across repositories. Avoid hard-coding one team's preferences as global defaults.
- Update `references/commit-patterns.md` when supported style families or fallback rules change materially.
- Keep staged-file scope inference limited and explainable.
- Prefer explicit rule discovery and history classification over repository-name special cases.
- Treat repo-local gitmoji settings as authoritative when present.
- Keep bugfix detection conservative and avoid mapping presentational changes to bugfix by default.
- Keep title-only commits as the default unless a repo clearly expects bodies.
- Never emit commit bodies with a literal `\n` sequence.
