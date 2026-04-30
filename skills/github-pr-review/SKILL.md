---
name: github-pr-review
description: Agent-neutral workflow for reviewing GitHub pull requests with gh CLI, local git, tests, and GitHub REST or GraphQL APIs, then posting summary or inline review comments as the user's authenticated GitHub account. Use when asked to set up PR review authentication, review a PR URL, review owner/repo#123, review the current branch PR, post PR review comments, review public or private repo PRs, use gh to inspect a PR diff, or leave feedback from the user's GitHub account.
---

# GitHub PR Review

## Overview

Review GitHub pull requests through general tools rather than agent-specific connectors. Prefer `gh`, local `git`, project test commands, and GitHub REST or GraphQL APIs. Browser automation is a last fallback only when CLI and API paths are blocked.

The workflow supports public and private repositories. Reading a public PR may be possible without authentication, but posting any review always requires an authenticated GitHub account. Private repositories require that the authenticated account has repo access, any required organization SSO authorization, and sufficient OAuth scopes or token permissions.

## Operating Rules

- Never print, persist, or ask the user to paste raw tokens unless there is no other path. Prefer `gh auth login` OAuth.
- When authentication exists, identify the account that will post the review and tell the user.
- Treat all posted comments as coming from the user's authenticated GitHub account.
- Draft the review first and ask for confirmation before posting unless the user explicitly said to post immediately.
- Use `approve` or `request changes` only when the user explicitly asks for that event. Default to a non-approving comment review.
- Prefer one batched review over scattered comments. Use inline comments only when the file and diff line mapping are certain.
- Prefer JSON payloads with `gh api --input` for multi-comment inline reviews. Avoid shell-expanded nested `comments[]` flags unless the payload is trivial.

## Workflow

### 1. Check Authentication

If the user asks to set up PR review access, use OAuth posting, or review as their account, check authentication before asking for a PR:

```bash
gh auth status
```

If not logged in, guide or run:

```bash
gh auth login
```

After login, confirm the account without exposing tokens:

```bash
gh api user --jq .login
```

PATs or API tokens are acceptable when the environment already provides them, but do not echo token values, write them into files, or include them in review artifacts.

If the user provided a PR URL up front, identify the PR first, then run the same authentication check before collecting or posting review context.

### 2. Identify the PR

Resolve the target in this order:

1. GitHub PR URL such as `https://github.com/owner/repo/pull/123`.
2. Compact reference such as `owner/repo#123`.
3. PR number or branch in the current repository.
4. Current branch PR with `gh pr view` when no PR identifier was given.

Useful commands:

```bash
gh pr view <number-or-url> --json number,title,url,author,baseRefName,headRefName
gh pr view --json number,title,url,author,baseRefName,headRefName
```

Use `-R owner/repo` when reviewing outside the current checkout.

### 3. Verify Access

Separate read access from posting access:

- Public repo read: may work without login, depending on `gh` configuration and rate limits.
- Any review posting: requires login.
- Private repo read or posting: requires account access to the repository.

When access fails, classify the likely cause:

- Not authenticated: ask the user to run `gh auth login`.
- Private repo appears as not found: the account may lack repo access or the repo/PR identifier may be wrong.
- Organization SSO/SAML error: the user must authorize the GitHub CLI OAuth app or token for the org.
- 403 or insufficient scopes: the token or OAuth grant may lack repo or pull request permissions.
- 404 on a private repo: do not assume the PR is absent; mention that GitHub masks missing private access as not found.

### 4. Collect PR Context

Use the bundled script when available:

```bash
skills/github-pr-review/scripts/collect_pr_context.sh <pr-url-or-owner/repo#number>
```

Or collect manually:

```bash
gh pr view <pr> --json title,body,author,labels,baseRefName,headRefName,additions,deletions,changedFiles,files,reviews,reviewRequests,statusCheckRollup
gh pr diff <pr> --name-only
gh pr diff <pr>
gh pr checks <pr>
```

If a local checkout is available, inspect related code beyond the diff before making strong claims. Search for call sites, schema consumers, feature flags, migrations, generated files, and tests. Run the repository's relevant checks when feasible, such as lint, typecheck, unit tests, or focused tests for changed areas.

### 5. Review Standard

Use a code-review stance. Prioritize:

- Correctness bugs and edge cases.
- Regression risk and blast radius.
- Security, authentication, authorization, and secret-handling issues.
- Concurrency, state, lifecycle, and data consistency problems.
- API, schema, migration, and backward-compatibility breaks.
- Missing or weak tests for changed behavior.
- Performance risks with concrete impact.

Deprioritize style preferences, naming nits, and broad refactors unless they hide real risk. Do not report speculative issues as facts; label uncertainty and include what would verify it.

For every finding, include:

- Severity: `blocking`, `important`, `minor`, or `question`.
- File and line reference when possible.
- The specific risk.
- A concrete fix or verification path.

If there are no material issues, say so plainly and mention any remaining test gaps or unverified areas.

### 6. Draft Format

Use a compact review draft:

```markdown
Findings:

1. blocking: <title>
   File: path/to/file.ext:123
   Risk: <what can break and when>
   Recommendation: <specific change or test>

2. important: <title>
   File: path/to/other.ext:45
   Risk: <risk>
   Recommendation: <fix>

Summary:
<short overall assessment, checks run, and remaining risk>
```

If there are no findings:

