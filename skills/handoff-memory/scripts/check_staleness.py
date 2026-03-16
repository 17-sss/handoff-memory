#!/usr/bin/env python3
"""Check whether a handoff document is likely stale relative to current repo activity."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from handoff_lib import (
    DOCUMENT_CHOICES,
    infer_workstream_repositories,
    match_workspace_repositories,
    repo_status,
    repository_children,
    resolve_document,
    snapshot_directory,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check whether the canonical repo-local, workspace-wide, or workstream document is stale."
    )
    parser.add_argument("--project-root", default=".", help="Repository or workspace root.")
    parser.add_argument(
        "--scope",
        choices=("auto", "repo", "workspace"),
        default="auto",
        help="Memory scope. Defaults to auto.",
    )
    parser.add_argument(
        "--document",
        choices=DOCUMENT_CHOICES,
        default="handoff",
        help="Document type. Repo scope only supports handoff. Workstream-specific documents require --workstream.",
    )
    parser.add_argument(
        "--workstream",
        help="Optional workstream name for workspace tasks that should keep separate canonical documents under _memory/workstreams/<name>/.",
    )
    parser.add_argument(
        "--handoff-path",
        help="Explicit repo-local or absolute HANDOFF path. Relative paths are resolved from the project root.",
    )
    parser.add_argument(
        "--repository",
        action="append",
        default=[],
        help="Workspace repository name to evaluate for staleness. Repeat for multiple repositories.",
    )
    parser.add_argument(
        "--max-age-hours",
        type=float,
        help="Age threshold. Defaults to 72 hours for repos and 24 hours for workspaces.",
    )
    parser.add_argument(
        "--fail-if-stale",
        action="store_true",
        help="Return a non-zero exit code when the document is stale.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Defaults to text.",
    )
    return parser


def summarize_scope_status(
    resolution,
    repositories: list[Path],
) -> list[dict[str, object]]:
    ignore_paths = {resolution.handoff_path, snapshot_directory(resolution)}
    if resolution.target_scope == "workspace":
        repos = repositories or repository_children(resolution.project_root)
        return [repo_status(repo_root) for repo_root in repos]
    if resolution.target_scope == "workstream":
        return [repo_status(repo_root) for repo_root in repositories]
    return [repo_status(resolution.project_root, ignore_paths=ignore_paths)]


def latest_epoch(values: list[dict[str, object]], key: str) -> int | None:
    candidates = [value[key] for value in values if value.get(key) is not None]
    return max(candidates) if candidates else None


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        resolution = resolve_document(
            Path(args.project_root),
            scope=args.scope,
            document=args.document,
            handoff_path=args.handoff_path,
            workstream=args.workstream,
        )
    except ValueError as error:
        parser.error(str(error))

    default_age = 24.0 if resolution.scope == "workspace" else 72.0
    max_age_hours = args.max_age_hours if args.max_age_hours is not None else default_age
    reasons: list[str] = []
    warnings: list[str] = []

    if not resolution.handoff_path.exists():
        payload = {
            **resolution.to_payload(),
            "stale": True,
            "reasons": ["Document does not exist."],
        }
        if args.format == "json":
            json.dump(payload, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            print("Stale: document does not exist.")
        return 1 if args.fail_if_stale else 0

    handoff_epoch = resolution.handoff_path.stat().st_mtime
    now_epoch = datetime.now(timezone.utc).timestamp()
    age_hours = round((now_epoch - handoff_epoch) / 3600, 2)

    if age_hours > max_age_hours:
        reasons.append(
            f"Document is {age_hours} hours old, which exceeds the {max_age_hours}-hour threshold."
        )

    selected_repositories: list[Path] = []
    repo_selection_source: str | None = None
    if resolution.target_scope == "workstream":
        if args.repository:
            selected_repositories = match_workspace_repositories(
                resolution.project_root,
                args.repository,
            )
            repo_selection_source = "cli"
        else:
            selected_repositories, repo_selection_source = infer_workstream_repositories(
                resolution.project_root,
                resolution.workstream or "",
            )
        if not selected_repositories:
            warnings.append(
                "Workstream repositories are not declared; repo activity checks were skipped."
            )
    scope_status = summarize_scope_status(resolution, selected_repositories)
    latest_commit = latest_epoch(scope_status, "latest_commit_epoch")
    latest_dirty = latest_epoch(scope_status, "latest_dirty_epoch")
    dirty_repos = [status["root"] for status in scope_status if status["dirty_paths_count"]]

    if latest_commit and latest_commit > handoff_epoch:
        reasons.append("Repository history has moved forward since the handoff was last updated.")
    if latest_dirty and latest_dirty > handoff_epoch:
        reasons.append("There are uncommitted changes newer than the handoff.")
    if dirty_repos:
        reasons.append(f"Dirty repositories: {', '.join(dirty_repos)}")

    payload = {
        **resolution.to_payload(),
        "stale": bool(reasons),
        "age_hours": age_hours,
        "max_age_hours": max_age_hours,
        "latest_commit_epoch": latest_commit,
        "latest_dirty_epoch": latest_dirty,
        "dirty_repositories": dirty_repos,
        "selected_repositories": [str(path) for path in selected_repositories],
        "repo_selection_source": repo_selection_source,
        "scope_status": scope_status,
        "reasons": reasons,
        "warnings": warnings,
    }

    if args.format == "json":
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        if reasons:
            print("Stale")
            for reason in reasons:
                print(f"- {reason}")
        else:
            print("Fresh")
            print(f"- Age: {age_hours} hours")
        for warning in warnings:
            print(f"Warning: {warning}")

    return 1 if args.fail_if_stale and reasons else 0


if __name__ == "__main__":
    raise SystemExit(main())
