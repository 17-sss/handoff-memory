# Commit Patterns

Inspect the target repository first. These notes define style families and fallback policy, not project-specific rules.

## Priority Order

Always apply commit-style evidence in this order:

1. Explicit repo-local rules
2. Recent history
3. Conservative fallback

If explicit rules and history are weak or mixed, fall back to Conventional Commits.

## Semantic First

Infer the staged diff meaning first, then translate that meaning into the repo's preferred style family.

Recommended global semantic categories:

- `feature`
- `bugfix`
- `critical-bug`
- `refactor`
- `structure`
- `move`
- `ui-style`
- `responsive`
- `accessibility`
- `docs`
- `config`
- `tooling`
- `cleanup`
- `modify`

Do not default ambiguous changes to `bugfix`. Ambiguous changes should land in a conservative fallback category such as `modify`, `cleanup`, or the repo-local generic gitmoji fallback.

## Phrasing Profile

Format and phrasing should be handled separately.

- `format`: conventional, gitmoji, plain, or repo-custom template
- `phrasing`: language, tone, title length, and common wording habits

Recent history should inform phrasing even when format falls back conservatively.

Useful phrasing signals:

- dominant language: `ko`, `en`, or `mixed`
- dominant tone: `concise conversational`, `concise technical`, `descriptive`, or `formal/report-like`
- title length profile: `short`, `medium`, or `long`
- common Korean suffixes and action nouns such as `추가`, `수정`, `정리`, `분리`, `적용`, `제거`, `완화`, `노출`, `조정`
- whether the repo tends to avoid report-like phrasing

Korean phrasing guidance:

- Prefer short and natural commit wording over translated or report-like explanations
- Prefer `~정리`, `~수정`, `~추가`, `~분리`, `~조정` style endings when they match the repo's history
- Move detailed explanation into the body instead of stretching the title

English phrasing guidance:

- Prefer concise imperative wording
- Keep titles short and direct unless history is clearly more descriptive

## Conventional Commits

Common format:

- `feat: add account assignment search`
- `fix(modal): prevent double close on escape`
- `refactor: simplify query state wiring`

Use Conventional Commits when:

- the repo explicitly documents Conventional Commits
- history is clearly conventional
- explicit rules and history are weak, mixed, or absent

## Gitmoji / Emoji Style

Common format:

- `🐛 (scope) fix broken validation state`
- `✨ add account assignment search`

Use gitmoji strongly only when:

- repo-local gitmoji config exists
- repo docs or templates explicitly require emoji commits
- recent history is clearly emoji-dominant

Guidance:

- If an allowlist exists, only use that allowlist
- Prefer repo-local meaning declarations over global emoji habits
- If confidence is low, use the repo-local fallback gitmoji when one exists
- If no safe gitmoji fallback exists, do not guess aggressively

## Plain Imperative Style

Common format:

- `Fix modal close timing`
- `Move legacy auth routes`
- `Update validation copy`

Use plain style when:

- repo docs explicitly prefer short imperative subjects
- recent history is clearly plain and imperative

## Repo-Custom Templates

Sometimes a repo documents a custom template in `AGENTS.md`, `CONTRIBUTING`, `README`, commit templates, or editor settings.

Guidance:

- Detect repo-custom rules and prefer them over history
- If the custom template cleanly matches a known family, use that family
- If the custom template is explicit but not machine-friendly, keep the rule visible and use a conservative fallback rather than inventing a risky format

## Body Policy

- `title-only-preferred`: omit the body unless the user asks for one or the change really benefits from it
- `body-optional`: short bullet body is allowed
- `body-required`: use a short bullet body

Never pass a literal `\n` string as a commit body. Use a real multiline second `-m` or `draft_commit_message.py --commit`.
