# 전수조사 — "스키마 정의됐는데 미수집 + 수집가능" 필드 (ESXi / OS)

> 일자: 2026-06-22. 트리거: ESXi `physical_disks`(항상 `[]`) + OS serial/wwn 누락을 고친 뒤,
> 같은 유형(schema 정의 + 수집가능 + 코드 미수집)을 ESXi/OS 전 채널에서 전수조사.
> 방법: field_dictionary channel + gather 코드 정독 + **실 장비 검증**(ESXi 10.100.64.1/2 pyvmomi,
> Linux 10.100.64.96 baremetal/161/165 SSH). Windows 는 타깃 부재 → MS Learn 문서 기반.

## 분류

- **(A) 순수 누락**: channel 에 해당 OS/esxi 포함 + 코드가 하드코딩 `[]`/`null` + 수집 가능. (physical_disks 와 동일 유형)
- **(B) channel drift**: 코드는 이미 수집하는데 field_dictionary channel 이 redfish 전용 (또는 미등록).
- **(C) 섹션 확장**: vSphere/OS 가 제공하나 sections.yml 이 redfish 전용 (thermal/power/firmware).

## ESXi (실측 — esxi01/02, ESXi 7.0.3)

| 필드 | 분류 | 현재 | 수집 가능? (실측) | 수집원 | 난이도 |
|---|---|---|---|---|---|
| `system.listening_ports` | A | `collect_runtime` 하드코딩 `[]` | **가능** | `firewall.ruleset[]`(enabled 20개) | S |
| `storage.controllers[]` | A/C | normalize_storage `[]` (ch=redfish) | **가능(부분)** | `storageDevice.hostBusAdapter[]`+`pciDevice`(vendor). 실측 vmhba2=MegaRAID SAS | S |
| `hardware.health` rollup | C | 미수집 | **가능** | `summary.overallStatus`+`hardwareStatusInfo`(mem32/cpu30 Green) | S |
| `thermal` (온도28+팬12) | C | 미수집(섹션 redfish) | **가능** | `numericSensorInfo` type=temperature/fan | M |
| `power` (PSU12) | C | `power: null` | **가능** | `numericSensorInfo` type=power(488W 등) | M |
| `memory.slots[]` 부분 | C | `[]` | **부분**(위치+health만, 용량/serial 없음) | `hardwareStatusInfo.memoryStatusInfo` | M |
| `firmware[]` 제한 | C | not_supported | **부분**(host build/patchLevel만) | `summary.config.product` | S |
| `storage.logical_volumes[]` | — | `[]` | **불가** | RAID는 BMC/Redfish 영역(실측: LUN으로만 보임) | — |
| `memory.installed_mb`/per-DIMM 용량 | — | null | **불가** | vSphere 총량만 | — |

## OS Linux (실측 — 96 baremetal R760 / 161 / 165)

| 필드 | 분류 | 현재 | 수집 가능? (실측) | 수집원 | 권한 | 난이도 |
|---|---|---|---|---|---|---|
| `storage.physical_disks[].health` | A | `health: none` 하드코딩 (**must**) | **가능(조건부)** | `smartctl -H` (161=OK). VM=SMART 미지원 | sudo+smartmontools 설치 | M |
| `network.adapters[].firmware_version` | A/C | `adapters[]`에 fw 키 없음 | **가능** | `ethtool -i`(96: bnxt_en `229.2.52.0`, tg3 `FFV22.91.5`) | **불필요** | S |
| `thermal` (온도) | C | 미수집(섹션 redfish) | **가능** | sysfs hwmon/thermal_zone(96: coretemp/nvme/nic 실측) | **불필요** | M |
| `storage.controllers[]` | A/C | `[]` 하드코딩 | **가능(식별)** | `lspci -nnk`(96: PERC H965i + mpi3mr). 상세는 storcli 필요 | 불필요(기본)/storcli | M |
| `firmware[]` BIOS | C | 항상 `[]`(섹션 redfish) | **가능(부분)** | `dmidecode -s bios-version`(161 실측) + `fwupdmgr` + ethtool NIC fw | dmidecode=sudo | M |
| `predicted_life_percent`/`failure_predicted` | A | OS 미수집 | **가능(SSD/NVMe)** | `nvme smart-log`/`smartctl -A` | sudo | M |
| `memory.slots[].serial/locator/rank` | B | slots 수집하나 serial/locator 누락 | **가능** | `dmidecode -t memory` | sudo | S |
| `cpu.flags/microcode` | C | 미수집(schema 미정의) | **가능** | `/proc/cpuinfo`(96: microcode 0x2b000643) | 불필요 | S |
| `interfaces[].speed_mbps` 정확화 | B | sysfs speed(-1 가능) | **개선** | `ethtool` Speed/Duplex | 불필요 | S |
| `storage.logical_volumes[]` | — | `[]` | **부분**(soft RAID mdadm만; HW RAID=storcli) | mdadm/storcli | 상 |
| `power` (PSU) | — | null | **불가**(OS 미노출, hwmon power_input 없음) | — | — |

