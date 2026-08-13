# Handoff — 2026-05-11 다음 cycle 후보 ticket

> 직전 세션 종료 시점 (commit `1387b505`, branch `main`) 의 다음 cycle 후보를 cold-start 6 절 형식으로 보존.
> rule 26 R6 / write-cold-start-ticket skill 형식.

---

## 1. 컨텍스트 (이전 세션 종료 시점)

- **종료 commit**: `1387b505` (2026-05-11)
- **마지막 cycle**: `hpe-ilo7-gen12-match-fix` [DONE]
  - iLO 7 adapter `firmware_patterns` Additive 확장 `["iLO.*7", "^\\d+\\.\\d+\\.\\d+", "^1\\.1[0-9]"]`
  - 2-part firmware "1.10" 매치 갭 fix
  - mock 5 시나리오 (S1=iLO7 fix / S2-S5 회귀) + pytest 590/590 + 하네스 PASS
- **사용자 명시 (2026-05-11)**: "다음 티켓으로 저장 하고 이번에는 세션 종료"
- **github + gitlab 동시 push 완료**: `a123b1cc..1387b505`
- **NEXT_ACTIONS 갱신 상태**: `docs/ai/NEXT_ACTIONS.md` 의 HPE CSUS 3200 4 항목 [PENDING] 유지

---

## 2. 다음 첫 지시 (cold-start prompt 후보 4종)

### 후보 A — Cycle 2 (Option A) HPE CSUS 3200 lab 검증 [BMC IP 확보 시 즉시 진입]

```
HPE Compute Scale-up Server 3200 (CSUS 3200) lab 검증 cycle 진입.

진입 정보 (사용자 입력 필요):
- BMC IP: <여기에 입력>
- 사이트 (loc): <ich / chj / yi>
- vault 분리 결정: <hpe 재사용 / 별도 vault/redfish/hpe_csus.yml 분리>

수행 (rule 50 R2 단계 10 + NEXT_ACTIONS 4 항목):
1. capture-site-fixture skill — probe_redfish.py 로 ServiceRoot / Systems /
   Managers / Chassis / UpdateService 캡처 + sanitize
   → tests/fixtures/redfish/hpe_csus_3200/
2. 추정값 정정 (rule 25 R7-A-1 — 사용자 실측 > spec):
   - Manufacturer 실측 string
   - Model 실측 string
   - RMC firmware 실측 version (현재 추정 ^[34]\\.[0-9]+\\..*)
   - Systems id pattern 실측 (현재 추정 "Partition0")
   - Oem.Hpe.PartitionInfo / FlexNodeInfo / GlobalConfiguration 확인
3. baseline 추가 — schema/baseline_v1/hpe_csus_3200_baseline.json (rule 13 R4)
4. Round 검증 — tests/evidence/2026-MM-DD-hpe-csus-3200-round1.md
5. docs/13 §16 status [PENDING] → [DONE]
6. docs/19 결과 entry
7. (선택) vault 분리 — vault/redfish/hpe_csus.yml (사용자 명시 승인 시)
8. pytest 회귀 + commit + push (rule 93 R1 자율)

진입 전 read 권장: adapters/redfish/hpe_csus_3200.yml /
docs/reference/live-validation.md §16 / docs/ai/NEXT_ACTIONS.md HPE CSUS 3200 행
```

### 후보 B — harness 자기개선 cycle [lab 없이 즉시 가능]

```
/harness-cycle skill 진입 — 6단계 파이프라인:
observer → architect → reviewer → governor → updater → verifier.

대상 측정 (rule 28 R1 11종):
- 출력 schema / PROJECT_MAP / 벤더 어댑터 매트릭스 / Jenkinsfile cron /
  하네스 표면 카운트 / 벤더 baseline / Fragment 토폴로지 /
  브랜치 갭 / 벤더 경계 위반 / 외부 시스템 계약 / COMPATIBILITY-MATRIX

drift 검출 → architect 명세 → reviewer 검수 → governor Tier 분류
(Tier 1 자동 / Tier 2 사용자 승인 / Tier 3 절대 금지)

세션 시작 시 [WARN] 로 보고된 PROJECT_MAP drift 2종 (adapters /
tests) 갱신은 본 cycle 에서 자동 cover.

산출: docs/ai/cycle-XXX-log.md + 영향 영역 자동 수정 (Tier 1) 또는
명세 (Tier 2 — 사용자 승인 대기)
```

