# ADR-2026-05-06-post — P2/P3 후보 22건 일괄 처리

> 상태: Accepted
> 날짜: 2026-05-06
> 대상: cycle 2026-05-06-multi-session-compatibility 의 M-G1 P2/P3 후보 22건 일괄 cycle
> trigger: rule 70 R8 #2 (표면 카운트 변경 — skills 49→51 / agents 59→60 / hooks 22→26)

## 컨텍스트 (Why)

cycle 2026-05-06-multi-session-compatibility 종료 시 M-G1 산출물로 22 P2/P3 후보 식별. 각 후보는 cycle 학습 (M-A status / M-C vault / 24 ticket 라이브러리화 / lab 부재 / 호환성 매트릭스) 의 형식화 작업.

사용자 명시 (2026-05-06):
> "남아있는 작업 남아있는 티켓 모두 진행하라"

→ 22 P2/P3 후보 일괄 처리 결정.

## 결정 (What)

다음 5 묶음으로 일괄 처리:

### A. M-A status 로직 묶음 (3 항목)

- **rule 13 R8** 신설 — status 판정 로직 변경 시 4 시나리오 매트릭스 (A/B/C/D) 동반 갱신 의무
- **skill verify-status-logic** 신설 — M-A 학습 lookup 표준화
- **hook pre_commit_status_logic_check.py** 신설 — build_status.yml 변경 시 시나리오 mock advisory

### B. M-C vault 묶음 (3 항목)

- **rule 27 R6** 신설 — vault 자동 반영 단서 3개 (cacheable / fact_caching / decrypt 캐시)
- **skill rotate-vault 보강** — 자동 반영 메커니즘 + 회전 후 다음 run 자동 반영 흐름 명시
- **docs/operate/05-vault.md** 신설 — M-C 결과 정본화

### C. cycle 오케스트레이션 묶음 (5 항목)

- **skill cycle-orchestrator** 신설 — 5 Phase 파이프라인 (ticket 작성 → 분석 → 결정 → 구현 → 회귀 → 종료)
- **skill add-vendor-no-lab** 신설 — lab 부재 vendor 추가 자동화
- **skill write-cold-start-ticket 보강** — 6 절 형식 + DEPENDENCIES + SESSION-PROMPTS 정착
- **agent ticket-decomposer** 신설 — Phase 0 sub
- **hook pre_commit_ticket_consistency.py** 신설 — cold-start 6 절 advisory

### D. standalone rule 묶음 (5 rule)

- **rule 26 R10** 신설 — 다중 worker 4 정본 (INDEX/HANDOFF/DEPENDENCIES/SESSION-PROMPTS)
- **rule 50 R2 단계 10** 신설 — lab 부재 vendor NEXT_ACTIONS 자동 등록
- **rule 96 R1-C** 신설 — lab 부재 vendor / 펌웨어 NEXT_ACTIONS 자동 등록
- **rule 28 #12** 신설 — COMPATIBILITY-MATRIX TTL 14일
- **rule 92 R2 Additive 검증 절차** 신설 — 호환성 cycle 5단계 검증

### E. 호환성 매트릭스 묶음 (4 항목 — P3)

- **hook post_commit_compatibility_matrix_check.py** 신설 — adapter capabilities 변경 시 docs/22 advisory
- **hook pre_commit_additive_only_check.py** 신설 — 호환성 cycle Additive 검증
- **docs/reference/compatibility-matrix.md** 신설 — M-D1 240 cell 정본화
- **script scripts/ai/measure_compatibility_matrix.py** 신설 — rule 28 #12 자동 측정

## 결과 (Impact)

### 표면 카운트 변경

| 영역 | 이전 | 이후 | 변동 |
|---|---|---|---|
| rules | 28 | 28 | 신규 0 (R8/R10/R6/R2-10/R1-C/#12/R2 절차 = 보강 7) |
| skills | 49 | 51 | +2 (verify-status-logic / cycle-orchestrator / add-vendor-no-lab — 3 신설 + write-cold-start / rotate-vault 보강) |
| agents | 59 | 60 | +1 (ticket-decomposer) |
| hooks | 22 | 26 | +4 (status_logic / ticket_consistency / additive_only / compat_matrix_check) |
| docs | 21 | 22 | +1 (compatibility-matrix) — docs/21 / docs/22 신설 |

### 검증

- pytest: 영향 없음 (advisory hook only — 기존 회귀 PASS 324건 유지)
- self-test: 신규 hook 4종 + script 1종 모두 PASS (총 ~30건)
- verify_harness_consistency.py: PASS
- pre_commit_harness_drift.py: surface-counts.yaml 갱신 (advisory)

### 호출자 영향

- envelope shape 변경 0 (rule 96 R1-B 보존)
- 정본 4종 (envelope / sections / field_dictionary / build_status) 의미 변경 0
- 본 cycle 은 모두 advisory hook + rule / skill / agent / docs 추가 — 운영 영향 0

### 학습 (M-G2 형식화)

- M-A status 학습 → rule 13 R8 + skill + hook 3 항목
- M-C vault 학습 → rule 27 R6 + skill 보강 + docs/21 3 항목
- M-G 24 ticket × 5 worker 라이브러리화 → cycle-orchestrator + ticket-decomposer + write-cold-start-ticket 보강
- M-D1 240 cell 매트릭스 → docs/22 + script + hook 정본화
- lab 부재 학습 → rule 50 R2 단계 10 + rule 96 R1-C + skill add-vendor-no-lab

## 대안 비교 (Considered)

### Alternative 1: P2 4건만 + P3 보류 (cycle 분할)

- 장점: 작업 범위 작음 / 1 commit 유지 가능
- 단점: P2/P3 묶음이 의존 관계 (rule 13 R8 ↔ skill verify-status-logic ↔ hook pre_commit_status_logic_check). 분할 시 일관성 떨어짐
- → **거절** — 사용자 명시 "모두 진행" + 묶음 의존성

### Alternative 2: 22건 모두 즉시 + ADR skip

- 장점: 작업 단순
- 단점: 표면 카운트 변경 5 영역 (skills / agents / hooks / docs / rules R8/R10 등) → rule 70 R8 #2 trigger 발생
- → **거절** — ADR 의무

### Alternative 3 (채택): 22건 모두 + ADR + rule 70 R8 #2 trace

- 장점: 사용자 명시 응답 + governance trace 보존
- 단점: 작업 범위 큼
- → **채택**

## 후속 작업

- 운영 안정화 1~2 cycle 관찰 (advisory hook 4종 false-positive 모니터링)
- blocking 격상 검토 (rule 13 R7+R8 / rule 27 R6 / rule 28 #12 / rule 92 R2 자동 검증 안정화 후)
- lab 도입 cycle (외부 의존)

## 관련

- cycle: 2026-05-06-multi-session-compatibility (M-G1/G2 산출물 일괄 처리)
- ADR: ADR-2026-05-06-rule13-r7-docs20-sync.md (선행)
- skill: cycle-orchestrator (신설)
- rule: 13 R8 / 26 R10 / 27 R6 / 28 #12 / 50 R2 단계 10 / 92 R2 / 96 R1-C
- docs: 21 vault-operations / 22 compatibility-matrix (신설)
