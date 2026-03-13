#!/usr/bin/env python3
"""Shared helpers for the handoff-memory skill."""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

REPO_HANDOFF_TEMPLATE = """# HANDOFF

## Metadata

- Project:
- Project ID:
- Repo Root:
- Branch:
- Last Updated:
- Updated By:

## TL;DR

- Summarize the current situation in 2-3 bullets.

## Current Objective

- State the immediate goal for the next session.

## Current State

- What is done:
- What is in progress:
- What still needs confirmation:

## Recent Changes

- Change:
- Validation:
- Impact:

## Known Issues / Watch List

- Issue:
- Risk:
- Workaround:

## Quick Reference

- Key files:
- Commands:
- Links / dashboards:

## Validation

- Checks run:
- Results:
- Not run yet:

## Next Actions

1. Put the first concrete next step here.
2. Add the second step only if it is already justified by the current state.

## Resume Checklist

- Re-open the files most relevant to the active task.
- Re-run the most relevant check before making more changes.
- Confirm the first next action still matches the repo state.

## Resume Prompt

Continue this project from the shared HANDOFF document. First verify the repo still matches the notes, then complete the first unfinished next action.
"""

WORKSPACE_HANDOFF_TEMPLATE = """# HANDOFF

## Metadata

- Workspace:
- Root:
- Last Updated:
- Updated By:

## TL;DR

- Summarize the cross-repo situation in 2-3 bullets.

## Current Objective

- State the shared goal for the next session.

## Current State

- What is stable:
- What is in progress:
- What still needs confirmation:

## Repo Impact

- Repositories involved:
- Cross-repo dependencies:
- Shared blockers:

## Recent Changes

- Change:
- Validation:
- Impact:

## Known Issues / Watch List

- Issue:
- Risk:
- Workaround:

## Quick Reference

- Key repositories:
- Shared commands:
- Dashboards / docs:

## Validation

- Checks run:
- Results:
- Not run yet:

## Next Actions

1. Put the first coordination step here.
2. Add the next step only if it is already justified by the current state.

## Resume Checklist

- Verify each impacted repo still matches the notes.
- Re-run the highest-signal shared check before editing further.
- Confirm the first next action still matches the workspace state.

## Resume Prompt

Continue this workspace from the shared HANDOFF document. First verify the involved repositories still match the notes, then complete the first unfinished next action.
"""

WORKSPACE_OVERVIEW_TEMPLATE = """# WORKSPACE

## Overview

- Workspace:
- Root:
- Purpose:

## Repositories

- Repo:
- Repo:

## Shared Commands

- Install:
- Dev:
- Test:

## Ownership / Boundaries

- Frontend:
- Backend:
- Infra:

## Environment Notes

- Shared services:
- Required tools:
- Local assumptions:
"""

WORKSPACE_DECISIONS_TEMPLATE = """# DECISIONS

## Decision Log

### YYYY-MM-DD - Title

- Status:
- Context:
- Decision:
- Consequences:
- Affected repositories:
"""

WORKSPACE_PATTERNS_TEMPLATE = """# PATTERNS

## Reusable Patterns

### Pattern Name

- Problem:
- Recommended approach:
- Example repositories:
- Notes:
"""

REPO_DOCUMENTS = {
    "handoff": (
        (Path("docs") / "HANDOFF.md", Path("memories") / "HANDOFF.md", Path("HANDOFF.md")),
        Path("docs") / "HANDOFF.md",
    ),
}

WORKSPACE_ROOT = Path("_memory")
SNAPSHOT_DIRNAME = "handoffs"
WORKSPACE_DOCUMENTS = {
    "handoff": (Path("HANDOFF.md"), WORKSPACE_HANDOFF_TEMPLATE),
    "workspace": (Path("WORKSPACE.md"), WORKSPACE_OVERVIEW_TEMPLATE),
    "decisions": (Path("DECISIONS.md"), WORKSPACE_DECISIONS_TEMPLATE),
    "patterns": (Path("PATTERNS.md"), WORKSPACE_PATTERNS_TEMPLATE),
}

