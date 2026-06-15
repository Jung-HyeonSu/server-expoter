# HPE Compute Scale-up Server 3200 (CSUS 3200 / RMC) 실 미러 전수 검수 — 2026-06-15

## 출처 (rule 70 R3 / rule 21 R2)

| 항목 | 값 |
|---|---|
| 장비 | HPE Compute Scale-up Server 3200 (CSUS 3200) — 4-socket nPartition, RMC 관리 |
| BMC | RMC (RackManager) 펌웨어 1.75.108-20260408_164726 |
| RedfishVersion | 1.19.0 (ServiceRoot.Product="Compute Scale-up Server 3200", Vendor=HPE) |
| 미러 도구 | `tests/redfish-probe/redfish_full_mirror.py` (BFS 자동발견) |
| 미러 위치 | `C:\github\서버mock데이터\HPE_CSUS3200\{01,02,03,04}` — **실 4 노드** (각 독립 RMC, IP 10.173.22.{101,102,80,91}, 490~637 리소스) |
| 재생 도구 | `tests/redfish-probe/replay_full_mirror.py` (offline → redfish_gather.py 구동, `--layout rmc_primary`) |
| provenance 대조 | `tests/redfish-probe/mirror_lookup.py` (envelope 값 ↔ raw 리소스 1:1) |
| 검수 방식 | 3-round 반복 다관점 검수 (Workflow: 7 perspective finder × self-verify, round1 은 적대적 verify 분리). 4 노드 구조 동일(Partition0 / Chassis[RackGroup,Rack1,r001u01] / Manager RMC); 03/04 는 FC HBA 더 많음 |

> 중요: replay 는 **라이브러리(redfish_gather.py)** 를 구동한다. envelope.data 는 라이브러리 산출물이며
> Ansible normalize YAML 은 replay 가 거치지 않는다. 라이브러리 결함은 replay 로 직접 검증, normalize/
> 스키마/baseline-layer 는 코드 정독 + raw 입력 증명으로 검증했다. (DL380 검수와 동일 2-layer 구분)

## 핵심 root cause — chassis 오선택 (CSUS-R1)

`detect_vendor` 가 `_resolve_first_member_uri(Chassis)` 로 Chassis 컬렉션 **첫 멤버 RackGroup**(집계용 — PowerSubsystem/ThermalSubsystem/NetworkAdapters 부재)을 chassis_uri 로 잡았다. 실제 compute chassis 는 `Systems/Partition0.Links.Chassis = /redfish/v1/Chassis/r001u01`. 그 결과 power/thermal 이 빈 chassis 에서 수집돼 `data.power={}`·`data.thermal={}` 인데 `collected=success`(누락이 정상처럼 보임), `network_adapters=unsupported`(false not-supported), **FC HBA 전량 소실**. 단일 chassis vendor(Dell/HPE/Lenovo 실미러 검증)는 `Links.Chassis[0]`==첫 멤버라 무영향.

## 수정 완료 (16건) — 전부 raw 대조로 faithful 확인 + 회귀 테스트 (Additive only)

