---
name: update-evidence-docs
description: 작업 완료 후 docs/ai/CURRENT_STATE.md, TEST_HISTORY.md, NEXT_ACTIONS.md 등 증거 문서 갱신 (rule 70). 사용자가 "문서 갱신", "증거 기록" 등 요청 시 또는 작업 종료 직전. - 작업 종료 시 / Round 검증 후 / PR 머지 후
---

# update-evidence-docs

## 목적

server-exporter 증거 문서 갱신. rule 70 트리거 표 따라 일관 적용.

## 갱신 대상

| 트리거 | 갱신 대상 |
|---|---|
| 기능 추가/수정 | docs/ai/CURRENT_STATE.md |
| 테스트 수행 | docs/ai/catalogs/TEST_HISTORY.md + tests/evidence/ |
| 구조 / 모듈 변경 | docs/ai/catalogs/PROJECT_MAP.md + fingerprint 갱신 |
| 컨벤션 위반 발견 | docs/ai/catalogs/CONVENTION_DRIFT.md (DRIFT-NNN) |
| 보안 이슈 | docs/ai/policy/SECURITY_POLICY.md |
| 다음 작업 식별 | docs/ai/NEXT_ACTIONS.md |
| 실패·반복 실수 | docs/ai/catalogs/FAILURE_PATTERNS.md (append-only) |
| Round 검증 | tests/evidence/<날짜>-<vendor>.md + docs/reference/decision-log.md |
| 외부 시스템 계약 변경 | docs/ai/catalogs/EXTERNAL_CONTRACTS.md |
| 벤더 어댑터 추가 | docs/ai/catalogs/VENDOR_ADAPTERS.md + .claude/ai-context/vendors/ |

## 절차

1. **변경 commit 식별**: `git log --oneline -10`
2. **각 commit이 어떤 트리거에 해당** 분류
3. **갱신 대상 list** 정리
4. **각 문서 갱신** (in-place)
5. **PROJECT_MAP fingerprint** 갱신 (구조 변경 시):
   ```bash
   python scripts/ai/check_project_map_drift.py --update
   ```
6. **surface-counts.yaml** 갱신 (.claude/ 변경 시):
   ```bash
   python scripts/ai/hooks/pre_commit_harness_drift.py --update
   ```
7. **commit**: `docs: docs/ai/* 갱신`

## 적용 rule / 관련

- **rule 70** (docs-and-evidence-policy) 정본
- rule 28 (empirical-verification-lifecycle)
- skill: `measure-reality-snapshot`
- agent: `docs-sync-worker`
- template: `.claude/templates/{CURRENT_STATE,NEXT_ACTIONS,TEST_HISTORY}.template.md`
