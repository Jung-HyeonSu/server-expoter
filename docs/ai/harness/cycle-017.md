# cycle-017 — 하네스 보강 (B1~B8 + D + E 일괄)

- 일자: 2026-05-01
- 사용자 명시:
  1. "하네스 자기개선 루프도 넣어라" / "에이전트는 오푸스로" / "한 에이전트가 작업한 것을 다른 에이전트가 검수" (cycle 진입 시 — commit `a1a3bf6b` 7 신규 agent + cross-review-workflow skill 적용)
  2. "하네스 보강 작업 모두 수행해라 남겨두지말고 모두" (본 cycle 진입)
  3. "하네스 전체 점검 하네스 작업을 마무리해라 묻지마라 전부해라" (commit + push 자율 진행)

## 진입 컨텍스트

cycle 2026-05-01 종료 ticket `docs/ai/archive/tickets/2026-05-01-gather-coverage/HARNESS-RETROSPECTIVE.md` 의 B1~B8 부족 + D 신규 후보 + E 권한 완화. 사용자 명시 "남겨두지말고 모두" → 일괄 적용.

## 적용 결과 매트릭스

### B1~B8 (부족)

| Gap | 보강 | 적용 위치 |
|---|---|---|
| B1 lab 한계 | rule 96 R1-A web sources 의무 | `.claude/rules/96-external-contract-integrity.md` |
| B2 reverse regression | rule 25 R7-A-1 사용자 실측 우선 | `.claude/rules/25-parallel-agents.md` |
| B3 새 JSON 키 자제 | rule 96 R1-B + envelope_change_check hook | `.claude/rules/96-...` + `scripts/ai/hooks/envelope_change_check.py` |
| B4 ticket cold-start | write-cold-start-ticket skill | `.claude/skills/write-cold-start-ticket/` |
| B5 fallback 패턴 | `_endpoint_with_fallback` 헬퍼 | `redfish-gather/library/redfish_gather.py:567` |
| B6 origin 주석 | adapter_origin_check hook | `scripts/ai/hooks/adapter_origin_check.py` |
| B7 사이트 fixture | capture-site-fixture skill | `.claude/skills/capture-site-fixture/` |
| B8 cross-channel | cross_channel_consistency_check hook | `scripts/ai/hooks/cross_channel_consistency_check.py` |

### D 신규 후보

| 후보 | 종류 | 적용 |
|---|---|---|
| envelope 13 필드 검출 | hook | envelope_change_check |
| adapter origin 검증 | hook | adapter_origin_check |
| cross-channel 일관성 | hook | cross_channel_consistency_check |
| /cold-start-handoff | skill | write-cold-start-ticket (흡수) |
| /web-evidence-fetch | skill | `.claude/skills/web-evidence-fetch/` |
| /lab-inventory-update | skill | `.claude/skills/lab-inventory-update/` |
| web-evidence-collector | agent (opus) | `.claude/agents/web-evidence-collector.md` |
| compatibility-detective | agent | (cycle 진입 시 이미 존재) |
| lab-tracker | agent (opus) | `.claude/agents/lab-tracker.md` |

### E 권한 완화

- `.claude/policy/agent-permissions.yaml` (cycle 진입 시 이미 존재 — cycle-011 보안 정책 해제 연속선)
- `ADR-2026-05-01-harness-full-permissions.md` (이미 존재)

## 표면 카운트 변동

| 항목 | 시작 | 종료 | Δ |
|---|---|---|---|
| agents | 57 | 59 | +2 |
| skills | 43 | 48 | +5 |
| hooks | 18 | 21 | +3 |
| rules | 28 | 28 | 0 (R7-A-1 / R1-A / R1-B 본문 신설) |
| policies | 10 | 10 | 0 |
| decisions | N | N+1 | +1 (ADR-2026-05-01-harness-reinforcement) |

## 검증 결과

