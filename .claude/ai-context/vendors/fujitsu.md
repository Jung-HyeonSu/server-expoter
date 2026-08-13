# Fujitsu — 벤더 OEM 메모

> 2026-05-01 신규 (F46 사용자 명시 승인). lab 부재 — web sources only.

## 식별

- **Manufacturer (Redfish ServiceRoot)**: "Fujitsu", "FUJITSU", "Fujitsu Limited", "Fujitsu Technology Solutions"
- **Aliases**: Fujitsu, FUJITSU
- **BMC 이름**: iRMC S4 / S5 / S6 (integrated Remote Management Controller)
- **vendor_aliases.yml** 정규화: `fujitsu`

## Adapter 매핑

| Adapter | priority | 대상 모델 / 펌웨어 |
|---|---|---|
| `adapters/redfish/fujitsu_irmc.yml` | 80 | PRIMERGY M5/M6/M7 (iRMC S5/S6, lab 부재 — web sources) |
| `adapters/redfish/redfish_generic.yml` | 0 | unknown 펌웨어 fallback |

## OEM 특이사항

- **Manager URI 추정**: `/redfish/v1/Managers/iRMC` (사이트 검증 필요)
- **System URI**: `/redfish/v1/Systems/0` (Fujitsu spec)
- **OEM namespace**: `Oem.ts_fujitsu` (Fujitsu Technology Solutions, vendor 공식 namespace)
- **iRMC 세대**:
  - iRMC S4 — PRIMERGY M2/M3
  - iRMC S5 — PRIMERGY M5
  - iRMC S6 — PRIMERGY M6/M7 (추정)
- **대표 모델**:
  - PRIMERGY RX2540 M5 (2U)
  - PRIMERGY RX2540 M6 (2U, Ice Lake)
  - PRIMERGY RX2530 M6 (1U)
  - PRIMERGY TX2550 M5 (Tower)
  - PRIMERGY RX4770 M6 (4-socket)

## Vault

- 위치: `vault/<loc>/redfish/fujitsu.yml` — **미생성 (사용자 명시 2026-05-01)**
- 부재 시 동작: precheck auth 단계 status=failed

## 검증 이력

- 실장비 검증: **부재**
- Baseline: 부재
- web sources 기반: Fujitsu 공식 GitHub (iRMCtools / iRMC-REST-API)

## 사이트 도입 시 절차

(F44 huawei.md 와 동일)

## Reference

- `docs/19_decision-log.md` — 2026-05-01 신규 vendor 4종 도입 결정
- ticket F46 (cycle 2026-05-01 — git history) — 본 vendor cold-start ticket
- iRMCtools (vendor 공식 GitHub): https://github.com/fujitsu/iRMCtools
- iRMC-REST-API (vendor 공식 GitHub): https://github.com/fujitsu/iRMC-REST-API
- Fujitsu PRIMERGY iRMC S5 RESTful API Spec: manualzz.com
