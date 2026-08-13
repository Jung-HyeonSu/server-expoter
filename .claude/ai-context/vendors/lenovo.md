# Lenovo — 벤더 OEM 메모

## 식별

- **Manufacturer**: "Lenovo", "IBM" (구 IBM x-series 인수)
- **Aliases**: Lenovo, IBM, XCC
- **BMC 이름**: XCC (XClarity Controller)
- **vendor_aliases.yml** 정규화: `lenovo`

## Adapter 매핑

| Adapter | priority | 대상 |
|---|---|---|
| `adapters/redfish/lenovo_xcc.yml` | 100 | XCC (현행) |
| `adapters/redfish/lenovo_xcc_legacy.yml` | 50 | 구 IMM2 / 초기 XCC |

## OEM 특이사항

- **Drive bay path**: `Chassis/<id>/Drives` 표준 + OEM
- **Firmware**: UpdateService 표준
- **Power**: 표준 PowerSupplies

## Vault

- 위치: `vault/<loc>/redfish/lenovo.yml`
- 일반적 계정: `USERID`
- 회전: `rotate-vault` skill

## 검증 이력

- Round 7-10: XCC 검증 완료
- Baseline: `schema/baseline_v1/lenovo_xcc_baseline.json`

## Reference

- `docs/reference/live-validation.md`
- Lenovo XCC Redfish API guide (외부)