| # | ID | sev | 내용 | raw 증거 |
|---|---|---|---|---|
| 1 | CSUS-R1 | CRIT | `_resolve_system_chassis_uri` 신설 — power/thermal/network_adapters/system 이 `System.Links.Chassis`(r001u01) 사용. 첫 멤버 RackGroup fallback 만 유지 | Partition0.Links.Chassis=[r001u01]; r001u01 에 PowerSubsystem/ThermalSubsystem/NetworkAdapters 존재, RackGroup 엔 부재 |
| 2 | CSUS-FC2 | CRIT | FC HBA WWPN — Port.FibreChannel 의 `AssociatedWorldWideNames` 읽기 추가(구 `AssociatedWWNs` 만) | Port PCIeCard10Port1.FibreChannel.AssociatedWorldWideNames=["51:40:2E:C0:20:82:C2:2C"] |
| 3 | CSUS-FC1 | CRIT | NDF↔Port 매칭: PhysicalPortAssignment 부재 시 ID 일치(NDF.Id==Port.Id) fallback + `_classify_port_protocol` 에 NDF.wwpn→FC 시그널 | NDF 가 Links.PCIeFunction 만 노출(PhysicalPortAssignment 없음), NDF.Id==Port.Id="PCIeCard10Port1", NDF.FibreChannel.WWPN 존재 |
| 4 | CSUS-R3 | MED | `gather_systems_multi` 에 product_hint + per-partition Links.Chassis 전달 → multi_node.partitions[].system manufacturer/model 채움 | Partition0 Manufacturer/Model 부재 → ServiceRoot.Product + r001u01.Manufacturer fallback |
| 5 | CSUS-R4 | MED | `bmc.oem.ilo_version` 의 `or Manager.Model` fallback 제거 (RMC→null) | Managers/RMC.Oem.Hpe(#HpeH3ManagerRmc) Firmware 부재, Model="...4S XNC Base Chassis"(버전 아님) |
| 6 | CSUS-R5 | LOW | `_classify_chassis_kind` 가 RackGroup/Rack ChassisType 인식 (구 kind=null) | RackGroup.ChassisType="RackGroup", Rack1="Rack" |
| 7 | CSUS-R6 | HIGH | `network_adapters[].port_count` — ControllerCapabilities.NetworkPortCount 부재 시 실제 수집 ports 수로 보정(구 0) | PCIeCard10.Controllers 에 ControllerCapabilities 없음, Ports Members=2 |
| 8 | CSUS-R9 | MED | PSU `firmware_version` = FirmwareVersion **or Version** fallback | PSU0 FirmwareVersion 부재, Version="Release -0005" |
| 9 | CSUS-R10 | MED | `power_control.power_consumed_watts` — EnvironmentMetrics 부재 시 PSU `Metrics.InputPowerWatts` 합 | /EnvironmentMetrics 404; PSU0~3 Metrics.InputPowerWatts=199/176.25/177.25/179.25 → 합 731 (env 731 일치) |
| 10 | CSUS-R11 | HIGH | thermal `fans[].reading` — Fan 에 SpeedPercent 없으면 Chassis/Sensors(ReadingType=Rotational).RelatedItem 역참조로 RPM | Fan ChassisFan0 SpeedPercent 부재; Sensors/CHASSIS_FAN0 Reading=4410 RPM, RelatedItem=[…/Fans/ChassisFan0] |
| 11 | CSUS-R12 | MED | memory `locator` — DeviceLocator 부재 + Slot=0(falsy)일 때 Location.PartLocation.ServiceLabel (Slot truthy vendor 불변) | 16 DIMM 전부 DeviceLocator 부재 + MemoryLocation.Slot=0; ServiceLabel="rack1/chassis_u1/cpu0/dimmA0" |
| 12 | CSUS-R8 | MED | `_classify_port_protocol` 에 Port.Ethernet dict → 'Ethernet' (FC/IB dict-presence 와 대칭). 구: PortProtocol/NetDevFuncType 없는 Ethernet 포트 port_type=null | env_03/04 Mellanox MCX631102 8 포트: Port.Ethernet.AssociatedMACAddresses 만 노출, PortProtocol/PortType 부재 → 구 None, 수정 후 Ethernet |
| 13 | CSUS-R13 | MED | FC 포트 `associated_address` = NDF.WWPN (구: assoc[0] — 다중 WWN 시 WWNN 오취득). fc_hbas[].wwpn 과 일관 | node03 Port.FibreChannel.AssociatedWorldWideNames=[WWNN ...EC:65, WWPN ...EC:64]; NDF.WWPN=...EC:64. 구 assoc[0]=WWNN, 수정 후 WWPN |
| 14 | CSUS-R14 | MED | `power_consumed_watts` — EnvironmentMetrics 부재 시 장비 권위 TelemetryService TotalPowerConsumedWatts 우선 (R10 PSU 입력합은 최후 fallback) | TelemetryService/MetricReports/Chassisr001u01_TotalPowerConsumedWatts MetricValue="591.5"(=591) — PSU InputPowerWatts 합 731(AC 입력, +24%)보다 정확 |
| 15 | CSUS-R15 | MED | `gather_managers_multi` 가 `multi_node.managers[].bmc` 에서 내부 임시키 `_network_meta` strip (top-level data.bmc 는 normalize 가 제거하나 multi_node 는 verbatim 통과해 누설) | env multi_node.managers[0].bmc 에 `_network_meta` 노출(rule 13 R5 envelope 비노출 키 위반) → 제거 |
| 16 | CSUS-R16 | MED | NetworkAdapter `firmware_version` — Controllers[0].FirmwarePackageVersion 부재 시 Links.PCIeDevices[].FirmwareVersion 링크추적 fallback | node03 Mellanox: FirmwarePackageVersion 부재, PCIeDevices/1.FirmwareVersion="26.46.3048 (MT_0000000575)" → 구 null, 수정 후 채움 (node01 FC HBA 는 PCIeDevice FW 도 부재 → null faithful) |

(번호 1~6 = batch1, 7~11 = batch2, 12~14 = batch3[round3], 15~16 = batch4[round4 재검수 발견]. ID 는 코드 주석 prefix.)

### 회귀 (rule 24 R2/R6) — 부작용 0 증명

- `pytest tests/` : **1151 passed, 5 skipped** (수정 전 baseline 1126 + 신규 회귀 25).
  - 신규: `tests/unit/test_csus_mirror_audit_fixes.py` (25) — 16 수정 + 회귀안전(meaningful Slot 보존, EnvironmentMetrics 우선, 실 iLO ilo_version 보존, DeviceLocator 우선, Ethernet dict 없으면 None, FC assoc==wwpn 일관, telemetry 우선, FirmwarePackageVersion 우선).
- **타 벤더 무영향 증명**: Dell R740 / HPE DL380 / Lenovo SR650 실 미러 replay envelope `git stash` pre/post diff 4회(batch1·2·3·4).
  - batch1·2·4: **완전 byte-identical** (해당 수정 전부 `Links.Chassis[0]`==첫 멤버 / ControllerCapabilities 보유 / FirmwareVersion 보유 / Slot truthy / legacy /Power 보유 / multi_node 미해당[CSUS 전용] / FirmwarePackageVersion 보유 조건에서 미발동).
  - batch3: HPE DL380·Lenovo SR650 **identical**; **Dell R740 는 FC 포트 4건 associated_address 가 WWNN→WWPN 으로 교정**(R13). raw 대조로 faithful 확인 — Dell fc_hbas[].wwpn 이 이미 `21:00:...`(NDF.WWPN)인데 ports[].associated_address 만 `20:00:...`(WWNN)이던 *기존 불일치*를 R13 이 해소(assoc==wwpn 일관). 커밋된 baseline(dell/hpe/lenovo)에는 associated_address/wwpn 필드 부재 → baseline 영향 0. (※ R13 은 전 벤더 적용 — Dell 개선은 의도된 cross-vendor 정합 교정)
- **HPE emulator golden 2종 faithful 재생성**: `hpe_emulator_dl325_gen10plus_fc`, `hpe_emulator_dl365_gen10plus` 의 `expected_output.json` — R13 으로 FC 포트 associated_address 가 WWNN→WWPN(fc_hbas.wwpn 과 일치)로 교정. blast-radius diff 로 **정확히 포트당 associated_address 1필드씩만** 변경 확인(구 golden 은 assoc≠wwpn 불일치를 박제). R8 은 이 emulator 들의 Ethernet 포트가 *이미* 분류돼 있어 golden 변동 0. dmtf mockup·나머지 emulator 3종 변동 0.

### 4 노드 수정 후 결과 (replay)

| 노드 | status | unsup | PSU | consumed | fan RPM | FC HBA | Ethernet port | port_count |
|---|---|---|---|---|---|---|---|---|
| 01 | success | [] | 4 | 591W | 10/10 | 4 | 0 | 2 |
| 02 | success | [] | 4 | 600W | 10/10 | 4 | 0 | 2 |
| 03 | success | [] | 4 | 1000W | 10/10 | 8 | 8 | 2 |
| 04 | success | [] | 4 | 945W | 10/10 | 8 | 8 | 2 |

- consumed = 장비 권위 TelemetryService TotalPowerConsumedWatts (591.5/600.25/1000.5/945.75 → int).
- top-level `data.power`/`data.thermal` == `multi_node.chassis[r001u01]` (병합 일관성 확인).

## 보고 — gated (자율 미수정, 결정/실측/승인 필요)

> 아래는 검수에서 confirmed 됐으나 (a) 보호 경로(schema/baseline·field_dictionary) (b) Ansible control node(Windows 미지원) (c) envelope shape 변경(호출자 계약) (d) lab 부재 OEM 실측 중 하나라 자율 수정하지 않고 보고한다.

| ID | sev | 내용 | 권장 조치 |
|---|---|---|---|
| BASE-01 | HIGH | `schema/baseline_v1/hpe_csus_3200_baseline.json` 이 구 MOCK(가상 3-partition/4-manager, 날조 PSU/WWPN/토폴로지) — 실 4노드와 전면 불일치. FC 위치도 baseline=storage.hbas vs 실=network_adapters.fc_hbas | 실 미러 정규화 결과로 baseline 교체 (rule 13 R4). **Ansible control node 필요 — 본 Windows 환경 미지원**(DL380 과 동일 제약). NEXT_ACTIONS 등재 |
| FD-01 | MED | field_dictionary drift — `multi_node.partitions[].boot` / `chassis[].thermal` / `composition` / `fabrics` / summary 신필드 미문서 (엔진은 이미 emit) | field_dictionary 보강 + 카운트 동기화 (보호 경로 — 사용자 승인) |
| OEM-01 | MED | `tasks/vendors/hpe/collect_oem.yml` 이 Superdome Flex 추정 필드명(PartitionInfo/FlexNodeInfo)을 읽어 CSUS 실 OEM(#HpeH3Npar: ProductId/ConsoleRouting/Physloc 등)과 불일치 → OEM fragment 영구 미생성(라이브러리 replay 미노출, 실 파이프라인 silent 누락) | lab/실 raw 로 HpeH3* 실 필드명 확인 후 collect_oem 교정 (lab 부재) |
| SYS-OEM | MED | `system.oem` 이 iLO-shaped all-null dict (CSUS HpeH3Npar 는 iLO 필드 없음). 현재 faithful(신규 키 추가 금지 정책)이나 호출자 오인 소지 | @odata.type HpeH3* 시 vendor-적합 OEM shape 검토 (보호 경로) |
| NET-SHAPE | LOW | top-level `data.network`=list vs `multi_node.partitions[].network`=dict — 동일 의미 섹션 타입 불일치(빈값 자체는 raw 충실) | network shape 통일 (envelope 변경 — rule 13 R5/R7 + 승인) |
| NET-SEC-MAP | MED | normalize `_rf_proc_map` 가 network/network_adapters 를 같은 'network' 로 collapse + build_sections unsupported 우선 → host network 성공이 network_adapters 404 에 가려질 latent 충돌 (CSUS 수정 후 미발동) | build_sections 충돌해소 규칙 명시 (normalize 다채널 영향 — 승인) |
| RMP-ADP | MED | Rmp(관리 프로세서) NetworkAdapter 가 placeholder 필터(mfr/model null+port_count 0)로 drop — 단 MgmtPort MAC 은 bmc.mac_address 에 이미 존재(데이터 손실 아님), 관리 어댑터라 host NIC 인벤토리 제외는 방어적 | 필터를 "Ports 멤버 존재 시 보존"으로 보강 검토 (Lenovo 빈슬롯 필터 회귀 위험 — 별도 검증) |
| RB-COUNT | LOW | multi_node.composition.resource_blocks[].processor_count/memory_count=0 — ResourceBlockType=ComputerSystem 은 Processors/Memory 배열 부재(데이터는 Systems/1 하위)라 0 이 충실 | lab 확보됐으니 Systems/{n} count fallback 검토 (LOW) |

## by-design / faithful (조치 불필요)

- 메모리 `manufacturer`="SK hynix" : raw "Hynix Semiconductor" 의 JEDEC/canonical 정규화(`_normalize_jedec`, cross-vendor 일관) — 의도된 동작.
- 메모리 `speed_mhz`=2400 : raw OperatingSpeedMhz 충실. `error_correction`/`rank_count`=null : raw 부재.
- storage drives=[] : Partition0/Storage/1.Drives=[] (무디스크 — boot from fabric). 충실.
- `data.network`(EthernetInterfaces)=[] : Partition0/EthernetInterfaces Members=0 (host NIC 은 Chassis NetworkAdapters 에 노출). 충실.
- thermal `temperatures` 의 `*_THROT_OFFSET` 음수값 : 장비가 ThermalMetrics.TemperatureReadingsCelsius 안에 throttle-offset 을 넣음 — raw 충실 passthrough(DeviceName 으로 구분 가능). 강제 수정 시 정상 sub-zero 판독 손실 위험 → 미수정.
- `power.power_supplies[].power_capacity_w`=null : raw PowerCapacityWatts 부재. 충실.

## 수렴 (round 별)

| round | 산출 | 수정(fix) | 비고 |
|---|---|---|---|
| 1 | env_01 | (검수) | 7관점 finder 51 raw findings → 적대적 verify rate-limit, critic 6 + 독립 raw 검증으로 R1/FC/R3/R4/R5 확정 |
| batch1 | v1 | R1,FC1,FC2,R3,R4,R5 (6) | replay 로 power/thermal/network_adapters/FC WWPN 채움 + 타벤더 identical |
| 2 | v1 | (재검수) | 7관점 self-verify 24 verified + critic 13 → batch2 5건 확정 (port_count/PSU fw·power/fan RPM/locator) |
| batch2 | v2 | R6,R9,R10,R11,R12 (5) | replay 로 port_count/fan RPM/PSU power 채움 + 타벤더 identical |
| 3 | v2 | (재검수) | 7관점 self-verify → 신규 3건 (Ethernet port_type / FC assoc=WWNN / power 부정확[telemetry]) |
| batch3 | v3 | R8,R13,R14 (3) | Ethernet 분류 + FC assoc=WWPN + telemetry 권위 power. emulator golden 2종 faithful 재생성, Dell FC assoc 교정 |
| 4 | v3 | (재검수) | 6관점 수렴 + 신규 3건 (_network_meta 누설 / adapter firmware PCIeDevice / Dell 문서정정[기반영]) |
| batch4 | v4 | R15,R16 (2) | _network_meta strip + adapter firmware PCIeDevice fallback. 타벤더 identical |
| 5 | v4 | **0 (수렴)** | 7관점 전부 CONVERGED — is_verified=true 신규 library 데이터버그 0건. 16건 raw 1:1 재확인 PASS |

(총 16 = R1·FC1·FC2·R3·R4·R5·R6·R9·R10·R11·R12·R8·R13·R14·R15·R16)

## 결론

- **라이브러리(redfish_gather.py) 데이터 정확성**: HPE CSUS 3200 실 4노드 raw 기준 전 leaf provenance 대조 —
  chassis 오선택(누락이 정상처럼)·FC HBA 소실·FC WWNN/WWPN 오매핑·port_count 잘못된 기본값·PSU 펌웨어/소비전력
  누락·fan RPM 링크추적 누락·memory locator 무용값·Ethernet 미분류·multi_node 식별필드 불일치·ilo_version OEM
  오매핑·내부 임시키 누설·adapter firmware 링크추적 누락을 **16건 수정**으로 해소. 전부 raw 충실 + Additive.
  5-round 반복 다관점 검수에서 수렴(각 round 신규 발견 6→5→3→2→0 추세).
- **회귀**: pytest 1151 passed, 타 벤더(Dell/HPE/Lenovo) 실미러 envelope byte-identical (Dell FC assoc 만 R13 의도 교정) — 부작용 0.
- **gated(8건)**: baseline 실측 교체(Ansible 필요)·field_dictionary/OEM/shape 정합은 보호 경로·다채널·lab 실측 필요라 보고.

---

## 재검수 (2026-06-15, 후속 세션) — CSUS-R17 신규 1건 + 3-round 수렴

> 직전 16건 수정 후 사용자 재요청으로 **독립 재검수**. 동일 4 노드 raw + replay_full_mirror.py + mirror_lookup.py.
> 검수 방식: Workflow 11 finder(7 관점 + 섹션 deep-dive + 교차노드) × 적대적 raw-provenance verify × 종합 — 3 round.

### 신규 수정 1건 (CSUS-R17)

| # | ID | sev | 내용 | raw 증거 |
|---|---|---|---|---|
| 17 | CSUS-R17 | MED | `_extract_oem_hpe` 가 vendor=hpe 전체에 iLO 전용 경로(AggregateHealthStatus/Bios.Current/PostState/ServerSignature)만 읽어, CSUS(#HpeH3Npar)에서 **모든 값 null 인 iLO 스켈레톤을 날조**(missing-looks-valid)하고 실 OEM 을 silent drop. OEM `@odata.type` 가 `#HpeH3Npar` 면 CSUS 전용 키(product_id/console_routing/console_routing_current_boot/dcd_version/host_os_name/version/description) 추출하도록 분기. iLO 는 default 분기 불변(Additive, rule 92 R2). | Systems/Partition0.Oem.Hpe.@odata.type=#HpeH3Npar.v1_3_0.HpeH3Npar; ProductId="1590PID03030201"·ConsoleRouting="default"(4노드), DCD.DCDVersion="5.0-7.1"·HostOS(RHEL 8.10)(03/04만). AggregateHealthStatus/Bios.Current/PostState/ServerSignature 4노드 전부 부재 |

- 회귀 테스트: `tests/unit/test_csus_mirror_audit_fixes.py` +3 (R17 #HpeH3Npar 추출 / 빈 DCD·HostOS→null / iLO 분기 보존). pytest 1151→1154 passed.
- 4노드 재생 검증: data.system.oem 이 raw Oem.Hpe(#HpeH3Npar)와 1:1 (01/02 dcd_version·host_os=null[raw 부재], 03/04 채움). top-level == multi_node.partitions[0].system.oem (병합 일관).
- field_dictionary `hardware.oem` 은 벤더 가변 object("키 구조가 벤더마다 완전히 다름")라 CSUS 키 추가는 계약 변경 아님(rule 96 R1-B 위반 아님, envelope 13필드 불변).

### 16 prior fixes 재검증 (3 round 모두 intact)

CSUS-R1·R3·R4·R5·R6·R8·R9·R10·R11·R12·R13·R14·R15·R16 + FC1·FC2 — 4 노드 raw 1:1 재확인 PASS, 회귀 0.

### 수렴 (round 별)

| round | 결과 | 비고 |
|---|---|---|
| 1 (수정 전) | 확정 1(CSUS-R17 bug) + 1(F2 enrichment) / 적대 검증 반증 6 | 11 finder × verify × 종합 |
| 2 (R17 수정 후) | 확정 0 / 반증 8 (전부 faithful-by-design·false-positive) | 독립 재감사, 회귀 0 |
| 3 (재확인) | 확정 0 / 후보 12 전부 비-결함 | 검증자 12건 API 529 overload 사망 → **오케스트레이터가 normalize_standard.yml 직접 정독으로 12건 자체 검증** |

### round 3 후보 12건 — 오케스트레이터 자체 검증 (전부 비-결함)

| 후보 | 판정 | 근거 (코드/raw 직접 확인) |
|---|---|---|
| network-field-type-mismatch ×4 (data.network=list) | replay 아티팩트 | normalize_standard.yml:444-445,545-552 가 라이브러리 list 를 dict 로 재조립. 호출자는 dict 수신 |
| section-naming cpu vs processors | replay 아티팩트 | :442 `processors: cpu` map + :492 `data.cpu` 를 `_rf_d_procs`(=라이브러리 data.processors)로 빌드 |
| missing-hardware-section | replay 아티팩트 | :469 `data.hardware` 를 라이브러리 `data.system`(_rf_d_system)으로 빌드. :459 별도 `data.system`=OS-runtime(null) |
| envelope-sections-structure (collected vs sections) | replay 아티팩트 | build_sections 가 collected/supported → sections dict 생성(production), replay 는 라이브러리 intermediate |
| missing thermal/network_adapters/users in baseline | BASE-01 | 기존 baseline 이 구 MOCK(미수집 섹션). 라이브러리는 정상 수집/정상 미수집. baseline 측 문제(gated) |
| MEM-01 (`CapacityMiB or 0`) | latent / 비-CSUS | CSUS DIMM 전부 CapacityMiB 보유 → 미발동. 범용(전 벤더) 코드, 실측 trigger 부재 → 보고만(아래) |
| csus-r17-stale-envelope | 아티팩트 | 검수 중 한 agent 가 구코드로 만든 `_check.json` stale 파일. 코드는 이미 정상(finder 자인) |

### 보고 — gated / 결정·환경 필요 (자율 미수정)

| ID | sev | 내용 | 사유 |
|---|---|---|---|
| F2 | IMPROVEMENT | Chassis #HpeH3Chassis OEM(Physloc/OemChassisType/PhysicalLocationString/ProcessorsCompatibilityKey) 미수집. CSUS/Superdome 전용 multi_node.chassis 에 한정(타 13벤더 무영향) | enrichment(틀린 값 아님) + multi_node.chassis 비-schema 신키 추가 = scope/계약 결정 |
| MEM-01 | LOW(latent) | `gather_memory`:1942 `_safe(mdata,'CapacityMiB') or 0` — 누락 시 0 날조(누락↔0 혼동). 범용 코드 | CSUS 미발동(전 DIMM CapacityMiB 보유). 실측 trigger 부재 → rule 25 R7-B(가설 수정 자제). 안전 수정案: `or 0` 제거 + `_safe_int(cap) if cap is not None else None` |
| BASE-01 | HIGH | baseline `data.system` 이 OS-게더 키(kernel/selinux/distribution) + 전 섹션 MOCK — 실 4노드와 불일치 | 실 baseline 재생성 = Ansible normalize 파이프라인 필요(본 Windows 환경 미지원) + 보호 경로(승인) |
| FD-01 | MED | field_dictionary 가 multi_node 신필드(boot/thermal/composition/fabrics/summary) 미문서 | 보호 경로 + Must/Nice 카운트 동기화 = schema 변경 승인(rule 13 R3) |
| OEM-01 | LOW | Ansible `collect_oem.yml` 이 실재 안 하는 OEM 필드(PartitionInfo/FlexNodeInfo/GlobalConfiguration) 추출 + 추출값 미사용(항상 `_data_fragment:{}`) = dead/no-op | 무해(라이브러리 CSUS-R17 이 system OEM 직접 수집). Ansible 환경 미보유로 검증 불가 → 정리 권장 |

### 결론

- **라이브러리 데이터 정확성(4 노드 raw 기준)**: 신규 결함 CSUS-R17 **1건 수정**(raw 충실 + Additive + 회귀 테스트). 직전 16건 전부 intact.
  3-round 수렴(신규 결함 1→0→0). round 3 의 12 후보는 전부 replay-vs-production 혼동 또는 baseline(BASE-01) 문제로, 오케스트레이터가 normalize_standard.yml 직접 정독으로 비-결함 확정.
- **회귀**: pytest 1154 passed(=1151+R17 3). 4노드 replay status=success·전 섹션 수집.
- **검증 한계 명시**: replay 는 라이브러리만 구동(Ansible normalize 미경유). normalize 층은 코드 정독 + raw 입력 증명으로 검증.
  round 3 검증자 일부가 API 529 overload 로 사망 → 해당 후보는 오케스트레이터가 직접 코드/ raw 대조로 검증(에이전트 미신뢰 원칙).
- **남은 항목**: 위 gated 5건은 보호 경로/Ansible 환경/scope 결정 필요로 자율 미수정 — 사용자 결정 대상.
