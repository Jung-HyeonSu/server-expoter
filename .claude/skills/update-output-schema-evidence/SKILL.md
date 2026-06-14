---
name: update-output-schema-evidence
description: schema/sections.yml + schema/field_dictionary.yml + schema/baseline_v1/ 3종 정합 갱신 (rule 13 R1). schema 변경 후 호출. 사용자가 "schema 정합 갱신", "field dictionary 동기화", "ERD 갱신" (server-exporter 어휘로는 schema doc) 등 요청 시 또는 schema 5개 이상 누적 변경 시 자동. - schema/sections.yml or field_dictionary.yml 수정 후 / 새 섹션 / 새 필드 / Round 검증 후 baseline 변경
---

# update-output-schema-evidence

## 목적

server-exporter 출력 schema 3종 (sections.yml + field_dictionary.yml + baseline_v1/{vendor}.json)의 정합성을 갱신. server-exporter는 DB 없으므로 출력 schema가 정본.

## 입력

- 변경된 schema 파일 list
- 영향 vendor (전수 / 일부)
- 변경 사유 (새 섹션 / 새 필드 / 펌웨어 응답 변경)

## 출력

```markdown
## Schema 정합 갱신 — <변경 요약>

### sections.yml
- 추가: power.efficiency 필드
- 변경: storage.volumes (배열 형식)

### field_dictionary.yml
- Must 추가: `bmc.firmware_version`
- Nice 추가: `power.efficiency`

### baseline_v1 영향 vendor
| Vendor | 변경 | 회귀 |
|---|---|---|
| dell | volumes 추가 | PASS |
| hpe | volumes 추가 | PASS |
| lenovo | (영향 없음) | SKIP |

### docs/ai/catalogs/SCHEMA_FIELDS.md
- validate_field_dictionary.py 기준 분포 갱신 (예: Must 42 / Nice 74 / Skip 6 = 122 entries — 실측은 매 cycle마다 갱신)
```

## 절차

1. **변경 file 수집**: schema/ 디렉터리 staged 파일
2. **3종 정합 검증** (`output_schema_drift_check.py`):
   - sections.yml에 정의된 섹션이 field_dictionary에 누락 없는지
   - field_dictionary Must 필드가 모든 vendor baseline에 존재하는지
   - baseline의 새 필드가 field_dictionary에 등록됐는지
3. **영향 vendor 식별**: 어느 baseline이 회귀 필요한지
4. **catalogs 갱신**:
   - `docs/ai/catalogs/SCHEMA_FIELDS.md` (Must / Nice / Skip 카운트)
   - `docs/ai/catalogs/VENDOR_ADAPTERS.md` (벤더 capabilities 갱신)
5. **Jenkins Stage 3** (Validate Schema) 통과 확인
6. **rule 96 origin 주석 갱신**: 외부 시스템 응답 형식 변경이 원인이면 adapter metadata에 tested_against 추가

## 적용 rule / 관련

- **rule 13** (output-schema-fields) R1 (3종 동반 갱신)
- rule 92 R5 (schema 버전 사용자 확인)
- rule 28 #1 (출력 schema 측정 대상)
- skill: `update-vendor-baseline`, `verify-json-output`, `plan-schema-change`
- agent: `schema-mapping-reviewer`, `schema-migration-worker`
- script: `scripts/ai/hooks/output_schema_drift_check.py`
