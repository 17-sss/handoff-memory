#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  post_review.sh PR_REF REVIEW_BODY_FILE [--repo OWNER/REPO] [--comment|--approve|--request-changes] [--dry-run]

PR_REF may be a PR URL, owner/repo#123, PR number, or branch understood by gh.
Default event is --comment. Approval and request-changes require explicit flags.
The script confirms the authenticated GitHub account before posting.
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
      warn "GitHub review posting failed. Inspect stderr for details."
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

  if [[ "$ref" =~ ^([^/[:space:]]+)/([^#[:space:]]+)#([0-9]+)$ ]]; then
    REPO="${BASH_REMATCH[1]}/${BASH_REMATCH[2]}"
    PR_REF="${BASH_REMATCH[3]}"
    return
  fi
}

print_command() {
  printf 'command:'
  printf ' %q' "$@"
  printf '\n'
}

PR_REF=""
REPO=""
EVENT="comment"
DRY_RUN=0
positionals=()

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
    --comment)
      EVENT="comment"
      shift
      ;;
    --approve)
      EVENT="approve"
      shift
      ;;
    --request-changes)
      EVENT="request-changes"
      shift
      ;;
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    -*)
      die "unknown option: $1"
      ;;
    *)
      positionals+=("$1")
      shift
      ;;
  esac
done

[[ ${#positionals[@]} -eq 2 ]] || die "expected PR_REF and REVIEW_BODY_FILE"

PR_REF=${positionals[0]}
BODY_FILE=${positionals[1]}

[[ -f "$BODY_FILE" ]] || die "review body file not found: $BODY_FILE"
[[ -s "$BODY_FILE" ]] || die "review body file is empty: $BODY_FILE"

parse_pr_ref "$PR_REF"

pr_args=()
if [[ -n "$PR_REF" ]]; then
  pr_args+=("$PR_REF")
fi
if [[ -n "$REPO" ]]; then
  pr_args+=("--repo" "$REPO")
fi

case "$EVENT" in
  comment)
    review_flag="--comment"
    ;;
  approve)
    review_flag="--approve"
    ;;
  request-changes)
    review_flag="--request-changes"
    ;;
  *)
    die "unsupported review event: $EVENT"
    ;;
esac

cmd=(gh pr review "${pr_args[@]}" "$review_flag" --body-file "$BODY_FILE")

if [[ "$DRY_RUN" -eq 1 ]] && ! command -v gh >/dev/null 2>&1; then
  warn "GitHub CLI 'gh' is not installed; dry-run only validates command construction."
  printf 'Review event: %s\n' "$EVENT"
  print_command "${cmd[@]}"
  printf 'dry-run: review was not posted\n'
  exit 0
fi

require_gh

if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  if [[ "$DRY_RUN" -eq 1 ]]; then
    warn "GitHub CLI is not authenticated. Actual posting requires 'gh auth login'."
    printf 'Review event: %s\n' "$EVENT"
    print_command "${cmd[@]}"
    printf 'dry-run: review was not posted\n'
    exit 0
  fi
  die "GitHub CLI is not authenticated. Run 'gh auth login' before posting a review."
fi

account=$(gh api user --jq .login 2>/dev/null || true)
[[ -n "$account" ]] || die "could not determine authenticated GitHub account"

printf 'Authenticated GitHub account: @%s\n' "$account"
printf 'Review event: %s\n' "$EVENT"
print_command "${cmd[@]}"

if [[ "$DRY_RUN" -eq 1 ]]; then
  printf 'dry-run: review was not posted\n'
  exit 0
fi

err_file=$(mktemp)
if ! "${cmd[@]}" 2> "$err_file"; then
  classify_error "$err_file"
  cat "$err_file" >&2
  rm -f "$err_file"
  exit 1
fi
rm -f "$err_file"
printf 'Review posted as @%s\n' "$account"