### 후보 C — lab 보유 vendor 4종 강화 [Round 12+]

```
lab 보유 vendor 강화 cycle — 사이트 사고 fixture / facts.firmware drift /
firmware 매트릭스 확장.

대상 4 vendor (NEXT_ACTIONS 매트릭스 [DONE] 영역):
- Dell iDRAC10 (commit 0a485823 — 사이트 검증 1대)
- HPE iLO7 (commit 1387b505 — 2-part firmware fix 적용 직후)
- Lenovo XCC3 (Accept-only header 정책 — cycle 2026-04-30)
- Cisco UCS X-series (commit 0a485823 — standalone CIMC)

각 vendor 별 Round 12+ 단계 (사용자 결정 — 4 중 1 선택):
1. facts.firmware 추출 path 정밀화 (Manager vs System)
2. 새 firmware 변형 시나리오 추가 (firmware_patterns 갭 사전 차단)
3. baseline 갱신 (실장비 응답 변경 시)
4. reverse regression 검토 (rule 25 R7-A-1)
```

### 후보 D — code/docs hygiene cycle [대형 자유]

```
repo-hygiene-planner + nonfunctional-refactor-worker — 죽은 코드 / 중복 /
archive 후보 / convention drift 정리.

대상:
- docs/ai/archive 후보 (1회성 cycle 보고서 정리)
- DRIFT-XXX open 항목 (현재 DRIFT-014 까지 — 11 open / 3 resolved 확인 필요)
- scripts/ai/ 중복 도구 통합
- knip / depcheck / ts-prune 대신 Python 도구로 dead code 식별

산출: 변경 commit 1~3개 + archive 이동 list + DRIFT 갱신
```

---

## 3. 의존성 / 전제 조건

| 후보 | 진입 조건 | 보류 사유 (현재) |
|---|---|---|
| A | BMC IP / 사이트 / vault 결정 | 사용자 입력 없음 |
| B | 없음 (lab 없이 진행) | 즉시 진입 가능 |
| C | 사이트 응답 / 사고 fixture (있으면 우선) | 즉시 진입 가능 (mock 회귀 강화는 lab 없이) |
| D | 없음 | 즉시 진입 가능 |

---

## 4. 작업 범위 (rule 13 / rule 22 / rule 26 R10)

- 후보 A/B/C/D 모두 단일 worker (N=1) — rule 26 R10 4 정본 (INDEX / HANDOFF / DEPENDENCIES / SESSION-PROMPTS) 의무 X
- 본 handoff 1 파일 만으로 충분 (cold-start 6 절)

---

## 5. 검증 기준 (rule 24 6 체크)

각 후보 종료 시:
- [ ] 정적 검증 (pytest / yamllint / verify_harness_consistency / verify_vendor_boundary)
- [ ] 발견 버그 0건 또는 수정 commit
- [ ] 문서 갱신 (rule 70 R1 매핑 — CURRENT_STATE + 영향 catalog)
- [ ] NEXT_ACTIONS 갱신 (후속 명시 / 없음 명시)
- [ ] (선택) git 태그
- [ ] 회귀 PASS

---

## 6. 에스컬레이션

| 발생 시 | 책임 |
|---|---|
| 후보 A — 추정값 정정 결과 vs spec 큰 차이 (rule 25 R7-A-1) | 사용자 실측 우선 + 다른 사이트 reverse regression 영향 사고 실험 |
| 후보 B — Tier 2 변경 (rules / agents / skills) 검출 | governor 가 사용자 에스컬레이션 — 자동 적용 X |
| 후보 B — Tier 3 변경 (settings 권한 / 보호 경로) 검출 | 사용자 명시 승인만 (자동 0건 보장) |
| 후보 C — reverse regression 사고 발견 | 즉시 사용자 보고 + capture-site-fixture skill |
| 후보 D — knip / depcheck 같은 외부 도구 의존 | Python 대체 도구 우선 (ansible / pytest 환경 영향 0) |

---

## 7. 직전 세션 산출 요약

| Cycle | 결과 | commit |
|---|---|---|
| `hpe-csus-add` | HPE CSUS 3200 adapter (priority=96, web sources 7건) + OEM regex 확장 + 문서 7개 + NEXT_ACTIONS 4 항목 | `a123b1cc` |
| `hpe-ilo7-gen12-match-fix` | iLO 7 firmware_patterns Additive 확장 + 회귀 도구 `verify_hpe_ilo7_fix.py` + DRIFT-014 entry | `1387b505` |
