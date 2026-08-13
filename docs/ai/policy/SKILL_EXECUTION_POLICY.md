# Skill Execution Policy — server-exporter

> Skill 자동 호출 / 우선순위 / 에스컬레이션 정책.

## 1. 자동 호출 (rule 91 R1)

`task-impact-preview`는 비단순 코드 변경 키워드 감지 시 **다른 skill 호출 전 자동**.

## 2. 진입점 skill (사용자 명시 호출)

| 사용자 의도 | skill |
|---|---|
| 새 요구 분석 | analyze-new-requirement |
| 모호한 요구 디스커버리 | discuss-feature-direction |
| 후보안 비교 | compare-feature-options |
| 추천 | recommend-product-direction |
| 기획 종합 | plan-product-change |
| 기능 변경 계획 | plan-feature-change |
| schema 변경 계획 | plan-schema-change |
| 구조 정리 | plan-structure-cleanup |
| 코드 리뷰 | review-existing-code |
| PR 준비 | pr-review-playbook |
| 회귀 테스트 | prepare-regression-check |
| 빠른 회귀 | run-baseline-smoke |
| TDD | write-quality-tdd |
| 명세 | write-spec |
| 영향 브리핑 | write-impact-brief |
| 흐름도 | write-feature-flowchart |
| 새 vendor | add-new-vendor |
| 펌웨어 프로파일 | probe-redfish-vendor |
| baseline 갱신 | update-vendor-baseline |
| schema 정합 갱신 | update-output-schema-evidence |
| 외부 시스템 디버그 | debug-external-integrated-feature |
| precheck 실패 | debug-precheck-failure |
| Jenkins 실패 | investigate-ci-failure |
| Vault 회전 | rotate-vault |
| 머지 후 검증 | review-incoming-merge |
| 하네스 cycle | harness-cycle |
| 하네스 전수조사 | harness-full-sweep |
| origin/main 분석 | pull-and-analyze-main |
| 측정 재 snapshot | measure-reality-snapshot |
| 문서 갱신 | update-evidence-docs |

## 3. 후속 라우팅 (`DYNAMIC_ROUTING_RULES.md` 참조)

task-impact-preview 결과 리스크별:

| 리스크 | 다음 |
|---|---|
| LOW | implement-safe-change 또는 직접 구현 |
| MED + 옵션 2+ | compare-feature-options → recommend-product-direction |
| HIGH | write-impact-brief + 사용자 명시 승인 대기 |
| Critical (벤더 경계 / schema / Jenkinsfile cron / vault) | 사용자 승인 없이 진입 금지 |

## 4. 자가 검수 금지 (rule 25 R7)

skill 결과를 사용자에게 제시하기 전, 별도 reviewer agent 호출:
- 도메인 코드 변경 → code-reviewer / fragment-engineer / vendor-boundary-guardian
- schema 변경 → schema-mapping-reviewer / output-schema-reviewer
- adapter 변경 → adapter-boundary-reviewer
- (cycle-011: security-reviewer 제거 — 보안 영향은 운영자 권장 수준 검토)
- 머지 / 릴리즈 → release-manager (이미 reviewer 역할)

## 관련

- rule 91 (task-impact-gate)
- rule 25 R7 (자가 검수 금지)
- skill: task-impact-preview, 모든 plan-*, review-* 등
- workflow: rule 91→95→92 연쇄
