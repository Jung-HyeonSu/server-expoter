# Cisco — 벤더 OEM 메모

## 식별

- **Manufacturer**: "Cisco Systems", "Cisco"
- **Aliases**: Cisco, Cisco Systems, CIMC, UCS
- **BMC 이름**: CIMC (UCS C-Series Integrated Management Controller)
- **vendor_aliases.yml** 정규화: `cisco`

## Adapter 매핑

| Adapter | priority | 대상 |
|---|---|---|
| `adapters/redfish/cisco_cimc.yml` | 100 | CIMC (UCS C-Series) |

## OEM 특이사항

- **Storage**: UCS RAID controller OEM path
- **Network**: VIC adapter OEM
- UCS Manager (UCSM)는 별도 경로 — server-exporter 범위 외 (현재 standalone CIMC만)

## Vault

- 위치: `vault/<loc>/redfish/cisco.yml`
- 일반적 계정: `admin`
- 회전: `rotate-vault` skill

## 검증 이력

- 초기 검증. 새 펌웨어 / 새 모델 시 `probe-redfish-vendor` skill로 프로파일링.

## Reference

- `docs/reference/live-validation.md`
- Cisco CIMC Redfish API doc (외부)
