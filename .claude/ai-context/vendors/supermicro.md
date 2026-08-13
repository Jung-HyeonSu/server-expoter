# Supermicro — 벤더 OEM 메모

## 식별

- **Manufacturer**: "Supermicro", "Super Micro Computer"
- **Aliases**: Supermicro, Super Micro, SMCI
- **BMC**: AMI MegaRAC 기반
- **vendor_aliases.yml** 정규화: `supermicro`

## Adapter 매핑

| Adapter | priority | 대상 |
|---|---|---|
| `adapters/redfish/supermicro_x12.yml` | 100 | X12 generation |
| `adapters/redfish/supermicro_x11.yml` | 80 | X11 generation |
| `adapters/redfish/supermicro_legacy.yml` | 30 | X10 이전 |

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
