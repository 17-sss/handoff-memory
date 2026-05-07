#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  create_pr.sh --repo OWNER/REPO [options]

Options:
  -R, --repo OWNER/REPO       Target repository
  --base BRANCH              Base branch (default: repository default branch)
  --head OWNER:BRANCH        Explicit PR head. If omitted, derived from repo owner and current branch.
  --title TITLE              PR title
  --body TEXT                PR body text
  --body-file FILE           PR body file
  --fill                     Let gh fill title/body from commits
  --fill-first               Let gh fill from first commit
  --fill-verbose             Let gh fill with verbose commit content
  --template FILE            PR template file; requires a title or fill source
  --draft                    Create as draft
  --reviewer LOGIN           Add reviewer; repeatable
  --assignee LOGIN           Add assignee; repeatable
  --label NAME               Add label; repeatable
  --milestone NAME           Add milestone
  --project NAME             Add project; repeatable
  --web                      Open browser flow; requires --yes for actual open
  --push --remote NAME       Push HEAD:current-branch before creating; requires --yes
  --use-rest                 Use constrained REST fallback instead of gh pr create
  --yes                      Execute mutations after validation
  --preview                  Force preview mode (default)
  -h, --help                 Show this help

Default mode is preview and performs no push, PR creation, browser open, or
mutating API request.
USAGE
}

die() { printf 'error: %s\n' "$*" >&2; exit 1; }
warn() { printf 'warning: %s\n' "$*" >&2; }

print_command() {
  printf 'command:'
  printf ' %q' "$@"
  printf '\n'
}

print_sanitized_error_file() {
  sed -E 's/(Authorization:[[:space:]]*)([^[:space:]]+)/\1[REDACTED]/Ig; s/(token|GH_TOKEN|GITHUB_TOKEN|PAT)=([^[:space:]]+)/\1=[REDACTED]/Ig' "$1" >&2
}

classify_error_file() {
  local file=$1 message
  message=$(tr '\n' ' ' <"$file")
  case "$message" in
    *SAML*|*SSO*|*"single sign-on"*) warn "GitHub org SSO/SAML authorization may be required." ;;
    *"Bad credentials"*|*"HTTP 401"*|*"authentication required"*|*"not logged in"*) warn "GitHub authentication failed or is missing." ;;
    *"HTTP 403"*|*"Resource not accessible"*|*"insufficient"*) warn "GitHub access was forbidden; check repository access and pull request permissions." ;;
    *"HTTP 404"*|*"Could not resolve to a Repository"*|*"Not Found"*) warn "GitHub returned not found; for private repos this can mean missing access, SSO, or a wrong repo." ;;
    *"HTTP 422"*|*"Validation Failed"*) warn "GitHub validation failed; check base, head, duplicate PRs, and required fields." ;;
    *) warn "GitHub command failed; inspect stderr." ;;
  esac
}

require_tools() {
  command -v git >/dev/null 2>&1 || die "git is required"
  command -v gh >/dev/null 2>&1 || die "GitHub CLI 'gh' is required"
}

repo_owner() { printf '%s\n' "${1%%/*}"; }
branch_from_head() {
  local head=$1
  if [[ "$head" == *:* ]]; then
    printf '%s\n' "${head#*:}"
  else
    printf '%s\n' "$head"
  fi
}

owner_from_head() {
  local head=$1
  if [[ "$head" == *:* ]]; then
    printf '%s\n' "${head%%:*}"
  else
    printf '%s\n' ""
  fi
}

parse_github_remote() {
  local url=$1
  case "$url" in
    git@github.com:*.git) printf '%s\n' "${url#git@github.com:}" | sed 's/\.git$//' ;;
    https://github.com/*.git) printf '%s\n' "${url#https://github.com/}" | sed 's/\.git$//' ;;
    https://github.com/*) printf '%s\n' "${url#https://github.com/}" | sed 's/\.git$//' ;;
    *) printf '\n' ;;
  esac
}

current_branch() {
  git symbolic-ref --quiet --short HEAD 2>/dev/null || die "detached HEAD is not allowed"
}

