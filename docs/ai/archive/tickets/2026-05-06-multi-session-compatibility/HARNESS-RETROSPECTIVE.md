# Harness Retrospective — 2026-05-06 multi-session-compatibility

> cycle 2026-05-06 multi-session-compatibility 종료 시점 학습 추출 (M-G1).
> A~F 영역 17 ticket [DONE] / G 2 ticket 학습.

## cycle 개요

| 항목 | 값 |
|---|---|
| 시작 | 2026-05-06 (Session-0 ticket 24건 작성, commit `abb41e59`) |
| 종료 | 2026-05-06 Session-5 (M-G1 완료, commit `~430ca790~`) |
| ticket 총 | 24건 (A 4 + B 3 + C 3 + D 4 + E 6 + F 2 + G 2) |
| ticket 진행 | **24건 [DONE/SKIP]** (M-A4 [SKIP], 23 [DONE]) |
| worker 세션 | Session-0 (orchestrator) + Session-1~5 (worker) |
| 사용자 명시 | "lab 접속 가능 장비 없음 → 모든 vendor / 모든 장비 호환" |
| commit | 11건 (Session-0~5) |
| pytest | 108 → **324 PASS** (총 +216 신규 테스트, M-A3 13 + M-B3 8 + M-C3 9 + M-E6 13 = 본 cycle 43건) |
| adapter | 38 → **39** (+1 — hpe_superdome_flex.yml) |
| docs | docs/20 신설 (625 → 825 라인) + docs/13 §15 추가 |

---

## 학습 패턴 8건

### 학습 1: 단일 cycle 내 N-worker ticket 분해 패턴

- **무엇이 일어났나** (관찰): Session-0 가 사용자 9 작업 항목을 24 cold-start ticket 으로 분해. Session-1~5 가 의존성 따라 순차 진행. 총 6 단계 (Phase 1 분석 → Phase 2 결정 → Phase 3 구현 → Phase 4 회귀 → Phase 5 학습) 자동 라우팅.
- **왜 발생** (원인): 단일 세션 컨텍스트 윈도우 한계 + 사용자 "다른 세션에서 작업하되 모두 상세 티켓화" 명시. cold-start ticket 형식 (의도 / 위치 / 변경 / 회귀 / 검증 / risk) 필요.
- **무엇을 학습** (insight): rule 26 (multi-session-guide) 의 정신을 **단일 cycle 안 다중 worker** 로 확장 가능. 메인 오케스트레이터 패턴이 cycle 자동화에 효과적.
- **하네스 보강 후보**:
  - skill: `cycle-orchestrator` (사용자 명시 → ticket 24건 자동 분해 + INDEX/HANDOFF/DEPENDENCIES 초안)
  - agent: `ticket-decomposer` (작업 항목 → cold-start ticket 변환)
  - rule 26 R10 (다음 추가): 단일 cycle 내 N-worker 운영 — INDEX + SESSION-HANDOFF + DEPENDENCIES + fixes/INDEX 4 정본 의무

### 학습 2: lab 부재 vendor 추가 패턴 확립 (F44~F47 + Superdome)

- **무엇이 일어났나** (관찰): cycle 2026-05-01 phase 2 (Huawei/Inspur/Fujitsu/Quanta 4 vendor) + 본 cycle M-E (HPE Superdome Flex) 모두 **lab 0 + web sources only** 패턴 적용. priority=80 (신규 4) / priority=95 (Superdome sub-line). vault 미생성 (사용자 명시 SKIP).
- **왜 발생** (원인): 사용자 lab 한계 + "코드를 모든 vendor 호환" 요구 → lab 부재 영역 web sources (vendor docs / DMTF / GitHub) 4종 의무 (rule 96 R1-A).
- **무엇을 학습** (insight): rule 50 R2 의 9 단계가 lab 부재 환경에 맞춰 단계 4 (vault) / 5 (baseline) skip 가능. priority 차등 — 신규 4 vendor (lab 0) priority=80, Superdome (sub-line, lab 0) priority=95.
- **하네스 보강 후보**:
  - rule 50 R2: 단계 9 → **10 으로 확장** (단계 10: 향후 lab 도입 시 capture-site-fixture skill trigger 등록)
  - skill: `add-vendor-no-lab` (lab 0 vendor 추가 자동화 — adapter spec + ai-context + boundary-map + sources 추적)
  - rule 96 R1-C: lab 부재 vendor 추가 시 **사이트 fixture 도입 trigger 필수 등록** (NEXT_ACTIONS.md 자동 추가)

