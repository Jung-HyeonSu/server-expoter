# Evidence — Tier 1+2 미수집 필드 구현 (audit 후속)

> 일자: 2026-06-22. 전수조사(AUDIT-defined-not-collected.md) 결과 중 Tier 1(무의존)+Tier 2(channel drift) 구현.
> 사용자 지시 "Tier 1+2 다 구현". commit: T2 `03dbebc6` / T1 `dcdf32e8` / esxi_baseline `8aa06f18`.

## Tier 2 — channel drift 정정 (schema only)

- `storage.physical_disks[].health` field_dictionary 신규 등록 (redfish,os) — Windows `Get-PhysicalDisk.HealthStatus` 이미 emit.
- `memory.slots[]` 7 서브필드(capacity_mb/type/speed_mhz/manufacturer/part_number/serial + 배열) channel 에 os 추가
  — Windows `Win32_PhysicalMemory` / Linux `dmidecode` 이미 수집.
- 검증: field_dictionary validator PASS, pytest 1254 passed.

## Tier 1 — 무의존 신규 수집 (실측 검증)

### Linux (gatherOS #, 10.100.64.96 baremetal Dell R760)
- **storage.controllers[]** (lspci, python+raw) — ✅ 실측 4개:
  | id | name | driver | type |
  |---|---|---|---|
  | 0000:52:00.0 | Dell PERC H965i Front | mpi3mr | RAID |
  | 0000:01:00.0 | Dell BOSS-N1 Monolithic | nvme | NVMe |
  | 0000:00:18.0/19.0 | Dell Sapphire Rapids SATA AHCI | ahci | SATA |
- **network.adapters[].firmware_version** (ethtool -i, pci 매칭) — ✅ 실측:
  tg3 `FFV22.91.5 bc 5720-v1.39` / bnxt_en `229.2.52.0/pkg 22.92.06.10` / i40e `8.40 0x8000b1fb 20.5.16`.
- status=success.

### ESXi (gatherESXi #, 10.100.64.2 esxi02)
- **storage.controllers[]** (hostBusAdapter + pciDevice vendor, esxi_disks 모듈 확장) — ✅ 실측 5개:
  vmhba0/1 AHCI(vmw_ahci, Intel) / vmhba2/3 FC(nfnic, Cisco) / vmhba4 SAS MegaRAID(lsi_mr3, Broadcom). esxi_baseline 반영.
- **system.runtime.listening_ports** (firewall.ruleset) — ⚠️ **부분**: root 접속 시 13개(`22/443/902/5989/...`) 정상,
  그러나 **gather(vault) 유저로는 `[]`** 반환. ESXi firewall config 읽기 권한(Host.Config.*) 부족 추정. graceful [] (에러 없음).

## 검증 요약

- ✅ Linux controllers + NIC firmware: 96 baremetal 실측, python+raw 양쪽.
- ✅ ESXi controllers: esxi02 실측, baseline 반영. pytest 1254 passed, validator PASS, vendor boundary 통과.
- ⚠️ ESXi listening_ports: root 동작 확인, 운영 vault 유저 권한 부족으로 production 에선 [] — 권한 grant 필요(ops, NEXT_ACTIONS).
- ⚠️ Linux baseline(ubuntu/rhel810, VM): 신규 controllers[]/adapters.firmware_version 키 미반영 — VM 재캡처 follow-up
  (pytest 영향 없음, 96 baremetal 로 feature 검증 완료).

## 후속

- ESXi gather 계정에 firewall 읽기 권한 grant → listening_ports 활성 (ops 결정).
- Linux ubuntu/rhel810 baseline 재캡처 (controllers/firmware 키 — VM 값).
- 잔여 Tier 3 (smartctl health/wear, thermal/power 섹션, OS firmware) — 의존성/섹션 결정 대기.
