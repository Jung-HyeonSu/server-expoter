# Lenovo Redfish 비판적 검증 + Fix (2026-04-29)

## 환경

- Jenkins Agent: `10.100.64.154` (Ubuntu 24.04, jenkins-agent-ops)
- Lenovo BMC: `10.50.11.232` — Lenovo ThinkSystem SR650 V2
  - XCC FirmwareVersion `AFBT58B 5.70 2025-08-11`, BIOS `AFE136D`
  - Redfish API `1.15.0`, ServiceRoot `Vendor="Lenovo"` (Oem 키 비어있음)
  - System UUID `A394FE0C-327A-11ED-8222-3A68DD89594F`, Serial `J30AF7LC`, SKU `7Z73CTO1WW`
  - CPU 2× Intel Xeon Gold 6338 (32C/64T, 2.0 GHz, x86-64)
  - DIMM 16× 32 GiB DDR4-3200 (Micron RDIMM, 총 512 GiB)
  - PSU 2× LENOVO-SP57Ax (PSU1 `Status.Health=Critical` / capacity 미보고, PSU2 750 W)
  - Storage RAID `ThinkSystem RAID 930-8i 2GB Flash PCIe (SAS3508)`, 4× 1.92 TB SATA SSD (Samsung MZ7L31T9HBLT)
  - NetworkAdapter slot-9 = Intel I350 1GbE 4-port; slot-2/5/6 PCIe slot 빈 placeholder
- 검증 방식: Reference dump (2026-04-28 deep_probe, 2457 endpoints) + lib monkey-patch replay
- 검증 스크립트: `replay_normalize.py` (lib `_get`/`_get_noauth` → on-disk reference)

## 발견 분류

### [HIGH] 데이터 손실 — 코드 fix 적용

| ID | RAW (실측 확정) | 이전 결과 | Fix 후 결과 | 위치 |
|---|---|---|---|---|
| A | `Chassis.Oem.Lenovo.ProductName="ThinkSystem SR650 V2"` (System.Oem.Lenovo 부재) | `hardware.oem.product_name=null` | `"ThinkSystem SR650 V2"` | `_extract_oem_lenovo` chassis_data fallback + `gather_system` chassis_uri fetch |
| B | `Manager.Oem.Lenovo.release_name="whitley_gp_23-5"` | `bmc.oem={}` | `{"release_name":"whitley_gp_23-5"}` | `gather_bmc` lenovo 분기 추가 (HPE/Supermicro와 동일 패턴) |
| C | `StorageControllers[0].Name="ThinkSystem RAID 930-8i 2GB Flash PCIe 12Gb Adapter"` (Storage 객체 Name="RAID Storage") | `storage.controllers[0].name="RAID Storage"` (컨테이너 라벨) | 실제 하드웨어 모델명 | `_extract_storage_controller_info` `controller_name` 키 + `_gather_standard_storage` 우선순위 |
| D | StorageControllers[0] `Model="SAS3508"` / `FirmwareVersion="51.23.0-5631"` / `Manufacturer="Lenovo"` / `Status.Health="OK"` | `storage.controllers[0]` 에 controller_* 키 부재 | 4 키 모두 채워짐 | `normalize_standard.yml _rf_norm_controllers` 가 lib 추출 결과 keep (이전엔 drop) |
| E | `Manager EthernetInterface NameServers/StaticNameServers` placeholder + `IPv4Addresses[0].Gateway="10.50.11.254"` | `network.dns_servers=[]` / `default_gateways=[]` | dns_servers=[] (raw 자체 placeholder만 — 정상), gateways=`[{ipv4,10.50.11.254}]` | `gather_bmc` placeholder skip (`""`/`"::"`/`"0.0.0.0"`) + normalize `_rf_norm_dns`/`_rf_norm_gateways` BMC NIC union |
| F | `network.summary.groups[*].link_type=null` 하드코딩 | 항상 null | `"ethernet"` (NetworkAdapter port_type → mac 매칭, 미매칭 시 fallback) | `_rf_summary_network` port_lt 매핑 + ethernet 기본값 |
| G | `Chassis/1/NetworkAdapters` 4 entries: slot-2/5/6 = `Manufacturer/Model=""` + `Controllers[0].ControllerCapabilities.NetworkPortCount=0` (PCIe slot 빈 placeholder); slot-9 = Intel I350 (실 NIC) | `network_adapters.adapters` 4건 (3건 빈값) | 1건 (slot-9만) | `gather_network_adapters_chassis` `port_count==0 + manufacturer==""+ model==""` skip + 빈 문자열 → None 정규화 |

