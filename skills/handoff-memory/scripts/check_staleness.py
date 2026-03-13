#!/usr/bin/env python3
"""Check whether a handoff document is likely stale relative to current repo activity."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from handoff_lib import (
    repo_status,
    repository_children,
    resolve_document,
    snapshot_directory,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Check whether the canonical handoff document is stale."
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
        choices=("handoff", "workspace", "decisions", "patterns"),
        default="handoff",
        help="Document type. Repo scope only supports handoff.",
    )
    parser.add_argument(
        "--handoff-path",
        help="Explicit repo-local or absolute HANDOFF path. Relative paths are resolved from the project root.",
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
) -> list[dict[str, object]]:
    ignore_paths = {resolution.handoff_path, snapshot_directory(resolution)}
    project_root = resolution.project_root
    scope = resolution.scope
    if scope == "workspace":
        repos = repository_children(project_root)
        return [repo_status(repo_root) for repo_root in repos]
    return [repo_status(project_root, ignore_paths=ignore_paths)]


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
        )
    except ValueError as error:
        parser.error(str(error))

    default_age = 24.0 if resolution.scope == "workspace" else 72.0
    max_age_hours = args.max_age_hours if args.max_age_hours is not None else default_age
    reasons: list[str] = []

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

    scope_status = summarize_scope_status(resolution)
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
        "scope_status": scope_status,
        "reasons": reasons,
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

    return 1 if args.fail_if_stale and reasons else 0


if __name__ == "__main__":
    raise SystemExit(main())