## OS Windows (문서 — 타깃 부재, MS Learn 기반)

| 필드 | 분류 | 현재 | 수집 가능? | 수집원 | 난이도 |
|---|---|---|---|---|---|
| `physical_disks[].health` | B | 코드 emit(HealthStatus) but field_dictionary 미등록 | **이미 수집**(문서만) | `Get-PhysicalDisk.HealthStatus` | S(문서) |
| `memory.slots[]` 서브필드 | B | 코드 수집(Win32_PhysicalMemory) but channel=redfish | **이미 수집**(channel drift) | — | S(schema) |
| `predicted_life_percent`/`failure_predicted` | A | 미수집 | **가능[문서]** | `Get-StorageReliabilityCounter.Wear` + `MSStorageDriver_FailurePredictStatus` | M |
| `network.interfaces[].driver` | B | driver_map엔 있으나 interface 미부착 | **가능** | `Get-NetAdapter` join | M |
| `controllers[]`/`logical_volumes[]` | A | `[]` 하드코딩 | **부분**(Storage Spaces만; HW RAID 불확실) | `Get-VirtualDisk`/`Get-StoragePool` | 상 |
| `power` | — | not_supported | **불가** | OS 표준 API 없음 | — |
| `thermal` | — | 미수집 | **거의 불가**(VM 미지원, 물리도 대개 미노출) | MSAcpi_ThermalZoneTemperature | — |

## 구현 권장 우선순위 (전 채널 종합)

**Tier 1 — 순수 누락(A) + 무의존성 + 실측확인 (가장 깔끔, physical_disks와 동일 유형)**
1. **ESXi `system.listening_ports`** — firewall.ruleset, runtime 섹션 이미 esxi, schema 무변경.
2. **ESXi `storage.controllers[]`** — hostBusAdapter+pciDevice (esxi_disks.py 동형 모듈).
3. **OS Linux `network.adapters[].firmware_version`** — ethtool -i, **sudo 불필요**, 96 실측.
4. **OS Linux `storage.controllers[]` 식별** — lspci -nnk, **sudo 불필요**, 96 실측(PERC H965i).

**Tier 2 — channel drift 정정(B) (코드 이미 수집, schema/문서만)**
5. **Windows `physical_disks[].health` field_dictionary 등록** (코드 이미 emit).
6. **`memory.slots[]` 서브필드 channel 에 os 추가** (Windows/Linux 이미 수집).

**Tier 3 — 의존성/섹션 결정 필요 (사용자 승인 — rule 92 R1 / 13 R3)**
7. `physical_disks[].health`/`predicted_life_percent` (smartctl/nvme — **smartmontools 설치** 필요, rule 92 R1).
8. `thermal` 섹션 OS+ESXi (sections.yml 확장 — schema 결정).
9. `power` 섹션 ESXi (numericSensorInfo — sections.yml 확장).
10. OS `firmware[]` (dmidecode/fwupd — sections.yml 확장 + dmidecode sudo).

**불가 (확정)**: ESXi logical_volumes/per-DIMM 용량, OS power(PSU), Windows thermal/power.

## 비고

- ESXi disk(physical_disks serial/wwn) 는 본 audit 트리거이자 이미 구현 완료(commit `583dc293`).
- Tier 1/2 는 무의존성·무섹션변경(또는 schema-only)이라 추가 구현 가능. Tier 3 은 의존성/섹션 결정이 사용자 몫.
