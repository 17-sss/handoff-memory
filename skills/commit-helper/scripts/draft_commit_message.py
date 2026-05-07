#!/usr/bin/env python3
"""Draft repo-aligned commit messages from structured inspect output."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

from inspect_commit_style import inspect_repo

EXTERNAL_HARNESS_POLICY = (
    'commit-helper-only: do not add orchestration metadata, Lore trailers, '
    'workflow notes, or automation co-author trailers unless repo-local rules '
    'or the user explicitly require them.'
)
EXTERNAL_HARNESS_TRAILER_PATTERNS = (
    'Co-authored-by: OmX <omx@oh-my-codex.dev>',
    'Constraint:',
    'Rejected:',
    'Confidence:',
    'Scope-risk:',
    'Directive:',
    'Tested:',
    'Not-tested:',
)

CONVENTIONAL_TYPE_BY_SEMANTIC = {
    'feature': 'feat',
    'bugfix': 'fix',
    'critical-bug': 'fix',
    'refactor': 'refactor',
    'structure': 'chore',
    'move': 'chore',
    'ui-style': 'style',
    'responsive': 'style',
    'accessibility': 'feat',
    'docs': 'docs',
    'config': 'chore',
    'tooling': 'chore',
    'cleanup': 'chore',
    'modify': 'chore',
}
KOREAN_ACTION_TERMS = (
    '추가',
    '수정',
    '정리',
    '분리',
    '적용',
    '제거',
    '완화',
    '노출',
    '조정',
    '개선',
    '이동',
    '변경',
    '연결',
    '지원',
    '처리',
)
KOREAN_REPORT_LIKE_REWRITES = (
    (r'\s*(?:을|를)\s+위한\s+', ' ', 'removed verbose "…을/를 위한" phrasing'),
    (r'\s*에\s+대한\s+', ' ', 'removed verbose "…에 대한" phrasing'),
    (r'\s*관련\s+', ' ', 'removed generic "관련" filler'),
    (r'\s*(?:을|를)\s+수행하도록\s+수정$', ' 수정', 'shortened "…수행하도록 수정" to a direct action noun'),
    (r'\s+할\s+수\s+있도록\s+', ' ', 'shortened "…할 수 있도록" phrasing'),
    (r'\s+되도록\s+', ' ', 'shortened "…되도록" phrasing'),
    (r'\s+하도록\s+', ' ', 'shortened "…하도록" phrasing'),
)
KOREAN_ACTION_PATTERN = '|'.join(KOREAN_ACTION_TERMS)


def normalize_summary(summary: str) -> str:
  return ' '.join(summary.replace('\\n', ' ').split())


def detect_text_language(text: str) -> str:
  hangul_count = len(re.findall(r'[가-힣]', text))
  latin_count = len(re.findall(r'[A-Za-z]', text))
  if hangul_count and hangul_count >= max(latin_count * 1.4, 2):
    return 'ko'
  if latin_count and latin_count >= max(hangul_count * 1.4, 2):
    return 'en'
  if hangul_count or latin_count:
    return 'mixed'
  return 'en'


def normalize_plain_summary(summary: str) -> str:
  normalized = normalize_summary(summary).rstrip('.')
  if normalized and normalized[0].isascii() and normalized[0].isalpha() and normalized[0].islower():
    normalized = normalized[0].upper() + normalized[1:]
  return normalized


def normalize_body_lines(body_lines: list[str]) -> tuple[list[str], bool]:
  normalized: list[str] = []
  had_literal_backslash_n = False
  for line in body_lines:
    if '\\n' in line:
      had_literal_backslash_n = True
    for chunk in line.replace('\\n', '\n').splitlines():
      cleaned = ' '.join(chunk.split()).strip()
      if cleaned:
        normalized.append(cleaned)
  return normalized, had_literal_backslash_n


def build_body(body_lines: list[str]) -> str | None:
  if not body_lines:
    return None
  bullets = [line if line.startswith('- ') else f'- {line}' for line in body_lines]
  return '\n'.join(bullets)


def add_warning(warnings: list[str], message: str) -> None:
  if message not in warnings:
    warnings.append(message)


def polish_korean_summary(
    summary: str,
    inspection: dict[str, object | None],
) -> tuple[str, list[str]]:
  polished = normalize_summary(summary).rstrip('.')
  reasons: list[str] = []

  updated = re.sub(
      rf'(.+?)(?:을|를)\s+({KOREAN_ACTION_PATTERN})할\s+수\s+있도록\s+수정$',
      r'\1 \2',
      polished,
  )
  if updated != polished:
    polished = updated
    reasons.append('shortened "…할 수 있도록 수정" into a direct Korean action noun')

  for pattern, replacement, reason in KOREAN_REPORT_LIKE_REWRITES:
    updated = re.sub(pattern, replacement, polished)
    updated = ' '.join(updated.split()).strip()
    if updated != polished:
      polished = updated
      if reason not in reasons:
        reasons.append(reason)

  preferred_actions = [
      action
      for action in inspection.get('common_action_nouns', [])
      if isinstance(action, str)
  ] or list(KOREAN_ACTION_TERMS)
  for action in preferred_actions:
    patterns = (
        (rf'{action}합니다$', action, f'normalized polite ending to the common action noun "{action}"'),
        (rf'{action}함$', action, f'normalized terse ending to the common action noun "{action}"'),
    )
    for pattern, replacement, reason in patterns:
      updated = re.sub(pattern, replacement, polished)
      if updated != polished:
        polished = updated
        if reason not in reasons:
          reasons.append(reason)

  updated = re.sub(
      rf'(.+?)(?:을|를)\s+({KOREAN_ACTION_PATTERN})$',
      r'\1 \2',
      polished,
  )
  if updated != polished:
    polished = updated
    reasons.append('removed an unnecessary object particle before a common Korean action noun')

  updated = re.sub(
      rf'(.+?)\s+((?:분리|정리|조정|적용|제거|완화|노출|변경|이동|추가))\s+수정$',
      r'\1 \2',
      polished,
  )
  if updated != polished:
    polished = updated
    reasons.append('removed a redundant trailing "수정" after an explicit Korean action noun')

  updated = re.sub(
      rf'(.+?)(?:을|를)\s+({KOREAN_ACTION_PATTERN})$',
      r'\1 \2',
      polished,
  )
  if updated != polished:
    polished = updated
    reasons.append('removed an unnecessary object particle after shortening the Korean action phrase')

  polished = ' '.join(polished.split()).strip()
  return polished or normalize_summary(summary).rstrip('.'), reasons


def polish_english_summary(summary: str) -> tuple[str, list[str]]:
  polished = normalize_summary(summary).rstrip('.')
  return polished, []


def polish_summary(
    summary: str,
    inspection: dict[str, object | None],
) -> tuple[str, list[str], str]:
  normalized = normalize_summary(summary).rstrip('.')
  summary_language = detect_text_language(normalized)
  dominant_language = inspection.get('dominant_language')
  preferred_summary_style = inspection.get('preferred_summary_style')
  avoid_report_like = bool(inspection.get('avoid_report_like_phrasing'))

  if summary_language == 'ko' or (
      summary_language == 'mixed' and dominant_language == 'ko'
  ) or preferred_summary_style in {'korean-concise', 'korean-descriptive'}:
    if avoid_report_like or summary_language == 'ko':
      polished, reasons = polish_korean_summary(normalized, inspection)
      return polished, reasons, 'ko'
  if summary_language == 'en' or preferred_summary_style == 'english-imperative':
    polished, reasons = polish_english_summary(normalized)
    return polished, reasons, 'en'
  return normalized, [], summary_language


def determine_effective_style_family(
    inspection: dict[str, object | None],
    style_override: str | None,
    warnings: list[str],
) -> str:
  inferred = str(inspection.get('selected_style_family') or 'conventional')
  explicit_style = inspection.get('explicit_rule_style_family')
  fallback_style = str(inspection.get('fallback_commit_style') or 'conventional')

  if style_override:
    if style_override != inferred:
      add_warning(
          warnings,
          f'style override {style_override!r} differs from inferred repo policy {inferred!r}.',
      )
    if inspection.get('repo_has_explicit_commit_rule') and explicit_style and style_override != explicit_style:
      add_warning(
          warnings,
          f'style override {style_override!r} may conflict with explicit repo-local rules ({explicit_style!r}).',
      )
    if style_override == 'gitmoji' and not inspection.get('should_use_gitmoji'):
      add_warning(
          warnings,
          'gitmoji override requested even though the repo is not currently in gitmoji mode.',
      )
    return style_override

  if inspection.get('style_mode') == 'fallback-conventional':
    return 'conventional'
  if inferred == 'custom':
    return fallback_style
  return inferred


def choose_gitmoji(
    inspection: dict[str, object | None],
    requested_gitmoji: str | None,
    warnings: list[str],
) -> tuple[dict[str, object] | None, bool]:
  allowed = inspection.get('allowed_gitmoji') or []
  recommendations = inspection.get('gitmoji_recommendations') or []
  recommended = inspection.get('recommended_gitmoji')
  fallback = inspection.get('fallback_gitmoji')

  if requested_gitmoji:
    if isinstance(allowed, list) and allowed and requested_gitmoji not in allowed:
      raise SystemExit(
          f'Gitmoji {requested_gitmoji!r} is not in the repo-local allowlist and cannot be used.'
      )
    if not inspection.get('should_use_gitmoji'):
      add_warning(
          warnings,
          'gitmoji override supplied for a repo that is not currently in gitmoji mode.',
      )
    if isinstance(recommended, dict) and recommended.get('emoji') != requested_gitmoji:
      add_warning(
          warnings,
          f'gitmoji override {requested_gitmoji!r} differs from the current recommendation {recommended.get("emoji")!r}.',
      )
    for candidate in recommendations:
      if isinstance(candidate, dict) and candidate.get('emoji') == requested_gitmoji:
        return candidate, False
    return {'emoji': requested_gitmoji, 'code': None, 'description': None}, False

  if isinstance(recommended, dict):
    return recommended, False

  if isinstance(fallback, dict):
    add_warning(
        warnings,
        'semantic confidence is low or ambiguous, so the helper is using a fallback gitmoji.',
    )
    return fallback, True

  if inspection.get('requires_human_gitmoji_review'):
    add_warning(
        warnings,
        'gitmoji mode is active but no safe recommendation was found; falling back to a non-gitmoji title is safer.',
    )
  return None, False


def infer_conventional_type(
    inspection: dict[str, object | None],
    override: str | None,
    warnings: list[str],
) -> str:
  if override:
    return override
  semantic_category = str(inspection.get('semantic_category') or 'modify')
  semantic_confidence = inspection.get('semantic_confidence')
  if semantic_confidence == 'low' and semantic_category == 'modify':
    add_warning(
        warnings,
        'semantic confidence is low; using a conservative conventional fallback type.',
    )
  return CONVENTIONAL_TYPE_BY_SEMANTIC.get(semantic_category, 'chore')


def build_title(
    style_family: str,
    inspection: dict[str, object | None],
    summary: str,
    scope: str | None,
    gitmoji_candidate: dict[str, object] | None,
    conventional_type: str,
    warnings: list[str],
) -> tuple[str, str]:
  if style_family == 'plain':
    return normalize_plain_summary(summary), 'plain'

  if style_family == 'gitmoji':
    if gitmoji_candidate and isinstance(gitmoji_candidate.get('emoji'), str):
      emoji = str(gitmoji_candidate['emoji'])
      if scope:
        return f'{emoji} ({scope}) {summary}', 'gitmoji'
      return f'{emoji} {summary}', 'gitmoji'

    add_warning(
        warnings,
        'no safe gitmoji was available, so the helper fell back to a conventional title.',
    )
    style_family = 'conventional'

  if style_family == 'conventional':
    if scope:
      return f'{conventional_type}({scope}): {summary}', 'conventional'
    return f'{conventional_type}: {summary}', 'conventional'

  return f'{conventional_type}: {summary}', 'conventional'


def build_commit_argv(repo: Path, title: str, body: str | None) -> list[str]:
  argv = ['git', '-C', str(repo), 'commit', '-m', title]
  if body:
    argv.extend(['-m', body])
  return argv


def main() -> int:
  parser = argparse.ArgumentParser(description='Draft a repo-aligned commit message from staged changes.')
  parser.add_argument('repo', help='Path to the target git repository')
  parser.add_argument('--summary', required=True, help='Short staged-only summary for the commit title')
  parser.add_argument('--scope', help='Override the inferred scope')
  parser.add_argument('--gitmoji', help='Override the recommended gitmoji with an allowed emoji')
  parser.add_argument('--type', dest='conventional_type', help='Override the inferred conventional commit type')
  parser.add_argument(
      '--style-family',
      choices=('conventional', 'gitmoji', 'plain'),
      help='Override the inferred style family and emit warnings if it conflicts with repo policy.',
  )
  parser.add_argument(
      '--body-line',
      action='append',
      default=[],
      help='One short bullet line for the commit body. Repeat this flag instead of using literal \\n.',
  )
  parser.add_argument('--no-body', action='store_true', help='Force a title-only commit draft')
  parser.add_argument('--commit', action='store_true', help='Create the commit with safe argv handling')
  parser.add_argument('--limit', type=int, default=30, help='Number of recent commits to inspect')
  args = parser.parse_args()

  repo = Path(args.repo).resolve()
  try:
    inspection = inspect_repo(repo, args.limit)
  except ValueError as exc:
    raise SystemExit(str(exc)) from exc

  summary = normalize_summary(args.summary)
  if not summary:
    raise SystemExit('Summary cannot be empty.')
  polished_summary, summary_polish_reason, summary_language = polish_summary(summary, inspection)

  warnings: list[str] = []
  effective_style_family = determine_effective_style_family(
      inspection,
      args.style_family,
      warnings,
  )
  scope = args.scope or inspection.get('preferred_scope')

  normalized_body_lines, had_literal_backslash_n = normalize_body_lines(args.body_line)
  body_policy = inspection.get('body_policy')
  if args.no_body:
    normalized_body_lines = []
  elif body_policy == 'body-required' and not normalized_body_lines:
    raise SystemExit('This repository appears to require commit bodies. Add one or more --body-line values.')
  elif body_policy == 'title-only-preferred' and normalized_body_lines:
    add_warning(
        warnings,
        'this repo usually prefers title-only commits, but a body was supplied.',
    )

  body = build_body(normalized_body_lines)
  gitmoji_candidate, used_fallback_gitmoji = choose_gitmoji(
      inspection,
      args.gitmoji,
      warnings,
  )
  conventional_type = infer_conventional_type(inspection, args.conventional_type, warnings)
  title, final_style_family = build_title(
      effective_style_family,
      inspection,
      polished_summary if effective_style_family != 'plain' else normalize_plain_summary(polished_summary),
      scope if isinstance(scope, str) else None,
      gitmoji_candidate,
      conventional_type,
      warnings,
  )
  commit_argv = build_commit_argv(repo, title, body)

  payload: dict[str, object | None] = {
      'title': title,
      'original_summary': summary,
      'polished_summary': polished_summary,
      'summary_changed': polished_summary != summary,
      'summary_polish_reason': summary_polish_reason or None,
      'body': body,
      'body_lines': normalized_body_lines,
      'body_policy': body_policy,
      'preferred_title_pattern': inspection.get('preferred_title_pattern'),
      'preferred_scope': inspection.get('preferred_scope'),
      'used_scope': scope,
      'used_gitmoji': gitmoji_candidate,
      'used_fallback_gitmoji': used_fallback_gitmoji,
      'requested_style_family': args.style_family,
      'effective_style_family': final_style_family,
      'inferred_style_family': inspection.get('selected_style_family'),
      'style_mode': inspection.get('style_mode'),
      'language': inspection.get('dominant_language'),
      'tone': inspection.get('dominant_tone'),
      'summary_language': summary_language,
      'semantic_category': inspection.get('semantic_category'),
      'semantic_confidence': inspection.get('semantic_confidence'),
      'gitmoji_reason': (
          gitmoji_candidate.get('reasons')
          if isinstance(gitmoji_candidate, dict) and gitmoji_candidate.get('reasons')
          else gitmoji_candidate.get('source')
          if isinstance(gitmoji_candidate, dict)
          else None
      ),
      'body_contains_literal_backslash_n': had_literal_backslash_n,
      'safe_git_commit_argv': commit_argv,
      'external_harness_policy': EXTERNAL_HARNESS_POLICY,
      'external_harness_trailers_added': False,
      'external_harness_trailer_patterns_blocked_by_policy': list(EXTERNAL_HARNESS_TRAILER_PATTERNS),
      'warnings': warnings or None,
      'commit_executed': False,
  }

  if args.commit:
    completed = subprocess.run(
        commit_argv,
        capture_output=True,
        text=True,
        check=False,
    )
    payload['commit_executed'] = True
    payload['commit_returncode'] = completed.returncode
    payload['commit_stdout'] = completed.stdout.strip() or None
    payload['commit_stderr'] = completed.stderr.strip() or None
    if completed.returncode != 0:
      json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
      sys.stdout.write('\n')
      return completed.returncode

  json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
  sys.stdout.write('\n')
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
