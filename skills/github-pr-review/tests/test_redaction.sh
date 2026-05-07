#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
SKILL_DIR=$(cd "$SCRIPT_DIR/.." && pwd)
TEST_TMP=$(mktemp -d "${TMPDIR:-/tmp}/github-pr-review-tests.XXXXXX")
trap 'rm -rf "$TEST_TMP"' EXIT

export PATH="$SCRIPT_DIR/fake-bin:$PATH"
export FAKE_SECRET_TOKEN='ghp_super_secret_token_1234567890'

assert_not_contains() {
  local file=$1 pattern=$2
  if grep -qF "$pattern" "$file"; then
    printf 'not ok - %s still contains %s\n' "$file" "$pattern" >&2
    cat "$file" >&2
    exit 1
  fi
}

assert_contains() {
  local file=$1 pattern=$2
  if ! grep -qF "$pattern" "$file"; then
    printf 'not ok - %s missing %s\n' "$file" "$pattern" >&2
    cat "$file" >&2
    exit 1
  fi
}

body="$TEST_TMP/review.md"
printf 'review body\n' > "$body"

post_out="$TEST_TMP/post.out"
post_err="$TEST_TMP/post.err"
if bash "$SKILL_DIR/scripts/post_review.sh" OWNER/REPO#1 "$body" >"$post_out" 2>"$post_err"; then
  printf 'not ok - post_review should fail under fake gh\n' >&2
  exit 1
fi
assert_not_contains "$post_err" "$FAKE_SECRET_TOKEN"
assert_not_contains "$post_err" 'Authorization: token='
assert_contains "$post_err" '[REDACTED]'
printf 'ok 1 - post_review redacts failing gh stderr\n'

collect_dir="$TEST_TMP/context"
collect_out="$TEST_TMP/collect.out"
collect_err="$TEST_TMP/collect.err"
if bash "$SKILL_DIR/scripts/collect_pr_context.sh" OWNER/REPO#1 --output-dir "$collect_dir" >"$collect_out" 2>"$collect_err"; then
  printf 'not ok - collect_pr_context should fail under fake gh\n' >&2
  exit 1
fi
for file in "$collect_dir"/* "$collect_err"; do
  [[ -f "$file" ]] || continue
  assert_not_contains "$file" "$FAKE_SECRET_TOKEN"
  assert_not_contains "$file" 'Authorization: token='
  assert_not_contains "$file" 'x-access-token:'
done
assert_contains "$collect_dir/pr-view.err" '[REDACTED]'
printf 'ok 2 - collect_pr_context redacts saved gh stderr\n'

printf 'All github-pr-review redaction tests passed\n'
