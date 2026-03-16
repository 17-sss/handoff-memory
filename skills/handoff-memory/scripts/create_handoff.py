#!/usr/bin/env python3
"""Initialize or refresh the canonical handoff or memory document."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from handoff_lib import (
    DOCUMENT_CHOICES,
    SNAPSHOT_KINDS,
    create_snapshot,
    ensure_document,
    infer_workstream_repositories,
    replace_repositories_in_text,
    resolve_document,
    sync_metadata,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or refresh a canonical repo-local, workspace-wide, or workstream document."
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
        "--author",
        help="Optional value for the Updated By metadata field.",
    )
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Write a timestamped snapshot before refreshing the canonical file. Intended for handoff documents.",
    )
    parser.add_argument(
        "--snapshot-kind",
        choices=SNAPSHOT_KINDS,
        help="Why this snapshot exists. Required with --snapshot so snapshots stay intentional.",
    )
    parser.add_argument(
        "--snapshot-reason",
        help="Short explanation of why this snapshot is worth keeping.",
    )
    parser.add_argument(
        "--snapshot-label",
        help="Optional label used in the snapshot file name.",
    )
    parser.add_argument(
        "--repository",
        action="append",
        default=[],
        help="Workspace repository name to record in a workstream document. Repeat for multiple repositories.",
    )
    parser.add_argument(
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Defaults to text.",
    )
    return parser


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

    if args.snapshot and not args.snapshot_kind:
        parser.error("--snapshot requires --snapshot-kind.")
    if args.snapshot_reason and not args.snapshot:
        parser.error("--snapshot-reason requires --snapshot.")
    if args.snapshot_kind and not args.snapshot:
        parser.error("--snapshot-kind requires --snapshot.")

    existed_before = resolution.handoff_path.exists()
    previous_text = (
        resolution.handoff_path.read_text(encoding="utf-8")
        if existed_before
        else ""
    )
    created = ensure_document(resolution)
    snapshot_path = None
    snapshot_repositories = list(args.repository)
    if not snapshot_repositories:
        if resolution.target_scope == "repo":
            snapshot_repositories = [resolution.project_root.name]
        elif resolution.target_scope == "workstream" and resolution.workstream:
            inferred, _ = infer_workstream_repositories(
                resolution.project_root,
                resolution.workstream,
            )
            snapshot_repositories = [path.name for path in inferred]
    if args.snapshot:
        if args.document != "handoff":
            parser.error("--snapshot only supports --document handoff.")
        if existed_before and previous_text.strip():
            snapshot_path = create_snapshot(
                resolution,
                previous_text,
                label=args.snapshot_label,
                kind=args.snapshot_kind,
                reason=args.snapshot_reason,
                repositories=snapshot_repositories,
            )

    updated_text = sync_metadata(
        previous_text or resolution.handoff_path.read_text(encoding="utf-8"),
        resolution,
        updated_by=args.author,
    )
    updated_text = replace_repositories_in_text(
        updated_text,
        resolution,
        args.repository,
    )
    changed = updated_text != previous_text
    resolution.handoff_path.write_text(updated_text, encoding="utf-8")

    payload = {
        **resolution.to_payload(),
        "created": created,
        "updated": changed or created,
        "snapshot_path": str(snapshot_path) if snapshot_path else None,
        "snapshot_kind": args.snapshot_kind,
        "snapshot_reason": args.snapshot_reason,
        "repositories": args.repository,
        "snapshot_repositories": snapshot_repositories,
    }

    if args.format == "json":
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(resolution.handoff_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
