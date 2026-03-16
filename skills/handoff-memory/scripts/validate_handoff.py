#!/usr/bin/env python3
"""Validate a handoff-memory document for structure and obvious placeholders."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from handoff_lib import (
    DOCUMENT_CHOICES,
    empty_sections,
    extract_sections,
    placeholder_lines,
    required_sections,
    resolve_document,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a canonical repo-local, workspace-wide, or workstream document."
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
        "--format",
        choices=("text", "json"),
        default="text",
        help="Output format. Defaults to text.",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return a non-zero exit code when placeholders or empty sections are found.",
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

    if not resolution.handoff_path.exists():
        payload = {
            **resolution.to_payload(),
            "valid": False,
            "error": "Document does not exist.",
        }
        if args.format == "json":
            json.dump(payload, sys.stdout, indent=2)
            sys.stdout.write("\n")
        else:
            print("Missing document")
        return 1

    text = resolution.handoff_path.read_text(encoding="utf-8")
    sections = extract_sections(text)
    required = list(required_sections(resolution.target_scope, resolution.document))
    missing = [name for name in required if name not in sections]
    placeholders = placeholder_lines(text)
    empty = empty_sections(text, resolution.target_scope, resolution.document)
    warnings: list[str] = []
    if len(text.splitlines()) > 220:
        warnings.append("Document is longer than 220 lines; consider tightening it.")

    valid = not missing and (not args.strict or (not placeholders and not empty))
    payload = {
        **resolution.to_payload(),
        "valid": valid,
        "sections_found": sections,
        "required_sections": required,
        "missing_sections": missing,
        "empty_sections": empty,
        "placeholder_lines": placeholders,
        "warnings": warnings,
    }

    if args.format == "json":
        json.dump(payload, sys.stdout, indent=2)
        sys.stdout.write("\n")
    else:
        if valid:
            print("Valid")
        else:
            print("Invalid")
        if missing:
            print(f"Missing sections: {', '.join(missing)}")
        if empty:
            print(f"Empty sections: {', '.join(empty)}")
        if placeholders:
            print("Placeholder lines:")
            for line in placeholders:
                print(f"- {line}")
        for warning in warnings:
            print(f"Warning: {warning}")

    return 0 if valid else 1


if __name__ == "__main__":
    raise SystemExit(main())
