#!/usr/bin/env python3
"""사용자 프롬프트 라우팅 — 키워드 기반 skill 추천 힌트.

server-exporter 도메인 라우팅:
- "추가해줘 / 구현해줘 / 만들어줘" → task-impact-preview 먼저
- "리팩토링" → plan-feature-change → task-impact-preview
- "벤더 추가" → add-new-vendor
- "Redfish 응답 변경" → debug-external-integrated-feature
- "회귀 테스트" → prepare-regression-check
- "스케줄러 / Jenkins cron" → scheduler-change-playbook (Jenkins)

Usage:
    python scripts/ai/hooks/user_prompt_router.py (stdin payload)
"""

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# 키워드 → 추천 skill (server-exporter 도메인)
ROUTES = [
    (["추가해줘", "구현해줘", "만들어줘", "개발해줘"], "task-impact-preview",
     "코드 변경 전 영향 미리보기 권장"),
    (["리팩토링", "구조 개선", "옮겨줘"], "plan-structure-cleanup",
     "구조 정리 계획 (기능 변경 없는 lane)"),
    (["고쳐줘", "수정해줘", "버그"], "task-impact-preview",
     "버그 수정 전 영향 미리보기"),
    (["벤더 추가", "새 벤더"], "add-new-vendor",
     "벤더 추가 3단계 가이드"),
    (["Redfish", "iDRAC", "iLO", "XCC", "BMC", "redfish 응답"],
     "debug-external-integrated-feature",
     "외부 시스템 계약 질의 우선"),
    (["회귀", "regression"], "prepare-regression-check",
     "회귀 테스트 대상 선정"),
    (["스케줄러", "Jenkins cron", "cron"], "scheduler-change-playbook",
     "스케줄러/cron 변경 절차"),
    (["리뷰해줘", "코드 리뷰"], "review-existing-code",
     "코드 리뷰 (4축: 구조/품질/보안/벤더경계)"),
    (["PR", "pull request"], "pr-review-playbook",
     "PR 생성 전 체크리스트"),
    (["흐름도", "플로우차트", "다이어그램"], "mermaid-visualization",
     "Mermaid 다이어그램"),
    (["벤더 영향", "어댑터 영향"], "vendor-change-impact",
     "벤더별 영향 분석"),
    (["fragment", "Fragment"], "validate-fragment-philosophy",
     "Fragment 철학 검증 (rule 22)"),
    (["adapter score", "어댑터 점수"], "score-adapter-match",
     "Adapter 점수 디버깅"),
    (["baseline 갱신", "baseline 회귀"], "update-vendor-baseline",
     "Baseline 갱신 절차"),
    (["precheck 실패", "4단계 진단"], "debug-precheck-failure",
     "Precheck 4단계 디버깅"),
    (["vault 회전", "vault 갱신"], "rotate-vault",
     "벤더 vault 회전"),
    (["계획 세워", "어떻게 만들지", "기능 계획"], "plan-feature-change",
     "기능 변경 계획"),
    (["기획", "명세"], "plan-product-change",
     "제품 기획"),
    (["빌드 깨졌", "Jenkins 실패"], "investigate-ci-failure",
     "CI/Jenkins 실패 분석"),
]


def main() -> int:
    if sys.stdin.isatty():
        return 0
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        payload = json.loads(raw)
    except (json.JSONDecodeError, AttributeError):
        return 0

    prompt = (payload.get("prompt") or payload.get("user_prompt") or "")[:500]
    if not prompt:
        return 0

    suggestions = []
    seen = set()
    for keywords, skill, reason in ROUTES:
        for kw in keywords:
            if kw.lower() in prompt.lower() and skill not in seen:
                suggestions.append(f"  - {skill}: {reason}")
                seen.add(skill)
                break
        if len(suggestions) >= 3:
            break

    if suggestions:
        print("[router] 추천 skill (선택적):")
        for s in suggestions:
            print(s)

    return 0


if __name__ == "__main__":
    sys.exit(main())
