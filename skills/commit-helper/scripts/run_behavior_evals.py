#!/usr/bin/env python3
"""Run deterministic behavior checks for the commit helper skill."""

from __future__ import annotations

import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INSPECT = ROOT / 'scripts/inspect_commit_style.py'
DRAFT = ROOT / 'scripts/draft_commit_message.py'


def run(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
  return subprocess.run(
      args,
      capture_output=True,
      text=True,
      check=False,
      env=env,
  )


def git(repo: Path, *args: str) -> str:
  completed = run('git', '-C', str(repo), *args)
  if completed.returncode != 0:
    raise RuntimeError(completed.stderr.strip() or completed.stdout.strip() or 'git command failed')
  return completed.stdout


def write(path: Path, content: str) -> None:
  path.parent.mkdir(parents=True, exist_ok=True)
  path.write_text(content, encoding='utf-8')


def init_repo(name: str) -> Path:
  repo = Path(tempfile.mkdtemp(prefix=f'{name}-', dir='/tmp'))
  git(repo, 'init')
  git(repo, 'config', 'user.name', 'Eval User')
  git(repo, 'config', 'user.email', 'eval@example.com')
  write(repo / 'README.md', '# temp\n')
  git(repo, 'add', 'README.md')
  git(repo, 'commit', '-m', 'Initial baseline')
  return repo


def make_history_commit(repo: Path, subject: str, *, body: str | None = None, filename: str | None = None) -> None:
  filename = filename or f'history/{abs(hash(subject)) % 100000}.txt'
  write(repo / filename, subject + '\n')
  git(repo, 'add', filename)
  if body:
    git(repo, 'commit', '-m', subject, '-m', body)
  else:
    git(repo, 'commit', '-m', subject)


def inspect(repo: Path, *, env: dict[str, str] | None = None) -> dict[str, object]:
  completed = run('python3', str(INSPECT), str(repo), env=env)
  if completed.returncode != 0:
    raise RuntimeError(completed.stderr.strip() or completed.stdout.strip())
  return json.loads(completed.stdout)


def draft(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
  return run('python3', str(DRAFT), str(repo), *args)


def assert_equal(actual: object, expected: object, message: str) -> None:
  if actual != expected:
    raise AssertionError(f'{message}: expected {expected!r}, got {actual!r}')


def assert_true(value: object, message: str) -> None:
  if not value:
    raise AssertionError(message)


def configure_gitmoji_repo(repo: Path) -> None:
  settings = {
      'gitmoji.onlyUseCustomEmoji': True,
      'gitmoji.addCustomEmoji': [
          {'emoji': '✨', 'code': ':sparkles:', 'description': '기능 추가'},
          {'emoji': '🐛', 'code': ':bug:', 'description': '버그 수정'},
          {'emoji': '🌊', 'code': ':ocean:', 'description': '코드 수정'},
          {'emoji': '📦', 'code': ':package:', 'description': '파일 이동 및 경로 수정'},
      ],
  }
  write(repo / '.vscode/settings.json', json.dumps(settings, ensure_ascii=False, indent=2) + '\n')
  git(repo, 'add', '.vscode/settings.json')
  git(repo, 'commit', '-m', '🌊 configure local gitmoji')


def case_explicit_conventional_repo() -> None:
  repo = init_repo('commit-helper-explicit-conventional')
  write(
      repo / 'CONTRIBUTING.md',
      'Use Conventional Commits. Examples: feat: add feature, fix: resolve bug.\n',
  )
  git(repo, 'add', 'CONTRIBUTING.md')
  git(repo, 'commit', '-m', 'docs: add commit convention')
  make_history_commit(repo, 'feat: add bootstrap config')
  write(repo / 'src/api.ts', 'export const apiClient = true;\n')
  git(repo, 'add', 'src/api.ts')
  inspected = inspect(repo)
  assert_equal(inspected['style_mode'], 'repo-local-explicit', 'explicit conventional repo should use explicit mode')
  assert_equal(inspected['selected_style_family'], 'conventional', 'explicit conventional repo should stay conventional')
  drafted = json.loads(draft(repo, '--summary', 'add API client bootstrap', '--no-body').stdout)
  assert_equal(drafted['effective_style_family'], 'conventional', 'draft should remain conventional')
  assert_equal(drafted['title'], 'feat: add API client bootstrap', 'feature should map to feat')


def case_explicit_gitmoji_allowlist_repo() -> None:
  repo = init_repo('commit-helper-explicit-gitmoji')
  settings = {
      'gitmoji.onlyUseCustomEmoji': True,
      'gitmoji.addCustomEmoji': [
          {'emoji': '✨', 'code': ':sparkles:', 'description': 'Add features'},
          {'emoji': '🐛', 'code': ':bug:', 'description': 'Fix bugs'},
          {'emoji': '🛠️', 'code': ':hammer_and_wrench:', 'description': 'Modify code safely'},
          {'emoji': '🚚', 'code': ':truck:', 'description': 'Move files or paths'},
      ],
  }
  write(repo / '.vscode/settings.json', json.dumps(settings, ensure_ascii=False, indent=2) + '\n')
  git(repo, 'add', '.vscode/settings.json')
  git(repo, 'commit', '-m', '🛠️ configure local gitmoji')
  make_history_commit(repo, '✨ add baseline feature')
  write(repo / 'src/feature.ts', 'export const featureFlag = true;\n')
  git(repo, 'add', 'src/feature.ts')
  inspected = inspect(repo)
  assert_true(inspected['should_use_gitmoji'], 'explicit gitmoji repo should enable gitmoji')
  assert_true(inspected['must_use_allowed_gitmoji'], 'explicit gitmoji repo should require allowlist usage')
  completed = draft(repo, '--summary', 'add feature flag', '--gitmoji', '🔥')
  assert_true(completed.returncode != 0, 'emoji outside the allowlist should be rejected')


def case_plain_imperative_history_repo() -> None:
  repo = init_repo('commit-helper-plain-history')
  make_history_commit(repo, 'Fix modal close timing')
  make_history_commit(repo, 'Update validation copy')
  make_history_commit(repo, 'Move legacy routes')
  write(repo / 'src/legacy/routes.ts', 'export const moved = true;\n')
  git(repo, 'add', 'src/legacy/routes.ts')
  inspected = inspect(repo)
  assert_equal(inspected['selected_style_family'], 'plain', 'plain dominant history should infer plain style')
  drafted = json.loads(draft(repo, '--summary', 'move legacy routes', '--no-body').stdout)
  assert_equal(drafted['effective_style_family'], 'plain', 'draft should use plain style')
  assert_equal(drafted['title'], 'Move legacy routes', 'plain style should normalize to an imperative title')


def case_mixed_history_without_rules() -> None:
  repo = init_repo('commit-helper-mixed-history')
  make_history_commit(repo, 'feat: add bootstrap')
  make_history_commit(repo, 'Fix modal close timing')
  make_history_commit(repo, '✨ add onboarding banner')
  make_history_commit(repo, 'docs: note setup')
  write(repo / 'src/misc.ts', 'export const value = 1;\n')
  git(repo, 'add', 'src/misc.ts')
  git(repo, 'commit', '-m', 'chore: add misc value')
  write(repo / 'src/misc.ts', 'export const value = 2;\n')
  git(repo, 'add', 'src/misc.ts')
  inspected = inspect(repo)
  assert_equal(inspected['style_mode'], 'fallback-conventional', 'mixed history without rules should fall back to conventional')
  drafted = json.loads(draft(repo, '--summary', 'adjust misc value', '--no-body').stdout)
  assert_equal(drafted['effective_style_family'], 'conventional', 'fallback mode should draft conventional titles')
  assert_true(drafted['title'].startswith('chore:'), 'ambiguous mixed history should use a conservative conventional fallback')


def case_presentational_modal_cleanup() -> None:
  repo = init_repo('commit-helper-presentational')
  make_history_commit(repo, 'style: baseline modal layout')
  make_history_commit(repo, 'style: adjust drawer spacing')
  write(repo / 'src/modal.css', '.modal { width: 360px; gap: 16px; }\n')
  write(repo / 'src/modal.tsx', 'export const wrapperClass = "modal wrapper";\n')
  git(repo, 'add', 'src/modal.css', 'src/modal.tsx')
  inspected = inspect(repo)
  assert_true(
      inspected['semantic_category'] in {'ui-style', 'modify', 'cleanup'},
      'presentational changes should not default to bugfix',
  )
  assert_equal(inspected['is_bugfix_confident'], False, 'presentational changes should not be bugfix-confident')
  drafted = json.loads(draft(repo, '--summary', 'adjust modal spacing', '--no-body').stdout)
  assert_true(not drafted['title'].startswith('fix:'), 'presentational changes should avoid fix: by default')


def case_actual_validation_bugfix() -> None:
  repo = init_repo('commit-helper-bugfix')
  make_history_commit(repo, 'fix: baseline validation')
  write(
      repo / 'src/validator.ts',
      'export function validate(input: string) {\n  if (!input) throw new Error("validation failed");\n  return true;\n}\n',
  )
  git(repo, 'add', 'src/validator.ts')
  inspected = inspect(repo)
  assert_true(
      inspected['semantic_category'] in {'bugfix', 'critical-bug'},
      'validation failure changes should classify as bugfix',
  )
  assert_true(inspected['is_bugfix_confident'], 'validation failure changes should be bugfix-confident')
  drafted = json.loads(draft(repo, '--summary', 'prevent validation failure on empty input', '--no-body').stdout)
  assert_true(drafted['title'].startswith('fix'), 'actual broken behavior should map to fix:')


def case_file_move_or_legacy_move() -> None:
  repo = init_repo('commit-helper-move')
  make_history_commit(repo, 'chore: baseline legacy routes')
  write(repo / 'src/legacy/auth.ts', 'export const legacy = true;\n')
  git(repo, 'add', 'src/legacy/auth.ts')
  git(repo, 'commit', '-m', 'chore: add legacy auth route')
  (repo / 'src/auth').mkdir(parents=True, exist_ok=True)
  git(repo, 'mv', 'src/legacy/auth.ts', 'src/auth/legacy.ts')
  inspected = inspect(repo)
  assert_true(
      inspected['semantic_category'] in {'move', 'structure'},
      'renames should classify as move or structure',
  )


def case_title_only_preferred_repo() -> None:
  repo = init_repo('commit-helper-title-only')
  make_history_commit(repo, 'feat: add first feature')
  make_history_commit(repo, 'chore: tweak config')
  write(repo / 'src/config.ts', 'export const enabled = true;\n')
  git(repo, 'add', 'src/config.ts')
  inspected = inspect(repo)
  assert_equal(inspected['body_policy'], 'title-only-preferred', 'repos without recurring bodies should prefer title-only commits')
  drafted = json.loads(draft(repo, '--summary', 'adjust config flag', '--no-body').stdout)
  assert_equal(drafted['body'], None, 'title-only preferred repos should allow no body')


def case_global_commit_template_ignored() -> None:
  repo = init_repo('commit-helper-global-template')
  make_history_commit(repo, 'Fix modal close timing')
  make_history_commit(repo, 'Update validation copy')
  template_home = Path(tempfile.mkdtemp(prefix='commit-helper-global-template-home-', dir='/tmp'))
  template_path = template_home / '.gitmessage.txt'
  write(template_path, 'feat: global conventional template\n\nBody required by global template.\n')
  write(
      template_home / '.gitconfig',
      f'[commit]\n\ttemplate = {template_path}\n',
  )
  write(repo / 'src/modal.ts', 'export const modal = true;\n')
  git(repo, 'add', 'src/modal.ts')
  env = os.environ.copy()
  env['HOME'] = str(template_home)
  env['XDG_CONFIG_HOME'] = str(template_home / '.config')
  inspected = inspect(repo, env=env)
  assert_equal(inspected['commit_template_path'], None, 'global templates outside the repo should not be repo-local rules')
  assert_equal(inspected['repo_has_explicit_commit_rule'], False, 'global templates should not create explicit rule sources')
  assert_equal(inspected['selected_style_family'], 'plain', 'global templates should not override history-inferred style')
  assert_equal(inspected['body_policy'], 'title-only-preferred', 'global templates should not require commit bodies')


def case_multiline_body_without_literal_backslash_n() -> None:
  repo = init_repo('commit-helper-multiline-body')
  write(
      repo / 'CONTRIBUTING.md',
      'Use Conventional Commits. Add a short bullet body when useful.\n',
  )
  git(repo, 'add', 'CONTRIBUTING.md')
  git(repo, 'commit', '-m', 'docs: add commit guidance')
  write(repo / 'src/api.ts', 'export const endpoint = "/v2";\n')
  git(repo, 'add', 'src/api.ts')
  completed = draft(
      repo,
      '--summary',
      'add v2 endpoint constant',
      '--body-line',
      'record new endpoint\\nkeep body multiline',
      '--commit',
  )
  if completed.returncode != 0:
    raise AssertionError(completed.stderr.strip() or completed.stdout.strip())
  payload = json.loads(completed.stdout)
  commit_body = git(repo, 'log', '-1', '--format=%B').strip()
  assert_true('\\n' not in payload['body'], 'draft body should not contain a literal backslash-n sequence')
  assert_true('\\n' not in commit_body, 'stored commit body should not contain a literal backslash-n sequence')
  assert_true('\n- keep body multiline' in commit_body, 'stored commit body should contain a real multiline bullet body')


def case_korean_emoji_repo_phrasing() -> None:
  repo = init_repo('commit-helper-ko-emoji-phrasing')
  configure_gitmoji_repo(repo)
  make_history_commit(repo, '🌊 (a:user) 저장 흐름 정리')
  make_history_commit(repo, '✨ (a:user) 조회 범위 조정')
  make_history_commit(repo, '🌊 (a:user) 렌더링 정리')
  write(repo / 'apps/user/query.ts', 'export const range = "all";\n')
  git(repo, 'add', 'apps/user/query.ts')
  drafted = json.loads(draft(repo, '--summary', '조회 범위에 대한 조정', '--no-body').stdout)
  assert_equal(drafted['language'], 'ko', 'korean emoji repo should infer Korean phrasing')
  assert_equal(drafted['polished_summary'], '조회 범위 조정', 'awkward Korean phrasing should be polished into concise wording')
  assert_true(drafted['title'].endswith('조회 범위 조정'), 'title should use the polished Korean summary')


def case_korean_verbose_summary_polish() -> None:
  repo = init_repo('commit-helper-ko-polish')
  make_history_commit(repo, 'fix: 저장 동작 수정')
  make_history_commit(repo, 'chore: 렌더링 정리')
  make_history_commit(repo, 'feat: 조회 범위 조정')
  write(repo / 'src/save.ts', 'export const saveState = true;\n')
  git(repo, 'add', 'src/save.ts')
  drafted = json.loads(draft(repo, '--summary', '저장 동작을 수행하도록 수정', '--no-body').stdout)
  assert_equal(drafted['polished_summary'], '저장 동작 수정', 'verbose Korean report-like phrasing should be shortened naturally')
  assert_true(drafted['summary_changed'], 'polished summary should be reported separately')


def case_mixed_repo_language_profile() -> None:
  repo = init_repo('commit-helper-mixed-language')
  make_history_commit(repo, 'feat: 저장 동작 수정')
  make_history_commit(repo, 'chore: 렌더링 정리')
  make_history_commit(repo, 'Fix modal close timing')
  make_history_commit(repo, 'feat: 조회 범위 조정')
  write(repo / 'src/profile.ts', 'export const profile = true;\n')
  git(repo, 'add', 'src/profile.ts')
  inspected = inspect(repo)
  assert_equal(inspected['dominant_language'], 'ko', 'mixed repo should detect the dominant language from recent history')
  assert_true(
      inspected['dominant_tone'] in {'concise conversational', 'concise technical', 'descriptive'},
      'mixed repo should emit a dominant tone signal',
  )


def case_explicit_conventional_repo_with_natural_wording() -> None:
  repo = init_repo('commit-helper-explicit-conventional-phrasing')
  write(
      repo / 'CONTRIBUTING.md',
      'Use Conventional Commits. Keep titles short and direct.\n',
  )
  git(repo, 'add', 'CONTRIBUTING.md')
  git(repo, 'commit', '-m', 'docs: add commit convention')
  make_history_commit(repo, 'feat: 조회 범위 조정')
  make_history_commit(repo, 'fix: 저장 동작 수정')
  write(repo / 'src/query.ts', 'export const queryRange = "team";\n')
  git(repo, 'add', 'src/query.ts')
  drafted = json.loads(draft(repo, '--summary', '조회 범위에 대한 조정', '--no-body').stdout)
  assert_true(
      bool(re.match(r'^(feat|fix|docs|style|refactor|chore)(\([^)]+\))?:\s', drafted['title'])),
      'explicit conventional repo should keep conventional formatting when semantics are generic',
  )
  assert_true(drafted['title'].endswith('조회 범위 조정'), 'explicit conventional repo should still polish the summary wording naturally')


def case_explicit_gitmoji_repo_with_natural_wording() -> None:
  repo = init_repo('commit-helper-explicit-gitmoji-phrasing')
  configure_gitmoji_repo(repo)
  make_history_commit(repo, '🌊 (a:user) 저장 흐름 정리')
  make_history_commit(repo, '🌊 (a:user) 탭 정리')
  make_history_commit(repo, '✨ (a:user) 조회 범위 조정')
  write(repo / 'apps/user/tabs.ts', 'export const tabs = ["base"];\n')
  git(repo, 'add', 'apps/user/tabs.ts')
  drafted = json.loads(draft(repo, '--summary', '탭을 분리할 수 있도록 수정', '--no-body').stdout)
  assert_true(drafted['effective_style_family'] == 'gitmoji', 'explicit gitmoji repo should stay in gitmoji mode')
  assert_equal(drafted['polished_summary'], '탭 분리', 'gitmoji repo should still polish awkward Korean wording naturally')
  assert_true(any(emoji in drafted['title'] for emoji in ['🌊', '✨', '🐛', '📦']), 'title should keep an allowed emoji')

def case_commit_helper_invocation_boundary() -> None:
  repo = init_repo('commit-helper-invocation-boundary')
  write(repo / 'src/skill.ts', 'export const skill = true;\n')
  git(repo, 'add', 'src/skill.ts')
  drafted = json.loads(draft(repo, '--summary', 'add commit helper boundary', '--no-body').stdout)
  rendered = '\n'.join(str(drafted.get(key) or '') for key in ('title', 'body'))
  forbidden = (
      'Co-authored-by: OmX',
      'Constraint:',
      'Rejected:',
      'Confidence:',
      'Scope-risk:',
      'Directive:',
      'Tested:',
      'Not-tested:',
  )
  assert_true(not any(item in rendered for item in forbidden), 'draft should not add external harness trailers')
  assert_equal(drafted['external_harness_trailers_added'], False, 'payload should report no external harness trailers')
  assert_true('commit-helper-only' in drafted['external_harness_policy'], 'payload should expose invocation boundary policy')


CASES = [
    ('explicit_conventional_repo', case_explicit_conventional_repo),
    ('explicit_gitmoji_allowlist_repo', case_explicit_gitmoji_allowlist_repo),
    ('plain_imperative_history_repo', case_plain_imperative_history_repo),
    ('mixed_history_without_rules', case_mixed_history_without_rules),
    ('presentational_modal_cleanup', case_presentational_modal_cleanup),
    ('actual_validation_bugfix', case_actual_validation_bugfix),
    ('file_move_or_legacy_move', case_file_move_or_legacy_move),
    ('title_only_preferred_repo', case_title_only_preferred_repo),
    ('global_commit_template_ignored', case_global_commit_template_ignored),
    ('multiline_body_without_literal_backslash_n', case_multiline_body_without_literal_backslash_n),
    ('korean_emoji_repo_phrasing', case_korean_emoji_repo_phrasing),
    ('korean_verbose_summary_polish', case_korean_verbose_summary_polish),
    ('mixed_repo_language_profile', case_mixed_repo_language_profile),
    ('explicit_conventional_repo_with_natural_wording', case_explicit_conventional_repo_with_natural_wording),
    ('explicit_gitmoji_repo_with_natural_wording', case_explicit_gitmoji_repo_with_natural_wording),
    ('commit_helper_invocation_boundary', case_commit_helper_invocation_boundary),
]


def main() -> int:
  results: list[dict[str, str]] = []
  failures = 0
  for name, fn in CASES:
    try:
      fn()
      results.append({'name': name, 'status': 'passed'})
    except Exception as exc:  # noqa: BLE001
      failures += 1
      results.append({'name': name, 'status': 'failed', 'message': str(exc)})

  print(json.dumps({'results': results, 'failures': failures}, indent=2, ensure_ascii=False))
  return 1 if failures else 0


if __name__ == '__main__':
  raise SystemExit(main())
