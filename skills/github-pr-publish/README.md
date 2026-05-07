# github-pr-publish

Agent-neutral workflow for safely publishing GitHub pull requests with `gh`, local `git`, and constrained GitHub REST fallback.

## Requirements

- GitHub CLI `gh`
- Local `git`
- A logged-in GitHub CLI session for private repos or actual PR creation

## Workflow Highlights

- Previews by default and performs no push, PR creation, browser open, or mutating API call without `--yes`
- Requires prompt-free PR content for creation
- Always constructs `gh pr create` with explicit `--head`
- Avoids the GitHub CLI PR-create preview flag because it can still push git changes
- Guards pushes behind `--push --remote <name> --yes`
- Rejects unsafe push situations such as forks, detached HEAD, wrong remotes, base/default/protected branches, and force-like paths
- Supports private repos through authenticated `gh` and clear SSO, auth, permission, private not-found, and validation diagnostics
- Includes fake `gh`/`git` tests that prove no mutation by default and no token leakage

## Common Commands

Read-only context collection:

```bash
skills/github-pr-publish/scripts/collect_publish_context.sh --repo OWNER/REPO
```

Preview a PR create operation:

```bash
skills/github-pr-publish/scripts/create_pr.sh \
  --repo OWNER/REPO \
  --base main \
  --head OWNER:feature-branch \
  --title "Add feature" \
  --body-file /tmp/pr-body.md
```

Create from an existing remote branch:

```bash
skills/github-pr-publish/scripts/create_pr.sh \
  --repo OWNER/REPO \
  --base main \
  --head OWNER:feature-branch \
  --title "Add feature" \
  --body-file /tmp/pr-body.md \
  --yes
```

First push then create:

```bash
skills/github-pr-publish/scripts/create_pr.sh \
  --repo OWNER/REPO \
  --base main \
  --title "Add feature" \
  --body-file /tmp/pr-body.md \
  --push --remote origin \
  --yes
```

## Package Layout

- `SKILL.md` - Main workflow, auth policy, safe create contract, and fallback rules
- `scripts/collect_publish_context.sh` - Read-only sanitized context collector
- `scripts/create_pr.sh` - Preview-first command builder and explicit executor
- `tests/` - Fake `gh`/`git` harness and command-construction tests
- `references/` - Maintenance notes for CLI/API behavior and agent adapters
- `agents/openai.yaml` - Codex Skills UI metadata only

Use `SKILL.md` as the source of truth for behavior.
