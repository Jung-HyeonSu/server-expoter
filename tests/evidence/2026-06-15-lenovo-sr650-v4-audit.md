# Lenovo ThinkSystem SR650 V4 — Redfish 개더링 실미러 검수

- 일자: 2026-06-15
- 대상 장비: Lenovo ThinkSystem SR650 V4 (BMC = XCC3 "Lenovo Xclarity Controller 3")
- 펌웨어: XCC `IHX414J 1.22 20250402` / UEFI `10U-1.20` / Redfish ServiceRoot 1.15.0
- 식별: SN `J902E57T`, SKU `7DGDCTO1WW`, UUID `343AFAA2-321B-11F0-911B-C4EFBB1D4346`
- raw 미러: `redfish_full_mirror.py` 산출 2901 리소스 (discovered 2908, fetched 2xx 2901)
- 재생 도구: `tests/redfish-probe/replay_full_mirror.py` (라이브러리 오프라인 재생)
- 대조 도구: `tests/redfish-probe/mirror_lookup.py` (envelope 값 ↔ 실 Redfish 리소스 1:1 provenance)

## 방법

`redfish_gather.py` 의 `detect_vendor → _collect_all_sections → _collect_multi_node_topology →
_compute_final_status` 흐름을 실 미러로 오프라인 재생해 envelope 산출 → 10 섹션 전 필드를
raw `@odata.id` 리소스의 실제 속성과 1:1 대조. "값 존재" 가 아니라 "올바른 리소스/속성에서
수집됐는가" 를 검증.

## [PASS] 확인된 정합 (faithful — 버그 아님)

전 섹션 raw 1:1 대조 결과 아래는 모두 실 장비 응답을 정확히 반영 (device-limitation, 버그 아님):

- **system**: BiosVersion `IHE110U`, SKU/PartNumber/Serial/UUID/Model 전부 raw Systems/1 일치.
  `cpu_summary.core_count/logical_processor_count/model=null` → raw ProcessorSummary 가 Count+Status
  만 노출 (genuinely absent). `asset_tag=null` (raw AssetTag=""). `health="Warning"` (raw Status.Health,
  HealthRollup=OK 별도 존재). `tpm=null` (raw TrustedModules 키 부재).
- **system.oem**: machine_type/machine_level/product_id/system_id/fru_serial/health_summary/
  led_indicator=null → V4 Chassis.Oem.Lenovo 가 해당 키 미노출 (대신 FruPartNumber/
  SystemBoardSerialNumber/ProductName 보유). `product_name` 은 System.Model fallback,
  `system_status="OSBooted"` (Oem.Lenovo.SystemStatus) 정확.
- **processors**: 2 소켓, total_cores 16 / total_threads 32 / MaxSpeedMHz 4300 / serial /
  architecture x86 / instruction_set x86-64 전부 raw Processors/<id> 일치. `part_number="UNKNOWN"`
  은 raw 리터럴 값.
- **memory**: 32 슬롯 중 16 populated → envelope 16 슬롯 전수 일치 (id/capacity/speed 6400=
  OperatingSpeedMhz/rank/width/ECC). Absent 16 정확히 제외. `total_mib=1048576` = populated 합.
- **storage**: 2 controller (slot1 RAID 940-16i / slot25 M.2) 전수, drives Links 추적 정확,
  volume 1개 (slot25 RAID1, slot1 Volumes 컬렉션 raw 에서 빈 멤버 → 정확히 0). controller
  Model/Manufacturer/Firmware = StorageControllers[0] 출처 정확. CapacitySources 404 graceful.
- **network_adapters**: 3 adapter (slot13 BCM5719 / slot4·slot6 BCM57504) + 12 port 전수,
  model/manufacturer/serial/part/firmware/link_status/speed raw NetworkAdapter 일치.
  `ports[].physical_port_number=null` (raw Port 에 해당 속성 부재).
- **power**: PowerControl[0]=Server 정확 선택 (CPU/Memory Sub-system member 배제).
  `power_consumed_watts=386` (순간) vs metrics `max=348` (window) — 둘 다 raw 실값. PSU 2개 전수.