### Envelope 무결성

- envelope 13 필드 정합 (`status, schema_version, target_type, collection_method, ip, hostname, vendor, sections, diagnosis, meta, correlation, errors, data`) — 변경 없음
- 사용자 제약 ("JSON 키 늘리지 마라") 준수 — 모든 fix 는 기존 envelope 키에 값 채움. `controller_name` 만 lib output 단계 (envelope 미노출) 신설.
- `bmc` dict — 임시 키 `_network_meta` 누설 검증 → False (`_rf_d_bmc_clean` 단계에서 제거)

### [MED/LOW] 보류 (Lenovo XCC 자체 한계 — fix 불가)

| ID | 내용 | 사유 |
|---|---|---|
| L1 | `bmc.health=null` | RAW `Manager.Status` 가 `{"State":"Enabled"}` 만 노출, `Health` 필드 자체 부재. Lenovo XCC 펌웨어 현재 응답 형식 |
| L2 | `bmc.last_reset_time=null` | RAW `Manager.LastResetTime` 부재. XCC 미보고 |
| L3 | `bmc.timezone=null` | RAW `Manager.TimeZoneName` 부재. `DateTimeLocalOffset="+00:00"` 만 응답 → `bmc.datetime_offset` 에 별도 채움 |
| L4 | `network.interfaces[*].addresses=[]` (모든 host NIC) | RAW `Systems/1/EthernetInterfaces/{NIC1..4,ToManager}.IPv4Addresses=[]` — host OS NIC IPv4 미보고. `Lenovo.SystemStatus="OSBooted"` 인데도 미응답. XCC 한계 |
| L5 | `power.power_supplies[0].power_capacity_w=null` (PSU1) | PSU1 `Status.Health="Critical"` (실 장비 PSU1 fault). RAW `PowerCapacityWatts=null` — BMC 가 의도적 미보고 |
| L6 | `system.fqdn="XCC-7Z73-J30AF7LC"` (BMC label, OS hostname 아님) | RAW `System.HostName="XCC-7Z73-J30AF7LC"` — Lenovo XCC 가 System.HostName 에 BMC label 을 응답. Host OS hostname 은 OS-gather 영역 |
| M1 | Power.PowerControl 3 entries (Server / CPU subsystem / Memory subsystem) 중 첫 entry 만 추출 | `power_control` 단일 dict 구조 (envelope 정의). CPU/Memory subsystem watt 별도 노출 시 envelope 키 증가 — 사용자 정책 위반 |
| M2 | `network_adapters.ports[*].link_state=null` (LinkStatus 만 응답) | RAW Lenovo `Ports.LinkState` 부재 (Redfish 1.x 에서 deprecated). LinkStatus(Up/Down) 로 충분 |

### [후속] Baseline 재캡처 필요

| ID | 내용 |
|---|---|
| B1 | `lenovo_baseline.json` 은 cycle-016 이전 (2026-04-01 캡처) — 본 cycle 의 cycle-016 Phase M/N 신규 키 (`hardware.asset_tag`, `system_type`, `part_number`, `last_reset_time`, `boot_progress`, `tpm`, `bmc.last_reset_time`, `timezone`, `power_state`, `mac_address`, `dns_name`, `uuid`, `datetime`, `datetime_offset`, `processors[*].processor_type`, `architecture`, `instruction_set`, `serial_number`, `part_number`, `memory.slots[*].rank_count`, `data_width_bits`, `bus_width_bits`, `error_correction`, `base_module_type`, `cpu.summary.groups[*].manufacturer`, `max_speed_mhz`, `architecture`, `memory.summary.groups[*].speed_mhz`, `manufacturer`, `part_number`, `network.summary.adapter_count`, `port_count`, `primary_speed_mbps`, `power.summary.psu_count`, `psu_active`, `redundant`, `total_capacity_w`, `consumed_watts`, `consumed_capacity_pct`) 모두 baseline 부재 — **baseline stale** |
| B2 | 본 commit fix (A~G) 적용 후 `lenovo_baseline.json` 재캡처 필요. 실 ansible-playbook 실행 (vault 자격증명 필요) |

## 변경 파일

