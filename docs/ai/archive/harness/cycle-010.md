# cycle-010 — T3 결정 항목 일괄 처리 + rule 70 R8 신설

## 일자
2026-04-28

## 진입 사유

사용자 명시 ("A 진행 — T3 옵션 분석 1장 브리핑" → "권장하는 작업 모두 수행 + 후속 작업 마무리") — cycle-009 완료 후 NEXT_ACTIONS의 사용자 결정 대기 항목 T3-04/05/06 일괄 처리.

## 처리 내역

### T3-04 — adapter `version` placeholder 일괄 삭제 (04-A 채택)

- **문제**: 27개 adapter (redfish 16 + os 7 + esxi 4) 모두 `version: "1.0.0"` 동일. `adapter_loader.py` / `module_utils/adapter_common.py` 어디서도 참조 0건 — placeholder.
- **결정**: **04-A 삭제** 채택. `tested_against` (rule 96 R1 origin 주석)이 펌웨어 검증 추적 충실. version placeholder는 컨벤션 noise.
- **변경**: 27개 adapter YAML에서 `version: "1.0.0"` 1줄 일괄 삭제 (`sed -i '/^version: "1.0.0"$/d'`)
- **검증**:
  - `grep -c "^version:" adapters/**/*.yml` → 27/27 = 0건
  - `python -c yaml.safe_load(...)` → 27/27 PASS, version 키 부재 확인
  - `verify_harness_consistency.py` PASS
- **대안 (거절)**:
  - 04-B sem-ver 추적: 매 PR bump 의무 — overhead + bump 누락 drift 위험 (MED)
  - 04-C last_modified 도입: timestamp 명시는 가능하나 git log로 충분
  - 04-D 현 상태 유지: noise 유지

### T3-05 — redfish_gather.py BMC IP 수집 (05-A 유지)

- **문제 후보**: `redfish_gather.py:511-529` EthernetInterfaces Members 순회 시 N+1 호출 의심.
- **실측**: break-on-first-IP 패턴 — 평균 1~2회 호출 (실 N+1 아님). cycle-008에서 `_resolve_first_member_uri` helper 추출로 가독성 개선됨.
- **결정**: **05-A 현재 유지**. NEXT_ACTIONS T3-05 close.
- **대안 (거절)**:
  - 05-B 모든 NIC 병렬: BMC 동시 요청 거부 vendor별 다름 (HIGH 리스크) + concurrent.futures stdlib 위반 위험
  - 05-C 첫 NIC만: multi-NIC 환경에서 IP 못 찾을 가능성 (MED)

### T3-06 — governance ADR 의무화 (06-B 조건부 채택)

- **문제**: `docs/ai/decisions/` ADR 1건만 (`ADR-2026-04-27-harness-import.md`). DRIFT-006 같은 governance 결정은 rule 본문 + CONVENTION_DRIFT.md만 trace.
- **결정**: **06-B 조건부 ADR**. rule 70 R8 신설 — 다음 3 trigger 시 ADR 의무:
  1. rule 본문 의미 변경 (Default / Allowed / Forbidden 절 추가·삭제·변경)
  2. 표면 카운트 변경 (`surface-counts.yaml` 카운트 증감)
  3. 보호 경로 정책 변경 (`protected-paths.yaml` 추가·삭제·완화)
- **추가 변경**:
  - `rule 70` R8 신설 + 금지 패턴 + 리뷰 포인트 항목 추가
  - `ADR-2026-04-28-rule12-oem-namespace-exception.md` 소급 작성 (DRIFT-006 governance trace 보강 — R8 적용 첫 사례)
- **대안 (거절)**:
  - 06-A 모든 결정 ADR 의무: overhead 과대, 작은 결정 위축 (HIGH 리스크)
  - 06-C 현 상태 유지: governance trace 약함

## 검증 결과

```
verify_harness_consistency.py     → PASS (rules: 29, skills: 43, agents: 51, policies: 10)
verify_vendor_boundary.py          → PASS (vendor 하드코딩 0건)
27 adapter YAML 파싱               → PASS (version 키 0/27)
check_project_map_drift.py         → drift 1건 (adapters fingerprint) → --update 적용
ansible-playbook --syntax-check    → SKIP (Windows 메인 환경 제약, WSL 후속 검증 가능)
```

## 영향

| 영역 | 변경 |
|---|---|
| `adapters/` (27 파일) | `version: "1.0.0"` 1줄 일괄 삭제 |
| `.claude/rules/70-docs-and-evidence-policy.md` | R8 신설 (ADR 의무 trigger) + 금지 패턴 + 리뷰 포인트 |
| `docs/ai/decisions/` (신규 1건) | `ADR-2026-04-28-rule12-oem-namespace-exception.md` |
| `.claude/policy/project-map-fingerprint.yaml` | adapters fingerprint 갱신 |
| `docs/ai/CURRENT_STATE.md` | cycle-010 항목 |
| `docs/ai/NEXT_ACTIONS.md` | T3-04/05/06 close + cycle-010 완료 항목 |
| `docs/ai/catalogs/TEST_HISTORY.md` | cycle-010 검증 기록 |

## 메모

- 본 ADR은 rule 70 R8 적용 첫 사례. 향후 R8 trigger 발생 시 동일 패턴으로 ADR 작성.
- T3-05 close로 NEXT_ACTIONS의 사용자 결정 대기 매트릭스 3건 모두 해소.
- DRIFT-006 옵션 (2) (redfish_gather.py vendor-agnostic 리팩토링)은 NEXT_ACTIONS P2에 보존 — 별도 cycle 진입 시 결정.
