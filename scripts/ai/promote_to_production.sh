#!/usr/bin/env bash
# scripts/ai/promote_to_production.sh
#
# main 의 순수 게더링 코드(하네스 제외)를 production 으로 자동 승격한다.
# rule 24 (완료 게이트) / rule 93 — 작업 완료 시 자동 호출 (사용자 명시 2026-06-30:
# "production 에 넣는건 자동이여야 한다"). 사용자 per-instance 승인 불요.
#
# 불변식:
#   - 하네스 경로(.claude/, CLAUDE.md, GUIDE_FOR_AI.md, docs/ai/, docs/superpowers/,
#     scripts/ai/, tests/reference/, tests/evidence/)는 절대 production 에 올리지 않는다.
#   - `git merge main -> production` 금지 — 파일 state sync 방식 (하네스 누출 차단).
#   - production 은 하네스-free 브랜치라 pre-commit 훅(scripts/ai/hooks/*)이 물리적으로
#     부재 → --no-verify 가 정당한 유일 커밋 방법.
#   - force push 금지.
#
# 사용: bash scripts/ai/promote_to_production.sh ["sync 커밋 메시지"]
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# 하네스 경로 정규식 (rule 00 / CLAUDE.md 의 "하네스로 분류" 목록과 일치)
HARNESS_RE='^(\.claude/|CLAUDE\.md|GUIDE_FOR_AI\.md|docs/ai/|docs/superpowers/|scripts/ai/|tests/reference/|tests/evidence/)'

cur="$(git branch --show-current)"
if [ "$cur" != "main" ]; then
  echo "[promote] main 에서만 실행한다 (현재: $cur) — skip"
  exit 0
fi
if [ -n "$(git status --porcelain --untracked-files=no)" ]; then
  echo "[promote] 미커밋 변경이 있다 — 먼저 main 에 commit 하라. 중단."
  exit 1
fi

git fetch origin --quiet 2>/dev/null || true

# production ↔ main 차이 파일 중 하네스 제외 = 순수 게더링 코드
mapfile -t pure < <(git diff --name-only origin/production main | grep -vE "$HARNESS_RE" || true)
if [ "${#pure[@]}" -eq 0 ]; then
  echo "[promote] 순수 코드 차이 없음 — production 이미 최신."
  exit 0
fi

echo "[promote] 순수 코드 ${#pure[@]} 파일 → production:"
printf '  %s\n' "${pure[@]}"

git checkout production --quiet

# 2026-08-13 수정: 종전에는 존재/삭제 파일을 한 번에 `git checkout main -- "${pure[@]}"`
#   로 넘기고 실패를 `2>/dev/null || true` 로 삼켰다. `git checkout` 은 **경로 하나라도
#   main 에 없으면 전체가 실패**하므로, 삭제 파일이 하나라도 섞이면 checkout 이 통째로
#   무산됐다. 그런데 뒤이은 `git rm` 루프는 정상 동작해서 **삭제만 반영되고 수정은
#   누락된 production** 이 만들어졌다 (실제 발생: 2026-08-13 승격에서 vault 12개 삭제만
#   반영되고 redfish_gather.py 등 수정 파일이 빠졌다).
#   → 존재 파일과 삭제 파일을 먼저 나누고, 실패를 삼키지 않는다.
exists=(); gone=()
for f in "${pure[@]}"; do
  if git cat-file -e "main:$f" 2>/dev/null; then exists+=("$f"); else gone+=("$f"); fi
done

if [ "${#exists[@]}" -gt 0 ]; then
  # 경로가 많으면 command line 길이 한계에 걸릴 수 있어 나눠서 적용한다.
  printf '%s\0' "${exists[@]}" | xargs -0 -n 200 git checkout main --
fi
for f in "${gone[@]}"; do
  git rm -q --ignore-unmatch -- "$f"   # main 에서 삭제된 파일은 production 에서도 삭제
done

# 적용 결과 검증 — 순수 코드가 실제로 main 과 같아졌는가.
#   여기서 확인하지 않으면 "일부만 반영된 production" 을 성공으로 보고하게 된다.
if [ "${#exists[@]}" -gt 0 ]; then
  if ! git diff --quiet main -- "${exists[@]}"; then
    echo "[promote] 순수 코드가 main 과 일치하지 않는다 — 롤백 후 중단."
    git diff --name-only main -- "${exists[@]}" | head -20
    git reset --hard --quiet
    git checkout main --quiet
    exit 1
  fi
fi

# 하네스 누출 최종 방어 (어떤 이유로든 하네스가 staged 되면 롤백)
if git diff --cached --name-only | grep -qE "$HARNESS_RE"; then
  echo "[promote] 하네스 누출 감지 — 롤백 후 중단."
  git reset --hard --quiet
  git checkout main --quiet
  exit 1
fi

if git diff --cached --quiet; then
  echo "[promote] staged 변경 없음 — skip."
  git checkout main --quiet
  exit 0
fi

msg="${1:-sync: 순수 게더링 코드 -> production (main)}"
git commit --no-verify -q -m "$msg"
git push origin production
git checkout main --quiet
echo "[promote] 완료 — production push (origin = github + gitlab)."
