# ADR-2026-05-29 — CSUS 3200 전 공통 섹션 수집 + HBA/InfiniBand 전 채널 통일

> 상태: Accepted (2026-05-29)
> 관련: ADR-2026-05-12 (CSUS RMC multi-node 정식 지원), rule 13 / 22 / 50 / 96
> cycle: hba-ib-csus (`docs/ai/tickets/2026-05-29-csus-hba-ib/`)

## 1. 컨텍스트 (Why)

사용자 명시 (2026-05-29):
- "csus 3200 장비도 지금 다른 장비들처럼 공통 json에 있는내용이 모두 담기게 해주세요. csus 장비는 lab 장비가없으니 인터넷에서 검색해서 봐야함. ... 지금 csus 3200 개더링에 대한 대대적인 개편이 필요합니다."
- "개더링 정보에 HBA 정보와 InfiniBand 정보도 개더링 할 수 있도록해주세요. (이건 모든 서버)"

실측 (10-agent recon + web research, 2026-05-29):
- **CSUS 3200 baseline 이 빈 skeleton** — storage/network/disks/hbas/ib + per-partition storage/network 전부 `[]`. cycle 2026-05-12 는 multi_node 토폴로지(partition/manager/chassis id) 만 채우고 per-partition 섹션 normalize 누락 + mock 미완성.
- **HBA/IB 분류가 dead-code** — `redfish_gather.py` 가 `Port.PortType` 로 FC/IB 판정하나 **DMTF PortType enum 에 FC/IB 값이 없음** (Port.v1_9_0.json 확인) → 실장비 영원히 미매치. ESXi 도 `'infiniband' in adapter_type` dead-code, Windows 는 FC 필터 없음 + IB hardcoded `[]`.
- HBA/IB schema (`storage.hbas[]`/`infiniband[]`, `network.adapters/ports/driver_map`) 는 **이미 v1 에 존재** (sections.yml + field_dictionary array-level entries).

## 2. 결정 (What) — 사용자 확정 D1/D2/D3

| # | 결정 | 값 |
|---|---|---|
| D1 | ESXi IB/FC 수집 깊이 | **API-only** (community.vmware, SSH 미사용). esxcli-over-SSH 는 NEXT_ACTIONS |
| D2 | Linux 보강 포함 | **포함** (WWNN/firmware/vendor/per-port GUID) |
| D3 | schema 처리 | **Additive, schema_version "1" 유지** (기존 v1 array 내부 서브필드만 추가) |

**FC/IB 분류 정본 (DMTF, EXTERNAL-CONTRACTS §1/§2)**:
- FC = `Port.PortProtocol ∈ {FC,FCP,FCoE}` 또는 `NetworkDeviceFunction.NetDevFuncType ∈ {FibreChannel,FibreChannelOverEthernet}`. WWPN/WWNN = NetworkDeviceFunction.FibreChannel.
- IB = `Port.LinkNetworkTechnology=='InfiniBand'` 또는 `NetworkDeviceFunction.NetworkDeviceTechnology=='InfiniBand'`. GUID = NetworkDeviceFunction.InfiniBand.
- `Port.PortType` enum 은 FC/IB 분류에 사용 금지 (값 부재).

**전 채널 통일 canonical shape** — `storage.hbas[]` {wwpn,wwnn,model,vendor,driver,firmware,link_status,link_speed_gbps,port_type,source}, `storage.infiniband[]` {adapter,port,node_guid,port_guid,link_status,rate,rate_gbps,vendor,firmware,source}. `source` ∈ {redfish,os,esxi} 로 출처 식별, `wwpn`/`node_guid` 로 cross-channel 상관.

**CSUS 개편** — 전 Partition 순회 + per-partition cpu/memory/storage/network **canonical 정규화** (Python `_normalize_{cpu,memory,storage,network}_raw`). realistic mock baseline 전면 작성 (FC HBA + RAID1 SATA boot + DDR5 + 3 partition).

## 3. 결과 (Impact)