### 학습 3: status 로직 의도 vs 사용자 기대 차이 (M-A 영역)

- **무엇이 일어났나** (관찰): 사용자 의심 "errors 에는 로그가 찍히는데 success로 빠지는경우" → M-A1 분석 시나리오 4 (A/B/C/D) 매트릭스. 시나리오 B (errors emit 시 status=success) 가 의도된 동작 (Case A 채택).
- **왜 발생** (원인): build_status.yml 의 errors[] 와 status 분리 의도가 코드 헤더 주석에 명시 부족. 사용자 의심 → AI 가 의도 명시 후 Case A 채택 (의도 주석 강화 only).
- **무엇을 학습** (insight): envelope 필드의 **의미 명시 (M-F1 docs/20)** 가 호출자 신뢰성에 결정적. drift 시 사용자 의심 발생.
- **하네스 보강 후보**:
  - skill: `verify-status-logic` (build_status.yml 변경 시 시나리오 매트릭스 자동 검증 — A/B/C/D 4 시나리오 invariants)
  - hook: `pre_commit_status_logic_check.py` (build_status.yml 변경 + 시나리오 mock fixture 동반 commit 의무)
  - rule 13 R8 (다음 추가): status 판정 로직 변경 시 의도 주석 + 시나리오 매트릭스 update 의무

### 학습 4: vault 자동 반영 검증 패턴 (M-C 영역)

- **무엇이 일어났나** (관찰): 사용자 질문 "vault 가 변경됐다면 자동으로 변경되는지" → M-C1/M-C2 정밀 검증 (cacheable 0 / fact_caching 0 / gather_facts: no) → YES 답변 + 단서 3개.
- **왜 발생** (원인): vault 운영 가이드에 "다음 run 부터 자동 반영" 명시 부재. cache 메커니즘 (Redis fact_cache vs task scope vs BMC 권한 cache) 분리 명시 필요.
- **무엇을 학습** (insight): vault 동작 메커니즘이 ansible 표준 (include_vars 캐시 없음) 이지만 사용자에게 명시 필요. F50 phase 4 BMC 권한 cache 와 vault 자동 반영 분리 명시.
- **하네스 보강 후보**:
  - docs: `docs/21_vault-operations.md` 신설 (M-C1/C2/C3 결과 정본화 — 5 시나리오 + cache 매트릭스 + BMC 분리)
  - skill: `rotate-vault` 보강 (M-C 결과 — 다음 run 부터 자동 반영 명시)
  - rule 27 R6 (다음 추가): vault 변경 후 다음 run 자동 반영 단서 3개 (single-run NO / rekey PARTIAL / BMC lock-out)

### 학습 5: 호환성 매트릭스 240 cell 전수 분석