SECTION_REQUIREMENTS = {
    ("repo", "handoff"): (
        "Metadata",
        "TL;DR",
        "Current Objective",
        "Current State",
        "Recent Changes",
        "Known Issues / Watch List",
        "Quick Reference",
        "Validation",
        "Next Actions",
        "Resume Checklist",
        "Resume Prompt",
    ),
    ("workspace", "handoff"): (
        "Metadata",
        "TL;DR",
        "Current Objective",
        "Current State",
        "Repo Impact",
        "Recent Changes",
        "Known Issues / Watch List",
        "Quick Reference",
        "Validation",
        "Next Actions",
        "Resume Checklist",
        "Resume Prompt",
    ),
    ("workspace", "workspace"): (
        "Overview",
        "Repositories",
        "Shared Commands",
        "Ownership / Boundaries",
        "Environment Notes",
    ),
    ("workspace", "decisions"): ("Decision Log",),
    ("workspace", "patterns"): ("Reusable Patterns",),
}

_EMPTY_METADATA_RE = re.compile(r"^(\s*-\s+[^:]+:\s*)$")
_REPO_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class Resolution:
    raw_project_root: Path
    project_root: Path
    scope: str
    detected_scope: str
    document: str
    handoff_path: Path
    resolution_source: str

    @property
    def exists(self) -> bool:
        return self.handoff_path.exists()

    def to_payload(self) -> dict[str, object]:
        return {
            "project_root": str(self.project_root),
            "scope": self.scope,
            "detected_scope": self.detected_scope,
            "document": self.document,
            "handoff_path": str(self.handoff_path),
            "resolution_source": self.resolution_source,
            "exists": self.exists,
        }


def run_git(project_root: Path, *args: str) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(project_root), *args],
            check=True,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    return result.stdout.strip() or None


def canonical_project_root(project_root: Path) -> Path:
    top_level = run_git(project_root, "rev-parse", "--show-toplevel")
    if top_level:
        return Path(top_level).resolve()
    return project_root.resolve()


def resolve_explicit_handoff_path(project_root: Path, handoff_path: str) -> Path:
    candidate = Path(handoff_path).expanduser()
    if candidate.is_absolute():
        return candidate.resolve()
    return (project_root / candidate).resolve()


def repository_children(project_root: Path) -> list[Path]:
    children: list[Path] = []
    for child in sorted(project_root.iterdir()):
        if child.name.startswith(".") or not child.is_dir():
            continue
        if (child / ".git").exists():
            children.append(child.resolve())
    return children


def detect_scope(project_root: Path) -> str:
    project_root = project_root.resolve()
    if run_git(project_root, "rev-parse", "--show-toplevel"):
        return "repo"
    if len(repository_children(project_root)) >= 2:
        return "workspace"
    if (project_root / WORKSPACE_ROOT).exists():
        return "workspace"
    return "repo"


def resolve_existing_repo_handoff_path(project_root: Path) -> tuple[Path, str]:
    recognized_paths, default_path = REPO_DOCUMENTS["handoff"]
    for relative_path in recognized_paths:
        candidate = project_root / relative_path
        if candidate.exists():
            return candidate.resolve(), "existing"
    return (project_root / default_path).resolve(), "default"


def resolve_workspace_document_path(project_root: Path, document: str) -> tuple[Path, str]:
    relative_name, _ = WORKSPACE_DOCUMENTS[document]
    candidate = project_root / WORKSPACE_ROOT / relative_name
    if candidate.exists():
        return candidate.resolve(), "existing"
    return candidate.resolve(), "default"


def resolve_document(
    raw_project_root: Path,
    scope: str = "auto",
    document: str = "handoff",
    handoff_path: str | None = None,
) -> Resolution:
    raw_project_root = raw_project_root.expanduser().resolve()
    detected_scope = detect_scope(raw_project_root)
    resolved_scope = detected_scope if scope == "auto" else scope
    project_root = (
        canonical_project_root(raw_project_root)
        if resolved_scope == "repo"
        else raw_project_root
    )

    if resolved_scope == "repo" and document != "handoff":
        raise ValueError("Repo scope only supports the handoff document.")

    if handoff_path:
        target = resolve_explicit_handoff_path(project_root, handoff_path)
        source = "explicit"
    elif resolved_scope == "workspace":
        target, source = resolve_workspace_document_path(project_root, document)
    else:
        target, source = resolve_existing_repo_handoff_path(project_root)

    return Resolution(
        raw_project_root=raw_project_root,
        project_root=project_root,
        scope=resolved_scope,
        detected_scope=detected_scope,
        document=document,
        handoff_path=target,
        resolution_source=source,
    )


