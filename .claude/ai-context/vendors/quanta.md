# Quanta (QCT) — 벤더 OEM 메모

> 2026-05-01 신규 (F47 사용자 명시 승인). lab 부재 — web sources only.

## 식별

- **Manufacturer (Redfish ServiceRoot)**: "Quanta", "QCT", "Quanta Computer", "Quanta Cloud Technology"
- **Aliases**: Quanta, QUANTA, Quanta Computer Inc., Quanta Cloud Technology, QCT
- **BMC 이름**: BMC (OpenBMC 기반 — 별도 표시명 없음)
- **vendor_aliases.yml** 정규화: `quanta`

## Adapter 매핑

| Adapter | priority | 대상 모델 / 펌웨어 |
|---|---|---|
| `adapters/redfish/quanta_qct_bmc.yml` | 80 | QuantaGrid / QuantaPlex (OpenBMC, lab 부재 — web sources) |
| `adapters/redfish/redfish_generic.yml` | 0 | OpenBMC 표준 fallback (부분 cover 가능) |

## OEM 특이사항

- **base platform**: OpenBMC (bmcweb 표준)
- **Manager URI**: `/redfish/v1/Managers/bmc` (OpenBMC 표준)
- **System URI**: `/redfish/v1/Systems/system` (OpenBMC 표준)
- **OEM namespace**: `Oem.OpenBmc` (vendor 표준 namespace) 또는 부재
- **OpenBMC 정렬** → 표준 Redfish 우선, OEM 의존 작음 (Lenovo XCC3 와 유사)
- **대표 모델**:
  - QuantaGrid D54Q-2U (2U, Sapphire Rapids)
  - QuantaGrid D52BQ-2U (2U)
  - QuantaPlex T42S-2U (2U)

## Vault

- 위치: `vault/<loc>/redfish/quanta.yml` — **미생성 (사용자 명시 2026-05-01)**
- 부재 시 동작: precheck auth 단계 status=failed

## 검증 이력

- 실장비 검증: **부재**
- Baseline: 부재
- web sources 기반: QCT 공식 + Red Hat 인증 카탈로그 + OpenBMC bmc-toolbox

## 사이트 도입 시 절차

(F44 huawei.md 와 동일. 단 OpenBMC 기반이므로 redfish_generic.yml 가 부분 cover 가능)

## Reference

- `docs/19_decision-log.md` — 2026-05-01 신규 vendor 4종 도입 결정
- ticket F47 (cycle 2026-05-01 — git history) — 본 vendor cold-start ticket
- QuantaGrid D54Q-2U: https://www.qct.io/product/index/Server/rackmount-server/2U-Rackmount-Server/QuantaGrid-D54Q-2U
- QCT D54Q-2U Spec PDF: exalit.com
- bmc-toolbox (multi-vendor BMC abstraction): https://bmc-toolbox.github.io/