```markdown
Findings:
No material issues found.

Summary:
Reviewed the diff and relevant context. Checks run: <commands or "not run">. Remaining risk: <short note>.
```

### 7. Publish the Review

Default path: show the draft to the user first. Post only after confirmation.

For a summary review:

```bash
gh pr review <pr> --comment --body-file review.md
```

The bundled helper wraps this:

```bash
skills/github-pr-review/scripts/post_review.sh <pr> review.md
```

Only use these when explicitly requested:

```bash
gh pr review <pr> --approve --body-file review.md
gh pr review <pr> --request-changes --body-file review.md
```

For inline comments, prefer the GitHub API only when line mapping is reliable. REST review comments should target diff lines with `line` and `side`, plus optional `start_line` and `start_side` for multi-line comments. Avoid deprecated `position`-based mapping unless the environment requires it. If mapping is uncertain, post a summary review with file and line references instead.

GraphQL can be used for review-thread operations such as adding review threads or replies. The `gh pr-review` extension from `agynio/gh-pr-review` is an optional convenience when installed, but this skill must still work with plain `gh pr review` and `gh api`.

### 8. Verify Inline Line Mapping

Inline comments must point to lines that are present in the PR diff, not merely to any line in the base branch. For new or modified code, use `side: RIGHT` and the target line number from the PR's head-side file. Use `side: LEFT` only for removed lines.

Before posting inline comments:

1. Inspect the patch:

   ```bash
   gh pr diff <pr>
   ```

2. Confirm the local file line when the checkout is available:

   ```bash
   nl -ba path/to/file.ext | sed -n '120,140p'
   ```

3. Confirm the file's PR patch from the API when possible:

   ```bash
   gh api repos/OWNER/REPO/pulls/NUMBER/files --paginate \
     --jq '.[] | select(.filename == "path/to/file.ext") | .patch'
   ```

4. Verify the target line is inside a diff hunk as an added line or context line for `side: RIGHT`.
5. If any mapping is uncertain, do not post inline comments. Post a summary review with file and line references instead.

### 9. Post Inline Review Comments

For one or more inline comments, prefer one review payload and `gh api --input`. This is more reliable than composing nested `comments[]` parameters in shell flags.

Create a temporary payload file. Use a sanitized repo slug and PR number, for example `/tmp/owner-repo-pr123-review.json`. Do not include tokens, secrets, raw auth headers, or unrelated private logs in this file.

```json
{
  "event": "COMMENT",
  "body": "Reviewed the PR and left inline notes on the risky parts.",
  "comments": [
    {
      "path": "src/example.ts",
      "line": 42,
      "side": "RIGHT",
      "body": "This condition now allows an empty value through. Please add a guard or a regression test for that case."
    },
    {
      "path": "src/other.ts",
      "line": 87,
      "side": "RIGHT",
      "body": "This call can now run before the token is initialized. Consider keeping the previous ordering or handling the missing-token branch."
    }
  ]
}
```

Post it:

```bash
gh api repos/OWNER/REPO/pulls/NUMBER/reviews \
  --method POST \
  --input /tmp/owner-repo-pr123-review.json \
  --jq '{id, state, html_url}'
```

Expected state for a comment-only review is `COMMENTED`. Give the `html_url` to the user. Delete the payload after posting when it is no longer needed:

```bash
rm /tmp/owner-repo-pr123-review.json
```

Only set `"event": "APPROVE"` or `"event": "REQUEST_CHANGES"` when the user explicitly asked for that review action. For multi-line comments, add `start_line` and `start_side` after verifying both ends of the range in the diff.

### 10. Verify Posted Review

After posting, verify the response and optionally confirm through the PR reviews list:

```bash
review_id=123456789
gh api repos/OWNER/REPO/pulls/NUMBER/reviews --paginate \
  --jq ".[] | select(.id == $review_id) | {id, state, html_url, user: .user.login}"
```

Check that:

- `state` is `COMMENTED` for normal review comments.
- `html_url` is present and opens the submitted review.
- `user.login` matches the authenticated account.
- The user received the `html_url` or a concise summary of where the review was posted.

### 11. Failure and Fallback

- If `gh` is missing, ask the user to install GitHub CLI before continuing.
- If authentication is missing, use `gh auth login`; do not switch to browser automation for normal login.
- If private access fails, distinguish wrong repo/PR, missing repo permission, SSO/SAML authorization, and insufficient OAuth scopes as far as the error allows.
- If `gh pr review` cannot express needed inline comments, use `gh api` with REST or GraphQL.
- If `gh api` returns a validation error for inline comments, re-check `path`, `line`, `side`, and whether the line is present in the diff. Fall back to a summary review if still uncertain.
- Mention browser automation only as a last fallback when CLI/API access is blocked and the user explicitly wants to proceed that way.

## Scripts

### `scripts/collect_pr_context.sh`

Collects PR metadata, changed files, diff, checks, and sanitized auth/account information into an output directory. It accepts a PR URL, `owner/repo#123`, a PR number, a branch, or no PR identifier for the current branch.

### `scripts/post_review.sh`

Posts a summary PR review from a body file. It confirms the authenticated account before posting. The default event is `--comment`; `--approve` and `--request-changes` require explicit options.

## Agent Adapters

For Codex, Claude Code, Cursor, and generic agent placement notes, read `references/agent-adapters.md` only when installing or adapting the package to another agent environment.
