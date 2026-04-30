---
name: commit-helper
description: Inspect explicit repo-local commit rules, recent history, and staged changes to draft commit messages in the right style family. Use when the user asks for a commit message, asks to commit staged changes, or wants help choosing between conventional, gitmoji, plain imperative, or repo-custom commit formats.
---

# Commit Helper

## Overview

Use this skill when the user wants a commit message that matches the target repository instead of assuming one universal format or one universal tone.

This skill supports a small set of common style families:

- Conventional Commits
- Emoji / gitmoji-style commits
- Plain imperative subjects
- Repo-custom templates or documented commit rules

The helper does not try to support every commit format in the wild. It separates:

- `format`: conventional, gitmoji, plain, or repo-custom template
- `phrasing`: language, tone, title length, and common wording habits

It first infers semantic meaning from the staged diff, then converts that meaning into the repository's preferred style family and phrasing profile.

## Compatibility and Prerequisites

- `python3` in `PATH`
- `git` in `PATH`
- read access to the target repository

## Default Workflow

1. Identify the target repository.
2. Read `AGENTS.md` if the repo has one.
3. Run `scripts/inspect_commit_style.py <repo-path>` before drafting or committing.
   - This is the canonical inspection step.
   - It checks explicit repo-local rules first, then recent history, then staged diff semantics.
4. Respect the priority order:
   - explicit repo-local rules
   - recent history
   - conservative fallback
5. Treat format and phrasing separately.
   - Format comes from explicit rules, history, and fallback policy.
   - Phrasing comes mostly from recent history, even when format falls back conservatively.
6. Use `scripts/draft_commit_message.py <repo-path> --summary ... [--body-line ...]` as the standard generation path.
   - Add `--commit` when the user asked you to create the commit.
   - Prefer this script over raw `git commit -m ...` because it preserves multiline bodies safely.
7. Draft from staged changes only.
8. If no strong signal exists, fall back to a conventional commit title and conservative phrasing.

## Writing Rules

- Do not assume one universal commit format.
- Write the commit from staged changes only.
- Keep the title scoped to the staged changes, not to unrelated unstaged work.
- Use explicit local rules over recent history whenever they conflict.
- Use recent history over generic heuristics whenever explicit local rules are absent.
- If explicit rules and history are weak or mixed, use the conservative fallback.
- The semantic layer is global. The presentation layer is repo-specific.
  - Infer staged diff meaning as one of: `feature`, `bugfix`, `critical-bug`, `refactor`, `structure`, `move`, `ui-style`, `responsive`, `accessibility`, `docs`, `config`, `tooling`, `cleanup`, or `modify`.
  - Then express that meaning in the repository's style family.
- Conventional fallback is the default safe fallback when the repo does not clearly signal another style.
- Phrasing fallback should stay conservative.
  - Korean: prefer short natural noun/verb-style wording over report-like description.
  - English: prefer short imperative wording.
  - Mixed repos: follow the dominant language when confidence is sufficient; otherwise keep the title short and neutral.
- Gitmoji is not the global default.
  - Strongly activate gitmoji only when repo-local config, repo documentation, or clear emoji-dominant history says to do so.
  - If a repo-local allowlist exists, do not use emojis outside that allowlist.
  - If gitmoji confidence is low, prefer the repo-local fallback gitmoji when one exists. Do not force a bugfix emoji on ambiguous changes.
- Bugfix classification must be conservative.
  - Use `bugfix` or `critical-bug` only when the staged diff clearly fixes broken behavior, validation blocks, regressions, crashes, or incorrect state.
  - UI spacing, modal sizing, wrapper cleanup, and layout changes should usually land in `ui-style`, `structure`, or `modify` instead.
- Keep `title-only-preferred`, `body-optional`, and `body-required` policies distinct.
- The helper should match repo-local wording habits when possible.
  - Track `dominant_language`, `dominant_tone`, `title_length_profile`, `common_korean_suffixes`, `common_action_nouns`, `preferred_summary_style`, and `avoid_report_like_phrasing`.
  - If the user-supplied summary is awkward, polish the wording without changing the underlying meaning.
- Body default: if the repo does not strongly require a body, treat `title-only-preferred` as the default.
- If a body is needed, keep it short and use a few bullet lines.
- Literal `\n` is forbidden in commit bodies. Do not build a shell string like `"title\n\nbody"`.
- Use `draft_commit_message.py --commit` as the standard commit execution path whenever practical.

## Safe Commit Examples

- Title-only draft:
  `python3 scripts/draft_commit_message.py <repo-path> --summary "..." --no-body`
- Title + multiline body draft:
  `python3 scripts/draft_commit_message.py <repo-path> --summary "..." --body-line "first bullet" --body-line "second bullet"`
- Safe commit execution without literal `\n`:
  `python3 scripts/draft_commit_message.py <repo-path> --summary "..." --body-line "first bullet" --body-line "second bullet" --commit`
- If you must use raw `git commit`, pass an actual multiline second `-m`, not a literal backslash escape:
  `BODY="$(printf '%s\n' '- first bullet' '- second bullet')"`
  `git -C <repo-path> commit -m "title" -m "$BODY"`

## Script

- `scripts/inspect_commit_style.py`
  - inspects explicit rule files such as `AGENTS.md`, `CONTRIBUTING.md`, `README*`, commit templates, commitlint configs, and `.vscode/settings.json`
  - classifies recent history into common style families: `conventional`, `gitmoji`, `plain`, or mixed
  - infers staged semantic categories before choosing a commit style expression
  - infers phrasing profile fields such as `dominant_language`, `dominant_tone`, `title_length_profile`, `common_korean_suffixes`, `common_action_nouns`, `preferred_summary_style`, and `avoid_report_like_phrasing`
  - emits policy fields such as `style_mode`, `repo_has_explicit_commit_rule`, `repo_has_gitmoji_signal`, `should_use_gitmoji`, `fallback_commit_style`, `fallback_gitmoji`, `requires_human_gitmoji_review`, `semantic_confidence`, `is_bugfix_confident`, and `presentational_change_likelihood`
- `scripts/draft_commit_message.py`
  - is the standard generation and commit path
  - assembles a staged-only title/body draft from inspect output
  - applies explicit-rule, history, and fallback policy in that order
  - polishes wording to match repo-local phrasing when it can do so safely
  - warns when manual overrides conflict with repo policy or low-confidence semantics
  - normalizes body bullets without literal `\n`
  - can execute `git commit` safely with subprocess argv via `--commit`

## Reference

- `references/commit-patterns.md`
  - style-family notes and conservative fallback guidance

## Evals

- `evals/train_queries.json`
- `evals/validation_queries.json`
- `evals/behavior_cases.json`
