#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  collect_publish_context.sh [--repo OWNER/REPO] [--base BRANCH] [--output-dir DIR]

Collects sanitized GitHub PR publishing context: auth account, repository
metadata, remotes, branch state, default/base candidates, upstream status, and
existing PR hints. The script is read-only and never prints or stores tokens.
USAGE
}

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
warn() { printf 'warning: %s\n' "$*" >&2; }

sanitize_stream() {
  sed -E \
    -e 's/(Authorization:[[:space:]]*)([^[:space:]]+)/\1[REDACTED]/Ig' \
    -e 's/(token|GH_TOKEN|GITHUB_TOKEN|PAT)=([^[:space:]]+)/\1=[REDACTED]/Ig' \
    -e 's#https?://[^/@[:space:]]+(:[^/@[:space:]]+)?@#https://[REDACTED]@#g' \
    -e 's/(github_pat_|gh[pousr]_)[A-Za-z0-9_]+/\1[REDACTED]/g'
}

sanitize_file() {
  local file=$1 tmp_file
  [[ -f "$file" ]] || return 0
  tmp_file="${file}.sanitized.$$"
  if sanitize_stream <"$file" >"$tmp_file"; then
    mv "$tmp_file" "$file"
  else
    rm -f "$tmp_file"
  fi
}

prepare_output_dir() {
  local prefix=$1 safe_name=$2 timestamp=$3 tmp_parent
  umask 077
  if [[ -z "$OUTPUT_DIR" ]]; then
    tmp_parent=${TMPDIR:-/tmp}
    OUTPUT_DIR=$(mktemp -d "$tmp_parent/${prefix}-${safe_name}-${timestamp}.XXXXXX") \
      || die "failed to create private output directory"
  else
    [[ ! -L "$OUTPUT_DIR" ]] || die "output directory must not be a symlink: $OUTPUT_DIR"
    mkdir -p -m 700 "$OUTPUT_DIR"
    chmod 700 "$OUTPUT_DIR"
  fi
}

classify_error_text() {
  local message=$1
  case "$message" in
    *SAML*|*SSO*|*"single sign-on"*) warn "GitHub org SSO/SAML authorization may be required." ;;
    *"Bad credentials"*|*"HTTP 401"*|*"authentication required"*|*"not logged in"*) warn "GitHub authentication failed or is missing." ;;
    *"HTTP 403"*|*"Resource not accessible"*|*"insufficient"*) warn "GitHub access was forbidden; check repo access and pull request permissions." ;;
    *"HTTP 404"*|*"Could not resolve to a Repository"*|*"Not Found"*) warn "GitHub returned not found; for private repos this can mean missing access, SSO, or a wrong repo." ;;
    *"HTTP 422"*|*"Validation Failed"*) warn "GitHub validation failed; check base, head, duplicate PRs, and required fields." ;;
    *) warn "GitHub command failed; inspect the saved stderr file." ;;
  esac
}

run_capture() {
  local label=$1 out_file=$2 err_file=$3
  shift 3
  printf 'collecting %s...\n' "$label"
  if ! "$@" >"$out_file" 2>"$err_file"; then
    sanitize_file "$out_file"
    sanitize_file "$err_file"
    classify_error_text "$(tr '\n' ' ' <"$err_file")"
    return 1
  fi
  sanitize_file "$out_file"
  sanitize_file "$err_file"
}

REPO=""
BASE=""
OUTPUT_DIR=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    -R|--repo) [[ $# -ge 2 ]] || die "--repo requires OWNER/REPO"; REPO=$2; shift 2 ;;
    --base) [[ $# -ge 2 ]] || die "--base requires a branch"; BASE=$2; shift 2 ;;
    -o|--output-dir) [[ $# -ge 2 ]] || die "--output-dir requires a directory"; OUTPUT_DIR=$2; shift 2 ;;
    *) die "unknown argument: $1" ;;
  esac
done

command -v git >/dev/null 2>&1 || die "git is required"
command -v gh >/dev/null 2>&1 || die "GitHub CLI 'gh' is required"

timestamp=$(date +%Y%m%d-%H%M%S)
safe_repo=${REPO:-current-repo}
safe_repo=${safe_repo//[^A-Za-z0-9._-]/-}
prepare_output_dir "github-pr-publish" "$safe_repo" "$timestamp"

if gh auth status --hostname github.com >/dev/null 2>&1; then
  account=$(gh api user --jq .login 2>/dev/null || true)
  printf 'authenticated_account=%s\n' "${account:-unknown}" >"$OUTPUT_DIR/auth.txt"
  printf 'GitHub auth: authenticated as @%s\n' "${account:-unknown}"
else
  printf 'authenticated_account=\nstatus=not-authenticated\n' >"$OUTPUT_DIR/auth.txt"
  warn "GitHub CLI is not authenticated; private repos and PR creation require login."
fi

repo_args=()
if [[ -n "$REPO" ]]; then
  repo_args+=("$REPO")
fi

run_capture "repository metadata" "$OUTPUT_DIR/repo-view.json" "$OUTPUT_DIR/repo-view.err" \
  gh repo view "${repo_args[@]}" --json nameWithOwner,visibility,defaultBranchRef,url || true

if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  git rev-parse --show-toplevel >"$OUTPUT_DIR/local-repo-root.txt" 2>/dev/null || true
  git status --short >"$OUTPUT_DIR/local-git-status.txt" 2>/dev/null || true
  git branch --show-current >"$OUTPUT_DIR/current-branch.txt" 2>/dev/null || true
  git remote -v >"$OUTPUT_DIR/remotes.txt" 2>/dev/null || true
  git rev-parse --abbrev-ref --symbolic-full-name '@{u}' >"$OUTPUT_DIR/upstream.txt" 2>"$OUTPUT_DIR/upstream.err" || true
  git rev-list --left-right --count '@{u}...HEAD' >"$OUTPUT_DIR/ahead-behind.txt" 2>"$OUTPUT_DIR/ahead-behind.err" || true
  sanitize_file "$OUTPUT_DIR/remotes.txt"
  sanitize_file "$OUTPUT_DIR/upstream.err"
  sanitize_file "$OUTPUT_DIR/ahead-behind.err"
fi

if [[ -n "$REPO" ]]; then
  gh pr list --repo "$REPO" --head "$(git branch --show-current 2>/dev/null || true)" --json number,title,url,state \
    >"$OUTPUT_DIR/existing-prs.json" 2>"$OUTPUT_DIR/existing-prs.err" || true
  sanitize_file "$OUTPUT_DIR/existing-prs.json"
  sanitize_file "$OUTPUT_DIR/existing-prs.err"
else
  gh pr status >"$OUTPUT_DIR/pr-status.txt" 2>"$OUTPUT_DIR/pr-status.err" || true
  sanitize_file "$OUTPUT_DIR/pr-status.txt"
  sanitize_file "$OUTPUT_DIR/pr-status.err"
fi

{
  printf 'output_dir=%s\n' "$OUTPUT_DIR"
  printf 'repo=%s\n' "${REPO:-current-repository}"
  printf 'base=%s\n' "${BASE:-default-branch}"
  printf 'created_at=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} >"$OUTPUT_DIR/manifest.txt"

printf 'Context written to %s\n' "$OUTPUT_DIR"
