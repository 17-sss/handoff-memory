---
name: github-pr-publish
description: Agent-neutral workflow for safely publishing GitHub pull requests with gh CLI, local git, and constrained GitHub REST fallback. Use when asked to create, open, publish, draft, or preflight a GitHub PR from a local branch; push a branch for PR creation; create a PR in a public or private repo; diagnose PR creation auth, SSO, permission, or not-found failures; or avoid unsafe gh pr create prompting, fork creation, or accidental pushes.
---

# GitHub PR Publish

## Overview

Publish GitHub pull requests through general tools rather than agent-specific connectors. Prefer `gh`, local `git`, and GitHub REST APIs. Browser flows are explicit-only fallbacks.

This workflow supports public and private repositories. Private repositories require an authenticated GitHub CLI account with repository access, any required organization SSO authorization, and enough token or OAuth permissions to create pull requests.

## Safety Contract

- Default to preview: show intended operations without pushing, creating a PR, opening a browser, or sending a mutating API request.
- Never print, persist, or ask the user to paste raw tokens. Prefer `gh auth login` OAuth.
- Never use GitHub CLI token-display auth flags or save raw auth logs.
- Identify the authenticated account before actual PR creation.
- Treat all created PRs and pushed branches as actions from the authenticated account and configured git remote.
- Never rely on interactive `gh pr create`. Actual creation requires complete prompt-free inputs.
- Always pass an explicit `--head` value to `gh pr create`.
- Do not rely on the GitHub CLI PR-create preview flag; this skill uses its own preview path because the CLI can still push git changes.
- Do not create forks. Do not force-push. Do not push from detached HEAD.
- Push only when explicitly requested with `--push --remote <name> --yes`.
- Push only `HEAD:<branch>` to the exact named remote after branch and remote checks pass.
- Refuse pushing base, default, or protected branches when detectable.
- Use REST fallback only after proving the remote head exists.

## Workflow

### 1. Check tools and authentication

For read-only preflight, `git` and `gh` should be available. For private repos and actual creation, `gh` must be authenticated.

Useful commands:

```bash
gh auth status --hostname github.com
gh api user --jq .login
```

If auth fails, guide the user to `gh auth login`. Do not ask for token values.

### 2. Collect publish context

Use the bundled read-only helper:

```bash
skills/github-pr-publish/scripts/collect_publish_context.sh --repo OWNER/REPO
```

It captures sanitized account status, repo metadata, remotes, branch state, default/base candidates, upstream/ahead-behind details, and existing PR hints under `/tmp/github-pr-publish-*`.

### 3. Draft PR content before creation

Prepare a final title and body before creating the PR. Include:

- Summary of the change
- Tests or checks run
- Risks, rollout notes, or follow-ups
- Linked issue when applicable

Prompt-free content is required for actual creation:

- `--title` plus `--body` or `--body-file`, or
- explicit `--fill`, `--fill-first`, or `--fill-verbose` when commit-derived content is intended

`--template` alone is not enough because a title source is still required. Use it only with `--title` or a verified fill/title source.

### 4. Preview the operation

Preview is the default:

```bash
skills/github-pr-publish/scripts/create_pr.sh \
  --repo OWNER/REPO \
  --base main \
  --head OWNER:feature-branch \
  --title "Add feature" \
  --body-file /tmp/pr-body.md
```

The preview prints the intended state machine:

```text
preview -> validate -> optional guarded push -> create -> verify
```

No remote mutation occurs without `--yes`.

### 5. Create a PR from an existing remote branch

When the branch already exists on the target remote:

```bash
skills/github-pr-publish/scripts/create_pr.sh \
  --repo OWNER/REPO \
  --base main \
  --head OWNER:feature-branch \
  --title "Add feature" \
  --body-file /tmp/pr-body.md \
  --yes
```

The helper verifies the remote head, creates the PR with explicit `--head`, then verifies the created PR with `gh pr view`.

### 6. Push then create

For a first push, be explicit:

```bash
skills/github-pr-publish/scripts/create_pr.sh \
  --repo OWNER/REPO \
  --base main \
  --title "Add feature" \
  --body-file /tmp/pr-body.md \
  --push --remote origin \
  --yes
```

The helper derives an explicit head from `OWNER` and the current branch, checks the branch is safe, checks the remote maps to the target repository, pushes exactly `HEAD:<branch>`, and then creates the PR.

### 7. REST fallback

Use REST only when the remote head already exists and the CLI create path is blocked:

```bash
skills/github-pr-publish/scripts/create_pr.sh \
  --repo OWNER/REPO \
  --base main \
  --head OWNER:feature-branch \
  --title "Add feature" \
  --body-file /tmp/pr-body.md \
  --use-rest \
  --yes
```

REST creation requires `head`, `base`, and `title` unless converting an issue. Success must return HTTP `201` and a PR URL.

### 8. Optional browser handoff

`--web` is explicit-only. Without `--yes`, it is preview-only. With `--yes`, the helper still runs account, repo, head, branch, and content validation before opening GitHub's browser-based flow.

### 9. Failure classification

Classify failures without overclaiming:

- Not authenticated or bad credentials: run or refresh `gh auth login`.
- SSO/SAML: authorize the GitHub CLI OAuth app or token for the organization.
- 403: missing repository access or insufficient permission.
- 404 on private repositories: may mean wrong repo, missing access, or unapproved SSO, not necessarily absence.
- 422: invalid base/head/title fields, duplicate PR, or API validation failure.

## Scripts

### `scripts/collect_publish_context.sh`

Read-only context collector. Writes sanitized files to `/tmp/github-pr-publish-*` and never stores tokens.

### `scripts/create_pr.sh`

Command renderer and explicit executor. Supports preview, guarded push, CLI create, REST fallback, and fake CLI tests.

## References

Read these only when maintaining or adapting behavior:

- `references/github-cli-pr-create.md` for CLI constraints
- `references/github-rest-create-pr.md` for REST fallback constraints
- `references/agent-adapters.md` for agent installation notes