def initial_content_for(scope: str, document: str) -> str:
    if scope == "workspace":
        return WORKSPACE_DOCUMENTS[document][1]
    return REPO_HANDOFF_TEMPLATE


def ensure_document(resolution: Resolution) -> bool:
    resolution.handoff_path.parent.mkdir(parents=True, exist_ok=True)
    if resolution.handoff_path.exists():
        return False
    resolution.handoff_path.write_text(
        initial_content_for(resolution.scope, resolution.document),
        encoding="utf-8",
    )
    return True


def current_branch(project_root: Path) -> str | None:
    branch = run_git(project_root, "rev-parse", "--abbrev-ref", "HEAD")
    if branch == "HEAD":
        return "detached"
    return branch


def normalize_remote_url(origin: str) -> str:
    normalized = origin.strip()
    normalized = normalized.removesuffix(".git")
    normalized = normalized.replace("git@github.com:", "github.com/")
    normalized = normalized.replace("ssh://git@github.com/", "github.com/")
    normalized = normalized.replace("https://", "")
    normalized = normalized.replace("http://", "")
    normalized = normalized.replace("/", "-")
    normalized = normalized.replace(":", "-")
    normalized = normalized.replace("_", "-")
    normalized = normalized.lower()
    normalized = re.sub(r"[^a-z0-9.-]+", "-", normalized)
    normalized = re.sub(r"-{2,}", "-", normalized).strip("-")
    return normalized


def project_identifier(project_root: Path) -> str:
    origin = run_git(project_root, "config", "--get", "remote.origin.url")
    if origin:
        return normalize_remote_url(origin)
    return project_root.name


