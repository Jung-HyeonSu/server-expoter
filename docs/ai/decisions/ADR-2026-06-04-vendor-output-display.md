# ADR-2026-06-04 — 출력 envelope vendor 표시값 매핑 (hpe→hp, CSUS 3200→hpCsus)

- 상태: Accepted
- 일시: 2026-06-04
- 결정 주체: 사용자(hshwang1994) 명시 지시 + AI(Claude) 구현
- 관련 rule: 12 R1, 13 R5/R7, 50 R1/R2, 92 R5, 96 R1-B
- supersede/refine: `docs/19_decision-log.md` 2026-05-12 결정 ("새 HPE sub-vendor 신설 거절") 의 부분 갱신

## 1. 컨텍스트 (Why)

호출자(다운스트림 소비자)가 envelope 최상위 `vendor` 필드에서 다음을 받기를 요구:
- HPE 계열 → `hp` (기존 `hpe`)
- HPE Compute Scale-up Server 3200 (CSUS 3200) → `hpCsus`

문제는 내부 canonical `hpe` 가 단순 표기가 아니라 **라우팅 키**라는 점:
- adapter 선택 / `vault/redfish/hpe.yml` 경로 / `OEM_EXTRACTORS['hpe']` /
  account 복구 retry (`vendor == 'hpe'`) 가 모두 `hpe` 로 분기.
- `Oem.Hpe` / `Oem.Hp` 는 Redfish spec OEM namespace (rule 96 외부 계약) — 불변.

따라서 canonical 을 전면 rename 하면 ~45~50 파일 + 암호화 vault 파일 rename + 런타임
인증 실패 위험인데, 기능적 이득은 0 (`HP`/`Hp` 는 이미 `hpe` 로 들어오는 입력 alias).

## 2. 결정 (What)

**Design A — 출력 라벨만 변경 (output-display relabel).**
내부 canonical `hpe` 는 그대로 두고, envelope 출력 `vendor` 값만 data-driven 표시 맵으로 치환.

- 표시 맵 정본: `common/vars/vendor_aliases.yml` (rule 12 R1 Allowed 위치)
  - `vendor_output_display: { hpe: hp }`
  - `adapter_output_display: { redfish_hpe_csus_3200: hpCsus }` (vendor_output_display 보다 우선)
- 적용 (data-driven — vendor 이름 하드코딩 없음):
  - redfish: `redfish-gather/site.yml` `_out_vendor` (성공/rescue/always 3 경로) —
    `adapter_output_display[adapter_id]` 우선 → `vendor_output_display[canonical]` → canonical.
    CSUS 식별 = `_selected_adapter.adapter_id == 'redfish_hpe_csus_3200'` (정확히 CSUS 3200 만).
  - esxi: `esxi-gather/site.yml` `_out_vendor` — `vendor_output_display` 적용 (CSUS 무관).
  - os: `os-gather/site.yml` Linux/Windows inline 매핑의 emit literal `hpe→hp`
    (기존 `# nosec rule12-r1` raw-fallback inline 매핑 — 표시 맵 mirror).
- 범위: 3 채널 전체 `hp`, `hpCsus` 는 redfish CSUS 3200 한정 (사용자 결정).
- schema enum: `schema/field_dictionary.yml` `fields.vendor.enum` 에서 `hpe`→`hp` + `hpCsus` 추가.
  (envelope 13 필드 shape 불변 → `schema_version` 정수는 `"1"` 유지.)

## 3. 결과 (Impact)

| 영역 | 변경 |
|---|---|
| `common/vars/vendor_aliases.yml` | `vendor_output_display` / `adapter_output_display` 신규 (canonical 불변) |
| `redfish-gather/site.yml` | `_out_vendor` 3 경로 data-driven 매핑 |
| `esxi-gather/site.yml` | `_out_vendor` data-driven 매핑 |
| `os-gather/site.yml` | Linux/Windows emit literal `hpe→hp` |
| `schema/field_dictionary.yml` | vendor enum `hpe`→`hp` + `hpCsus` (Stage 3 gate) + help 갱신 (camelCase 예외 명시) |
| `schema/baseline_v1/hpe_baseline.json` | envelope vendor `hpe→hp` |
| `schema/baseline_v1/hpe_csus_3200_baseline.json` | envelope vendor `hpe→hpCsus` |
| `schema/output_examples/redfish_hpe_ilo6.jsonc` / `redfish_hpe_csus_3200.jsonc` | 표시값 갱신 |
| `tests/regression/test_cross_channel_consistency.py` | `CANONICAL_VENDORS` 에 `hp`/`hpCsus` |
| `tests/regression/test_vendor_output_display.py` | 신규 회귀 (D1~D6) |

**무손상 (Design A 핵심)**: adapter 선택 / vault 경로 / OEM 추출 / account 복구 분기 /
`vendor == 'hpe'` 분기 / `Oem.Hpe` namespace / raw `data.hardware.vendor`("HPE") 전부 불변.

**호환성 주의 (rule 96 R1-B)**: envelope `vendor` 값은 외부 계약. `hpe` 로 필터링하던
다운스트림 소비자는 `hp`/`hpCsus` 로 갱신 필요. (사용자 요구 자체가 다운스트림 요구.)

**검증**: pytest 748 passed (기존 + 신규 회귀) / vendor-boundary PASS / harness-consistency
PASS / validate_field_dictionary PASS / output_schema_drift PASS / Jinja 표시식 단위 검증 PASS.
(`ansible-playbook --syntax-check` 는 Windows dev box ansible 부재로 미실행 — Linux Agent/CI 수행.)

## 4. 대안 비교 (Considered)

| 대안 | 결과 |
|---|---|
| **A. 출력 라벨만 변경 (채택)** | ~10 파일, MED. 내부 라우팅 무손상. CSUS 구분은 adapter_id 단일 신호. |
| B. 내부 canonical 전면 rename (`hpe→hp`) | ~45~50 파일 + 암호화 vault rename + 런타임 인증 실패 위험. 기능 이득 0. **거절.** |
| C. CSUS 를 vendor 말고 diagnosis 로만 | 이미 `diagnosis.details.adapter_candidate` / `multi_node_layout` 존재하나, 사용자는 `vendor` 필드값 `hpCsus` 자체를 요구. **불충족.** |
| `manager_layout == 'rmc_primary'` 로 CSUS 식별 | 동작은 하나 Superdome Flex(`rmc_primary_ilo_secondary`)와의 구분이 layout 값에 암묵 의존. `adapter_id` 가 더 명시적 → adapter_id 채택. |

## 5. 2026-05-12 결정과의 관계

`docs/19_decision-log.md` 2026-05-12 행("새 HPE sub-vendor 신설 거절 — vendor_aliases.yml
변경 불필요")은 **내부 canonical 차원에서 여전히 유효** (canonical `hpe` 유지, vendor_aliases
의 vendor 목록 불변, OEM tasks 재사용). 본 ADR 은 그 위에 **출력 표시 계층**만 추가한 것으로
충돌이 아니라 refine. CSUS 는 내부적으로 `hpe` 로 라우팅되고 출력에서만 `hpCsus` 로 표시된다.
