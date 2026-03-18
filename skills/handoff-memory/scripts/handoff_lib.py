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

1. Put the first concrete step the next session should execute here, not a broad exploration topic.
2. Add the second step only if it is already justified by the current state.

## Resume Checklist

- Re-open the files most relevant to the active task.
- Re-run the most relevant check before making more changes.
- Confirm the first next action still matches the repo state.

## Resume Prompt

Continue this project from the shared HANDOFF document. First verify the repo still matches the notes, then execute the first unfinished next action. Do not reopen already-settled design direction unless the user or current repo state invalidates it.
"""

WORKSPACE_HANDOFF_TEMPLATE = """# HANDOFF

## Metadata

- Workspace:
- Root:
- Last Updated:
- Updated By:

## Active Workstreams

- Workstream:
- Status:
- Repositories:

## Current Coordination State

- What is stable:
- What is in progress:
- What needs handoff:

## Shared Watch List

- Issue:
- Risk:
- Owner:

## Quick Reference

- Key repositories:
- Shared commands:
- Dashboards / docs:

## Next Actions

1. Put the first coordination step the next session should execute here, not a brainstorming prompt.
2. Add the next step only if it is already justified by the current state.

## Resume Prompt

Continue this workspace from the shared HANDOFF document. First identify the active workstream or active repo set, then verify only those related repositories before editing. After verification, execute the first unfinished next action instead of reopening already-settled direction unless the user or repo state invalidates it. Use a workspace-wide scan only when the task truly spans the whole workspace.
"""

WORKSTREAM_HANDOFF_TEMPLATE = """# HANDOFF

## Metadata

- Workspace:
- Workstream:
- Root:
- Workstream Root:
- Last Updated:
- Updated By:

## TL;DR

- Summarize the workstream state in 2-3 bullets.

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

1. Put the first coordination step the next session should execute here, not a brainstorming prompt.
2. Add the next step only if it is already justified by the current state.

## Resume Checklist

- Verify each impacted repo still matches the notes.
- Re-run the highest-signal shared check before editing further.
- Confirm the first next action still matches the workstream state.

## Resume Prompt

Continue this workstream from the shared HANDOFF document. First verify the involved repositories still match the notes, then execute the first unfinished next action. Do not reopen already-settled design direction unless the user or current repo state invalidates it.
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

WORKSTREAM_OVERVIEW_TEMPLATE = """# WORKSTREAM

## Overview

- Workstream:
- Workspace Root:
- Workstream Root:
- Purpose:

## Repositories

- Repo:
- Repo:

## Shared Goal

- Outcome:
- Non-goals:

## Ownership / Boundaries

- Primary owner:
- Repo boundaries:

## Entry Points / Commands

- Key paths:
- Commands:

## Notes

- Constraints:
- Coordination notes:
"""

DECISIONS_TEMPLATE = """# DECISIONS

## Decision Log

### YYYY-MM-DD - Title

- Status:
- Context:
- Decision:
- Consequences:
- Affected repositories:
"""

