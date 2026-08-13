---
name: plan-schema-change
description: 새 섹션 / 새 필드 / Must↔Nice 재분류 / baseline 일괄 갱신 등 schema 변경 계획. 사용자가 "새 섹션 추가하자", "field dictionary에 X 추가", "schema 변경 계획", "Must 필드 추가" 등 요청 시. - 새 섹션 / 새 필드 도입 / 펌웨어 업그레이드로 응답 변경 / Must↔Nice 재분류
---

# plan-schema-change

## 목적

server-exporter 출력 schema 변경 계획. 정본 = `schema/sections.yml + schema/field_dictionary.yml + baseline_v1/`. (server-exporter는 DB 없음 — 출력 schema가 동등 역할)

## 입력

- 변경 종류:
  - 새 섹션 추가 (10 → 11 sections)
  - 기존 섹션에 필드 추가 (Must / Nice / Skip 분류)
  - Nice → Must 격상 (모든 vendor baseline에 존재 검증 후)
  - Must → Nice 강등 (호환성 영향 큼, 사용자 명시 승인)
- 사유 (호출자 요구 / 펌웨어 변경 / 운영 요구)

## 출력

```markdown
## Schema 변경 계획 — Power 섹션에 efficiency 필드 추가

### 변경 범위
- schema/sections.yml: power 섹션에 efficiency 필드 추가
- schema/field_dictionary.yml: Nice 분류로 추가 (vendor 차등 지원)
- schema/baseline_v1/{vendor}.json: HPE / Dell 만 갱신 (지원 vendor)

### 영향 vendor
- Dell: iDRAC9 6.x+ 지원 (PowerSupplies.Efficiency endpoint)
- HPE: iLO5+ 지원
- Lenovo / Supermicro / Cisco: 미지원 (Nice이므로 OK)

### 회귀
- Jenkins Stage 3 (Validate Schema): pass (Nice 필드)
- Jenkins Stage 4 (E2E Regression): Dell + HPE baseline 회귀

### 절차 (rule 13 R1 3종 동반)
1. schema/sections.yml 갱신
2. schema/field_dictionary.yml 갱신
3. probe-redfish-vendor로 Dell + HPE 실장비 검증
4. update-vendor-baseline으로 baseline JSON 갱신
5. update-output-schema-evidence로 정합 검증
6. PR squash 머지

### 사용자 승인 필요 (rule 92 R5)
- schema 버전 결정: v1 → v1.1 또는 v2?
```

## 적용 rule / 관련

- **rule 13** (output-schema-fields) 정본
- rule 92 R5 (schema 버전 사용자 확인)
- rule 91 (task-impact-preview) — 사전 영향 분석
- skill: `update-output-schema-evidence`, `update-vendor-baseline`, `task-impact-preview`
- agent: `schema-migration-worker`, `schema-mapping-reviewer`
- 정본: `docs/contract/02-output-envelope.md`, `docs/develop/05-field-mapping.md`