ensure_safe_branch() {
  local branch=$1 base=$2 default_branch=$3
  [[ -n "$branch" ]] || die "head branch is empty"
  [[ "$branch" != "$base" ]] || die "refusing to push base branch '$branch'"
  [[ "$branch" != "$default_branch" ]] || die "refusing to push default branch '$branch'"
  case "$branch" in
    main|master|trunk) die "refusing to push protected-looking branch '$branch'" ;;
  esac
}

validate_content() {
  local has_title=0 has_body=0 has_fill=0
  [[ -n "$TITLE" ]] && has_title=1
  [[ -n "$BODY" || -n "$BODY_FILE" || -n "$TEMPLATE" ]] && has_body=1
  [[ "$FILL_MODE" != "" ]] && has_fill=1

  if [[ -n "$BODY_FILE" ]]; then
    [[ -f "$BODY_FILE" ]] || die "body file not found: $BODY_FILE"
    [[ -s "$BODY_FILE" ]] || die "body file is empty: $BODY_FILE"
  fi
  if [[ -n "$TEMPLATE" ]]; then
    [[ -f "$TEMPLATE" ]] || die "template file not found: $TEMPLATE"
    [[ $has_title -eq 1 || $has_fill -eq 1 ]] || die "--template requires --title or an explicit fill source"
  fi
  if [[ $has_fill -eq 1 ]]; then
    return
  fi
  [[ $has_title -eq 1 ]] || die "PR creation requires --title or an explicit fill source"
  [[ $has_body -eq 1 ]] || die "PR creation requires --body, --body-file, --template, or an explicit fill source"
}

validate_rest_content() {
  [[ -n "$TITLE" ]] || die "REST fallback requires explicit --title; fill modes cannot provide REST title fields"
  [[ -n "$BODY" || -n "$BODY_FILE" || -n "$TEMPLATE" ]] || die "REST fallback requires --body, --body-file, or --template"
}

verify_remote_matches_repo() {
  local remote=$1 repo=$2 url remote_repo
  url=$(git remote get-url "$remote" 2>/dev/null) || die "remote not found: $remote"
  remote_repo=$(parse_github_remote "$url")
  [[ -n "$remote_repo" ]] || die "remote '$remote' is not a github.com remote understood by this skill"
  [[ "$remote_repo" == "$repo" ]] || die "remote '$remote' points to '$remote_repo', not '$repo'; fork remotes are not supported"
}

remote_head_exists() {
  local remote=$1 branch=$2
  git ls-remote --exit-code "$remote" "refs/heads/$branch" >/dev/null 2>&1
}