| 검증 | 결과 |
|---|---|
| `pytest tests/unit/` | PASS (76/76) |
| `verify_harness_consistency.py` | PASS (rules 28 / skills 48 / agents 59 / policies 10) |
| `verify_vendor_boundary.py` | PASS (vendor 하드코딩 0건) |
| `output_schema_drift_check.py` | PASS (sections=10 / fd_paths=65) |
| `check_project_map_drift.py --update` | drift 0 (재baseline) |
| `commit_msg_check.py --self-test` | PASS (5/5) |
| `envelope_change_check.py --self-test` | PASS |
| `adapter_origin_check.py --self-test` | PASS |
| `cross_channel_consistency_check.py --self-test` | PASS |
| `python -m ast` (`redfish_gather.py`) | PASS |

## 변경 파일 (16건)

### 신규 (10)

```
.claude/agents/web-evidence-collector.md
.claude/agents/lab-tracker.md
.claude/skills/cross-review-workflow/SKILL.md            (디렉터리 변환)
.claude/skills/write-cold-start-ticket/SKILL.md
.claude/skills/capture-site-fixture/SKILL.md
.claude/skills/web-evidence-fetch/SKILL.md
.claude/skills/lab-inventory-update/SKILL.md
scripts/ai/hooks/envelope_change_check.py
scripts/ai/hooks/adapter_origin_check.py
scripts/ai/hooks/cross_channel_consistency_check.py
docs/ai/decisions/ADR-2026-05-01-harness-reinforcement.md
docs/ai/harness/cycle-017.md                             (본 보고서)
```

### 수정 (6)

```
.claude/rules/25-parallel-agents.md                      (R7-A-1 신설)
.claude/rules/96-external-contract-integrity.md          (R1-A + R1-B 신설)
.claude/policy/surface-counts.yaml                       (57→59 / 43→48 / 18→21)
.claude/policy/project-map-fingerprint.yaml              (8 모듈 재baseline)
redfish-gather/library/redfish_gather.py                 (_endpoint_with_fallback 추가)
docs/ai/archive/tickets/2026-05-01-gather-coverage/HARNESS-RETROSPECTIVE.md  (G절 — 적용 결과)
docs/ai/NEXT_ACTIONS.md                                  (상단 entry 추가)
```

### 삭제 (1)

```
.claude/skills/cross-review-workflow.md                  (→ 디렉터리 형식)
```

## 학습 (cycle 2026-05-01)

1. **사용자 실측 > spec** (cycle 2026-04-30 reverse regression) → rule 25 R7-A-1 본문 화
2. **호환성 ≠ 새 데이터** (Additive only) → rule 96 R1-B 본문 화
3. **lab 한계 본질적 제약** → web sources 의무 (rule 96 R1-A)
4. **fallback 패턴 일관성** → 헬퍼 함수 추상화 (Storage / Power / Thermal 동일 형식)
5. **다중 agent cross-review** (cycle 진입 시 사용자 명시) → cross-review-workflow skill + 7 specialist/implementer/reviewer agent

## 후속 (다음 cycle)

본 cycle 종료 후 사용자 명시 "다음 세션에서 작업". 잔여 영역:

### AI 환경에서 가능 (다음 세션 우선)

- **harness-evolution-coordinator 6단계 정기 cycle 진입** — observer drift 11종 측정 + Tier 분류 + cross-review (cycle-016 이후 자기개선 cycle 공백)
- **gather-coverage P1 3건** — F5 power EnvironmentMetrics / F13 Cisco AccountService not_supported / F23 OS unsupported 분류 점진 전환
- **사이트 fixture 캡처 (capture-site-fixture skill 첫 실 적용)** — HPE Gen12 / Lenovo XCC3 / Dell iDRAC8

### 외부 의존 / 사용자 결정

- OPS-9 repo private 전환
- OPS-3 vault credential 회전 timing
- OPS-AS-DELL-1 Dell iDRAC9 AccountService `find_empty_slot` 진단
- 새 vendor (Huawei / Inspur) PO + 실장비
- Round 11 실장비 검증

## 갱신 history

- 2026-05-01: cycle-017 본 보고서 신규
