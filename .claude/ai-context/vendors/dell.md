# Dell — 벤더 OEM 메모

## 식별

- **Manufacturer (Redfish ServiceRoot)**: "Dell Inc.", "Dell EMC"
- **Aliases**: Dell, Dell Inc., Dell EMC, iDRAC
- **BMC 이름**: iDRAC8 / iDRAC9
- **vendor_aliases.yml** 정규화: `dell`

## Adapter 매핑

| Adapter | priority | 대상 펌웨어 |
|---|---|---|
| `adapters/redfish/dell_idrac9.yml` | 100 | iDRAC9 (Redfish full) |
| `adapters/redfish/dell_idrac8.yml` | 50 | iDRAC8 (Redfish 일부) |
| `adapters/redfish/dell_idrac.yml` | 10 | generic Dell fallback |

## OEM 특이사항

- **Storage controller path**: iDRAC9는 표준 Redfish, iDRAC8는 OEM path 사용 가능
- **Power supplies**: `Power.PowerSupplies` 표준 + OEM details
- **Firmware inventory**: `UpdateService/FirmwareInventory` (iDRAC9), iDRAC8는 부분 지원

## Vault

- 위치: `vault/<loc>/redfish/dell.yml`
- 공통 사용자: 일반적으로 `root` 또는 `service_account`
- 회전 절차: `rotate-vault` skill

## 검증 이력

- Round 7-10: iDRAC9 펌웨어 5.x / 6.x 검증 완료
- Baseline: `schema/baseline_v1/dell_baseline.json`
- Probe 스크립트: `tests/redfish-probe/probe_redfish.py --vendor dell`

## Reference

- `docs/13_redfish-live-validation.md` — 실장비 검증 결과
- `docs/10_adapter-system.md` — Adapter 점수 / 매트릭스
- Dell Redfish API doc (외부): support.dell.com
