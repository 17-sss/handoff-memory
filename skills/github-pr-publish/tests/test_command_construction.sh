#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd)
SCRIPT="$ROOT/skills/github-pr-publish/scripts/create_pr.sh"
COLLECT_SCRIPT="$ROOT/skills/github-pr-publish/scripts/collect_publish_context.sh"
FAKE_BIN="$ROOT/skills/github-pr-publish/tests/fake-bin"
TMPDIR=${TMPDIR:-/tmp}
TEST_TMP=$(mktemp -d "$TMPDIR/github-pr-publish-tests.XXXXXX")
trap 'rm -rf "$TEST_TMP"' EXIT

export PATH="$FAKE_BIN:$PATH"
export FAKE_GH_LOG="$TEST_TMP/gh.log"
export FAKE_GIT_LOG="$TEST_TMP/git.log"
export FAKE_REPO="OWNER/REPO"
export FAKE_REMOTE_URL="git@github.com:OWNER/REPO.git"
export FAKE_BRANCH="feature-branch"
export FAKE_BASE="main"
export FAKE_ACCOUNT="octocat"
export FAKE_PR_URL="https://github.com/OWNER/REPO/pull/123"

pass_count=0
fail() { printf 'not ok - %s\n' "$*" >&2; exit 1; }
pass() { pass_count=$((pass_count + 1)); printf 'ok %d - %s\n' "$pass_count" "$*"; }
reset_logs() { : >"$FAKE_GH_LOG"; : >"$FAKE_GIT_LOG"; unset FAKE_DETACHED FAKE_REMOTE_HAS_HEAD FAKE_AUTH_FAIL FAKE_ALLOW_PUSH FAKE_REMOTE_URL FAKE_API_FAIL FAKE_CREATE_404 FAKE_SECRET_TOKEN FAKE_API_INPUT_COPY; export FAKE_REMOTE_URL="git@github.com:OWNER/REPO.git"; export FAKE_REMOTE_HAS_HEAD=1; }
run_ok() { local out=$1; shift; "$SCRIPT" "$@" >"$out" 2>"$out.err"; }
run_fail() { local out=$1; shift; if "$SCRIPT" "$@" >"$out" 2>"$out.err"; then cat "$out" "$out.err" >&2; fail "expected failure: $*"; fi; }
assert_contains() { grep -F -- "$2" "$1" >/dev/null || { cat "$1" >&2; fail "expected '$2' in $1"; }; }
assert_not_contains() { ! grep -F -- "$2" "$1" >/dev/null || { cat "$1" >&2; fail "unexpected '$2' in $1"; }; }
assert_private_tree() {
  python3 - "$1" <<'PY'
import os
import stat
import sys
from pathlib import Path

root = Path(sys.argv[1])
paths = [root] + [path for path in root.rglob("*") if path.exists()]
for path in paths:
    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & 0o077:
        raise SystemExit(f"{path} is not private: {oct(mode)}")
PY
}

body="$TEST_TMP/body.md"
printf 'Summary\n\nTests: fake\n' >"$body"

reset_logs
out="$TEST_TMP/preview.out"
run_ok "$out" --repo OWNER/REPO --base main --head OWNER:feature-branch --title 'Add feature' --body-file "$body"
assert_contains "$out" 'preview: no remote mutation performed'
assert_contains "$out" '--head OWNER:feature-branch'
assert_not_contains "$FAKE_GH_LOG" 'pr create'
assert_not_contains "$FAKE_GIT_LOG" 'push'
pass 'preview performs no mutation and renders explicit head'

reset_logs
out="$TEST_TMP/missing-head.out"
run_fail "$out" --repo OWNER/REPO --base main --head feature-branch --title 'Add feature' --body-file "$body" --yes
assert_contains "$out.err" '--head must include owner namespace'
pass 'missing owner namespace in --head is rejected'

