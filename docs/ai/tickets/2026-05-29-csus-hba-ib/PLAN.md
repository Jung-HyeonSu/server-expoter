# 작업 계획 — CSUS 3200 개편 + HBA/InfiniBand 전 채널 수집

> 정본 reference: `EXTERNAL-CONTRACTS.md` (외부 계약), `INDEX.md` (요청/결론).
> 원칙: **Additive only** (rule 92 R2 / rule 96 R1-B) — envelope 13 필드 / 기존 path / sections 10 / 기존 baseline 의미 변경 0. schema version bump 없음.

---

## 1. 현행 실측 (2026-05-29)

| 채널 | HBA (FC) | InfiniBand | 비고 |
|---|---|---|---|
| Redfish | dead code (`PortType` 분류) → 실장비 미매치 | dead code (동일) | 분류 키만 정정하면 됨 (수집 traversal 은 이미 있음) |
| OS Linux | 동작 (sysfs fc_host) | 동작 (sysfs infiniband) | WWNN/vendor/firmware 보강 여지 |
| OS Windows | 부분 (`Get-InitiatorPort`, FC 필터 없음) | hardcoded `[]` | FC 필터 + enrich + IB(Get-NetAdapter) 추가 |
| ESXi | 부분 (`vmware_host_vmhba_info`, port_type/speed/wwnn 드랍) | dead code | API-only 한계 — native IB 미관측 |
| CSUS 3200 | mock 빈 | mock 빈 | per-partition storage/network 미normalize + mock skeleton |

공통 인프라:
- `sections.yml` / `field_dictionary.yml`: `storage.hbas[]`,`storage.infiniband[]`,`network.adapters[]`,`network.ports[]`,`network.driver_map[]` **이미 v1 등록** (array-level). → 서브필드 entry 만 Additive 추가.
- `merge_fragment.yml`: list 누적(concat) + dict 재귀 병합 보장 → 채널별 gather 가 `storage.hbas` 만 기여해도 안전 (rule 22 준수).
- `init_fragments.yml` / `build_empty_data.yml` / `build_failed_output.yml`: 3중 skeleton 동기화 의무 (서브키 추가 시 3곳 모두).

---

## 2. 통일 출력 shape (canonical, 전 채널 공통)

> 목적: redfish/os/esxi 가 **같은 키**를 emit → 호출자가 채널 무관 파싱 + cross-channel 상관(WWPN/GUID)으로 동일 장비 식별. 기존 채널별 추가 키는 **보존**(Additive). 캐노니컬 코어가 없던 채널은 채워 넣음.

**`data.storage.hbas[]`** (FC HBA):
| 필드 | 타입 | 비고 |
|---|---|---|
| `wwpn` | string\|null | canonical 소문자 hex (`0x...` colon 정규화) — cross-channel 매칭 키 |
| `wwnn` | string\|null | Lenovo/Supermicro/일부 OS 에서 null |
| `model` | string\|null | |
| `vendor` | string\|null | vendor_aliases 정규화 |
| `driver` | string\|null | OS/ESXi (lpfc/qlnativefc 등) |
| `firmware` | string\|null | |
| `link_status` | string\|null | up/down/no_link/unknown |
| `link_speed_gbps` | number\|null | field_dictionary 문서 명칭 채택 |
| `port_type` | string | "FibreChannel" \| "FCoE" \| "iSCSI"(subtype) |
| `source` | string | "redfish" \| "os" \| "esxi" (신규 — 출처 식별) |
| (채널 extra 보존) | | redfish: adapter_id/port_id; esxi: device/pci/bus; os(linux): host |

**`data.storage.infiniband[]`** (IB):
| 필드 | 타입 | 비고 |
|---|---|---|
| `adapter` | string\|null | |
| `port` | string\|null | |
| `node_guid` | string\|null | Windows 는 표준 API 부재 → null |
| `port_guid` | string\|null | |
| `link_status` | string\|null | active/down/unknown |
| `rate` | string\|null | 사람 표기 (예: "200 Gb/sec (4X HDR)") — field_dictionary 문서 명칭 |
| `rate_gbps` | number\|null | 숫자 source-of-truth (신규, Additive) |
| `vendor` | string\|null | |
| `firmware` | string\|null | |
| `source` | string | "redfish" \| "os" \| "esxi" |

> **Additive 영향**: 유일하게 채워진 baseline 은 `esxi_baseline.json` (hbas 5건, 기존 키 name/driver/adapter_type/wwpn/wwnn/pci/bus). 본 작업은 이 키들을 **유지**하고 canonical 코어(link_speed_gbps/port_type/source 등)를 **추가**. 기존 키 삭제/리네임 금지.

---

## 3. Phase 별 작업

