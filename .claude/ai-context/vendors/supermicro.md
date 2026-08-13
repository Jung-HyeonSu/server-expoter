# Supermicro — 벤더 OEM 메모

## 식별

- **Manufacturer**: "Supermicro", "Super Micro Computer"
- **Aliases**: Supermicro, Super Micro, SMCI
- **BMC**: AMI MegaRAC 기반
- **vendor_aliases.yml** 정규화: `supermicro`

## Adapter 매핑

| Adapter | priority | 대상 |
|---|---|---|
| `adapters/redfish/supermicro_x14.yml` | 110 | X14 |
| `adapters/redfish/supermicro_x13.yml` | 100 | X13 |
| `adapters/redfish/supermicro_x12.yml` | 100 | X12 |
| `adapters/redfish/supermicro_x11.yml` | 100 | X11 |
| `adapters/redfish/supermicro_ars.yml` | 80 | ARS 계열 |
| `adapters/redfish/supermicro_x10.yml` | 75 | X10 |
| `adapters/redfish/supermicro_x9.yml` | 50 | X9 |
| `adapters/redfish/supermicro_bmc.yml` | 10 | generic fallback |

X11~X13 은 priority 가 100 으로 같다. 동률이라 `specificity` 와 `match_score` 로
갈린다 — 모델 문자열이 비어 있으면 어느 쪽이 이길지 확정되지 않는다.

## OEM 특이사항

- BMC가 AMI MegaRAC 기반이라 Redfish 응답이 표준에 가까움
- 펌웨어 버전별로 일부 path 차이 있음
- IPMI도 동시에 활성 (필요 시 fallback)

## Vault

- 위치: `vault/<loc>/redfish/supermicro.yml`
- 일반적 계정: `ADMIN`
- 회전: `rotate-vault` skill

## 검증 이력

- 일부 펌웨어 검증. 새 펌웨어 시 `probe-redfish-vendor` skill로 프로파일링 후 baseline 갱신.

## Reference

- `docs/reference/live-validation.md`
