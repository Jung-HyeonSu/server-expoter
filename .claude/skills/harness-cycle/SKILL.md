---
name: harness-cycle
description: server-exporter 하네스 자기개선 1 cycle 수동 트리거. 6단계 파이프라인 (observer → architect → reviewer → governor → updater → verifier). 사용자가 "/harness-cycle", "harness 사이클" 등 요청 시. - 정기 자기개선 / 사용자 피드백 수렴 / drift 누적 후
---

# harness-cycle

## 6 단계 (rule 28 + 자기개선 루프)

| 단계 | Agent | 역할 |
|---|---|---|
| 1. Observe | `harness-observer` | rule 28 측정 대상 13종 재측정 + drift 검출 |
| 2. Architect | `harness-architect` | 변경 명세 (diff 수준) — 구현 안 함 |
| 3. Review | `harness-reviewer` | 명세 검수 (자가 승인 금지, rule 25 R7) |
| 4. Govern | `harness-governor` | Tier 1/2/3 분류 + 사용자 에스컬레이션 결정 |
| 5. Update | `harness-updater` | 승인된 명세 적용 (Tier 1 자동 / Tier 2 사용자 승인 후) |
| 6. Verify | `harness-verifier` | verify_harness_consistency.py + smoke test |

## 두 루프 분리

- 제품 루프 (`wave-coordinator`): os/esxi/redfish-gather / common / adapters / schema / tests
- 하네스 루프 (`harness-evolution-coordinator`): .claude/, docs/ai/, scripts/ai/

서로 대상 파일 침범 금지.

## Tier 분류

| Tier | 예시 | 적용 |
|---|---|---|
| 1 | docs 초안 / stale 정정 / catalogs 갱신 | 자동 (reviewer APPROVE 후) |
| 2 | rules / agents / skills 변경 / policy 수정 | governor 심사 |
| 3 | settings 권한 완화 / 보호 경로 제거 | 사용자 에스컬레이션만 |

## 출력

- `docs/ai/harness/cycle-NNN.md` — 본 cycle 로그
- 변경 commit (Tier 1만 자동 / Tier 2는 사용자 승인 후)
- 다음 cycle 시작점 표기

## 절차

1. `harness-evolution-coordinator` agent 호출 (메인 orchestrator)
2. 6 단계 sub-agent 순차 호출
3. 결과 cycle log에 기록
4. 사용자 보고

## 적용 rule / 관련

- rule 28 (empirical-verification-lifecycle)
- rule 70 (docs-and-evidence-policy)
- agent: `harness-evolution-coordinator`, `harness-observer`, `harness-architect`, `harness-reviewer`, `harness-governor`, `harness-updater`, `harness-verifier`
- workflow: `docs/ai/workflows/HARNESS_EVOLUTION_MODEL.md` (Plan 3 작성 예정)
- command: `/harness-cycle`
