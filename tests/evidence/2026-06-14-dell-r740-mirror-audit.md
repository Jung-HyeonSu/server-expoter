# DELL R740 실 미러 기준 gather 검수 — 2026-06-14

> 대상: `tests/redfish-probe/redfish_full_mirror.py` 로 떠온 DELL R740 실장비 Redfish 전수 미러
> (`C:/github/서버mock데이터/DELL_R740/01`, fetched_ok 6135, ServiceTag J0KV603, iDRAC9 FW 7.00.00.184).
> 방법: 미러를 실제 `redfish_gather.py` 에 오프라인 재생(신규 `replay_full_mirror.py`)해 수집 envelope 를
> 재현하고, 출력 전 필드를 미러 source 리소스/필드와 1:1 대조(provenance) + 다차원 적대 검증.

## 검수 도구 (신규)

- `tests/redfish-probe/replay_full_mirror.py` — full mirror 를 `_get`/`_get_noauth` monkeypatch 로
  실 gather(`detect_vendor → _collect_all_sections → _collect_multi_node_topology → _compute_final_status`)에
  재생. `@odata.id` 키잉 + headers.json `_status` 보존. stdlib 전용. HPE/Lenovo 미러에도 일반화 확인.

## 검수 결과 요약

| 항목 | 결과 |
|---|---|
| vendor 감지 | dell (ServiceRoot Oem.Dell) [PASS] |
| 수집 status | success / 9 섹션 collected / errors 0 |
| 섹션별 count 정합 | proc 2 / mem 8 / NIC 12 / storage ctrl 3 / NA 7 — 전부 source 일치 |
| 발견 WRONG_DATA | 3건 (FW-1 / NET-1 / STO-1) — **전부 수정 + 검증** |
| 회귀 | pytest 1081 passed (수정 전후 동일, 신규 실패 0; e2e_browser 2건은 live Jenkins 환경 의존 — 기존) |

## 수정한 WRONG_DATA 3건 (실 미러로 fix 검증 완료)

### FW-1 — firmware Current-/Installed- 중복 (51 → 32)
- **증상**: Dell iDRAC FirmwareInventory 가 동일 구동 펌웨어를 `Current-<id>-<ver>__<FQDD>` 와
  `Installed-<...>__<FQDD>` 두 멤버로 노출(같은 SoftwareId/Version/Name). dedup 없어 호출자가 펌웨어
  2배 카운트(실측 51개 중 19개가 중복쌍).
- **출처 검증**: `UpdateService/FirmwareInventory` Members 62 = Current 19 + Installed 32 + Previous 11.
  19개 Current-/Installed- 쌍은 Version/Updateable/Name 100% 동일(diff 0).
- **수정**: `gather_firmware` 에 status-prefix(`Installed-`/`Current-`/`Available-`/`Rollback-`) 제거 key
  로 dedup. **version 포함 key** 라 pending-update(Current=old, Installed=new) 처럼 version 이 다른 쌍은
  보존. prefix 없는 Id(HPE 숫자/Lenovo)는 key=자기자신 → 무영향(Additive).
- **검증**: 51 → 32, 잔여 중복 key 0. HPE dl360 emulator(숫자 Id) 23 → 23 무영향 확인.

### NET-1 — 멀티컨트롤러 NIC port_count 과소집계 (NIC.Integrated.1 2 → 4)
- **증상**: `gather_network_adapters_chassis` 가 `port_count` 를 `Controllers[0].ControllerCapabilities.
  NetworkPortCount` 하나만 읽음. Dell rNDC(`BRCM GbE 4P 5720-t rNDC`)는 NetworkAdapter 1개가
  Controller 2개(각 2포트)를 노출 → 4포트 카드가 2로 보고.
- **출처 검증**: NIC.Integrated.1 Controllers=2(각 NetworkPortCount=2), NetworkPorts Members=4.
- **수정**: 모든 Controller 의 NetworkPortCount 합산. 단일 컨트롤러 카드는 합=그 값 → 불변(Additive).
- **검증**: 7 adapter 전부 emitted port_count == Controller 합 == 실제 NetworkPorts 멤버 수.
  NIC.Integrated.1 2→4, 나머지 불변.