def current_user() -> str:
    return (
        Path.home().name
        or subprocess.run(
            ["whoami"],
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip()
        or "unknown"
    )


def iso_timestamp(now: datetime | None = None) -> str:
    current = now or datetime.now(timezone.utc).astimezone()
    return current.replace(microsecond=0).isoformat()


def replace_metadata_fields(text: str, replacements: dict[str, str]) -> str:
    lines = text.splitlines()
    output: list[str] = []
    for line in lines:
        replaced = line
        for field, value in replacements.items():
            prefix = f"- {field}:"
            if replaced.startswith(prefix):
                replaced = f"{prefix} {value}"
                break
        output.append(replaced)
    suffix = "\n" if text.endswith("\n") else ""
    return "\n".join(output) + suffix


def sync_metadata(
    text: str,
    resolution: Resolution,
    updated_by: str | None = None,
    now: datetime | None = None,
) -> str:
    timestamp = iso_timestamp(now)
    actor = updated_by or current_user()
    if resolution.scope == "repo":
        replacements = {
            "Project": resolution.project_root.name,
            "Project ID": project_identifier(resolution.project_root),
            "Repo Root": str(resolution.project_root),
            "Branch": current_branch(resolution.project_root) or "unknown",
            "Last Updated": timestamp,
            "Updated By": actor,
        }
        return replace_metadata_fields(text, replacements)

    if resolution.document == "handoff":
        replacements = {
            "Workspace": resolution.project_root.name,
            "Root": str(resolution.project_root),
            "Last Updated": timestamp,
            "Updated By": actor,
        }
        return replace_metadata_fields(text, replacements)

    if resolution.document == "workspace":
        replacements = {
            "Workspace": resolution.project_root.name,
            "Root": str(resolution.project_root),
        }
        return replace_metadata_fields(text, replacements)

    return text


def snapshot_directory(resolution: Resolution) -> Path:
    if resolution.scope == "workspace":
        return resolution.project_root / WORKSPACE_ROOT / SNAPSHOT_DIRNAME
    return resolution.project_root / "docs" / SNAPSHOT_DIRNAME


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "handoff"


def create_snapshot(
    resolution: Resolution,
    source_text: str,
    label: str | None = None,
    now: datetime | None = None,
) -> Path:
    timestamp = (now or datetime.now()).strftime("%Y-%m-%d-%H%M%S")
    base_label = label or resolution.project_root.name
    snapshot_dir = snapshot_directory(resolution)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    candidate = snapshot_dir / f"{timestamp}-{slugify(base_label)}.md"
    index = 1
    while candidate.exists():
        candidate = snapshot_dir / f"{timestamp}-{slugify(base_label)}-{index}.md"
        index += 1
    candidate.write_text(source_text, encoding="utf-8")
    return candidate.resolve()


def extract_sections(text: str) -> list[str]:
    return _REPO_SECTION_RE.findall(text)


def required_sections(scope: str, document: str) -> tuple[str, ...]:
    return SECTION_REQUIREMENTS[(scope, document)]


def placeholder_lines(text: str) -> list[str]:
    placeholders: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if "YYYY-MM-DD" in stripped:
            placeholders.append(stripped)
            continue
        if stripped.startswith("- ") and _EMPTY_METADATA_RE.match(stripped):
            placeholders.append(stripped)
            continue
        if stripped in {
            "- Summarize the current situation in 2-3 bullets.",
            "- Summarize the cross-repo situation in 2-3 bullets.",
            "- State the immediate goal for the next session.",
            "- State the shared goal for the next session.",
            "- Repo:",
            "- Repo: Repo name",
            "- Change:",
            "- Validation:",
            "- Impact:",
            "- Issue:",
            "- Risk:",
            "- Workaround:",
            "- Key files:",
            "- Commands:",
            "- Links / dashboards:",
            "- Key repositories:",
            "- Shared commands:",
            "- Dashboards / docs:",
            "- What is done:",
            "- What is in progress:",
            "- What still needs confirmation:",
            "- What is stable:",
            "1. Put the first concrete next step here.",
            "1. Put the first coordination step here.",
            "2. Add the second step only if it is already justified by the current state.",
            "2. Add the next step only if it is already justified by the current state.",
            "- Re-open the files most relevant to the active task.",
            "- Re-run the most relevant check before making more changes.",
            "- Confirm the first next action still matches the repo state.",
            "- Verify each impacted repo still matches the notes.",
            "- Re-run the highest-signal shared check before editing further.",
            "- Confirm the first next action still matches the workspace state.",
        }:
            placeholders.append(stripped)
    return placeholders


def empty_sections(text: str, scope: str, document: str) -> list[str]:
    required = required_sections(scope, document)
    matches = list(_REPO_SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[start:end].strip()

    empty: list[str] = []
    for name in required:
        body = sections.get(name, "")
        if not body:
            empty.append(name)
            continue
        remaining_lines = [
            line.strip()
            for line in body.splitlines()
            if line.strip() and line.strip() not in placeholder_lines(body)
        ]
        if not remaining_lines:
            empty.append(name)
    return empty


def latest_commit_epoch(project_root: Path) -> int | None:
    value = run_git(project_root, "log", "-1", "--format=%ct")
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def dirty_paths(
    project_root: Path,
    ignore_paths: set[Path] | None = None,
) -> list[Path]:
    ignored = {path.resolve() for path in (ignore_paths or set())}
    commands = (
        ("diff", "--name-only"),
        ("diff", "--cached", "--name-only"),
        ("ls-files", "--others", "--exclude-standard"),
    )
    paths: set[Path] = set()
    for args in commands:
        output = run_git(project_root, *args)
        if not output:
            continue
        for raw in output.splitlines():
            candidate = (project_root / raw).resolve()
            if candidate in ignored:
                continue
            if any(parent in ignored for parent in candidate.parents):
                continue
            if candidate.exists():
                paths.add(candidate)
    return sorted(paths)


def latest_dirty_epoch(
    project_root: Path,
    ignore_paths: set[Path] | None = None,
) -> int | None:
    dirty = dirty_paths(project_root, ignore_paths=ignore_paths)
    if not dirty:
        return None
    return int(max(path.stat().st_mtime for path in dirty))


def repo_status(
    project_root: Path,
    ignore_paths: set[Path] | None = None,
) -> dict[str, object]:
    dirty = dirty_paths(project_root, ignore_paths=ignore_paths)
    return {
        "root": str(project_root),
        "branch": current_branch(project_root) or "unknown",
        "latest_commit_epoch": latest_commit_epoch(project_root),
        "dirty_paths_count": len(dirty),
        "latest_dirty_epoch": int(max(path.stat().st_mtime for path in dirty)) if dirty else None,
    }
