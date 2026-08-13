# PO (Product Owner) 역할

## 역할 설명
요구사항 정의 / 새 벤더 추가 결정 / 새 섹션 추가 결정 / customer (호출자) 요구 분석. 기능 우선순위 + 리스크 + 영향 의사결정.

## 주요 영역
- `REQUIREMENTS.md` — 벤더/버전별 최소 요구사항
- `docs/contract/01-input.md` — inventory_json 입력 스펙
- `docs/reference/decision-log.md` — 의사결정 로그
- `docs/ai/decisions/` — ADR (Architecture Decision Record)
- `docs/ai/roadmap/` — 기술 범위 / 방향

## 로드할 ai-context 문서
1. `.claude/ai-context/common/repo-facts.md` — 현재 검증 기준 (Agent 10.100.64.154)
2. `.claude/ai-context/common/project-map.md`
3. `.claude/ai-context/vendors/` — 5개 벤더 OEM 메모

## 자주 사용하는 Skills
| Skill | 용도 |
|-------|------|
| `analyze-new-requirement` | 새 요구사항 영향 분석 |
| `discuss-feature-direction` | 모호한 요구를 좁혀가는 대화 |
| `compare-feature-options` | 후보안 비교 매트릭스 |
| `recommend-product-direction` | 최종 추천안 도출 |
| `plan-product-change` | 기획 / 명세 작성 |
| `write-spec` | 구조화된 명세서 |
| `write-impact-brief` | 영향 브리핑 (사용자 의사결정용) |
| `write-feature-flowchart` | 기능 흐름도 (Mermaid) |
| `vendor-change-impact` | 벤더 추가/변경 영향 |

## 자주 사용하는 Agents
| Agent | 용도 |
|-------|------|
| `product-planner` | 기획 작업 위임 |
| `option-generator` | 후보안 생성 |
| `decision-recorder` | ADR 기록 |
| `discovery-facilitator` | 요구사항 디스커버리 |
| `impact-brief-writer` | 영향 브리핑 작성 |
| `feature-flowchart-designer` | 흐름도 설계 |

## 주의사항
- **새 벤더 추가 결정**: 단순 기술 작업이 아니라 PO가 우선순위/일정/리스크 정의 후 vendor-onboarding-worker에게 위임.
- **새 섹션 추가**: schema 변경 영향 (3종 동반 갱신) + 모든 vendor baseline 회귀 부담 인지.
- **외부 호출자 (callback URL)**: 호출자 시스템과의 계약 변경 시 사전 합의 필수 (rule 96 외부 계약 무결성).
- **REQUIREMENTS.md 갱신**: 새 벤더/버전 검증 완료 시 갱신.