### P1 — Redfish FC/IB 분류 정정 (CRIT 버그 fix)
- **파일**: `redfish-gather/library/redfish_gather.py` (`gather_network_adapters_chassis` 2135-2271), `redfish-gather/tasks/normalize_standard.yml` (514-516, 523-524).
- FC 판정: `Port.PortProtocol ∈ {FC,FCP,FCoE}` (없으면 `NetworkDeviceFunction.NetDevFuncType=='FibreChannel'`). `PortType` 분류 제거.
- IB 판정: `Port.LinkNetworkTechnology=='InfiniBand'` (또는 `NetworkDeviceFunction.NetworkDeviceTechnology=='InfiniBand'`).
- WWPN/WWNN: NDF.FibreChannel.{WWPN‖PermanentWWPN}/{WWNN‖PermanentWWNN} 우선; StorageController.Identifiers[FC_WWN] fallback.
- IB GUID: NDF.InfiniBand.{NodeGUID/PortGUID} (+ Permanent*); Port.InfiniBand.Associated*GUIDs[]. None 가드 (구 펌웨어).
- 구/신 path 양립: `Ports`(신, CurrentSpeedGbps) vs `NetworkPorts`(구, CurrentLinkSpeedMbps/1000).
- `storage.hbas`/`infiniband` 를 canonical shape 로 normalize. `network` 기존 노출은 **유지**(삭제 금지 — Additive).
- stdlib only 유지 (rule 10 R2). vendor 분기는 OEM tasks 만 (rule 12 R1).

### P2 — CSUS 3200 multi_node 완전 수집 + 현실 baseline
- **파일**: `redfish_gather.py` (`gather_systems_multi` 2610-2648, `_collect_multi_node_topology` 2693-2752), `normalize_standard.yml` (per-partition normalize loop), `adapters/redfish/hpe_csus_3200.yml`, `schema/baseline_v1/hpe_csus_3200_baseline.json`, `tests/fixtures/redfish/hpe_csus_3200/*`.
- 전 Partition 순회 (Members[0] 한계 제거) — 각 partition storage/network 를 top-level 와 동일 normalize → `multi_node.partitions[].storage{controllers,physical_disks,logical_volumes,hbas,infiniband,summary}` + `.network{interfaces,adapters,ports}`.
- 재사용 가능한 normalize 매크로 1개로 top-level / per-partition 동일 처리 (코드 중복 제거).
- top-level `data.storage`/`data.network`/`data.hbas`/`data.infiniband` 도 Partition0 representative + chassis NetworkAdapters 에서 채움 (현재 빈 것 해소).
- baseline 을 **현실 mock** 으로 (EXTERNAL-CONTRACTS §5 evidence): SystemType=PhysicallyPartitioned, Links.Chassis 다중, chassis 에 FC HBA NetworkAdapter(WWPN)+SATA controller+SSD, partition별 storage/network 채움, RMC manager. origin 주석 + DRIFT-correctable + NEXT_ACTIONS.
- fixture 정정: `SystemType`, `Links.Chassis[]`, Storage members, EthernetInterfaces, chassis NetworkAdapters(FC).

### P3 — ESXi HBA enrich + IB 정책
- **파일**: `esxi-gather/tasks/collect_network_extended.yml` (101-127 normalize, 166-182 fragment).
- FC: `port_type`/`speed`/`wwnn` 보존 추가; 분류를 type+driver 2-signal 로 (lpfc/qlnativefc=FC, iscsi_vmk=iSCSI, SAS/RAID→controllers 제외). dead `'infiniband' in type` 제거.
- IB: native 미관측 명시 → `^nmlx` driver NIC 로 best-effort 추론 entry (note 포함) 또는 `not_supported`. (raw esxcli=SSH → **결정 D1**).
- 빈 `{}` vmhba entry 필터.

### P4 — Windows HBA enrich + IB 추가
- **파일**: `os-gather/tasks/windows/gather_storage.yml` (118-156 HBA), `gather_network.yml` (IB), `os-gather/site.yml`.
- FC: `Get-InitiatorPort -ConnectionType FibreChannel` 필터 + `MSFC_FCAdapterHBAAttributes`/`MSFC_FibrePortHBAAttributes` enrich (model/vendor/driver/firmware/speed, WWN hex-join). try/catch + Get-CimClass 존재 검사.
- IB: `Get-NetAdapter -IncludeHidden` PhysicalMediaType=InfiniBand / NdisPhysicalMedium=11 + `Get-PnpDevice VEN_15B3` fallback → `storage.infiniband[]`. node_guid=null (갭 문서화, 날조 금지).
- IB 미지원 시 `_sections_unsupported_fragment` 활용.

