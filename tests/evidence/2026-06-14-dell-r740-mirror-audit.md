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

---

## 2차 전수 재검수 (multi-agent, 2 round + 적대 검증) — 2026-06-14

> 방법: 위 3 fix 가 적용된 상태에서 DELL R740 실 미러 기준으로 **2 라운드 독립 각도** 재검수.
> Round 1 = output-first 12 관점 agent (system/bmc/processors/memory/storage/network/network_adapters/
> firmware/power/normalize-schema/exception-collection/vendor-oem), 각 finding 을 **독립 skeptic 2명**이
> raw 재fetch 로 적대 검증(기본 refute). Round 2 = raw-first 6 리소스군 완전성 sweep + 4 fix 재검증.
> 총 85 agent (R1 78 + R2 7). 도구: `replay_full_mirror.py` + 신규 `mirror_lookup.py` (provenance 1:1 조회).

### 결과 요약

| 항목 | 결과 |
|---|---|
| 모듈 수집 데이터 정합 (provenance) | **wrong-data BUG 0건** — 모든 값이 올바른 Redfish 리소스/속성에서 수집 [PASS] |
| 적대 검증 (Round 1) | 31 confirmed / 1 refuted (STO-7 거짓양성: sum 에서 0 drop 은 no-op) / 1 uncertain |
| Round 2 raw-first 6 sweep | **신규 BUG 0건** (adversarial verify 0 confirmed) |
| 4 fix 재검증 (FW-1/NET-1/STO-1/SYS-5) | 4/4 PASS — 재발 0 [PASS] |
| pytest 회귀 | 1081 passed / 5 skipped (baseline 동일, SYS-5 전후 불변) [PASS] |
| SYS-5 envelope 영향 | byte-identical (값 변화 0, latent 0°C 보호만) [PASS] |

confirmed 31건 중 **wrong-data BUG 은 0건**. 31건 전부 IMPROVEMENT(네이밍/스키마 문서/enrichment/
교차채널 계약/설계 범위) 이며 사용자 결정 대상(아래) 또는 의도된 설계.

### 이번 세션 신규 수정 1건 (적용 + 검증 완료)

#### SYS-5 — estimated_exhaust_temp `or` → 명시 None (latent 0°C 보호)
- **증상**: `_extract_oem_dell` 가 `EstimatedExhaustTemperatureCelsius or EstimatedExhaustTemperatureCel`.
  정상 값 0(0°C 배기온)이 falsy 로 흘러 두 번째 키/None 으로 오기재되는 latent 버그.
- **출처 검증**: raw `Oem.Dell.DellSystem.EstimatedExhaustTemperatureCelsius = 24`, 두 번째 키 부재.
- **수정**: `redfish-gather/library/redfish_gather.py` — `is not None` 명시 비교로 genuine 0 보존.
- **검증**: replay envelope byte-identical (값 24 불변), pytest 1081 pass 불변. Additive(현 값 영향 0).

### 4 fix 재검증 evidence (재발 없음)
- FW-1: raw 62 멤버(19 Current+32 Installed+11 Previous) → emitted 32. Previous skip + 동일버전 dup-pair
  collapse, 충돌 version 0 → 정당 펌웨어 유실 0. [PASS]
- NET-1: NIC.Integrated.1 port_count=4 = Controllers[0]+[1] NetworkPortCount(2+2) = 실 NetworkPorts 멤버 4.
  단일 컨트롤러 어댑터 불변(2). [PASS]
- STO-1: boot_volume true 정확히 1건(Disk.Virtual.0) = 컨트롤러 `BootVirtualDiskFQDD`==vol_id. 표준
  `BootVolume`/Dell `BootVolumeSource` 둘 다 raw 부재 → 컨트롤러 OEM fallback 만 권위 source. [PASS]
- SYS-5: raw Celsius=24 보존, `is not None` 가드 유지. [PASS]

### 의도된 설계로 재확인(버그 아님)
- `users` 섹션 부재: AccountService 에 2 계정 노출되나 redfish envelope 은 `sections.users=not_supported`
  + `users=[]`. 전 redfish baseline 동일. users 정본은 OS 채널. → silent-missing 아님(호출자 오인 없음).
- thermal 미수집: `/Chassis/.../Thermal` 에 fan 6 + temp 4 노출되나 schema 에 thermal 섹션 없음
  (ADR-2026-06-09 가 thermal 을 multi-chassis CSUS/Superdome 으로 한정). 단일노드 envelope 은
  thermal 을 주장하지 않으므로 데이터 거짓 아님 → 설계 범위 결정 사항(아래).

### 사용자 결정 필요 (계약/스키마/baseline/교차채널 — rule 13 R3·R4 / 50 / 92 R5 / 보호경로)

> 아래는 전부 raw 로 검증된 IMPROVEMENT. 값은 정확하거나 의도된 동작이며, 변경 시 **호출자 계약 /
> sections.yml / 보호 baseline / 다채널 정합**에 영향 → AI 자율 수정 보류, 결정 주체=사용자.

1. **firmware `category` 오분류** (normalize, 미문서 enrichment): drive→storage_controller(4),
   driver_pack→drive, backplane→storage_controller, service_module→bmc, fc_hba→other.
   elif 첫매치 우선 + 광범위 substring(`raid`/`drive`) 충돌. **검증된 정정 순서**(specific→broad,
   disk 를 backplane 위로) 준비 완료(jinja2 render 로 Dell 7건 정정 확인). 단 `category` 가
   `hpe_csus_3200_baseline.json`(MOCK)에만 존재 + 그 CSUS 모듈 firmware id 재현 불가 → CSUS 무영향
   증명 불가. 적용 시 CSUS 재-baseline 필요(보호 경로).
2. **link_status enum 계약 불일치** (교차채널): 코드 `_normalize_link_status`→`up`/`down`/`unknown`,
   field_dictionary enum=`["linkup","linkdown","none",null]`, baseline 은 혼재(up/down + linkup/linkdown +
   Connected/Disconnected/offline). Dell R740 는 raw 충실(up/down). redfish/os/esxi 3채널 어휘 통일 +
   전 baseline 재캡처 필요.
3. **thermal 섹션 신설** (schema): 단일노드 fan/temp 수집 원하면 sections.yml + field_dictionary +
   전 baseline + gather_thermal 단일노드 배선. 7단계 절차 + 승인.
4. **field_dictionary 문서 보강**(Additive): bmc.* 15필드 / memory.slots[]·total_mb / cpu·memory·
   storage·network summary group shape 등 emitted 되나 미문서. 문서 정책 결정.
5. **소소(값 정확, 네이밍/enrichment)**: lifecycle_version dead read(Dell 항상 null) / led_state
   deprecated IndicatorLED vs canonical LocationIndicatorActive(=false) 불일치 / boot_progress OEM
   detail(`OemLastState`) 손실 / speed_mhz=MaxSpeedMHz(4000) vs OperatingSpeedMHz(2400) 미노출 /
   architecture `x86` vs `x86_64` / controller_firmware `""` vs null / power.summary.redundant 휴리스틱
   vs 실 RedundancyStatus / consumed_capacity_pct 분모 모호 / bmc network_services 미노출.

### 결론
DELL R740 실 미러 기준 **수집 데이터 정합성 = wrong-data BUG 0 / mis-collected 0 / 회귀 0 / SYS-5 부작용 0**.
남은 항목은 전부 사용자 결정(계약/스키마/보호 baseline/다채널) 또는 의도된 설계. 2 라운드(output-first +
raw-first) × 적대 검증으로 수렴 확인.