- **무엇이 일어났나** (관찰): M-D1 → 9 vendor × N gen × 10 sections = **240 cell 호환성 매트릭스**. OK 27 / OK★ 167 / FB 9 / GAP 7 / BLOCK 6 / N/A 24. 분류 기호 7종 (OK/OK★/FB/GAP/BLOCK/?/N/A).
- **왜 발생** (원인): 사용자 "모든 밴더 모든 세대 모든 장비 지원" 명시 + cycle 2026-05-01 35건 fallback 누적 → cycle 2026-05-06 240 cell 추적 필요.
- **무엇을 학습** (insight): 호환성 매트릭스가 cycle 별로 진화 (35건 → 240 cell). 자동 측정 도구 + Gap 우선 분류 (P1/P2/P3) 가 fallback 추가 우선순위 결정에 효과적.
- **하네스 보강 후보**:
  - script: `scripts/ai/measure_compatibility_matrix.py` (rule 28 #11 외부 계약 lifecycle 의 sub — 매트릭스 자동 측정)
  - rule 28 #12 (다음 추가): COMPATIBILITY-MATRIX TTL 14일 + 무효화 trigger (adapter capabilities 변경 / sections.yml channels 변경 / web sources 갱신)
  - hook: `post_commit_compatibility_matrix_check.py` (adapter capabilities 변경 시 매트릭스 갱신 advisory)

### 학습 6: 24 ticket cold-start 형식 검증

- **무엇이 일어났나** (관찰): 본 cycle ticket 24건 → 다음 세션 cold-start 가능 형식 (의도 / 위치 / 변경 / 회귀 / 검증 / risk). Session-1~5 모두 ticket 본문만으로 진입 가능.
- **왜 발생** (원인): write-cold-start-ticket skill 의 효과 검증. 다음 세션이 컨텍스트 0 진입 시 ticket 만 보고 작업 가능해야 함.
- **무엇을 학습** (insight): cold-start 형식이 N-worker 패턴의 핵심 enabler. ticket 정합성 자동 검증 hook 도입 시 장기 운영 안정성 향상.
- **하네스 보강 후보**:
  - hook: `pre_commit_ticket_consistency.py` (cold-start 형식 검증 — 6 절 모두 존재 + status [PENDING/IN-PROGRESS/DONE/SKIP] 명시)
  - skill: `write-cold-start-ticket` 보강 (본 cycle 24 ticket 패턴 라이브러리화)

### 학습 7: Additive only 원칙 검증 효과 (M-D3)

- **무엇이 일어났나** (관찰): M-D3 W1~W6 9 라인 변경 (5 capabilities 추가 + 4 users drift 정정). 사용자 명시 (2026-05-01 "기존에있는것을 버리는게아니라 더 다양한환경을 호환하기위해서") 정합. pytest 회귀 0건.
- **왜 발생** (원인): rule 92 R2 (Additive only) + rule 96 R1-B (envelope shape 변경 자제) + 기존 fallback 코드 (cycle 2026-05-01 PowerSubsystem / SimpleStorage) 활용. 신규 fallback 코드 0 라인 추가.
- **무엇을 학습** (insight): Additive only 원칙이 **기존 fallback 활용** + **adapter capabilities 1 라인 추가** 만으로 호환성 영역 확장 가능. 9 라인 변경 / 0 회귀 효과 입증.
- **하네스 보강 후보**:
  - rule 92 R2 보강: Additive only 검증 절차 명시 (변경 라인 별 기존 path 유지 확인 + envelope shape 변경 0 + pytest 회귀)
  - hook: `pre_commit_additive_only_check.py` (코드 변경 line 별 기존 동작 영향 사전 분석 — diff 기반 advisory)

### 학습 8: 정본 docs/20 신설의 호출자 계약 효과

- **무엇이 일어났나** (관찰): M-F1 docs/20_json-schema-fields.md 신설 (625 라인) + M-F2 §11 (200 라인) → envelope 13 + sections 10 + field_dictionary 65 + 3채널 비교 정본 통합.
- **왜 발생** (원인): 사용자 "json스키마 키값이 무엇을 의미하는지 모르겠어" 명시 → 정본 reference 부재. build_output.yml / sections.yml / field_dictionary.yml 정본은 있으나 통합 의미 문서 부재.
- **무엇을 학습** (insight): 호출자 계약 안정성을 위해 envelope 의미 docs 가 critical. 정본 코드 변경 시 docs 동기화 필요 (rule 13 R5 / rule 96 R1-B 정합).
- **하네스 보강 후보**:
  - hook: `pre_commit_docs20_sync_check.py` (sections.yml / field_dictionary.yml / build_output.yml 변경 시 docs/20 동기화 advisory)
  - rule 13 R9 (다음 추가): envelope 정본 변경 시 docs/20 갱신 의무

---

## rule 보강 후보 (M-G2 입력)

| rule | 변경 spec | 우선 |
|---|---|---|
| rule 26 R10 (신규) | 단일 cycle 내 N-worker 운영 — 4 정본 (INDEX/HANDOFF/DEPENDENCIES/fixes-INDEX) 의무 | P2 |
| rule 50 R2 단계 10 (확장) | lab 부재 vendor 추가 시 사이트 fixture 도입 trigger 등록 의무 | P2 |
| rule 96 R1-C (신규) | lab 부재 vendor 추가 후 NEXT_ACTIONS.md 자동 등록 | P2 |
| rule 13 R8 (신규) | status 판정 로직 변경 시 의도 주석 + 시나리오 매트릭스 update 의무 | P2 |
| rule 13 R9 (신규) | envelope 정본 변경 시 docs/20 갱신 의무 | P1 |
| rule 27 R6 (신규) | vault 변경 후 다음 run 자동 반영 단서 3개 명시 | P3 |
| rule 28 #12 (신규) | COMPATIBILITY-MATRIX TTL 14일 + invalidation trigger | P2 |
| rule 92 R2 보강 | Additive only 검증 절차 명시 (변경 라인 별 영향 분석) | P3 |

→ rule 신규 5 + 보강 3 = 8 후보. Tier 분류는 M-G2 에서.

## skill 보강 후보

| skill | 신규/갱신 | 의도 |
|---|---|---|
| `cycle-orchestrator` (신규) | 신규 | 사용자 명시 → ticket N건 자동 분해 + 4 정본 초안 |
| `add-vendor-no-lab` (신규) | 신규 | lab 0 vendor 추가 자동화 (adapter + ai-context + boundary-map + sources) |
| `verify-status-logic` (신규) | 신규 | build_status.yml 변경 시 시나리오 매트릭스 자동 검증 |
| `rotate-vault` (보강) | 갱신 | M-C 결과 — 다음 run 자동 반영 단서 명시 |
| `write-cold-start-ticket` (보강) | 갱신 | 본 cycle 24 ticket 패턴 라이브러리화 |

## agent 보강 후보

| agent | 신규/갱신 | 의도 |
|---|---|---|
| `ticket-decomposer` (신규) | 신규 | 작업 항목 → cold-start ticket 분해 (cycle-orchestrator 의 sub) |

## hook 보강 후보

| hook | 신규/갱신 | trigger |
|---|---|---|
| `pre_commit_ticket_consistency.py` (신규) | 신규 | docs/ai/tickets/ 변경 시 cold-start 6 절 정합 검증 |
| `pre_commit_status_logic_check.py` (신규) | 신규 | build_status.yml 변경 시 시나리오 mock fixture 동반 commit 의무 |
| `pre_commit_docs20_sync_check.py` (신규) | 신규 | sections.yml / field_dictionary.yml / build_output.yml 변경 시 docs/20 동기화 |
| `post_commit_compatibility_matrix_check.py` (신규) | 신규 | adapter capabilities 변경 시 매트릭스 갱신 advisory |
| `pre_commit_additive_only_check.py` (신규) | 신규 | 코드 변경 diff 기반 Additive 검증 advisory |

→ hook 신규 5 후보. Tier 1 (advisory) 권장.

## docs 신설 후보

| docs | 의도 | 우선 |
|---|---|---|
| `docs/20_json-schema-fields.md` | M-F1 산출물 (이미 [DONE]) | P0 (완료) |
| `docs/21_vault-operations.md` | M-C1/C2/C3 결과 정본화 — vault 자동 반영 + 5 시나리오 + BMC 분리 | P2 |
| `docs/22_compatibility-matrix.md` | M-D1 산출물 정본화 — 240 cell 매트릭스 + Gap 우선 분류 | P3 |

## script / 자동화 후보

| script | 의도 |
|---|---|
| `scripts/ai/measure_compatibility_matrix.py` | rule 28 #12 sub — 매트릭스 자동 측정 |

---

## 다음 cycle 권장

1. **Tier 분류 (M-G2)**: rule 8 + skill 5 + agent 1 + hook 5 + docs 2 + script 1 = **22 후보** Tier 1/2/3 분류
2. **lab 도입 후속 cycle** (사이트 fixture 캡처):
   - Supermicro X9 6 cell BLOCK 해소
   - Lenovo XCC v3 OpenBMC 1.17.0 reverse regression fixture
   - Superdome Flex multi-partition 전수 수집 (Systems Members[0] 단일 진입 패턴 확장)
   - 신규 4 vendor 사이트 실측 fixture (Huawei/Inspur/Fujitsu/Quanta)
3. **자동화 cycle**: rule 28 #12 + COMPATIBILITY-MATRIX 자동 측정 도구 도입
4. **호출자 계약 안정성**: docs/20 정본화 후 호출자 시스템 통합 가이드 (별도 cycle)

---

## 갱신 history

| 일시 | 변경 |
|---|---|
| 2026-05-06 (M-G1) | HARNESS-RETROSPECTIVE 초안 — 학습 8건 + 보강 22 후보 |