**코드 (Additive only — envelope 13 필드 / 기존 path 변경 0)**:
- `redfish-gather/library/redfish_gather.py` — `gather_network_adapters_chassis` FC/IB 분류 재작성 + `_fetch_ndf_index`/`_classify_port_protocol`/`_make_fc_hba`/`_make_ib_port`/`_normalize_wwn` 신설. `gather_systems_multi` per-partition normalize (`_normalize_cpu/memory/storage/network_raw`).
- `esxi-gather/tasks/collect_network_extended.yml` — FC 2-signal 분류 + enrich + nmlx IB 추론.
- `os-gather/tasks/windows/gather_storage.yml` — Get-InitiatorPort FC 필터 + MSFC_* enrich + Get-NetAdapter IB.
- `os-gather/tasks/linux/gather_hba_ib.yml` — WWNN/driver/firmware + per-port GID/rate_gbps/vendor.

**schema / baseline (D3 Additive)**:
- `schema/field_dictionary.yml` 74 → **83 entries** (+9 Nice — `storage.hbas[].*` / `storage.infiniband[].*` 서브필드). schema_version "1" 유지.
- `schema/baseline_v1/hpe_csus_3200_baseline.json` 현실 mock 전면 작성 (전 섹션 + 3 canonical partition). regression registry 등록 (envelope 회귀 9 baseline).
- `schema/baseline_v1/esxi_baseline.json` hbas 5→2 (SATA AHCI / SAS RAID 제외 — FC 만, 동일 raw 재분류). 나머지 baseline 은 lab FC/IB 부재로 빈 유지.

**테스트**: `tests/unit/test_hpe_csus_multi_node.py` +7 (per-partition normalize), `tests/regression/test_hba_ib_canonical.py` 신규 (cross-channel canonical), 회귀 **pytest 699 PASS / 0 FAIL** (full suite).

**문서**: docs/20 §6.3.1 (HBA/IB), field_dictionary, EXTERNAL-CONTRACTS, 본 ADR, CURRENT_STATE, decision-log, NEXT_ACTIONS.

## 4. 대안 비교 (Considered)

| 대안 | 채택 | 사유 |
|---|---|---|
| ESXi esxcli-over-SSH fallback (D1-B) | ✗ | SSH 활성 = 운영·보안 결정 (rule 92 R1). API-only 로 충분 (FC 보강) + ESXi native IB 미노출은 SSH 로도 해결 안 됨. NEXT_ACTIONS 보류 |
| schema_version "2" bump (D3-B) | ✗ | 서브필드는 기존 v1 array 내부 — envelope shape 변경 0. 버전 bump 시 전 baseline + 호출자 분기 부담. Additive 로 충분 |
| per-partition normalize 를 Ansible(normalize_standard.yml) 매크로로 | ✗ | top-level normalize 안정 경로 destabilize 위험. lab 부재 code path 라 Python self-contained + unit test 가 더 안전 |
| CSUS 실 baseline (lab 검증) | ✗ (불가) | lab 부재 — web evidence mock + DRIFT-correctable + 사이트 캡처 NEXT_ACTIONS (rule 96 R1-A/R1-C). "검증됨" 주장 금지 (rule 25 R7-B) |
| IB 를 ESXi/Windows 에서 native 수집 | ✗ (불가) | ESXi 는 native IB host port 미노출 (SR-IOV/passthrough), Windows 는 node_guid 표준 API 부재. best-effort + OS Linux(ibstat/sysfs) 정본 |

## 5. lab 부재 후속 (rule 96 R1-C / 50 R2 step 10 → NEXT_ACTIONS)

- CSUS 3200 사이트 fixture 캡처 → 실 baseline 교체 (mock 대체).
- FC HBA / IB HCA 보유 사이트(Dell/HPE/Lenovo/Cisco/ESXi/Windows) fixture 캡처 → 해당 baseline `storage.hbas`/`infiniband` 채움.
- ESXi esxcli-over-SSH fallback 검토 (D1-B 재평가).
- lab 도입 후 별도 round (`hba-ib-lab-validation`, `csus-3200-lab-validation`).
