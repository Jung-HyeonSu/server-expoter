---
name: update-vendor-baseline
description: 실장비 검증 결과로 schema/baseline_v1/{vendor}_baseline.json을 갱신한다. 펌웨어 업그레이드 / 새 응답 필드 / 의도된 schema 변경 후 사용. 사용자가 "baseline 갱신", "Dell baseline 새로 떠줘", "회귀 기준선 업데이트" 등 요청 시. - 펌웨어 업그레이드 후 / schema 변경 후 영향 vendor 회귀 / probe-redfish-vendor 결과 반영 / Round 검증 완료 후
---

# update-vendor-baseline

## 목적

`schema/baseline_v1/<vendor>_baseline.json` 회귀 기준선을 실장비 검증 결과로 갱신. baseline은 Jenkins Stage 4 (E2E Regression)의 비교 기준 → 임의 수정 절대 금지 (rule 13 R4 + rule 21 R1).

## 입력

- 영향 vendor (예: dell / hpe / lenovo / supermicro / cisco)
- 변경 사유:
  - 펌웨어 업그레이드 (외부 시스템)
  - schema 변경 (sections.yml + field_dictionary.yml 동반)
  - 새 vendor 첫 baseline 추가
- evidence (Round 검증 결과 / probe dump)

## 출력 / 결과

```markdown
## Baseline 갱신 — Dell iDRAC9 7.x

### 대상 파일
- schema/baseline_v1/dell_baseline.json

### 변경 내역
| 섹션 | 변경 | 근거 |
|---|---|---|
| storage | volumes 배열 추가 (3건) | iDRAC9 7.x부터 표준 endpoint 노출 |
| firmware | NIC.Slot.1 펌웨어 버전 갱신 | 펌웨어 업그레이드 |

### Evidence
- tests/evidence/<날짜>-<vendor>-<펌웨어>/
- probe dump: ServiceRoot.json, Storage.json, FirmwareInventory.json
- diff: tests/evidence/<날짜>-<vendor>-<펌웨어>/diff-vs-baseline.md

### 회귀 검증 결과
- pytest tests/regression/ -k dell PASS

### 후속
- docs/reference/decision-log.md "Round X" 추가
- docs/ai/catalogs/TEST_HISTORY.md append
- adapter dell_idrac9.yml의 metadata.tested_against에 "7.x" 추가 (rule 96 R1)
```

## 절차

1. **사용자 승인 확인** (rule 13 R4): 임의 갱신 금지. 변경 사유 명확
2. **probe-redfish-vendor 결과 reference**: tests/evidence/<날짜>-<vendor>-*/ 의 dump
3. **diff 작성**:
   - 기존 baseline_v1/<vendor>_baseline.json
   - 새 dump (정규화 적용 후)
   - 추가 / 변경 / 삭제 필드 명시
4. **field_dictionary 정합** (rule 13 R2):
   - 새 필드가 Must 대상이면 다른 vendor에도 존재하는지 확인 (없으면 Nice로 분류)
   - field_dictionary.yml 동반 갱신
5. **새 baseline 작성**:
   - JSON envelope 13 필드 형식 유지 (rule 20 R1)
   - section list가 sections.yml과 일치
6. **회귀 검증**:
   ```bash
   pytest tests/regression/ -k dell -v
   ```
7. **adapter origin 주석 갱신** (rule 96 R1): metadata.tested_against / 마지막 동기화 일자
8. **evidence 보존** (rule 21 R4): Round 검증 결과 tests/evidence/에
9. **문서 갱신**:
   - docs/reference/decision-log.md "Round X"
   - docs/ai/catalogs/TEST_HISTORY.md
   - docs/ai/CURRENT_STATE.md
10. **PR squash 머지** (rule 93 R5)

## server-exporter 도메인 적용

- 영향 채널: redfish 주 (os / esxi도 동일 절차 적용 가능 — `update-vendor-baseline --channel esxi`)
- 영향 vendor: 갱신 대상 1개 (다른 vendor baseline은 미수정)
- 영향 schema: 동반 갱신 가능 (rule 13 R1 3종 동반)

## 실패 / 오탐 처리

- baseline 수정 후 회귀 FAIL → 즉시 revert + 원인 분석 (코드 회귀 또는 외부 시스템 의도된 변경 구분)
- field_dictionary와 baseline 정합 위반 → output_schema_drift_check.py가 검출
- 다른 vendor baseline에 영향 의심 → 전수 회귀 (Jenkins Stage 4) 의무

## 적용 rule / 관련

- **rule 13** (output-schema-fields) R4 (실측 기반 갱신)
- **rule 21** (output-baseline-fixtures) R1 (AI 임의 수정 금지)
- rule 40 (qa-pytest-baseline) — Round 검증
- rule 96 R1 (origin 주석 갱신)
- skill: `probe-redfish-vendor`, `update-output-schema-evidence`, `prepare-regression-check`
- agent: `qa-regression-worker`, `schema-reviewer`
- 정본: `docs/reference/live-validation.md`
- 정본: `schema/baseline_v1/`, `tests/evidence/`

## 보안

- baseline JSON에 BMC 사용자 이름 / IP 주소 같은 식별 가능 정보 redaction (`security-redaction-policy.yaml`)
- 내부 IP는 `10.x.x.x`로 익명화 (예시는 그대로 두되 commit 본은 redacted)
