#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  collect_pr_context.sh [PR_REF] [--repo OWNER/REPO] [--output-dir DIR]

PR_REF may be:
  https://github.com/owner/repo/pull/123
  owner/repo#123
  123
  branch-name
  omitted, to use the current branch PR

The script writes gh pr view, gh pr diff, changed files, checks, and sanitized
auth/account context to the output directory. It never prints or stores tokens.
USAGE
}

die() {
  printf 'error: %s\n' "$*" >&2
  exit 1
}

warn() {
  printf 'warning: %s\n' "$*" >&2
}

classify_error() {
  local err_file=$1
  local message
  message=$(tr '\n' ' ' < "$err_file")

  case "$message" in
    *SAML*|*SSO*|*"single sign-on"*|*"organization has enabled or enforced SAML"*)
      warn "GitHub org SSO/SAML authorization may be required for this account."
      ;;
    *"Bad credentials"*|*"HTTP 401"*|*"not logged in"*|*"authentication required"*)
      warn "GitHub authentication failed. Run 'gh auth login' or refresh the token."
      ;;
    *"HTTP 403"*|*"Resource not accessible"*|*"insufficient"*|*"requires authentication"*)
      warn "GitHub access was forbidden. The account may lack repo access or required scopes."
      ;;
    *"HTTP 404"*|*"Could not resolve to a Repository"*|*"Not Found"*)
      warn "GitHub returned not found. For private repos this can mean missing repo access, SSO authorization, or a wrong repo/PR."
      ;;
    *)
      warn "GitHub command failed. Inspect the saved stderr file for details."
      ;;
  esac
}

require_gh() {
  command -v gh >/dev/null 2>&1 || die "GitHub CLI 'gh' is required."
}

parse_pr_ref() {
  local ref=$1

  if [[ "$ref" =~ ^https?://github\.com/([^/]+)/([^/]+)/pull/([0-9]+)(/.*)?$ ]]; then
    REPO="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
    PR_REF="${BASH_REMATCH[3]}"
    return
  fi

  if [[ "$ref" =~ ^git@github\.com:([^/]+)/([^/]+)\.git/pull/([0-9]+)$ ]]; then
    REPO="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
    PR_REF="${BASH_REMATCH[3]}"
    return
  fi

  if [[ "$ref" =~ ^([^/[:space:]]+)/([^#[:space:]]+)#([0-9]+)$ ]]; then
    REPO="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
    PR_REF="${BASH_REMATCH[3]}"
    return
  fi
}

run_capture() {
  local label=$1
  local out_file=$2
  local err_file=$3
  shift 3

  printf 'collecting %s...\n' "$label"
  if ! "$@" > "$out_file" 2> "$err_file"; then
    classify_error "$err_file"
    printf 'failed command:'
    printf ' %q' "$@"
    printf '\n'
    return 1
  fi
}

PR_REF=""
REPO=""
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    -R|--repo)
      [[ $# -ge 2 ]] || die "--repo requires OWNER/REPO"
      REPO=$2
      shift 2
      ;;
    --output-dir|-o)
      [[ $# -ge 2 ]] || die "--output-dir requires a directory"
      OUTPUT_DIR=$2
      shift 2
      ;;
    -*)
      die "unknown option: $1"
      ;;
    *)
      [[ -z "$PR_REF" ]] || die "only one PR_REF is supported"
      PR_REF=$1
      shift
      ;;
  esac
done

require_gh

if [[ -n "$PR_REF" ]]; then
  parse_pr_ref "$PR_REF"
fi

pr_args=()
if [[ -n "$PR_REF" ]]; then
  pr_args+=("$PR_REF")
fi
if [[ -n "$REPO" ]]; then
  pr_args+=("--repo" "$REPO")
fi

timestamp=$(date +%Y%m%d-%H%M%S)
safe_ref=${PR_REF:-current-branch}
safe_ref=${safe_ref//[^A-Za-z0-9._-]/-}
if [[ -z "$OUTPUT_DIR" ]]; then
  OUTPUT_DIR="/tmp/github-pr-review-${safe_ref}-${timestamp}"
fi
mkdir -p "$OUTPUT_DIR"

auth_file="$OUTPUT_DIR/auth.txt"
if gh auth status --hostname github.com >/dev/null 2>&1; then
  account=$(gh api user --jq .login 2>/dev/null || true)
  if [[ -n "$account" ]]; then
    printf 'authenticated_account=%s\n' "$account" > "$auth_file"
    printf 'GitHub auth: authenticated as @%s\n' "$account"
  else
    printf 'authenticated_account=unknown\n' > "$auth_file"
    warn "GitHub auth exists, but the account login could not be read."
  fi
else
  printf 'authenticated_account=\nstatus=not-authenticated\n' > "$auth_file"
  warn "GitHub CLI is not authenticated. Public PR reads may work, but posting reviews and private repos require 'gh auth login'."
fi

view_fields="number,title,body,state,isDraft,author,labels,baseRefName,headRefName,additions,deletions,changedFiles,files,commits,reviews,reviewRequests,reviewDecision,statusCheckRollup,url"

run_capture "PR metadata JSON" "$OUTPUT_DIR/pr-view.json" "$OUTPUT_DIR/pr-view.err" \
  gh pr view "${pr_args[@]}" --json "$view_fields"

run_capture "PR metadata text" "$OUTPUT_DIR/pr-view.txt" "$OUTPUT_DIR/pr-view-text.err" \
  gh pr view "${pr_args[@]}"

run_capture "changed files" "$OUTPUT_DIR/pr-files.txt" "$OUTPUT_DIR/pr-files.err" \
  gh pr diff "${pr_args[@]}" --name-only

run_capture "diff patch" "$OUTPUT_DIR/pr-diff.patch" "$OUTPUT_DIR/pr-diff.err" \
  gh pr diff "${pr_args[@]}"

if ! gh pr checks "${pr_args[@]}" > "$OUTPUT_DIR/pr-checks.txt" 2> "$OUTPUT_DIR/pr-checks.err"; then
  warn "PR checks were unavailable or failed; continuing with saved stderr."
fi

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git rev-parse --show-toplevel > "$OUTPUT_DIR/local-repo-root.txt" 2>/dev/null || true
  git status --short > "$OUTPUT_DIR/local-git-status.txt" 2>/dev/null || true
fi

resolved_url=$(gh pr view "${pr_args[@]}" --json url --jq .url 2>/dev/null || true)
{
  printf 'output_dir=%s\n' "$OUTPUT_DIR"
  printf 'repo=%s\n' "${REPO:-current-repository}"
  printf 'pr_ref=%s\n' "${PR_REF:-current-branch}"
  printf 'url=%s\n' "$resolved_url"
  printf 'created_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$OUTPUT_DIR/manifest.txt"

printf 'Context written to %s\n' "$OUTPUT_DIR"
