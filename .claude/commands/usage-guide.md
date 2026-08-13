---
description: server-exporter AI 하네스 사용법. 역할별 시작 방법과 주요 skill 호출 방법.
argument-hint: "[역할] 예: gather, qa, po"
---

# server-exporter AI 하네스 사용 가이드

이 하네스의 주요 작업 surface는 `.claude/skills/` 디렉터리.

## 핵심 Skill (server-exporter 도메인)

| Skill | 용도 | 호출 예시 |
|---|---|---|
| `analyze-new-requirement` | 새 요구사항 영향 분석 | "새 벤더 Huawei 추가 요구 분석해줘" |
| `task-impact-preview` | 코드 변경 전 영향 미리보기 | "BMC firmware 섹션 추가하면 어디 영향?" |
| `review-existing-code` | 4축 리뷰 (구조/품질/보안/벤더경계) | "redfish_gather.py 리뷰해줘" |
| `validate-fragment-philosophy` | Fragment 철학 위반 검증 | "이 PR이 다른 gather fragment 침범해?" |
| `score-adapter-match` | Adapter 점수 디버깅 | "왜 dell_idrac9가 선택 안 됐지?" |
| `add-new-vendor` | 새 벤더 추가 3단계 | "Huawei 벤더 추가하자" |
| `probe-redfish-vendor` | 새 펌웨어 프로파일링 | "iLO 6.5에 대한 deep probe" |
| `update-vendor-baseline` | 실장비 검증 후 baseline 갱신 | "Dell iDRAC9 6.x baseline 갱신" |
| `debug-precheck-failure` | 4단계 진단 디버깅 | "ping은 됐는데 protocol 실패" |
| `vendor-change-impact` | 벤더별 영향 분석 | "이 변경 Lenovo XCC에 영향?" |
| `verify-adapter-boundary` | adapter 경계 검증 | "common 코드에 vendor 하드코딩?" |
| `verify-json-output` | 출력 envelope 검증 | "callback 출력 envelope 형식 맞아?" |
| `update-output-schema-evidence` | sections + field_dictionary + baseline 정합 | "schema 변경 후 정합 갱신" |
| `prepare-regression-check` | 회귀 테스트 대상 선정 | "어떤 baseline 회귀 돌려야 해?" |
| `run-baseline-smoke` | 빠른 baseline smoke | `/run-baseline-smoke` |
| `rotate-vault` | 벤더별 vault 회전 | "Dell vault 회전" |
| `scheduler-change-playbook` | Jenkins cron 변경 절차 | "Jenkinsfile cron 시간 바꾸자" |
| `investigate-ci-failure` | Jenkins 실패 분석 | "Jenkins 빌드 깨짐 원인" |
| `pr-review-playbook` | PR 전 체크리스트 | "PR 올리기 전 체크" |

## 기획 / 계획

| Skill | 용도 |
|---|---|
| `plan-product-change` | 기획 artifact 생성 |
| `plan-feature-change` | 기능 변경 계획 |
| `plan-schema-change` | 새 섹션 / 필드 계획 |
| `plan-structure-cleanup` | 구조 정리 계획 |
| `compare-feature-options` | 후보안 매트릭스 |
| `recommend-product-direction` | 추천안 도출 |
| `discuss-feature-direction` | 모호한 요구 좁히기 |
| `write-spec` | 명세서 |
| `write-impact-brief` | 영향 브리핑 |
| `write-feature-flowchart` | Mermaid 흐름도 |

## 운영 / 하네스

| Skill | 용도 |
|---|---|
| `harness-cycle` | 하네스 self-improvement 1 cycle |
| `harness-full-sweep` | 전수조사 (1회성 대형) |
| `update-evidence-docs` | docs/ai/ 갱신 |
| `measure-reality-snapshot` | rule 28 측정 대상 재측정 |
| `pull-and-analyze-main` | origin/main 분석 |
| `review-incoming-merge` | 머지 후 자동 검증 |

## 슬래시 명령

- `/harness-cycle` — 하네스 1 cycle
- `/harness-full-sweep` — 전수조사
- `/review-guide` — 리뷰 절차
- `/scheduler-guide` — Jenkins cron 변경 절차
- `/usage-guide` — 본 가이드

## 정본

- `CLAUDE.md` — Tier 0 정본
- rule 22 (fragment-philosophy) — Fragment 철학
- `REQUIREMENTS.md` — 요구사항
- `docs/` 문서 — 운영