### STO-1 — boot_volume 오탐 (false → true)
- **증상**: `_extract_storage_volumes` 가 boot 판정을 `Volume.Oem.Dell.DellVolume.BootVolumeSource`(R740
  iDRAC9 펌웨어 미제공) 에만 의존 → 실제 OS RAID1 볼륨인데 boot_volume=false.
- **출처 검증**: 컨트롤러 `Oem.Dell.DellController.BootVirtualDiskFQDD = 'Disk.Virtual.0:RAID.Slot.6-1'`
  = Volume.Id. 표준 `Volume.BootVolume` 도 `DellVolume.BootVolumeSource` 도 모두 null.
- **수정**: 표준 `Volume.BootVolume` → (없으면) 컨트롤러 `BootVirtualDiskFQDD` 와 `vol_id` 매칭 →
  (없으면) 기존 BootVolumeSource fallback. 비-Dell/FQDD 부재 경로 영향 0(Additive).
- **검증**: 부팅 볼륨만 true, 나머지 false. false→true 확인.

## 검수했고 정상(=의도된 설계, finding 아님)으로 확인한 항목

- system: serial(SerialNumber)/sku(SKU)/part_number(PartNumber) 정확 분리, bios_date "01/28/2026"→
  "2026-01-28" ISO 변환(월/일 스왑 없음), oem.* 11필드 전부 Oem.Dell.DellSystem 정확 매핑(rollup 뒤바뀜
  없음), tpm(TrustedModules[0]), lifecycle_version=null(source 실제 None).
- bmc: firmware_version=Manager.FirmwareVersion(7.00.00.184, FirmwareInventory stale 3.36 아님),
  ip/mac/gateway 가 Manager 자체 EthernetInterface(NIC.1)에서 옴(System NIC 혼입 없음), name='iDRAC'
  벤더 표시명(의도), name_servers placeholder(0.0.0.0/::) 필터 정상.
- cpu/memory: per-CPU TotalCores/Threads, per-DIMM CapacityMiB/Operating speed, data_width(64)/bus_width(72)
  비스왑, manufacturer "Hynix Semiconductor"→"SK hynix" 의도된 cross-channel canonical(line 385-388).
- storage: drive capacity_gb(decimal /1e9) / volume total_mb(MiB /2^20) 정확, SimpleStorage 5번째 device
  는 backplane(BP14G+EXP)이라 drive 제외 정상 — 4 physical disk 전부 수집(silent drop 없음).
- network_adapters: FC HBA WWPN/WWNN 가 NetworkDeviceFunction(Port 아님)에서, FC speed_gbps=None 은
  포트 Down(source 무speed) 충실 반영.
- power: power_control(PowerControl[0])/PSU 2개, PowerSubsystem 와 legacy Power 병합 중복 없음.

## 개선 후보(값은 정상 — 호출자 계약/스키마 사유로 코드 변경 보류, 사용자 판단 필요)

- speed_mhz 의미: processors=MaxSpeedMHz(=max turbo 4000), memory=OperatingSpeedMhz(=현재 2933).
  값은 각 섹션 canonical Redfish 필드라 정확하나 동일 필드명이 max/current 의미 혼용. envelope 필드명
  변경은 호출자 계약(rule 13 R5) — 스키마 변경은 사용자 승인 필요.
- storage 단위 네이밍: volume total_mb(=MiB)/drive capacity_gb(=decimal GB) 혼용. 값 정확, 프로젝트
  전역 컨벤션. 네이밍 변경=스키마 변경.
- `_normalize_dimm_label`(redfish_gather.py:1297) dead code — 정의+단위테스트만, production 미배선.
  DELL R740 출력엔 무영향(DeviceLocator 이미 'DIMM A5'). 타 벤더 라벨 영향 가능 → 별도 검토.

## 다음 단계 (HPE_CSUS3200 / HPE_DL380 / Lenovo SR650)

- 3개 fix 모두 Additive — 비-Dell 경로 영향 0(설계). 단 각 벤더 미러로 동일 provenance 검수 필요.
- **HPE_CSUS3200**: 미러 4 subdir(01~04, RMC + 노드). `--layout rmc_primary` 로 multi_node 경로 검수 필요.
- HPE_DL380(hpe) / Lenovo SR650(lenovo): 단일노드, 드라이버 smoke=success 확인. 본격 provenance 검수 대기.
- 회귀: 각 벤더 검수 후 pytest 전수 재확인.