### P5 — Linux HBA/IB 보강 (선택 — **결정 D2**)
- **파일**: `os-gather/tasks/linux/gather_hba_ib.yml`.
- WWNN (`/sys/class/fc_host/host*/node_name`), firmware (`.../firmware_version`), vendor/driver (lspci `-d ::0c04` FC class 매칭), per-port IB GUID. canonical shape 정렬 (rate_gbps/source 추가). raw fallback 양 모드 유지.

### P6 — schema / baseline / 문서 / 테스트
- `field_dictionary.yml`: `storage.hbas[].{wwpn,wwnn,model,vendor,driver,firmware,link_status,link_speed_gbps,port_type,source}` + `storage.infiniband[].{adapter,port,node_guid,port_guid,link_status,rate,rate_gbps,vendor,firmware,source}` 서브필드 entry (Nice, Additive). Must/Nice/Skip 카운트 갱신.
- baseline: 영향 baseline (esxi 보강 / csus 현실화). 나머지(dell/hpe/lenovo/cisco/ubuntu/windows/rhel)는 lab 부재로 빈 유지 + 사이트 실측 시 채움 (NEXT_ACTIONS).
- `init_fragments` / `build_empty_data` / `build_failed_output` 3중 skeleton 동기화 (infiniband rate_gbps/source 등 신규 키).
- tests: `tests/unit/` HBA/IB 정규화 단위(FC PortProtocol 분류, IB LinkNetworkTechnology, WWN hex, None 가드), mock fixtures, baseline 회귀.
- 문서: `docs/16_os-esxi-mapping.md`, `docs/10_adapter-system.md`, `docs/13_redfish-live-validation.md`(CSUS Round), `docs/20_json-schema-fields.md`(rule 13 R7), `docs/19_decision-log.md`, `docs/ai/CURRENT_STATE.md`, catalogs (EXTERNAL_CONTRACTS/COMPATIBILITY-MATRIX/FIELD_USAGE_MATRIX/SCHEMA_FIELDS), `.claude/ai-context/vendors/`.
- ADR: `ADR-2026-05-29-hba-ib-csus.md` (field_dictionary 서브필드 추가 + CSUS per-partition normalize — rule 70 R8).

---

## 4. 리스크 + 회귀 전략

| 리스크 | 등급 | 대응 |
|---|---|---|
| 다중 채널 fragment + 전 baseline 회귀 동시 | HIGH | Phase 분리 + 각 Phase 후 `pytest tests/` + `ansible-playbook --syntax-check` + envelope shape 검증 (`envelope_change_check.py`) |
| CSUS lab 부재 — 실측 검증 불가 | HIGH | web evidence mock (rule 96 R1-A) + DRIFT-correctable + 사이트 캡처 NEXT_ACTIONS (rule 96 R1-C). mock 은 "검증됨" 주장 금지 (rule 25 R7-B) |
| HBA/IB 중복 분류 (NIC vs FC/IB 포트) | MED | PortProtocol/LinkNetworkTechnology 단일 기준 + WWPN/GUID dedup. network 노출 유지하되 storage.* canonical |
| Windows/ESXi 명령 부재 | LOW | Get-Command/Get-CimClass 존재 검사 + try/catch → graceful 빈 list (Linux best-effort 동일) |
| 3중 skeleton drift | MED | 신규 서브키 3파일 동시 갱신 + 회귀 |

회귀 게이트 (rule 24/40/92): Jenkins Stage 3(schema 정합) + Stage 4(baseline 회귀) 등가 로컬 — `output_schema_drift_check.py`, 영향 vendor baseline 전수, `verify_harness_consistency.py`, `verify_vendor_boundary.py`.

---

## 5. 결정 (사용자 확정 2026-05-29)

- **D1 = API-only** — ESXi 는 community.vmware 만, SSH 미사용. FC port_type/speed/wwnn 보강 + nmlx NIC IB best-effort 추론. esxcli-over-SSH 는 NEXT_ACTIONS.
- **D2 = 포함** — Linux 보강(P5) 진행: WWNN/firmware/vendor(lspci)/per-port GUID + canonical shape.
- **D3 = Additive, 버전 유지** — schema_version="1" 유지. 기존 v1 array 내부 서브필드만 Additive 추가. envelope shape 변경 0.

→ P1~P6 전부 진행.

---

## 6. NEXT_ACTIONS (lab 부재 후속 — rule 50 R2 step 10 / rule 96 R1-C)

- CSUS 3200 사이트 fixture 캡처 (`capture-site-fixture`) → 실 baseline 교체 (mock 대체).
- FC HBA / IB HCA 보유 사이트 (Dell/HPE/Lenovo/Cisco/ESXi/Windows) fixture 캡처 → 해당 baseline `storage.hbas`/`infiniband` 채움 (rule 13 R4).
- lab 도입 후 별도 round (`hba-ib-lab-validation`, `csus-3200-lab-validation`).