reset_logs
out="$TEST_TMP/missing-content.out"
run_fail "$out" --repo OWNER/REPO --base main --head OWNER:feature-branch --title 'Add feature' --yes
assert_contains "$out.err" 'PR creation requires --body'
pass 'missing body/fill source is rejected'

reset_logs
template="$TEST_TMP/template.md"
printf 'Template body\n' >"$template"
out="$TEST_TMP/template-alone.out"
run_fail "$out" --repo OWNER/REPO --base main --head OWNER:feature-branch --template "$template" --yes
assert_contains "$out.err" '--template requires --title'
pass 'template alone is rejected'

reset_logs
out="$TEST_TMP/web-preview.out"
run_ok "$out" --repo OWNER/REPO --base main --head OWNER:feature-branch --title 'Add feature' --body-file "$body" --web
assert_contains "$out" '--web'
assert_not_contains "$FAKE_GH_LOG" 'pr create'
pass 'web without yes remains preview-only'

reset_logs
export FAKE_AUTH_FAIL=1
out="$TEST_TMP/auth-fail.out"
run_fail "$out" --repo OWNER/REPO --base main --head OWNER:feature-branch --title 'Add feature' --body-file "$body" --yes
assert_contains "$out.err" "Run 'gh auth login'"
pass 'auth failure is classified without token output'

reset_logs
export FAKE_DETACHED=1
out="$TEST_TMP/detached.out"
run_fail "$out" --repo OWNER/REPO --base main --head OWNER:feature-branch --title 'Add feature' --body-file "$body" --yes
assert_contains "$out.err" 'detached HEAD is not allowed'
pass 'detached HEAD is rejected'

reset_logs
export FAKE_BRANCH=main
out="$TEST_TMP/default-branch.out"
run_fail "$out" --repo OWNER/REPO --base main --title 'Add feature' --body-file "$body" --push --remote origin --yes
assert_contains "$out.err" "refusing to push base branch"
export FAKE_BRANCH=feature-branch
pass 'base/default branch push is rejected'

reset_logs
export FAKE_REMOTE_URL="git@github.com:FORK/REPO.git"
out="$TEST_TMP/fork.out"
run_fail "$out" --repo OWNER/REPO --base main --title 'Add feature' --body-file "$body" --push --remote origin --yes
assert_contains "$out.err" 'fork remotes are not supported'
pass 'fork/wrong remote is rejected'

reset_logs
out="$TEST_TMP/force.out"
run_fail "$out" --repo OWNER/REPO --base main --head OWNER:feature-branch --title 'Add feature' --body-file "$body" -f --yes
assert_contains "$out.err" 'force-like push options are not supported'
pass 'force-like option is rejected'

reset_logs
export FAKE_REMOTE_HAS_HEAD=0
out="$TEST_TMP/no-remote-head.out"
run_fail "$out" --repo OWNER/REPO --base main --head OWNER:feature-branch --title 'Add feature' --body-file "$body" --yes
assert_contains "$out.err" 'remote head'
pass 'create without remote head or push is rejected'

reset_logs
export FAKE_REMOTE_HAS_HEAD=0
export FAKE_ALLOW_PUSH=1
out="$TEST_TMP/push-create.out"
run_ok "$out" --repo OWNER/REPO --base main --title 'Add feature' --body-file "$body" --push --remote origin --yes
assert_contains "$FAKE_GIT_LOG" 'push origin HEAD:feature-branch'
assert_contains "$FAKE_GH_LOG" 'pr create'
assert_contains "$FAKE_GH_LOG" '--head OWNER:feature-branch'
pass 'guarded push creates with explicit derived head'

reset_logs
out="$TEST_TMP/rest-fill-only.out"
run_fail "$out" --repo OWNER/REPO --base main --head OWNER:feature-branch --fill --use-rest --yes
assert_contains "$out.err" 'REST fallback requires explicit --title'
assert_not_contains "$FAKE_GH_LOG" 'api -i repos/OWNER/REPO/pulls --method POST'
pass 'REST fallback rejects fill-only before mutating POST'