REPO=""
BASE=""
HEAD=""
TITLE=""
BODY=""
BODY_FILE=""
TEMPLATE=""
FILL_MODE=""
DRAFT=0
WEB=0
PUSH=0
REMOTE=""
USE_REST=0
YES=0
PREVIEW=1
REVIEWERS=()
ASSIGNEES=()
LABELS=()
PROJECTS=()
MILESTONE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    -R|--repo) [[ $# -ge 2 ]] || die "--repo requires OWNER/REPO"; REPO=$2; shift 2 ;;
    --base) [[ $# -ge 2 ]] || die "--base requires a branch"; BASE=$2; shift 2 ;;
    --head) [[ $# -ge 2 ]] || die "--head requires OWNER:BRANCH"; HEAD=$2; shift 2 ;;
    --title) [[ $# -ge 2 ]] || die "--title requires text"; TITLE=$2; shift 2 ;;
    --body) [[ $# -ge 2 ]] || die "--body requires text"; BODY=$2; shift 2 ;;
    --body-file) [[ $# -ge 2 ]] || die "--body-file requires a file"; BODY_FILE=$2; shift 2 ;;
    --fill|--fill-first|--fill-verbose) FILL_MODE=$1; shift ;;
    --template) [[ $# -ge 2 ]] || die "--template requires a file"; TEMPLATE=$2; shift 2 ;;
    --draft) DRAFT=1; shift ;;
    --reviewer) [[ $# -ge 2 ]] || die "--reviewer requires a login"; REVIEWERS+=("$2"); shift 2 ;;
    --assignee) [[ $# -ge 2 ]] || die "--assignee requires a login"; ASSIGNEES+=("$2"); shift 2 ;;
    --label) [[ $# -ge 2 ]] || die "--label requires a name"; LABELS+=("$2"); shift 2 ;;
    --milestone) [[ $# -ge 2 ]] || die "--milestone requires a name"; MILESTONE=$2; shift 2 ;;
    --project) [[ $# -ge 2 ]] || die "--project requires a name"; PROJECTS+=("$2"); shift 2 ;;
    --web) WEB=1; shift ;;
    --push) PUSH=1; shift ;;
    --remote) [[ $# -ge 2 ]] || die "--remote requires a name"; REMOTE=$2; shift 2 ;;
    --use-rest) USE_REST=1; shift ;;
    --yes) YES=1; PREVIEW=0; shift ;;
    --preview) PREVIEW=1; YES=0; shift ;;
    -f) die "force-like push options are not supported" ;;
    *) die "unknown option: $1" ;;
  esac
done

require_tools
[[ -n "$REPO" ]] || die "--repo OWNER/REPO is required"
[[ "$REPO" == */* ]] || die "--repo must be OWNER/REPO"

if [[ -z "$BASE" ]]; then
  BASE=$(gh repo view "$REPO" --json defaultBranchRef --jq .defaultBranchRef.name 2>/dev/null || true)
  BASE=${BASE:-main}
fi
DEFAULT_BRANCH=$(gh repo view "$REPO" --json defaultBranchRef --jq .defaultBranchRef.name 2>/dev/null || true)
DEFAULT_BRANCH=${DEFAULT_BRANCH:-$BASE}

LOCAL_BRANCH=$(current_branch)
if [[ -z "$HEAD" ]]; then
  HEAD="$(repo_owner "$REPO"):$LOCAL_BRANCH"
fi
HEAD_BRANCH=$(branch_from_head "$HEAD")
HEAD_OWNER=$(owner_from_head "$HEAD")
[[ -n "$HEAD_OWNER" ]] || die "--head must include owner namespace, e.g. OWNER:branch"
[[ "$HEAD_OWNER" == "$(repo_owner "$REPO")" ]] || die "fork heads are not supported; head owner '$HEAD_OWNER' differs from repo owner '$(repo_owner "$REPO")'"

validate_content
if [[ $USE_REST -eq 1 ]]; then
  validate_rest_content
fi

if [[ $PUSH -eq 1 && -z "$REMOTE" ]]; then
  die "--push requires --remote <name>"
fi
if [[ $PUSH -eq 0 && -n "$REMOTE" ]]; then
  warn "--remote was provided without --push; it will be used for remote-head verification only"
fi
REMOTE=${REMOTE:-origin}
verify_remote_matches_repo "$REMOTE" "$REPO"
ensure_safe_branch "$LOCAL_BRANCH" "$BASE" "$DEFAULT_BRANCH"

printf 'State machine: preview -> validate -> optional guarded push -> create -> verify\n'
printf 'Mode: %s\n' "$([[ $YES -eq 1 ]] && printf execute || printf preview)"
printf 'Repository: %s\nBase: %s\nHead: %s\nRemote: %s\n' "$REPO" "$BASE" "$HEAD" "$REMOTE"

content_args=()
if [[ -n "$TITLE" ]]; then content_args+=(--title "$TITLE"); fi
if [[ -n "$BODY" ]]; then content_args+=(--body "$BODY"); fi
if [[ -n "$BODY_FILE" ]]; then content_args+=(--body-file "$BODY_FILE"); fi
if [[ -n "$FILL_MODE" ]]; then content_args+=("$FILL_MODE"); fi
if [[ -n "$TEMPLATE" ]]; then content_args+=(--template "$TEMPLATE"); fi

common_args=(--repo "$REPO" --base "$BASE" --head "$HEAD")
[[ $DRAFT -eq 1 ]] && common_args+=(--draft)
[[ $WEB -eq 1 ]] && common_args+=(--web)
if ((${#REVIEWERS[@]})); then for reviewer in "${REVIEWERS[@]}"; do common_args+=(--reviewer "$reviewer"); done; fi
if ((${#ASSIGNEES[@]})); then for assignee in "${ASSIGNEES[@]}"; do common_args+=(--assignee "$assignee"); done; fi
if ((${#LABELS[@]})); then for label in "${LABELS[@]}"; do common_args+=(--label "$label"); done; fi
if ((${#PROJECTS[@]})); then for project in "${PROJECTS[@]}"; do common_args+=(--project "$project"); done; fi
[[ -n "$MILESTONE" ]] && common_args+=(--milestone "$MILESTONE")

if [[ $PREVIEW -eq 1 ]]; then
  if [[ $PUSH -eq 1 ]]; then print_command git push "$REMOTE" "HEAD:$LOCAL_BRANCH"; fi
  if [[ $USE_REST -eq 1 ]]; then
    printf 'REST preview: POST /repos/%s/pulls with explicit head/base/title-or-issue after remote-head proof\n' "$REPO"
  else
    print_command gh pr create "${common_args[@]}" "${content_args[@]}"
  fi
  printf 'preview: no remote mutation performed\n'
  exit 0
fi

if ! gh auth status --hostname github.com >/dev/null 2>&1; then
  die "GitHub CLI is not authenticated. Run 'gh auth login' before creating a PR."
fi
ACCOUNT=$(gh api user --jq .login 2>/dev/null || true)
[[ -n "$ACCOUNT" ]] || die "could not determine authenticated GitHub account"
printf 'Authenticated GitHub account: @%s\n' "$ACCOUNT"

if [[ $PUSH -eq 1 ]]; then
  print_command git push "$REMOTE" "HEAD:$LOCAL_BRANCH"
  git push "$REMOTE" "HEAD:$LOCAL_BRANCH"
elif ! remote_head_exists "$REMOTE" "$HEAD_BRANCH"; then
  die "remote head '$HEAD_BRANCH' was not found on '$REMOTE'; use --push --remote $REMOTE --yes or push it yourself first"
fi

if [[ $USE_REST -eq 1 ]]; then
  remote_head_exists "$REMOTE" "$HEAD_BRANCH" || die "REST fallback requires an existing remote head"
  payload=$(mktemp)
  body_text=""
  if [[ -n "$BODY_FILE" ]]; then
    body_text=$(cat "$BODY_FILE")
  elif [[ -n "$BODY" ]]; then
    body_text=$BODY
  elif [[ -n "$TEMPLATE" ]]; then
    body_text=$(cat "$TEMPLATE")
  fi
  python3 - "$payload" "$TITLE" "$HEAD" "$BASE" "$body_text" "$DRAFT" <<'PY'
import json, sys
path, title, head, base, body, draft = sys.argv[1:]
obj = {"head": head, "base": base, "title": title, "body": body, "draft": draft == "1"}
with open(path, "w", encoding="utf-8") as f:
    json.dump(obj, f)
PY
  api_path="repos/$REPO/pulls"
  print_command gh api -i "$api_path" --method POST --input "$payload"
  err_file=$(mktemp)
  if ! response=$(gh api -i "$api_path" --method POST --input "$payload" 2>"$err_file"); then
    classify_error_file "$err_file"; print_sanitized_error_file "$err_file"; rm -f "$err_file" "$payload"; exit 1
  fi
  rm -f "$err_file" "$payload"
  printf '%s\n' "$response" | grep -Eq '(^HTTP/[0-9.]+ 201|^Status: 201)' || die "REST create did not return HTTP 201"
  url=$(printf '%s\n' "$response" | python3 -c 'import json,sys; s=sys.stdin.read(); i=s.find("{"); print(json.loads(s[i:]).get("html_url", "") if i >= 0 else "")')
  [[ -n "$url" ]] || die "REST create response did not include html_url"
else
  cmd=(gh pr create "${common_args[@]}" "${content_args[@]}")
  print_command "${cmd[@]}"
  err_file=$(mktemp)
  if ! url=$("${cmd[@]}" 2>"$err_file"); then
    classify_error_file "$err_file"; print_sanitized_error_file "$err_file"; rm -f "$err_file"; exit 1
  fi
  rm -f "$err_file"
  url=$(printf '%s\n' "$url" | tail -n 1)
fi

printf 'Pull request created as @%s: %s\n' "$ACCOUNT" "$url"
if [[ -n "$url" ]]; then
  gh pr view "$url" --json number,url,state,isDraft,headRefName,baseRefName,author || true
fi
