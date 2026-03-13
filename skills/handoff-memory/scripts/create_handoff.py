#!/usr/bin/env python3
"""Initialize or refresh the canonical handoff document."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from handoff_lib import (
    create_snapshot,
    ensure_document,
    resolve_document,
    sync_metadata,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Create or refresh a canonical repo-local or workspace-local handoff document."
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
        "--author",
        help="Optional value for the Updated By metadata field.",
    )
    parser.add_argument(
        "--snapshot",
        action="store_true",
        help="Write a timestamped snapshot before refreshing the canonical file. Intended for handoff documents.",
    )
    parser.add_argument(
        "--snapshot-label",
        help="Optional label used in the snapshot file name.",
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
        )
    except ValueError as error:
        parser.error(str(error))

    existed_before = resolution.handoff_path.exists()
    previous_text = (
        resolution.handoff_path.read_text(encoding="utf-8")
        if existed_before
        else ""
    )
    created = ensure_document(resolution)
    snapshot_path = None
    if args.snapshot:
        if args.document != "handoff":
            parser.error("--snapshot only supports --document handoff.")
        if existed_before and previous_text.strip():
            snapshot_path = create_snapshot(
                resolution,
                previous_text,
                label=args.snapshot_label,
            )

    updated_text = sync_metadata(
        previous_text or resolution.handoff_path.read_text(encoding="utf-8"),
        resolution,
        updated_by=args.author,
    )
    changed = updated_text != previous_text
    resolution.handoff_path.write_text(updated_text, encoding="utf-8")

    payload = {
        **resolution.to_payload(),
        "created": created,
        "updated": changed or created,
        "snapshot_path": str(snapshot_path) if snapshot_path else None,
    }

    if args.format == "json":
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(resolution.handoff_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
