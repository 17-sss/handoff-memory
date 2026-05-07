# commit-helper

Korean version: [README.ko.md](./README.ko.md)

Reusable commit-message helper that inspects explicit repo-local rules, recent history, and staged changes to support a small set of common commit style families: Conventional Commits, gitmoji/emoji style, plain imperative style, and repo-custom templates. It also infers repo-local phrasing habits so the resulting title sounds closer to the way the team actually writes commit subjects.

## Use When

- The user asks for a commit message
- The user wants to commit staged changes but the repo convention is unclear
- The current repository uses a different style from the last one you touched
- The repository may restrict emoji-based commits to a local allowlist


## Invocation Boundary

When this skill is invoked, commit messages come only from repo-local rules, recent history, staged diff semantics, and explicit user wording. It must not add orchestration metadata, Lore trailers, workflow notes, or automation co-author trailers unless the target repository's own rules or the user explicitly require them. If an external hook demands those non-repo trailers, treat it as a blocker instead of polluting the commit message.

## Key Files

- `scripts/inspect_commit_style.py`
- `scripts/draft_commit_message.py`
- `references/commit-patterns.md`
- `evals/behavior_cases.json`

## Current Guarantees

- Follows `explicit local rules > recent history > conservative fallback`
- Uses Conventional Commits as the safe fallback when no strong signal exists
- Activates gitmoji strongly only when repo-local config, repo documentation, or emoji-dominant history justifies it
- Keeps semantic inference global and style expression repo-specific
- Separates commit `format` from commit `phrasing`
- Infers wording profile signals such as dominant language, tone, title length, and common Korean action nouns
- Uses `draft_commit_message.py` as the standard safe execution path, including multiline bodies without literal `\n`