PATTERNS_TEMPLATE = """# PATTERNS

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
WORKSTREAMS_ROOT = WORKSPACE_ROOT / "workstreams"
SNAPSHOT_DIRNAME = "handoffs"
SNAPSHOT_KINDS = (
    "handoff",
    "risk",
    "deploy",
    "migration",
    "debug",
    "decision",
    "milestone",
    "other",
)
WORKSPACE_DOCUMENTS = {
    "handoff": (Path("HANDOFF.md"), WORKSPACE_HANDOFF_TEMPLATE),
    "workspace": (Path("WORKSPACE.md"), WORKSPACE_OVERVIEW_TEMPLATE),
    "decisions": (Path("DECISIONS.md"), DECISIONS_TEMPLATE),
    "patterns": (Path("PATTERNS.md"), PATTERNS_TEMPLATE),
}
WORKSTREAM_DOCUMENTS = {
    "handoff": (Path("HANDOFF.md"), WORKSTREAM_HANDOFF_TEMPLATE),
    "workstream": (Path("WORKSTREAM.md"), WORKSTREAM_OVERVIEW_TEMPLATE),
    "decisions": (Path("DECISIONS.md"), DECISIONS_TEMPLATE),
    "patterns": (Path("PATTERNS.md"), PATTERNS_TEMPLATE),
}
DOCUMENT_CHOICES = ("handoff", "workspace", "workstream", "decisions", "patterns")

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
        "Active Workstreams",
        "Current Coordination State",
        "Shared Watch List",
        "Quick Reference",
        "Next Actions",
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
    ("workstream", "handoff"): (
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
    ("workstream", "workstream"): (
        "Overview",
        "Repositories",
        "Shared Goal",
        "Ownership / Boundaries",
        "Entry Points / Commands",
        "Notes",
    ),
    ("workstream", "decisions"): ("Decision Log",),
    ("workstream", "patterns"): ("Reusable Patterns",),
}

_EMPTY_METADATA_RE = re.compile(r"^(\s*-\s+[^:]+:\s*)$")
_SECTION_RE = re.compile(r"^##\s+(.+?)\s*$", re.MULTILINE)
_WORKSTREAM_LINE_RE = re.compile(r"^- Workstream:\s*(.+?)\s*$", re.MULTILINE)
_REPO_LINE_RE = re.compile(r"^- Repo:\s*(.+?)\s*$", re.MULTILINE)
_INVOLVED_REPOS_RE = re.compile(r"^- Repositories involved:\s*(.+?)\s*$", re.MULTILINE)
_KEY_REPOSITORIES_RE = re.compile(r"^- Key repositories:\s*(.+?)\s*$", re.MULTILINE)
_PLACEHOLDER_VALUES = {
    "",
    "repo",
    "repositories",
    "repositories involved",
    "key repositories",
    "workstream",
    "status",
}


@dataclass(frozen=True)
class Resolution:
    raw_project_root: Path
    project_root: Path
    scope: str
    detected_scope: str
    document: str
    handoff_path: Path
    resolution_source: str
    workstream: str | None = None
    workstream_slug: str | None = None

    @property
    def exists(self) -> bool:
        return self.handoff_path.exists()

    @property
    def target_scope(self) -> str:
        if self.scope == "workspace" and self.workstream:
            return "workstream"
        return self.scope

    @property
    def workstream_root(self) -> Path | None:
        if not self.workstream_slug:
            return None
        return (self.project_root / WORKSTREAMS_ROOT / self.workstream_slug).resolve()

    def to_payload(self) -> dict[str, object]:
        return {
            "project_root": str(self.project_root),
            "scope": self.scope,
            "target_scope": self.target_scope,
            "detected_scope": self.detected_scope,
            "document": self.document,
            "handoff_path": str(self.handoff_path),
            "resolution_source": self.resolution_source,
            "exists": self.exists,
            "workstream": self.workstream,
            "workstream_slug": self.workstream_slug,
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


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-").lower()
    return slug or "handoff"


def workstream_slug(value: str) -> str:
    return slugify(value)


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


def workstream_directory(project_root: Path, workstream_name: str) -> Path:
    return (project_root / WORKSTREAMS_ROOT / workstream_slug(workstream_name)).resolve()


def resolve_workspace_document_path(project_root: Path, document: str) -> tuple[Path, str]:
    relative_name, _ = WORKSPACE_DOCUMENTS[document]
    candidate = project_root / WORKSPACE_ROOT / relative_name
    if candidate.exists():
        return candidate.resolve(), "existing"
    return candidate.resolve(), "default"


def resolve_workstream_document_path(
    project_root: Path,
    workstream_name: str,
    document: str,
) -> tuple[Path, str]:
    relative_name, _ = WORKSTREAM_DOCUMENTS[document]
    candidate = workstream_directory(project_root, workstream_name) / relative_name
    if candidate.exists():
        return candidate.resolve(), "existing"
    return candidate.resolve(), "default"


def resolve_document(
    raw_project_root: Path,
    scope: str = "auto",
    document: str = "handoff",
    handoff_path: str | None = None,
    workstream: str | None = None,
) -> Resolution:
    raw_project_root = raw_project_root.expanduser().resolve()
    detected_scope = detect_scope(raw_project_root)
    resolved_scope = detected_scope if scope == "auto" else scope
    project_root = (
        canonical_project_root(raw_project_root)
        if resolved_scope == "repo"
        else raw_project_root
    )

    if resolved_scope == "repo":
        if workstream:
            raise ValueError("Repo scope does not support --workstream.")
        if document != "handoff":
            raise ValueError("Repo scope only supports the handoff document.")

    if resolved_scope == "workspace" and workstream and document == "workspace":
        raise ValueError("Use --document workstream for workstream-scoped overview files.")

    if handoff_path:
        target = resolve_explicit_handoff_path(project_root, handoff_path)
        source = "explicit"
    elif resolved_scope == "workspace" and workstream:
        if document not in WORKSTREAM_DOCUMENTS:
            raise ValueError(f"Document {document!r} does not support --workstream.")
        target, source = resolve_workstream_document_path(project_root, workstream, document)
    elif resolved_scope == "workspace":
        if document not in WORKSPACE_DOCUMENTS:
            raise ValueError(f"Document {document!r} requires --workstream.")
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
        workstream=workstream,
        workstream_slug=workstream_slug(workstream) if workstream else None,
    )


def initial_content_for(resolution: Resolution) -> str:
    if resolution.target_scope == "repo":
        return REPO_HANDOFF_TEMPLATE
    if resolution.target_scope == "workspace":
        return WORKSPACE_DOCUMENTS[resolution.document][1]
    return WORKSTREAM_DOCUMENTS[resolution.document][1]


def ensure_document(resolution: Resolution) -> bool:
    resolution.handoff_path.parent.mkdir(parents=True, exist_ok=True)
    if resolution.handoff_path.exists():
        return False
    resolution.handoff_path.write_text(
        initial_content_for(resolution),
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


def extract_sections(text: str) -> list[str]:
    return _SECTION_RE.findall(text)


def section_bodies(text: str) -> dict[str, str]:
    matches = list(_SECTION_RE.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1).strip()] = text[start:end]
    return sections


def replace_section_body(text: str, section_name: str, body_lines: list[str]) -> str:
    matches = list(_SECTION_RE.finditer(text))
    for index, match in enumerate(matches):
        if match.group(1).strip() != section_name:
            continue
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        replacement = "\n\n" + "\n".join(body_lines).rstrip() + "\n"
        return text[:start] + replacement + text[end:]
    return text


def replace_repositories_in_text(
    text: str,
    resolution: Resolution,
    repositories: list[str] | None,
) -> str:
    if not repositories:
        return text
    if resolution.document in {"workspace", "workstream"}:
        return replace_section_body(
            text,
            "Repositories",
            [f"- Repo: {repo}" for repo in repositories],
        )
    if resolution.document == "handoff" and resolution.target_scope == "workstream":
        return replace_metadata_fields(
            text,
            {"Repositories involved": ", ".join(repositories)},
        )
    return text


def sync_metadata(
    text: str,
    resolution: Resolution,
    updated_by: str | None = None,
    now: datetime | None = None,
) -> str:
    timestamp = iso_timestamp(now)
    actor = updated_by or current_user()
    if resolution.target_scope == "repo":
        replacements = {
            "Project": resolution.project_root.name,
            "Project ID": project_identifier(resolution.project_root),
            "Repo Root": str(resolution.project_root),
            "Branch": current_branch(resolution.project_root) or "unknown",
            "Last Updated": timestamp,
            "Updated By": actor,
        }
        return replace_metadata_fields(text, replacements)

    if resolution.target_scope == "workspace":
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

    replacements = {
        "Workspace": resolution.project_root.name,
        "Workstream": resolution.workstream or "",
        "Root": str(resolution.project_root),
        "Workstream Root": str(resolution.workstream_root) if resolution.workstream_root else "",
    }
    if resolution.document == "handoff":
        replacements.update(
            {
                "Last Updated": timestamp,
                "Updated By": actor,
            }
        )
    return replace_metadata_fields(text, replacements)


def snapshot_directory(resolution: Resolution) -> Path:
    if resolution.target_scope == "repo":
        return resolution.project_root / "docs" / SNAPSHOT_DIRNAME
    if resolution.target_scope == "workspace":
        return resolution.project_root / WORKSPACE_ROOT / SNAPSHOT_DIRNAME
    assert resolution.workstream_root is not None
    return resolution.workstream_root / SNAPSHOT_DIRNAME


def create_snapshot(
    resolution: Resolution,
    source_text: str,
    label: str | None = None,
    kind: str = "handoff",
    reason: str | None = None,
    repositories: list[str] | None = None,
    now: datetime | None = None,
) -> Path:
    timestamp = (now or datetime.now()).strftime("%Y-%m-%d-%H%M%S")
    base_label = label or resolution.workstream or resolution.project_root.name
    snapshot_dir = snapshot_directory(resolution)
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    candidate = snapshot_dir / f"{timestamp}-{slugify(kind)}-{slugify(base_label)}.md"
    index = 1
    while candidate.exists():
        candidate = snapshot_dir / f"{timestamp}-{slugify(kind)}-{slugify(base_label)}-{index}.md"
        index += 1
    created_at = iso_timestamp(now)
    repo_text = ", ".join(repositories or []) or "n/a"
    metadata_lines = [
        "# SNAPSHOT METADATA",
        "",
        f"- Created At: {created_at}",
        f"- Scope: {resolution.target_scope}",
        f"- Kind: {kind}",
        f"- Source Canonical: {resolution.handoff_path}",
        f"- Workspace: {resolution.project_root.name if resolution.target_scope != 'repo' else 'n/a'}",
        f"- Workstream: {resolution.workstream or 'n/a'}",
        f"- Repositories: {repo_text}",
        f"- Reason: {reason or 'checkpoint'}",
        "",
        "---",
        "",
    ]
    candidate.write_text("\n".join(metadata_lines) + source_text, encoding="utf-8")
    return candidate.resolve()


def required_sections(target_scope: str, document: str) -> tuple[str, ...]:
    return SECTION_REQUIREMENTS[(target_scope, document)]


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
            "- Summarize the workstream state in 2-3 bullets.",
            "- State the immediate goal for the next session.",
            "- State the shared goal for the next session.",
            "- Workstream:",
            "- Status:",
            "- Repositories:",
            "- Issue:",
            "- Risk:",
            "- Owner:",
            "- What is stable:",
            "- What is in progress:",
            "- What needs handoff:",
            "- What is done:",
            "- What still needs confirmation:",
            "- Repositories involved:",
            "- Cross-repo dependencies:",
            "- Shared blockers:",
            "- Change:",
            "- Validation:",
            "- Impact:",
            "- Workaround:",
            "- Key files:",
            "- Commands:",
            "- Links / dashboards:",
            "- Key repositories:",
            "- Shared commands:",
            "- Dashboards / docs:",
            "- Checks run:",
            "- Results:",
            "- Not run yet:",
            "- Repo:",
            "- Outcome:",
            "- Non-goals:",
            "- Primary owner:",
            "- Repo boundaries:",
            "- Key paths:",
            "- Constraints:",
            "- Coordination notes:",
            "1. Put the first coordination step here.",
            "1. Put the first concrete next step here.",
            "2. Add the next step only if it is already justified by the current state.",
            "2. Add the second step only if it is already justified by the current state.",
            "- Re-open the files most relevant to the active task.",
            "- Re-run the most relevant check before making more changes.",
            "- Confirm the first next action still matches the repo state.",
            "- Verify each impacted repo still matches the notes.",
            "- Re-run the highest-signal shared check before editing further.",
            "- Confirm the first next action still matches the workstream state.",
        }:
            placeholders.append(stripped)
    return placeholders


def empty_sections(text: str, target_scope: str, document: str) -> list[str]:
    required = required_sections(target_scope, document)
    sections = section_bodies(text)
    placeholders = set(placeholder_lines(text))
    empty: list[str] = []
    for name in required:
        body = sections.get(name, "")
        if not body.strip():
            empty.append(name)
            continue
        remaining_lines = [
            line.strip()
            for line in body.splitlines()
            if line.strip() and line.strip() not in placeholders
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


def repositories_from_overview_text(text: str) -> list[str]:
    sections = section_bodies(text)
    repo_section = sections.get("Repositories", "")
    names = [match.group(1).strip() for match in _REPO_LINE_RE.finditer(repo_section)]
    return [name for name in names if name and name.lower() != "repo"]


def repositories_from_handoff_text(text: str) -> list[str]:
    match = _INVOLVED_REPOS_RE.search(text)
    if not match:
        return []
    return split_repository_names(match.group(1))


def split_repository_names(raw: str) -> list[str]:
    value = raw.strip()
    if not value or value.lower() in _PLACEHOLDER_VALUES:
        return []
    parts = [part.strip(" `") for part in value.split(",")]
    return [part for part in parts if part and part.lower() not in _PLACEHOLDER_VALUES]


def workspace_workstreams_from_handoff_text(text: str) -> list[dict[str, object]]:
    sections = section_bodies(text)
    body = sections.get("Active Workstreams", "")
    if not body:
        return []

    entries: list[dict[str, object]] = []
    current: dict[str, object] | None = None
    for raw_line in body.splitlines():
        line = raw_line.strip()
        if line.startswith("- Workstream:"):
            if current and current.get("name"):
                entries.append(current)
            current = {
                "name": line.split(":", 1)[1].strip(),
                "status": "",
                "repositories": [],
            }
        elif current and line.startswith("- Status:"):
            current["status"] = line.split(":", 1)[1].strip()
        elif current and line.startswith("- Repositories:"):
            current["repositories"] = split_repository_names(line.split(":", 1)[1])
    if current and current.get("name"):
        entries.append(current)

    cleaned: list[dict[str, object]] = []
    for entry in entries:
        name = str(entry.get("name", "")).strip()
        if not name or name.lower() in _PLACEHOLDER_VALUES:
            continue
        cleaned.append(
            {
                "name": name,
                "status": str(entry.get("status", "")).strip(),
                "repositories": list(entry.get("repositories", [])),
            }
        )
    return cleaned


def infer_active_workspace_workstream(text: str) -> str | None:
    entries = workspace_workstreams_from_handoff_text(text)
    if not entries:
        return None

    active_keywords = ("active", "in progress", "ongoing", "current", "working", "open")
    active = [
        str(entry["name"])
        for entry in entries
        if any(keyword in str(entry["status"]).lower() for keyword in active_keywords)
    ]
    if len(active) == 1:
        return active[0]

    if len(entries) == 1:
        return str(entries[0]["name"])

    return None


def key_repositories_from_workspace_handoff_text(text: str) -> list[str]:
    sections = section_bodies(text)
    body = sections.get("Quick Reference", "")
    if not body:
        return []
    match = _KEY_REPOSITORIES_RE.search(body)
    if not match:
        return []
    return split_repository_names(match.group(1))


def workspace_repository_map(project_root: Path) -> dict[str, Path]:
    repos = repository_children(project_root)
    mapping: dict[str, Path] = {}
    for repo in repos:
        mapping[repo.name.lower()] = repo
        mapping[str(repo).lower()] = repo
        mapping[str(repo.relative_to(project_root)).lower()] = repo
    return mapping


def match_workspace_repositories(project_root: Path, names: list[str]) -> list[Path]:
    mapping = workspace_repository_map(project_root)
    matched: list[Path] = []
    for raw_name in names:
        candidate = raw_name.strip()
        if not candidate:
            continue
        path = mapping.get(candidate.lower())
        if path is None:
            path = mapping.get(Path(candidate).name.lower())
        if path and path not in matched:
            matched.append(path)
    return matched


def workstream_supporting_paths(project_root: Path, workstream_name: str) -> dict[str, Path]:
    root = workstream_directory(project_root, workstream_name)
    return {
        "workstream": root / "WORKSTREAM.md",
        "handoff": root / "HANDOFF.md",
        "decisions": root / "DECISIONS.md",
        "patterns": root / "PATTERNS.md",
    }


def infer_workstream_repositories(
    project_root: Path,
    workstream_name: str,
) -> tuple[list[Path], str | None]:
    paths = workstream_supporting_paths(project_root, workstream_name)
    overview_path = paths["workstream"]
    if overview_path.exists():
        names = repositories_from_overview_text(overview_path.read_text(encoding="utf-8"))
        matched = match_workspace_repositories(project_root, names)
        if matched:
            return matched, "workstream-overview"

    handoff_path = paths["handoff"]
    if handoff_path.exists():
        names = repositories_from_handoff_text(handoff_path.read_text(encoding="utf-8"))
        matched = match_workspace_repositories(project_root, names)
        if matched:
            return matched, "workstream-handoff"

    return [], None


def infer_workspace_repositories(
    project_root: Path,
) -> tuple[list[Path], str | None, str | None]:
    handoff_path = project_root / WORKSPACE_ROOT / "HANDOFF.md"
    if not handoff_path.exists():
        return [], None, None

    text = handoff_path.read_text(encoding="utf-8")
    active_workstream = infer_active_workspace_workstream(text)
    if active_workstream:
        matched, source = infer_workstream_repositories(project_root, active_workstream)
        if matched:
            return matched, source or "workspace-active-workstream", active_workstream

        entries = workspace_workstreams_from_handoff_text(text)
        for entry in entries:
            if entry["name"] != active_workstream:
                continue
            matched = match_workspace_repositories(
                project_root,
                list(entry.get("repositories", [])),
            )
            if matched:
                return matched, "workspace-active-workstream", active_workstream

    key_repositories = key_repositories_from_workspace_handoff_text(text)
    if key_repositories:
        matched = match_workspace_repositories(project_root, key_repositories)
        if matched:
            return matched, "workspace-key-repositories", active_workstream

    entries = workspace_workstreams_from_handoff_text(text)
    if len(entries) == 1:
        matched = match_workspace_repositories(
            project_root,
            list(entries[0].get("repositories", [])),
        )
        if matched:
            return matched, "workspace-single-workstream", str(entries[0]["name"])

    return [], None, active_workstream