- **thermal**: legacy `/Thermal` 경로, fans 12 + temperatures 22 = raw 정확히 일치
  (TMargin 센서 포함 faithful). reading/upper_critical/physical_context 출처 정확.
- **bmc**: ip 10.173.12.150 (Manager/1 NIC 우선, ToHost 아님), firmware_version
  `IHX414J 1.22 20250402` (Manager.FirmwareVersion), dns_name/datetime/uuid/health 일치.
  `oem.release_name="bhs_gp_w2w3"`. `timezone=null` (Manager.TimeZoneName 부재 — faithful).
- **구조**: 라이브러리 collected `processors/network_adapters` → normalize 가 schema `cpu` /
  `network` 로 매핑 (normalize_standard.yml 439-445). multi_node=null (단일 노드 정확).

## [NEW] 발견·수정 (real bug)

### FIX1 [HIGH] firmware — pending 엔트리 유실 (`category=missing-data`)

- **현상**: raw FirmwareInventory 26 멤버 중 envelope 24 — `BMC-Primary-Pending`, `UEFI-Pending`
  2건 누락. 둘 다 raw `Version=""` (XCC3 V4 는 빈 문자열, XCC1 V2 는 null 로 노출).
- **원인**: B43 (pending 보존: `pending=true`+`version=null` 정상) 의도가, 뒤에 추가된 Cisco 빈
  슬롯 노이즈 필터 (`ver.strip().upper() in ('N/A','NA','')`) 보다 **나중에** 평가돼,
  `Version=""` 인 pending 이 노이즈로 먼저 드롭됨. `lenovo_baseline.json` 은 pending 엔트리를
  보존(version=null) — 즉 설계상 보존이 맞음. XCC3 의 `""` 표기만 드롭되는 회귀.
- **수정**: `gather_firmware` 에서 `is_pending` 를 빈-version 필터 **앞**으로 이동, pending 은
  필터 예외 + `version=""` → `None` 정규화. (`redfish-gather/library/redfish_gather.py`)
- **검증**: 재생 envelope firmware 24→26, 두 pending `version=null, pending=true` 로 복원.
  비-pending 빈 슬롯(Cisco) 동작 불변 (Additive).

### FIX2 [MEDIUM] network — MAC 대소문자 불일치 (`category=data-mismatch`)

- **현상**: 동일 물리 NIC 이 `data.network[].mac` = `8C:84:74:EC:F4:F0` (대문자) vs
  `data.network_adapters.adapters[].mac` = `8c:84:74:ec:f4:f0` (소문자) 로 갈림. raw XCC 가
  System EthernetInterface MAC 을 대문자로 노출 → `gather_network` 가 verbatim 노출.
- **원인**: round3 XC-4 소문자 정규화가 bmc/ports 에만 적용, `gather_network` 누락 (당시 HPE raw
  가 소문자라 우연히 일관 → Lenovo 대문자에서 표면화). 라이브러리 lowercase 규약(_normalize_wwn
  독스트링) 의 적용 누락.
- **수정**: `gather_network` mac `.lower()` 정규화 (raw colon-hex 무손실).
- **검증**: 재생 envelope 전 network mac 소문자 + network_adapters/bmc 와 case 일관. summary
  MAC-join (normalize_standard.yml 324/335) 은 양측 upper 재정규화라 영향 없음.

## 회귀

- `python -m pytest tests/` (e2e_browser 2건 lab-network 의존 제외): **1123 passed, 6 skipped, 0 fail**.
- DMTF golden `dmtf_rackmount1` — network mac 소문자화로 갱신 필요 → diff 가 **MAC case 단독**임을
  확인 후 `convert_dmtf_mockup.py` 동일 경로(emulator_harness.run_gather)로 golden 재생성 → PASS.
- 사전 환경 실패 2건: `tests/e2e_browser/test_jenkins_master.py` (live Jenkins 10.100.64.152 lab
  망 도달 불가) — 본 검수와 무관, 회귀 아님.