reset_logs
export FAKE_REMOTE_HAS_HEAD=0
export FAKE_ALLOW_PUSH=1
out="$TEST_TMP/rest-fill-push.out"
run_fail "$out" --repo OWNER/REPO --base main --head OWNER:feature-branch --fill --use-rest --push --remote origin --yes
assert_contains "$out.err" 'REST fallback requires explicit --title'
assert_not_contains "$FAKE_GIT_LOG" 'push'
assert_not_contains "$FAKE_GH_LOG" 'api -i repos/OWNER/REPO/pulls --method POST'
pass 'REST fallback validates title before guarded push or POST'

reset_logs
export FAKE_REMOTE_HAS_HEAD=0
out="$TEST_TMP/rest-fill-before-remote.out"
run_fail "$out" --repo OWNER/REPO --base main --head OWNER:feature-branch --fill --use-rest --yes
assert_contains "$out.err" 'REST fallback requires explicit --title'
assert_not_contains "$FAKE_GIT_LOG" 'ls-remote'
pass 'REST fallback validates title before remote-head proof'

reset_logs
out="$TEST_TMP/rest.out"
run_ok "$out" --repo OWNER/REPO --base main --head OWNER:feature-branch --title 'Add feature' --body-file "$body" --use-rest --yes
assert_contains "$FAKE_GH_LOG" 'api -i repos/OWNER/REPO/pulls --method POST'
assert_contains "$out" 'Pull request created'
pass 'REST fallback posts after remote-head proof and reports URL'

reset_logs
template_body="$TEST_TMP/template-body.md"
payload_copy="$TEST_TMP/rest-template-payload.json"
printf '## Summary\n\nTemplate body content\n' >"$template_body"
export FAKE_API_INPUT_COPY="$payload_copy"
out="$TEST_TMP/rest-template.out"
run_ok "$out" --repo OWNER/REPO --base main --head OWNER:feature-branch --title 'Add feature' --template "$template_body" --use-rest --yes
python3 - "$payload_copy" <<'PY'
import json, sys
with open(sys.argv[1], encoding='utf-8') as f:
    payload = json.load(f)
if payload.get("body") != "## Summary\n\nTemplate body content":
    raise SystemExit(f"unexpected body: {payload.get('body')!r}")
PY
pass 'REST fallback sends template content as PR body'

reset_logs
export FAKE_CREATE_404=1
export FAKE_SECRET_TOKEN='super-secret-token'
out="$TEST_TMP/private-404.out"
run_fail "$out" --repo OWNER/REPO --base main --head OWNER:feature-branch --title 'Add feature' --body-file "$body" --yes
assert_contains "$out.err" 'private repos this can mean missing access'
assert_not_contains "$out.err" 'super-secret-token'
assert_not_contains "$out.err" 'Authorization: token='
pass 'private 404 is classified and sensitive auth output is redacted'

reset_logs
export FAKE_REMOTE_URL='https://x-access-token:super-secret-token@github.com/OWNER/REPO.git'
collect_dir="$TEST_TMP/collect"
mkdir -p "$collect_dir"
chmod 755 "$collect_dir"
bash "$COLLECT_SCRIPT" --repo OWNER/REPO --output-dir "$collect_dir" >"$TEST_TMP/collect.out" 2>"$TEST_TMP/collect.err"
assert_not_contains "$collect_dir/remotes.txt" 'super-secret-token'
assert_not_contains "$collect_dir/remotes.txt" 'x-access-token:'
assert_contains "$collect_dir/remotes.txt" '[REDACTED]'
assert_private_tree "$collect_dir"
pass 'publish context collector redacts credentialed remote URLs with private permissions'

printf 'All %d github-pr-publish tests passed\n' "$pass_count"
