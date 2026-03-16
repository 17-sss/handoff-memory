#!/usr/bin/env python3
"""Resolve the canonical repo-local, workspace-wide, or workstream handoff path."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from handoff_lib import DOCUMENT_CHOICES, ensure_document, resolve_document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Resolve the canonical repo-local, workspace-wide, or workstream memory path."
    )
    parser.add_argument(
        "--project-root",
        default=".",
        help="Repository or project root used for detection. Defaults to the current directory.",
    )
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
        "--ensure",
        action="store_true",
        help="Create the file when missing.",
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

    if args.ensure:
        ensure_document(resolution)

    payload = resolution.to_payload()
    if args.format == "json":
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        print(resolution.handoff_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
