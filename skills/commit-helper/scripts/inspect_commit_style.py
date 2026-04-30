#!/usr/bin/env python3
"""Inspect commit style, repo-local rules, and staged change semantics."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

CONVENTIONAL_TYPES = (
    'feat',
    'fix',
    'docs',
    'style',
    'refactor',
    'perf',
    'test',
    'build',
    'ci',
    'chore',
    'revert',
)
STYLE_FAMILIES = ('conventional', 'gitmoji', 'plain', 'custom')
STYLE_MODES = ('repo-local-explicit', 'history-inferred', 'fallback-conventional')
SEMANTIC_CATEGORIES = (
    'feature',
    'bugfix',
    'critical-bug',
    'refactor',
    'structure',
    'move',
    'ui-style',
    'responsive',
    'accessibility',
    'docs',
    'config',
    'tooling',
    'cleanup',
    'modify',
)
INTERNAL_SIGNALS = SEMANTIC_CATEGORIES + (
    'dependency-add',
    'dependency-remove',
    'deletion',
)
CONVENTIONAL_RE = re.compile(
    rf"^({'|'.join(CONVENTIONAL_TYPES)})(\([^)]+\))?!?:\s"
)
EMOJI_SCOPE_RE = re.compile(r'^[^A-Za-z0-9\s].*\([^)]+\)')
EMOJI_PREFIX_RE = re.compile(r'^[^A-Za-z0-9\s]')
SCOPE_RE = re.compile(r'\(([^)]+)\)')
RECENT_MESSAGE_FIELD_SEP = '\x1f'
RECENT_MESSAGE_RECORD_SEP = '\x1e'
RECENT_SUBJECT_LIMIT = 10
VSCODE_SETTINGS_PATH = Path('.vscode/settings.json')
PACKAGE_MANIFEST_FILES = (
    'package.json',
    'pnpm-lock.yaml',
    'yarn.lock',
    'package-lock.json',
    'bun.lock',
    'bun.lockb',
)
DEPENDENCY_SECTION_KEYS = (
    'dependencies',
    'devDependencies',
    'peerDependencies',
    'optionalDependencies',
)
GENERIC_DIR_NAMES = {
    '.github',
    'src',
    'app',
    'apps',
    'lib',
    'libs',
    'package',
    'packages',
    'server',
    'client',
    'docs',
    'tests',
    'test',
}
MONOREPO_SCOPE_ROOTS = {
    'apps': 'app',
    'packages': 'pkg',
    'libs': 'lib',
    'services': 'service',
    'modules': 'module',
}
COMMIT_RULE_FILE_CANDIDATES = (
    'AGENTS.md',
    'CONTRIBUTING.md',
    'CONTRIBUTING',
    'README.md',
    'README.ko.md',
    '.gitmessage',
    '.gitmessage.txt',
    '.github/CONTRIBUTING.md',
)
COMMIT_RULE_GLOBS = (
    'README*.md',
    '*commit*.md',
    '*commit*.txt',
    '.github/*commit*.md',
    'docs/*commit*.md',
    'commitlint.config.*',
    '.commitlintrc*',
)
EXPLICIT_GITMOJI_HINTS = (
    'gitmoji',
    'emoji commit',
    'emoji commits',
    'emoji-based commit',
    'emoji based commit',
    'use emoji in commit',
)
EXPLICIT_CONVENTIONAL_HINTS = (
    'conventional commit',
    'conventional commits',
    'commitlint',
    'config-conventional',
    'semantic-release',
)
EXPLICIT_PLAIN_HINTS = (
    'imperative mood',
    'plain imperative',
    'use the imperative',
    'subject line',
)
EXPLICIT_COMMIT_RULE_HINTS = (
    'commit message',
    'commit messages',
    'commit title',
    'commit convention',
    'commit conventions',
    'commit format',
)
STRUCTURED_TEMPLATE_HINTS = (
    '<type>',
    '<scope>',
    '<subject>',
    '[scope]',
    '[subject]',
    '{scope}',
    '{subject}',
    '{{scope}}',
    '{{subject}}',
)
BUGFIX_KEYWORDS = (
    'bug',
    'bugs',
    'fix',
    'fixed',
    'fixes',
    'regression',
    'broken',
    'crash',
    'error',
    'errors',
    'exception',
    'exceptions',
    'invalid',
    'mismatch',
    'wrong',
    'incorrect',
    'failing',
    'failure',
    '403',
    '404',
    '500',
    'validation',
    'unauthorized',
    'forbidden',
    'permission denied',
    '오류',
    '버그',
    '예외',
    '실패',
    '잘못',
    '깨진',
    '정합성',
)
CRITICAL_BUG_KEYWORDS = (
    'critical hotfix',
    'critical bug',
    'hotfix',
    'outage',
    'panic',
    'fatal',
    'urgent',
    '치명적',
)
DIFF_KEYWORD_GROUPS = {
    'feature': (
        'add',
        'added',
        'introduce',
        'new feature',
        'support ',
        '추가',
        '도입',
    ),
    'refactor': (
        'refactor',
        'extract',
        'reorganize',
        'simplify',
        'rename variable',
        '리팩토링',
        '추출',
        '단순화',
    ),
    'structure': (
        'barrel',
        'module',
        'modules',
        'route group',
        'route layout',
        're-export',
        'export *',
        'directory',
        'folder',
        'architecture',
        '구조',
        '모듈',
        '폴더',
    ),
    'move': (
        'rename',
        'renamed',
        'move',
        'moved',
        'relocate',
        'path',
        'route path',
        'legacy move',
        '이동',
        '경로',
    ),
    'ui-style': (
        'class name',
        'classname',
        'style',
        'styles',
        'css',
        'scss',
        'theme',
        'token',
        'tokens',
        'spacing',
        'padding',
        'margin',
        'gap',
        'width',
        'height',
        'layout',
        'wrapper',
        'modal',
        'drawer',
        'dialog',
        'typography',
        'font',
        'color',
        'grid',
        'flex',
        'align',
        'shadow',
        'animation',
        'transition',
        '스타일',
        '레이아웃',
        '간격',
        '모달',
    ),
    'responsive': (
        'responsive',
        'mobile',
        'tablet',
        'breakpoint',
        'viewport',
        'media query',
        '반응형',
    ),
    'accessibility': (
        'a11y',
        'aria-',
        'accessibility',
        'screen reader',
        'keyboard navigation',
        'role=',
        'alt=',
        '접근성',
    ),
    'docs': (
        'readme',
        'documentation',
        'docs/',
        '.md',
        '문서',
    ),
    'config': (
        'config',
        'settings',
        'env',
        'build',
        'eslint',
        'prettier',
        'tsconfig',
        'vite',
        'webpack',
        'docker',
        'workflow',
        'ci',
        'lint',
        '설정',
        '환경',
    ),
    'tooling': (
        'tooling',
        'devtool',
        'script',
        'scripts/',
        'codemod',
        'generator',
        'cli',
        'dev experience',
        '개발 도구',
        '스크립트',
    ),
    'cleanup': (
        'cleanup',
        'clean up',
        'tidy',
        'remove unused',
        'dead code',
        'prune',
        '정리',
        '미사용',
    ),
    'modify': (
        'update',
        'adjust',
        'change',
        'modify',
        'revise',
        '정리',
        '수정',
        '변경',
    ),
}
PATH_SIGNAL_RULES = (
    ('docs', ('docs/', 'readme', '.md')),
    ('ui-style', ('.css', '.scss', '.sass', '.less', 'styles/', 'theme/', 'tokens/')),
    ('responsive', ('responsive', 'mobile', 'tablet', 'breakpoint', 'viewport')),
    ('accessibility', ('a11y', 'aria', 'accessibility')),
    ('config', ('.github/', '.vscode/', '.npmrc', '.nvmrc', '.env', 'tsconfig', 'eslint', 'prettier', 'vite.config', 'webpack.config', 'dockerfile', 'docker-compose')),
    ('tooling', ('scripts/', 'tools/', 'codemods/', 'devtools/')),
)
CATEGORY_SPECIFICITY = {
    'critical-bug': 100,
    'bugfix': 90,
    'feature': 82,
    'move': 80,
    'structure': 78,
    'ui-style': 76,
    'responsive': 74,
    'accessibility': 74,
    'refactor': 72,
    'docs': 70,
    'config': 68,
    'tooling': 66,
    'cleanup': 64,
    'dependency-add': 62,
    'dependency-remove': 62,
    'deletion': 60,
    'modify': 10,
}
SIGNAL_WEIGHTS = {
    'critical-bug': 12,
    'bugfix': 8,
    'feature': 6,
    'refactor': 7,
    'structure': 8,
    'move': 9,
    'ui-style': 8,
    'responsive': 8,
    'accessibility': 8,
    'docs': 7,
    'config': 7,
    'tooling': 7,
    'cleanup': 6,
    'modify': 1,
    'dependency-add': 9,
    'dependency-remove': 9,
    'deletion': 9,
}
CODE_DEFAULT_CATEGORIES = {
    ':sparkles:': ('feature',),
    ':bug:': ('bugfix',),
    ':ambulance:': ('critical-bug',),
    ':recycle:': ('refactor',),
    ':building_construction:': ('structure',),
    ':truck:': ('move',),
    ':lipstick:': ('ui-style',),
    ':art:': ('structure',),
    ':iphone:': ('responsive',),
    ':wheelchair:': ('accessibility',),
    ':memo:': ('docs',),
    ':wrench:': ('config',),
    ':hammer:': ('tooling',),
    ':heavy_plus_sign:': ('dependency-add',),
    ':heavy_minus_sign:': ('dependency-remove',),
    ':fire:': ('deletion',),
    ':alien:': ('config',),
}
DEFAULT_GITMOJI_DETAILS = [
    {'emoji': '✨', 'code': ':sparkles:', 'description': 'Introduce new features.'},
    {'emoji': '🐛', 'code': ':bug:', 'description': 'Fix a bug.'},
    {'emoji': '🚑', 'code': ':ambulance:', 'description': 'Critical hotfix.'},
    {'emoji': '♻️', 'code': ':recycle:', 'description': 'Refactor code.'},
    {'emoji': '🏗️', 'code': ':building_construction:', 'description': 'Make architectural changes.'},
    {'emoji': '🚚', 'code': ':truck:', 'description': 'Move or rename resources.'},
    {'emoji': '💄', 'code': ':lipstick:', 'description': 'Add or update the UI and style files.'},
    {'emoji': '📱', 'code': ':iphone:', 'description': 'Work on responsive design.'},
    {'emoji': '♿️', 'code': ':wheelchair:', 'description': 'Improve accessibility.'},
    {'emoji': '📝', 'code': ':memo:', 'description': 'Add or update documentation.'},
    {'emoji': '🔧', 'code': ':wrench:', 'description': 'Add or update configuration files.'},
    {'emoji': '🔨', 'code': ':hammer:', 'description': 'Add or update development scripts.'},
    {'emoji': '➕', 'code': ':heavy_plus_sign:', 'description': 'Add a dependency.'},
    {'emoji': '➖', 'code': ':heavy_minus_sign:', 'description': 'Remove a dependency.'},
    {'emoji': '🔥', 'code': ':fire:', 'description': 'Remove code or files.'},
]
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
REPORT_LIKE_PHRASES = (
    '을 위한',
    '를 위한',
    '에 대한',
    '관련',
    '수행하도록',
    '할 수 있도록',
    '되도록',
    '하기 위한',
    '목적으로',
    '기반으로',
    '에 맞춰',
)
KOREAN_CONCISE_HINTS = (
    '정리',
    '분리',
    '조정',
    '완화',
    '노출',
    '추가',
    '수정',
)
TECHNICAL_SUBJECT_HINTS = (
    'api',
    'query',
    'hook',
    'hooks',
    'resolver',
    'modal',
    'drawer',
    'layout',
    'eslint',
    'config',
    'schema',
    'route',
    'state',
    'cache',
)


def git(repo: Path, *args: str, check: bool = True) -> str:
  completed = subprocess.run(
      ['git', '-C', str(repo), *args],
      capture_output=True,
      text=True,
      check=False,
  )
  if check and completed.returncode != 0:
    message = completed.stderr.strip() or completed.stdout.strip() or 'git command failed'
    raise RuntimeError(message)
  return completed.stdout.strip()


def git_optional(repo: Path, *args: str) -> tuple[bool, str]:
  completed = subprocess.run(
      ['git', '-C', str(repo), *args],
      capture_output=True,
      text=True,
      check=False,
  )
  return completed.returncode == 0, completed.stdout


def is_git_repository(repo: Path) -> bool:
  completed = subprocess.run(
      ['git', '-C', str(repo), 'rev-parse', '--git-dir'],
      capture_output=True,
      text=True,
      check=False,
  )
  return completed.returncode == 0


def classify_subject(subject: str) -> str:
  if CONVENTIONAL_RE.match(subject):
    return 'conventional'
  if EMOJI_SCOPE_RE.match(subject):
    return 'emoji-scope'
  if EMOJI_PREFIX_RE.match(subject):
    return 'emoji-prefix'
  return 'plain'


def subject_style_family(subject: str) -> str:
  pattern = classify_subject(subject)
  if pattern == 'conventional':
    return 'conventional'
  if pattern in {'emoji-scope', 'emoji-prefix'}:
    return 'gitmoji'
  return 'plain'


def extract_scope(subject: str) -> str | None:
  match = SCOPE_RE.search(subject)
  return match.group(1) if match else None


def extract_leading_emoji(subject: str) -> str | None:
  if not subject or not EMOJI_PREFIX_RE.match(subject):
    return None
  token = subject.split(maxsplit=1)[0]
  return token if token else None


def strip_subject_format(subject: str) -> str:
  stripped = subject.strip()
  conventional = CONVENTIONAL_RE.match(stripped)
  if conventional:
    return stripped[conventional.end():].strip()

  if EMOJI_PREFIX_RE.match(stripped):
    stripped = re.sub(r'^[^A-Za-z0-9\s]+\s*', '', stripped).strip()
    stripped = re.sub(r'^\([^)]+\)\s*', '', stripped).strip()
  return stripped


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


def infer_title_length_profile(avg_length: float) -> str:
  if avg_length <= 18:
    return 'short'
  if avg_length <= 32:
    return 'medium'
  return 'long'


def infer_dominant_tone(
    core_subjects: list[str],
    dominant_language: str,
    average_length: float,
) -> tuple[str, bool]:
  if not core_subjects:
    return 'concise technical', True

  report_like_ratio = sum(
      1
      for subject in core_subjects
      if any(phrase in subject for phrase in REPORT_LIKE_PHRASES)
  ) / len(core_subjects)
  descriptive_ratio = sum(
      1
      for subject in core_subjects
      if len(subject) >= 28 or ',' in subject or ' and ' in subject.lower() or '&' in subject
  ) / len(core_subjects)
  technical_ratio = sum(
      1
      for subject in core_subjects
      if any(text_contains_keyword(subject.lower(), keyword) for keyword in TECHNICAL_SUBJECT_HINTS)
  ) / len(core_subjects)

  if report_like_ratio >= 0.35:
    return 'formal/report-like', False
  if descriptive_ratio >= 0.35 or average_length >= 26:
    return 'descriptive', dominant_language != 'ko'
  if technical_ratio >= 0.35 or dominant_language == 'en':
    return 'concise technical', True
  return 'concise conversational', True


def analyze_phrasing_profile(subjects: list[str]) -> dict[str, object | None]:
  core_subjects = [strip_subject_format(subject) for subject in subjects if strip_subject_format(subject)]
  if not core_subjects:
    return {
        'dominant_language': 'mixed',
        'dominant_tone': 'concise technical',
        'title_length_profile': 'medium',
        'common_korean_suffixes': [],
        'common_action_nouns': [],
        'preferred_summary_style': 'conservative-short',
        'avoid_report_like_phrasing': True,
        'phrasing_confidence': 'low',
    }

  language_counts = Counter(detect_text_language(subject) for subject in core_subjects)
  total = sum(language_counts.values())
  top_language, top_count = language_counts.most_common(1)[0]
  second_count = language_counts.most_common(2)[1][1] if len(language_counts) > 1 else 0

  dominant_language = 'mixed'
  phrasing_confidence = 'low'
  ratio = top_count / total if total else 0
  delta = top_count - second_count
  if ratio >= 0.75 and delta >= 2:
    dominant_language = top_language
    phrasing_confidence = 'high'
  elif ratio >= 0.55 and delta >= 1:
    dominant_language = top_language
    phrasing_confidence = 'medium'

  average_length = sum(len(subject) for subject in core_subjects) / len(core_subjects)
  title_length_profile = infer_title_length_profile(average_length)
  dominant_tone, avoid_report_like = infer_dominant_tone(core_subjects, dominant_language, average_length)

  korean_suffix_counts: Counter[str] = Counter()
  action_counts: Counter[str] = Counter()
  for subject in core_subjects:
    for action in KOREAN_ACTION_TERMS:
      if subject.endswith(action):
        korean_suffix_counts[action] += 1
      if action in subject:
        action_counts[action] += 1

  common_korean_suffixes = [item for item, _ in korean_suffix_counts.most_common(6)]
  common_action_nouns = [item for item, _ in action_counts.most_common(8)]

  preferred_summary_style = 'conservative-short'
  if dominant_language == 'ko':
    preferred_summary_style = 'korean-concise'
    if dominant_tone in {'descriptive', 'formal/report-like'}:
      preferred_summary_style = 'korean-descriptive'
  elif dominant_language == 'en':
    preferred_summary_style = 'english-imperative'
  elif dominant_language == 'mixed':
    preferred_summary_style = 'mixed-bilingual'

  if dominant_language == 'ko' and any(item in common_action_nouns for item in KOREAN_CONCISE_HINTS):
    avoid_report_like = True

  return {
      'dominant_language': dominant_language,
      'dominant_tone': dominant_tone,
      'title_length_profile': title_length_profile,
      'common_korean_suffixes': common_korean_suffixes,
      'common_action_nouns': common_action_nouns,
      'preferred_summary_style': preferred_summary_style,
      'avoid_report_like_phrasing': avoid_report_like,
      'phrasing_confidence': phrasing_confidence,
  }


def get_recent_messages(repo: Path, limit: int) -> list[dict[str, str]]:
  raw = git(repo, 'log', '--no-merges', '--format=%s%x1f%b%x1e', f'-n{limit}')
  messages: list[dict[str, str]] = []
  for record in raw.split(RECENT_MESSAGE_RECORD_SEP):
    if not record.strip():
      continue
    subject, _, body = record.partition(RECENT_MESSAGE_FIELD_SEP)
    messages.append({
        'subject': subject.strip(),
        'body': body.strip(),
    })
  return messages


def get_staged_files(repo: Path) -> list[str]:
  raw = git(repo, 'diff', '--cached', '--name-only')
  return [line for line in raw.splitlines() if line]


def get_staged_name_status(repo: Path) -> list[tuple[str, list[str]]]:
  raw = git(repo, 'diff', '--cached', '--name-status', '--find-renames')
  entries: list[tuple[str, list[str]]] = []
  for line in raw.splitlines():
    if not line:
      continue
    parts = line.split('\t')
    if len(parts) < 2:
      continue
    entries.append((parts[0], parts[1:]))
  return entries


def get_staged_diff(repo: Path) -> str:
  return git(repo, 'diff', '--cached', '--no-ext-diff', '--no-color', '--unified=0')


def get_commit_template_path(repo: Path) -> str | None:
  template = git(repo, 'config', '--get', 'commit.template', check=False).strip()
  if not template:
    return None

  candidate = Path(template)
  if candidate.is_absolute():
    return str(candidate)
  return str((repo / candidate).resolve())


def load_text_file(path: Path) -> str | None:
  try:
    return path.read_text(encoding='utf-8')
  except OSError:
    return None


def text_contains_keyword(text: str, keyword: str) -> bool:
  if not keyword:
    return False
  if any(char in keyword for char in ' /._-*():='):
    return keyword in text
  if keyword.isascii() and any(char.isalpha() for char in keyword):
    pattern = re.compile(rf'(?<![A-Za-z0-9]){re.escape(keyword)}(?![A-Za-z0-9])')
    return bool(pattern.search(text))
  return keyword in text


def get_diff_content_lines(staged_diff: str) -> list[str]:
  content_lines: list[str] = []
  for line in staged_diff.splitlines():
    if not line:
      continue
    if line.startswith(('diff --git ', 'index ', '@@ ', 'new file mode ', 'deleted file mode ')):
      continue
    if line.startswith(('--- ', '+++ ')):
      continue
    if line.startswith(('+', '-')):
      content_lines.append(line[1:])
  return content_lines


def strip_jsonc_comments(text: str) -> str:
  result: list[str] = []
  in_string = False
  in_line_comment = False
  in_block_comment = False
  escape = False
  index = 0

  while index < len(text):
    char = text[index]
    next_char = text[index + 1] if index + 1 < len(text) else ''

    if in_line_comment:
      if char == '\n':
        in_line_comment = False
        result.append(char)
      index += 1
      continue

    if in_block_comment:
      if char == '*' and next_char == '/':
        in_block_comment = False
        index += 2
        continue
      if char == '\n':
        result.append(char)
      index += 1
      continue

    if in_string:
      result.append(char)
      if escape:
        escape = False
      elif char == '\\':
        escape = True
      elif char == '"':
        in_string = False
      index += 1
      continue

    if char == '"':
      in_string = True
      result.append(char)
      index += 1
      continue

    if char == '/' and next_char == '/':
      in_line_comment = True
      index += 2
      continue

    if char == '/' and next_char == '*':
      in_block_comment = True
      index += 2
      continue

    result.append(char)
    index += 1

  return ''.join(result)


def strip_trailing_commas(text: str) -> str:
  result: list[str] = []
  in_string = False
  escape = False
  index = 0

  while index < len(text):
    char = text[index]

    if in_string:
      result.append(char)
      if escape:
        escape = False
      elif char == '\\':
        escape = True
      elif char == '"':
        in_string = False
      index += 1
      continue

    if char == '"':
      in_string = True
      result.append(char)
      index += 1
      continue

    if char == ',':
      lookahead = index + 1
      while lookahead < len(text) and text[lookahead].isspace():
        lookahead += 1
      if lookahead < len(text) and text[lookahead] in '}]':
        index += 1
        continue

    result.append(char)
    index += 1

  return ''.join(result)


def load_jsonc(path: Path) -> object:
  raw = path.read_text(encoding='utf-8')
  normalized = strip_trailing_commas(strip_jsonc_comments(raw))
  return json.loads(normalized)


def infer_categories_from_description(description: str) -> tuple[str, ...]:
  lowered = ' '.join(description.lower().split())
  categories: list[str] = []
  seen: set[str] = set()

  def push(category: str) -> None:
    if category not in seen:
      seen.add(category)
      categories.append(category)

  if any(keyword in lowered for keyword in CRITICAL_BUG_KEYWORDS):
    push('critical-bug')
  if any(keyword in lowered for keyword in BUGFIX_KEYWORDS):
    push('bugfix')

  description_hints = (
      (('new feature', 'introduce new', 'feature', '추가', '도입'), ('feature',)),
      (('refactor', 'reorganize', '리팩토링', '단순화'), ('refactor',)),
      (('architectural', 'architecture', '구조', 'module structure'), ('structure',)),
      (('move', 'rename', 'path', 'route', '이동', '경로'), ('move',)),
      (('ui', 'style', 'styles', 'layout', 'spacing', 'color', '스타일', '레이아웃'), ('ui-style',)),
      (('responsive', 'mobile', 'breakpoint', '반응형'), ('responsive',)),
      (('accessibility', 'a11y', 'aria', '접근성'), ('accessibility',)),
      (('docs', 'documentation', 'readme', '문서'), ('docs',)),
      (('config', 'configuration', 'settings', '환경', '설정'), ('config',)),
      (('tooling', 'script', 'development scripts', '개발 도구', '스크립트'), ('tooling',)),
      (('cleanup', 'clean up', 'dead code', 'unused', '정리', '미사용'), ('cleanup',)),
      (('dependency', 'dependencies'), ('dependency-add', 'dependency-remove', 'tooling')),
      (('remove code', 'remove file', 'delete', '삭제'), ('deletion',)),
      (('update', 'change', 'modify', '수정', '변경'), ('modify',)),
  )
  for phrases, mapped_categories in description_hints:
    if any(phrase in lowered for phrase in phrases):
      for category in mapped_categories:
        push(category)

  return tuple(categories)


def classify_gitmoji_entry(entry: dict[str, str], *, repo_local: bool) -> dict[str, object]:
  code = entry.get('code', '')
  description = entry.get('description', '')
  description_categories = list(infer_categories_from_description(description))
  code_categories = list(CODE_DEFAULT_CATEGORIES.get(code, ()))

  primary: list[str]
  secondary: list[str]
  semantic_source = 'none'

  description_specificity = max(
      (CATEGORY_SPECIFICITY.get(category, 0) for category in description_categories),
      default=0,
  )
  code_specificity = max(
      (CATEGORY_SPECIFICITY.get(category, 0) for category in code_categories),
      default=0,
  )

  if repo_local and description_categories and description_specificity >= code_specificity:
    primary = description_categories
    secondary = [category for category in code_categories if category not in primary]
    semantic_source = 'description'
  elif code_categories:
    primary = code_categories
    secondary = [category for category in description_categories if category not in primary]
    semantic_source = 'code'
  elif description_categories:
    primary = description_categories
    secondary = []
    semantic_source = 'description'
  else:
    primary = []
    secondary = []

  semantic_categories = primary + [category for category in secondary if category not in primary]
  specificity = max(
      (CATEGORY_SPECIFICITY.get(category, 0) for category in semantic_categories),
      default=0,
  )
  return {
      'semantic_primary': primary,
      'semantic_secondary': secondary,
      'semantic_categories': semantic_categories,
      'semantic_source': semantic_source,
      'semantic_specificity': specificity,
      'is_fallback': primary == ['modify'] or semantic_categories == ['modify'],
  }


def build_default_gitmoji_catalog() -> list[dict[str, object]]:
  details: list[dict[str, object]] = []
  for entry in DEFAULT_GITMOJI_DETAILS:
    detail = dict(entry)
    detail.update(classify_gitmoji_entry(entry, repo_local=False))
    details.append(detail)
  return details


def detect_gitmoji_constraints(repo: Path) -> dict[str, object | None]:
  settings_path = repo / VSCODE_SETTINGS_PATH
  payload: dict[str, object | None] = {
      'gitmoji_config_path': None,
      'gitmoji_config_error': None,
      'gitmoji_only_custom': None,
      'must_use_allowed_gitmoji': False,
      'allowed_gitmoji': None,
      'allowed_gitmoji_details': None,
      'disallowed_gitmoji': [],
  }
  if not settings_path.exists():
    return payload

  payload['gitmoji_config_path'] = str(settings_path)

  try:
    settings = load_jsonc(settings_path)
  except (OSError, json.JSONDecodeError) as exc:
    payload['gitmoji_config_error'] = str(exc)
    return payload

  if not isinstance(settings, dict):
    payload['gitmoji_config_error'] = 'settings.json did not parse to an object'
    return payload

  only_custom = settings.get('gitmoji.onlyUseCustomEmoji')
  if isinstance(only_custom, bool):
    payload['gitmoji_only_custom'] = only_custom

  custom_emoji = settings.get('gitmoji.addCustomEmoji')
  if isinstance(custom_emoji, list):
    allowed: list[str] = []
    details: list[dict[str, object]] = []
    seen: set[str] = set()
    for item in custom_emoji:
      if not isinstance(item, dict):
        continue
      emoji = item.get('emoji')
      code = item.get('code')
      description = item.get('description')
      if not isinstance(emoji, str) or not emoji or emoji in seen:
        continue
      seen.add(emoji)
      allowed.append(emoji)
      detail = {
          'emoji': emoji,
          'code': code if isinstance(code, str) else None,
          'description': description if isinstance(description, str) else None,
      }
      detail.update(
          classify_gitmoji_entry(
              {
                  'emoji': emoji,
                  'code': code if isinstance(code, str) else '',
                  'description': description if isinstance(description, str) else '',
              },
              repo_local=True,
          )
      )
      details.append(detail)
    payload['allowed_gitmoji'] = allowed
    payload['allowed_gitmoji_details'] = details

  allowed_gitmoji = payload.get('allowed_gitmoji')
  if isinstance(allowed_gitmoji, list) and allowed_gitmoji and payload.get('gitmoji_only_custom') is True:
    payload['must_use_allowed_gitmoji'] = True
    payload['disallowed_gitmoji'] = ['<any emoji not present in allowed_gitmoji>']

  return payload


def iter_explicit_rule_files(repo: Path, commit_template_path: str | None) -> list[Path]:
  candidates: list[Path] = []
  seen: set[Path] = set()

  def push(path: Path) -> None:
    resolved = path.resolve()
    if resolved in seen or not resolved.exists() or not resolved.is_file():
      return
    seen.add(resolved)
    candidates.append(resolved)

  for name in COMMIT_RULE_FILE_CANDIDATES:
    push(repo / name)

  for pattern in COMMIT_RULE_GLOBS:
    for path in repo.glob(pattern):
      push(path)

  if commit_template_path:
    push(Path(commit_template_path))

  return candidates


def detect_doc_style_family(text: str) -> tuple[str | None, list[str]]:
  lowered = text.lower()
  reasons: list[str] = []
  hits: Counter[str] = Counter()

  if any(hint in lowered for hint in EXPLICIT_GITMOJI_HINTS):
    hits['gitmoji'] += 2
    reasons.append('mentions gitmoji or emoji commit rules')
  if any(hint in lowered for hint in EXPLICIT_CONVENTIONAL_HINTS):
    hits['conventional'] += 2
    reasons.append('mentions Conventional Commits or commitlint-style rules')
  if re.search(r'(^|[\s`])(feat|fix|docs|style|refactor|chore)(\([^)]+\))?!?:', lowered):
    hits['conventional'] += 2
    reasons.append('contains conventional commit examples')
  if any(hint in lowered for hint in EXPLICIT_PLAIN_HINTS):
    hits['plain'] += 1
    reasons.append('mentions imperative/plain subject guidance')
  if any(hint in lowered for hint in EXPLICIT_COMMIT_RULE_HINTS) and any(
      hint in lowered for hint in STRUCTURED_TEMPLATE_HINTS):
    hits['custom'] += 1
    reasons.append('contains structured commit template placeholders')
  if 'commit.template' in lowered or '.gitmessage' in lowered:
    hits['custom'] += 1
    reasons.append('references a commit template')

  if not hits:
    return None, []

  for style in ('gitmoji', 'conventional', 'plain', 'custom'):
    if hits.get(style):
      return style, reasons
  return None, reasons


def detect_explicit_commit_rules(
    repo: Path,
    gitmoji_constraints: dict[str, object | None],
) -> dict[str, object | None]:
  commit_template_path = get_commit_template_path(repo)
  sources: list[dict[str, object]] = []
  style_votes: Counter[str] = Counter()
  repo_has_gitmoji_signal = False

  if gitmoji_constraints.get('allowed_gitmoji_details') or gitmoji_constraints.get('gitmoji_config_path'):
    sources.append({
        'path': str(repo / VSCODE_SETTINGS_PATH),
        'style_family': 'gitmoji',
        'reason': 'repo-local gitmoji settings found in editor configuration',
        'source_kind': 'gitmoji-config',
    })
    style_votes['gitmoji'] += 3
    repo_has_gitmoji_signal = True

  for path in iter_explicit_rule_files(repo, commit_template_path):
    text = load_text_file(path)
    if text is None:
      continue
    style_family, reasons = detect_doc_style_family(text)
    if style_family is None:
      if commit_template_path and str(path) == commit_template_path:
        sources.append({
            'path': str(path),
            'style_family': 'custom',
            'reason': 'commit template exists but does not cleanly match a known family',
            'source_kind': 'commit-template',
        })
        style_votes['custom'] += 1
      continue

    source_kind = 'commit-template' if commit_template_path and str(path) == commit_template_path else 'doc'
    sources.append({
        'path': str(path),
        'style_family': style_family,
        'reason': '; '.join(dict.fromkeys(reasons[:2])) or 'explicit commit rule signal detected',
        'source_kind': source_kind,
    })
    style_votes[style_family] += 2 if source_kind == 'commit-template' else 1
    if style_family == 'gitmoji':
      repo_has_gitmoji_signal = True

  explicit_rule_style_family = None
  for style in ('gitmoji', 'conventional', 'plain', 'custom'):
    if style_votes.get(style):
      explicit_rule_style_family = style
      break

  return {
      'commit_template_path': commit_template_path,
      'explicit_rule_sources': sources or None,
      'repo_has_explicit_commit_rule': bool(sources),
      'explicit_rule_style_family': explicit_rule_style_family,
      'repo_has_gitmoji_signal': repo_has_gitmoji_signal,
  }


def classify_history_style(subjects: list[str]) -> dict[str, object | None]:
  family_counts: Counter[str] = Counter(subject_style_family(subject) for subject in subjects)
  recent_emoji_counts: Counter[str] = Counter()
  for subject in subjects:
    emoji = extract_leading_emoji(subject)
    if emoji:
      recent_emoji_counts[emoji] += 1

  total = sum(family_counts.values())
  top_family = None
  top_count = 0
  second_count = 0
  if family_counts:
    ranked = family_counts.most_common()
    top_family, top_count = ranked[0]
    second_count = ranked[1][1] if len(ranked) > 1 else 0

  history_style_family = 'mixed'
  history_style_confidence = 'low'
  if total == 0:
    history_style_family = 'unknown'
  elif top_family and top_count >= 3:
    ratio = top_count / total
    delta = top_count - second_count
    if ratio >= 0.75 and delta >= 2:
      history_style_family = top_family
      history_style_confidence = 'high'
    elif ratio >= 0.6 and delta >= 1:
      history_style_family = top_family
      history_style_confidence = 'medium'

  return {
      'history_style_family': history_style_family,
      'history_style_confidence': history_style_confidence,
      'recent_emoji_counts': dict(recent_emoji_counts) or None,
  }


def generate_scope_candidates(path: str) -> list[str]:
  parts = Path(path).parts
  if not parts:
    return []

  candidates: list[str] = []
  seen: set[str] = set()

  def normalize_token(value: str) -> str:
    return Path(value).stem or value

  def push(value: str) -> None:
    if value and value not in seen:
      seen.add(value)
      candidates.append(value)

  if len(parts) >= 2 and parts[0] in MONOREPO_SCOPE_ROOTS:
    root = parts[0]
    name = parts[1]
    short = root[0]
    singular = MONOREPO_SCOPE_ROOTS[root]
    push(f'{short}:{name}')
    push(f'{singular}:{name}')
    push(f'{root}/{name}')
    push(normalize_token(name))
    return candidates

  first = parts[0]
  if first not in GENERIC_DIR_NAMES:
    push(normalize_token(first))
  elif len(parts) >= 2:
    push(normalize_token(parts[1]))
  return candidates


def infer_path_scopes(staged_files: list[str], scope_counts: dict[str, int]) -> list[str]:
  scope_candidates: list[str] = []
  for path in staged_files:
    candidates = generate_scope_candidates(path)
    if not candidates:
      continue

    preferred = None
    for candidate in candidates:
      if scope_counts.get(candidate):
        preferred = candidate
        break
    if preferred is None:
      preferred = candidates[0]
    if preferred not in scope_candidates:
      scope_candidates.append(preferred)

  return scope_candidates[:3]


def should_use_scope(path_scope_hints: list[str], scope_counts: dict[str, int]) -> bool:
  if scope_counts:
    return True
  if len(path_scope_hints) > 1:
    return True
  return any(':' in hint or '/' in hint for hint in path_scope_hints)


def load_dependency_sections(content: str) -> dict[str, set[str]] | None:
  try:
    manifest = json.loads(content)
  except json.JSONDecodeError:
    return None
  if not isinstance(manifest, dict):
    return None

  sections: dict[str, set[str]] = {}
  for key in DEPENDENCY_SECTION_KEYS:
    value = manifest.get(key)
    if isinstance(value, dict):
      sections[key] = {name for name in value if isinstance(name, str)}
  return sections


def detect_manifest_dependency_delta(repo: Path, path: str) -> tuple[set[str], set[str]]:
  ok_head, head_content = git_optional(repo, 'show', f'HEAD:{path}')
  ok_staged, staged_content = git_optional(repo, 'show', f':{path}')

  head_sections = load_dependency_sections(head_content) if ok_head else {}
  staged_sections = load_dependency_sections(staged_content) if ok_staged else {}
  if head_sections is None or staged_sections is None:
    return set(), set()

  added: set[str] = set()
  removed: set[str] = set()
  for key in DEPENDENCY_SECTION_KEYS:
    head_values = head_sections.get(key, set())
    staged_values = staged_sections.get(key, set())
    added.update(staged_values - head_values)
    removed.update(head_values - staged_values)
  return added, removed


def add_signal(
    signals: dict[str, dict[str, object]],
    signal: str,
    reason: str,
    weight: int | None = None,
) -> None:
  score = weight if weight is not None else SIGNAL_WEIGHTS.get(signal, 1)
  existing = signals.get(signal)
  if existing is None:
    signals[signal] = {'signal': signal, 'score': score, 'reasons': [reason]}
    return

  if reason not in existing['reasons']:
    existing['reasons'].append(reason)
  if score > existing['score']:
    existing['score'] = score


def detect_semantic_signals(
    repo: Path,
    staged_files: list[str],
    name_status: list[tuple[str, list[str]]],
    staged_diff: str,
) -> list[dict[str, object]]:
  if not staged_files and not name_status:
    return []

  signals: dict[str, dict[str, object]] = {}
  diff_content = get_diff_content_lines(staged_diff)
  added_content = [
      line[1:]
      for line in staged_diff.splitlines()
      if line.startswith('+') and not line.startswith('+++ ')
  ]
  removed_content = [
      line[1:]
      for line in staged_diff.splitlines()
      if line.startswith('-') and not line.startswith('--- ')
  ]
  lowered_diff = '\n'.join(line.lower() for line in diff_content)

  for status, paths in name_status:
    normalized = status[0]
    if normalized == 'R':
      add_signal(signals, 'move', 'staged diff renames or moves files', weight=12)
      if len(paths) >= 2 and Path(paths[0]).parent != Path(paths[-1]).parent:
        add_signal(signals, 'structure', 'renamed files cross directories or package boundaries', weight=8)
    elif normalized == 'D':
      add_signal(signals, 'deletion', 'staged diff deletes files', weight=10)
    elif normalized == 'A':
      add_signal(signals, 'feature', 'staged diff adds new files', weight=5)

    for path in paths:
      lowered_path = path.lower()
      for signal, keywords in PATH_SIGNAL_RULES:
        if any(keyword in lowered_path for keyword in keywords):
          add_signal(signals, signal, f'file path matches {signal} patterns: {path}')

      if lowered_path.endswith(('index.ts', 'index.tsx', 'mod.ts')) or '/routes/' in lowered_path:
        add_signal(signals, 'structure', f'file path suggests routing or barrel structure changes: {path}')

      if lowered_path.endswith(PACKAGE_MANIFEST_FILES):
        add_signal(signals, 'tooling', f'package manifest or lockfile changed: {path}', weight=7)

  if any(text_contains_keyword(lowered_diff, keyword) for keyword in CRITICAL_BUG_KEYWORDS):
    add_signal(signals, 'critical-bug', 'staged diff includes critical bug or hotfix keywords')
  if any(text_contains_keyword(lowered_diff, keyword) for keyword in BUGFIX_KEYWORDS):
    add_signal(signals, 'bugfix', 'staged diff includes broken behavior, error, or validation keywords')

  for signal, keywords in DIFF_KEYWORD_GROUPS.items():
    if any(text_contains_keyword(lowered_diff, keyword) for keyword in keywords):
      add_signal(signals, signal, f'staged diff includes {signal}-oriented keywords')

  if any(
      line.lower().startswith(('export *', 'export {')) or ' from "./' in line.lower() or " from './" in line.lower()
      for line in added_content + removed_content):
    add_signal(signals, 'structure', 'staged diff changes exports or internal module paths', weight=9)

  added_dependencies: set[str] = set()
  removed_dependencies: set[str] = set()
  for path in staged_files:
    if not path.endswith('package.json'):
      continue
    added, removed = detect_manifest_dependency_delta(repo, path)
    added_dependencies.update(added)
    removed_dependencies.update(removed)

  if added_dependencies:
    preview = ', '.join(sorted(added_dependencies)[:3])
    add_signal(signals, 'dependency-add', f'dependency manifest adds packages: {preview}', weight=12)
    add_signal(signals, 'tooling', f'dependency change affects tooling or package graph: {preview}', weight=8)
  if removed_dependencies:
    preview = ', '.join(sorted(removed_dependencies)[:3])
    add_signal(signals, 'dependency-remove', f'dependency manifest removes packages: {preview}', weight=12)
    add_signal(signals, 'tooling', f'dependency change affects tooling or package graph: {preview}', weight=8)

  if removed_content and not added_content and not removed_dependencies:
    add_signal(signals, 'cleanup', 'staged diff is removal-only changes', weight=8)
  elif len(removed_content) >= 5 and len(removed_content) > len(added_content) * 2:
    add_signal(signals, 'cleanup', 'staged diff removes substantially more code than it adds', weight=7)

  if staged_files:
    add_signal(signals, 'modify', 'staged files exist but no stronger semantic category fully dominates')

  return sorted(
      signals.values(),
      key=lambda item: (
          -int(item['score']),
          -CATEGORY_SPECIFICITY.get(str(item['signal']), 0),
          str(item['signal']),
      ),
  )


def summarize_semantics(
    internal_signals: list[dict[str, object]],
) -> dict[str, object | None]:
  if not internal_signals:
    return {
        'semantic_category': 'modify',
        'semantic_candidates': [{'signal': 'modify', 'score': 1, 'reasons': ['no staged semantic signals detected']}],
        'semantic_confidence': 'low',
        'is_bugfix_confident': False,
        'presentational_change_likelihood': 'low',
        'gitmoji_signal_summary': [{'signal': 'modify', 'score': 1, 'reasons': ['no staged semantic signals detected']}],
    }

  internal_lookup = {
      item['signal']: item
      for item in internal_signals
      if isinstance(item.get('signal'), str)
  }
  global_scores: dict[str, dict[str, object]] = {}
  reasons_by_signal: dict[str, list[str]] = {}

  def add_global(signal: str, score: int, reasons: list[str]) -> None:
    existing = global_scores.get(signal)
    if existing is None:
      global_scores[signal] = {'signal': signal, 'score': score}
      reasons_by_signal[signal] = list(reasons)
      return
    if score > int(existing['score']):
      existing['score'] = score
    for reason in reasons:
      if reason not in reasons_by_signal[signal]:
        reasons_by_signal[signal].append(reason)

  for signal in internal_signals:
    name = signal['signal']
    score = int(signal['score'])
    reasons = [reason for reason in signal.get('reasons', []) if isinstance(reason, str)]
    if name in SEMANTIC_CATEGORIES:
      add_global(name, score, reasons)
    elif name in {'dependency-add', 'dependency-remove'}:
      add_global('tooling', max(score, 8), reasons)
    elif name == 'deletion':
      add_global('cleanup', max(score - 1, 6), reasons)

  candidates = sorted(
      (
          {
              'signal': signal,
              'score': int(payload['score']),
              'reasons': reasons_by_signal.get(signal, [])[:4],
          }
          for signal, payload in global_scores.items()
      ),
      key=lambda item: (
          -int(item['score']),
          -CATEGORY_SPECIFICITY.get(str(item['signal']), 0),
          str(item['signal']),
      ),
  )

  if not candidates:
    candidates = [{'signal': 'modify', 'score': 1, 'reasons': ['no global semantic category matched']}]

  top = candidates[0]
  second = candidates[1] if len(candidates) > 1 else None
  delta = int(top['score']) - int(second['score']) if second else int(top['score'])

  presentational_score = max(
      global_scores.get('ui-style', {'score': 0})['score'],
      global_scores.get('responsive', {'score': 0})['score'],
  )
  presentational_change_likelihood = 'low'
  if int(presentational_score) >= 8:
    presentational_change_likelihood = 'high'
  elif int(presentational_score) >= 5:
    presentational_change_likelihood = 'medium'

  bugfix_score = max(
      int(global_scores.get('bugfix', {'score': 0})['score']),
      int(global_scores.get('critical-bug', {'score': 0})['score']),
  )
  bugfix_confident = bool(
      bugfix_score >= 8 and delta >= 2 and presentational_change_likelihood != 'high'
  )
  if global_scores.get('critical-bug'):
    bugfix_confident = True

  semantic_category = str(top['signal'])
  if semantic_category in {'bugfix', 'critical-bug'} and not bugfix_confident:
    replacement = next(
        (
            item
            for item in candidates[1:]
            if item['signal'] not in {'bugfix', 'critical-bug'}
        ),
        None,
    )
    semantic_category = str(replacement['signal']) if replacement else 'modify'

  semantic_confidence = 'low'
  if semantic_category == 'modify':
    semantic_confidence = 'low'
  elif delta >= 4 and int(top['score']) >= 8:
    semantic_confidence = 'high'
  elif delta >= 2 and int(top['score']) >= 5:
    semantic_confidence = 'medium'

  if semantic_category in {'bugfix', 'critical-bug'} and not bugfix_confident:
    semantic_confidence = 'low'

  return {
      'semantic_category': semantic_category,
      'semantic_candidates': candidates,
      'semantic_confidence': semantic_confidence,
      'is_bugfix_confident': bugfix_confident,
      'presentational_change_likelihood': presentational_change_likelihood,
      'gitmoji_signal_summary': internal_signals,
  }


def build_gitmoji_catalog(
    gitmoji_constraints: dict[str, object | None],
    should_use_gitmoji: bool,
) -> list[dict[str, object]]:
  details = gitmoji_constraints.get('allowed_gitmoji_details')
  if isinstance(details, list) and details:
    return [detail for detail in details if isinstance(detail, dict)]
  if should_use_gitmoji:
    return build_default_gitmoji_catalog()
  return []


def build_fallback_gitmoji(
    catalog: list[dict[str, object]],
    recent_emoji_counts: dict[str, int] | None,
) -> dict[str, object] | None:
  fallback = next(
      (
          item
          for item in catalog
          if isinstance(item, dict) and item.get('is_fallback')
      ),
      None,
  )
  if isinstance(fallback, dict):
    return {
        'emoji': fallback.get('emoji'),
        'code': fallback.get('code'),
        'description': fallback.get('description'),
        'source': 'catalog-fallback',
    }

  if recent_emoji_counts:
    ranked = sorted(recent_emoji_counts.items(), key=lambda item: (-item[1], item[0]))
    if ranked:
      emoji = ranked[0][0]
      return {
          'emoji': emoji,
          'code': None,
          'description': 'Most common recent emoji from local history.',
          'source': 'history-fallback',
      }
  return None


def matching_signals_for_category(
    category: str,
    signal_lookup: dict[str, dict[str, object]],
) -> list[dict[str, object]]:
  aliases = {
      'critical-bug': ('bugfix',),
      'cleanup': ('modify',),
      'tooling': ('config',),
  }
  matches: list[dict[str, object]] = []
  direct = signal_lookup.get(category)
  if direct is not None:
    matches.append(direct)
  for alias in aliases.get(category, ()):
    alias_match = signal_lookup.get(alias)
    if alias_match is not None and alias_match not in matches:
      matches.append(alias_match)
  return matches


def recommend_gitmoji(
    catalog: list[dict[str, object]],
    internal_signals: list[dict[str, object]],
    recent_emoji_counts: dict[str, int] | None,
) -> dict[str, object | None]:
  payload: dict[str, object | None] = {
      'gitmoji_recommendations': None,
      'recommended_gitmoji': None,
      'requires_human_gitmoji_review': False,
  }
  if not catalog:
    return payload

  signal_lookup = {
      item['signal']: item
      for item in internal_signals
      if isinstance(item.get('signal'), str)
  }
  candidates: list[dict[str, object]] = []
  for detail in catalog:
    primary_categories = [
        category
        for category in detail.get('semantic_primary', [])
        if isinstance(category, str)
    ]
    secondary_categories = [
        category
        for category in detail.get('semantic_secondary', [])
        if isinstance(category, str)
    ]
    if not primary_categories and not secondary_categories:
      continue

    score = int(detail.get('semantic_specificity', 0))
    matched_primary: list[str] = []
    matched_secondary: list[str] = []
    reasons: list[str] = []

    for category in primary_categories:
      for match in matching_signals_for_category(category, signal_lookup):
        score += int(match.get('score', 0)) * 10
        if category not in matched_primary:
          matched_primary.append(category)
        for reason in match.get('reasons', []):
          if isinstance(reason, str) and reason not in reasons:
            reasons.append(reason)

    for category in secondary_categories:
      for match in matching_signals_for_category(category, signal_lookup):
        score += int(match.get('score', 0)) * 4
        if category not in matched_secondary:
          matched_secondary.append(category)
        for reason in match.get('reasons', []):
          if isinstance(reason, str) and reason not in reasons:
            reasons.append(reason)

    if recent_emoji_counts:
      score += recent_emoji_counts.get(str(detail.get('emoji')), 0) * 2

    if detail.get('is_fallback') and any(signal_name != 'modify' for signal_name in signal_lookup):
      score -= 8

    if not matched_primary and not matched_secondary and not detail.get('is_fallback'):
      continue

    candidates.append({
        'emoji': detail.get('emoji'),
        'code': detail.get('code'),
        'description': detail.get('description'),
        'semantic_primary': primary_categories,
        'semantic_secondary': secondary_categories,
        'semantic_categories': detail.get('semantic_categories'),
        'semantic_source': detail.get('semantic_source'),
        'score': score,
        'matched_primary': matched_primary,
        'matched_secondary': matched_secondary,
        'reasons': reasons[:4],
        'is_fallback': bool(detail.get('is_fallback')),
    })

  if not candidates:
    payload['requires_human_gitmoji_review'] = True
    return payload

  candidates.sort(
      key=lambda item: (
          -int(item['score']),
          -len(item['matched_primary']),
          1 if item.get('is_fallback') else 0,
          str(item.get('emoji')),
      )
  )
  payload['gitmoji_recommendations'] = candidates[:5]
  payload['recommended_gitmoji'] = candidates[0]
  return payload


def infer_body_policy(
    recent_messages: list[dict[str, str]],
    commit_template_path: str | None,
) -> str:
  if commit_template_path:
    return 'body-required'
  if not recent_messages:
    return 'title-only-preferred'

  body_ratio = sum(1 for message in recent_messages if message.get('body')) / len(recent_messages)
  if body_ratio >= 0.7:
    return 'body-optional'
  if body_ratio >= 0.25:
    return 'body-optional'
  return 'title-only-preferred'


def select_style_family(
    explicit_rules: dict[str, object | None],
    history_style: dict[str, object | None],
) -> dict[str, object]:
  explicit_style = explicit_rules.get('explicit_rule_style_family')
  history_family = history_style.get('history_style_family')
  history_confidence = history_style.get('history_style_confidence')

  if explicit_rules.get('repo_has_explicit_commit_rule'):
    selected = explicit_style if explicit_style in STYLE_FAMILIES else 'conventional'
    if selected == 'custom':
      selected = history_family if history_family in {'conventional', 'gitmoji', 'plain'} and history_confidence in {'high', 'medium'} else 'conventional'
    return {
        'style_mode': 'repo-local-explicit',
        'selected_style_family': selected,
        'fallback_commit_style': selected if selected in {'gitmoji', 'plain'} else 'conventional',
    }

  if history_family in {'conventional', 'gitmoji', 'plain'} and history_confidence in {'high', 'medium'}:
    return {
        'style_mode': 'history-inferred',
        'selected_style_family': history_family,
        'fallback_commit_style': history_family if history_family in {'gitmoji', 'plain'} else 'conventional',
    }

  return {
      'style_mode': 'fallback-conventional',
      'selected_style_family': 'conventional',
      'fallback_commit_style': 'conventional',
  }


def infer_preferred_title_pattern(
    selected_style_family: str,
    preferred_scope: str | None,
) -> str:
  if selected_style_family == 'gitmoji':
    return 'emoji + scope + summary' if preferred_scope else 'emoji + summary'
  if selected_style_family == 'plain':
    return 'summary'
  return 'type(scope): summary' if preferred_scope else 'type: summary'


def build_repo_style_hint(
    style_mode: str,
    selected_style_family: str,
    body_policy: str,
    should_use_gitmoji: bool,
) -> str:
  if style_mode == 'fallback-conventional':
    return 'No strong repo-local commit rule was detected, so the helper falls back to Conventional Commits.'
  if selected_style_family == 'gitmoji':
    body_hint = 'title-only by default' if body_policy == 'title-only-preferred' else 'short body bullets when needed'
    if should_use_gitmoji:
      return f'This repository is treated as gitmoji/emoji-based, with {body_hint}.'
  if selected_style_family == 'plain':
    return 'This repository is treated as plain imperative style with an optional body.'
  return 'This repository is treated as Conventional Commits with semantic type selection.'


def inspect_repo(repo: Path, limit: int = 30) -> dict[str, object | None]:
  if not is_git_repository(repo):
    raise ValueError(f'Not a git repository: {repo}')

  recent_messages = get_recent_messages(repo, limit)
  subjects = [message['subject'] for message in recent_messages if message.get('subject')]
  pattern_counts: dict[str, int] = {}
  scope_counts: dict[str, int] = {}
  for subject in subjects:
    pattern = classify_subject(subject)
    pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1
    scope = extract_scope(subject)
    if scope:
      scope_counts[scope] = scope_counts.get(scope, 0) + 1

  gitmoji_constraints = detect_gitmoji_constraints(repo)
  explicit_rules = detect_explicit_commit_rules(repo, gitmoji_constraints)
  history_style = classify_history_style(subjects)
  phrasing_profile = analyze_phrasing_profile(subjects)
  selected_style = select_style_family(explicit_rules, history_style)
  repo_has_gitmoji_signal = bool(
      explicit_rules.get('repo_has_gitmoji_signal') or history_style.get('history_style_family') == 'gitmoji'
  )
  should_use_gitmoji = bool(
      selected_style.get('selected_style_family') == 'gitmoji' and (
          explicit_rules.get('repo_has_gitmoji_signal') or history_style.get('history_style_family') == 'gitmoji'
      )
  )

  staged_files = get_staged_files(repo)
  staged_name_status = get_staged_name_status(repo)
  staged_diff = get_staged_diff(repo)
  path_scope_hints = infer_path_scopes(staged_files, scope_counts)
  preferred_scope = ', '.join(path_scope_hints) if should_use_scope(path_scope_hints, scope_counts) else None
  body_policy = infer_body_policy(recent_messages, explicit_rules.get('commit_template_path'))
  preferred_title_pattern = infer_preferred_title_pattern(
      str(selected_style['selected_style_family']),
      preferred_scope,
  )

  internal_signals = detect_semantic_signals(repo, staged_files, staged_name_status, staged_diff)
  semantic_summary = summarize_semantics(internal_signals)
  if (
      selected_style['style_mode'] == 'fallback-conventional'
      and semantic_summary.get('semantic_confidence') == 'low'
  ):
    semantic_summary['semantic_category'] = 'modify'

  catalog = build_gitmoji_catalog(gitmoji_constraints, should_use_gitmoji)
  fallback_gitmoji = build_fallback_gitmoji(
      catalog,
      history_style.get('recent_emoji_counts') if isinstance(history_style.get('recent_emoji_counts'), dict) else None,
  )
  gitmoji_recommendation = recommend_gitmoji(
      catalog,
      internal_signals,
      history_style.get('recent_emoji_counts') if isinstance(history_style.get('recent_emoji_counts'), dict) else None,
  )

  if not should_use_gitmoji:
    gitmoji_recommendation['recommended_gitmoji'] = None
    gitmoji_recommendation['gitmoji_recommendations'] = None
    gitmoji_recommendation['requires_human_gitmoji_review'] = False
    fallback_gitmoji = None
  elif semantic_summary.get('semantic_confidence') == 'low' and fallback_gitmoji is not None:
    gitmoji_recommendation['recommended_gitmoji'] = None
    gitmoji_recommendation['requires_human_gitmoji_review'] = False
  elif semantic_summary.get('semantic_confidence') == 'low' and fallback_gitmoji is None:
    gitmoji_recommendation['recommended_gitmoji'] = None
    gitmoji_recommendation['requires_human_gitmoji_review'] = True

  payload = {
      'repo': repo.name,
      'repo_path': str(repo),
      'branch': git(repo, 'rev-parse', '--abbrev-ref', 'HEAD'),
      'commit_template_path': explicit_rules.get('commit_template_path'),
      'style_mode': selected_style['style_mode'],
      'selected_style_family': selected_style['selected_style_family'],
      'explicit_rule_style_family': explicit_rules.get('explicit_rule_style_family'),
      'history_style_family': history_style.get('history_style_family'),
      'history_style_confidence': history_style.get('history_style_confidence'),
      'repo_has_explicit_commit_rule': explicit_rules.get('repo_has_explicit_commit_rule'),
      'repo_has_gitmoji_signal': repo_has_gitmoji_signal,
      'should_use_gitmoji': should_use_gitmoji,
      'fallback_commit_style': selected_style['fallback_commit_style'],
      'fallback_gitmoji': fallback_gitmoji,
      'requires_human_gitmoji_review': gitmoji_recommendation.get('requires_human_gitmoji_review'),
      'dominant_pattern': max(pattern_counts.items(), key=lambda item: item[1])[0] if pattern_counts else None,
      'preferred_title_pattern': preferred_title_pattern,
      'preferred_scope': preferred_scope,
      'body_policy': body_policy,
      'pattern_counts': pattern_counts,
      'scope_counts': scope_counts,
      'path_scope_hints': path_scope_hints,
      'staged_files': staged_files,
      'recent_subjects': subjects[:RECENT_SUBJECT_LIMIT],
      'explicit_rule_sources': explicit_rules.get('explicit_rule_sources'),
      'repo_style_hint': build_repo_style_hint(
          str(selected_style['style_mode']),
          str(selected_style['selected_style_family']),
          body_policy,
          should_use_gitmoji,
      ),
      **gitmoji_constraints,
      **phrasing_profile,
      **semantic_summary,
      **gitmoji_recommendation,
  }
  return payload


def main() -> int:
  parser = argparse.ArgumentParser(description='Inspect commit style and staged change semantics.')
  parser.add_argument('repo', help='Path to the target git repository')
  parser.add_argument('--limit', type=int, default=30, help='Number of recent commits to inspect')
  args = parser.parse_args()

  repo = Path(args.repo).resolve()
  try:
    payload = inspect_repo(repo, args.limit)
  except ValueError as exc:
    raise SystemExit(str(exc)) from exc

  json.dump(payload, sys.stdout, indent=2, ensure_ascii=False)
  sys.stdout.write('\n')
  return 0


if __name__ == '__main__':
  raise SystemExit(main())
