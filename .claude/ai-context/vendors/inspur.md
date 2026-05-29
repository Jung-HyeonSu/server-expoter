# Inspur — 벤더 OEM 메모

> 2026-05-01 신규 (F45 사용자 명시 승인). lab 부재 — web sources only.

## 식별

- **Manufacturer (Redfish ServiceRoot)**: "Inspur", "Inspur Information Technology Company Limited", "Inspur Information"
- **Aliases**: Inspur, INSPUR, Inspur Systems
- **BMC 이름**: ISBMC (Inspur Server BMC)
- **vendor_aliases.yml** 정규화: `inspur`

## Adapter 매핑

| Adapter | priority | 대상 모델 / 펌웨어 |
|---|---|---|
| `adapters/redfish/inspur_isbmc.yml` | 80 | NF/TS 시리즈 M5/M6 (lab 부재 — web sources) |
| `adapters/redfish/redfish_generic.yml` | 0 | unknown 펌웨어 fallback |

## OEM 특이사항

- **Manager URI**: `/redfish/v1/Managers/<id>` (표준)
- **System URI**: `/redfish/v1/Systems/<id>`
- **OEM namespace**: `Oem.Inspur` (부분 사용 가능)
- **표준 Redfish + IPMI 2.0** 지원
- **대표 모델**:
  - NF5280M5 (2U, dual-socket Intel Xeon Cascade Lake)
  - NF5280M6 (2U, Ice Lake)
  - NF5280LM6 (2U, optimized)
  - NF8480M6 (4-socket)

## Vault

- 위치: `vault/redfish/inspur.yml` — **미생성 (사용자 명시 2026-05-01)**
- 부재 시 동작: precheck auth 단계 status=failed

## 검증 이력

- 실장비 검증: **부재**
- Baseline: 부재
- web sources 기반: NF5280M5 User Manual section 9.14 Redfish

## 사이트 도입 시 절차

(F44 huawei.md 와 동일 — rule 50 R2 vault 단계 + baseline + Round 검증)

## Reference

- `docs/19_decision-log.md` — 2026-05-01 신규 vendor 4종 도입 결정
- ticket F45 (cycle 2026-05-01 — git history) — 본 vendor cold-start ticket
- Inspur NF5280M5 User Manual: manualzz.com
- Inspur Information White Paper (2023): inspur.com