```
redfish-gather/library/redfish_gather.py:
  - _extract_oem_lenovo():            chassis_data fallback (Chassis.Oem.Lenovo.ProductName)
                                      + System.Model 최종 fallback
  - gather_system():                  chassis_uri 인자 추가 + chassis_data 1회 fetch (Lenovo OEM 용)
  - gather_bmc():                     lenovo 분기 추가 (Manager.Oem.Lenovo.release_name)
                                      + NameServers/StaticNameServers placeholder skip
                                      ('' / '0.0.0.0' / '::' / '::0' / '::1')
  - _extract_storage_controller_info(): controller_name 키 추가 (StorageControllers[0].Name)
  - _gather_standard_storage():       ctrl_name 우선순위 (controller_name → storage Name fallback)
  - gather_network_adapters_chassis(): 빈 placeholder filter (NetworkPortCount=0 +
                                       manufacturer/model 모두 빈 문자열) skip
                                       + 빈 문자열 → None 정규화
  - _collect_all_sections():          gather_system 에 chassis_uri 전달

redfish-gather/tasks/normalize_standard.yml:
  - _rf_norm_controllers:             controller_model/firmware/manufacturer/health 키 keep (이전 drop)
  - _rf_summary_network:              link_type 정규화
                                      (NetworkAdapter port_type → mac 매칭, fallback 'ethernet')
                                      port_lt dict 신설 + nic_mac normalize 매칭
```

## 영향 vendor

| Vendor | A 영향 (product_name) | B 영향 (bmc.oem) | C/D 영향 (controller name/model) | F 영향 (link_type) | G 영향 (NetworkAdapter filter) |
|---|---|---|---|---|---|
| Dell    | 영향 없음 (`_extract_oem_dell` 별도, ProductName 사용 안 함) | 영향 없음 (Dell 분기 없음 — 기존 oem dict 비었음) | StorageControllers[0].Name 응답 시 정확한 모델명 채워짐 | 'ethernet' 기본값 (정확) | NetworkPortCount > 0 응답 시 영향 없음 |
| HPE     | 영향 없음 (`_extract_oem_hpe` 별도) | 영향 없음 (HPE 분기 기존 유지 — `ilo_version`) | 동일 | 동일 | 동일 |
| Lenovo  | [OK] null → "ThinkSystem SR650 V2" | [OK] {} → {release_name} | [OK] "RAID Storage" → 실 모델명 | [OK] null → ethernet | [OK] 4건 → 1건 |
| Supermicro | 영향 없음 | 영향 없음 (Supermicro 분기 기존 유지 — `bmc_ip`) | 동일 | 동일 | 동일 |
| Cisco   | 영향 없음 (`_OEM_EXTRACTORS` 미등록 — strategy=standard_only) | 영향 없음 | 동일 | 동일 | 동일 |

코드 변경은 모두 vendor-agnostic 정합 + Lenovo-specific extractor 추가. 다른 vendor 영향 없음 (회귀 검사 PASS).

## 검증 결과 (실측)

```
# replay_normalize.py 출력 (lib 단계, mock _get → on-disk reference)
vendor: lenovo
status: success
sections collected: [system, bmc, processors, memory, storage, network, firmware, power, network_adapters]
errors: 0

system.oem.product_name              = "ThinkSystem SR650 V2"     # ← A fix
bmc.oem                              = {"release_name": "whitley_gp_23-5"}  # ← B fix
storage.controllers[0].name          = "ThinkSystem RAID 930-8i 2GB Flash PCIe 12Gb Adapter"  # ← C fix
storage.controllers[0].controller_*  = {model: SAS3508, firmware: 51.23.0-5631, ...}  # ← D fix (lib)
bmc._network_meta.ipv4_gateways      = ["10.50.11.254"]            # ← E fix (BMC NIC gateway)
bmc._network_meta.name_servers       = []                           # ← Lenovo placeholder만 — 정상
network_adapters.adapters count      = 1 (slot-9 only, slot-2/5/6 filtered)  # ← G fix

# replay_full.py 출력 (lib + normalize Jinja2 시뮬레이션)
network_default_gateways             = [{family: ipv4, address: 10.50.11.254}]  # ← E fix (normalize)
network_summary_groups[*].link_type  = "ethernet" (모든 그룹)        # ← F fix (normalize)
network_dns_servers                  = [] (Lenovo placeholder만이라 정상)
storage_controllers[0]               = {name: "ThinkSystem RAID 930-8i ...", controller_model: SAS3508, ...}  # ← C+D 통합
```

- pytest 158/158 PASS (회귀 검사)
- verify_harness_consistency.py PASS (rules:28, skills:43, agents:49, policies:9)
- verify_vendor_boundary.py PASS (common/ + 3-channel gather 에 vendor 하드코딩 없음)
- Python py_compile PASS (redfish_gather.py)
- YAML parse PASS (normalize_standard.yml)
- ansible-playbook --syntax-check PASS (redfish-gather/site.yml)
