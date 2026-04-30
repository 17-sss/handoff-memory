# commit-helper

영문 문서: [README.md](./README.md)

여러 저장소에서 재사용 가능한 범용 commit helper입니다. explicit repo-local rule, recent history, staged diff를 함께 보고 Conventional Commits, gitmoji/emoji style, plain imperative style, repo-custom template 중 현재 저장소에 맞는 스타일 패밀리를 선택합니다. 형식뿐 아니라 최근 히스토리에서 문체/톤도 추론해 팀이 실제로 쓰는 commit 제목 느낌에 더 가깝게 맞추려 합니다.

## 사용 시점

- 사용자가 커밋 메시지를 만들어 달라고 할 때
- staged 변경사항을 커밋하려는데 현재 저장소의 스타일이 애매할 때
- 방금 작업한 저장소와 이번 저장소의 커밋 규칙이 다를 수 있을 때
- emoji 기반 커밋 저장소가 로컬 allowlist를 둘 수 있을 때

## 주요 파일

- `scripts/inspect_commit_style.py`
- `scripts/draft_commit_message.py`
- `references/commit-patterns.md`
- `evals/behavior_cases.json`

## 현재 보장하는 동작

- `explicit local rules > recent history > conservative fallback` 우선순위를 따릅니다
- 강한 신호가 없으면 Conventional Commit을 기본 fallback으로 사용합니다
- gitmoji는 repo-local config, repo 문서, emoji-dominant history가 있을 때만 강하게 활성화합니다
- semantic inference는 전역 규칙으로 유지하고, 표현 형식만 repo별 스타일에 맞게 바꿉니다
- commit `format`과 commit `phrasing`을 분리해 다룹니다
- dominant language, tone, title length, common Korean action noun 같은 wording profile을 추론합니다
- `draft_commit_message.py`를 사실상 표준 실행 경로로 사용해 literal `\n` 없는 안전한 commit body를 만듭니다
