# HPE — 벤더 OEM 메모

## 식별

- **Manufacturer**: "HPE", "Hewlett Packard Enterprise", "Hewlett-Packard"
- **Aliases**: HPE, HP, Hewlett Packard Enterprise, iLO
- **BMC 이름**: iLO5 / iLO6
- **vendor_aliases.yml** 내부 canonical 정규화: `hpe` (adapter/vault/OEM 라우팅 키 — 불변)
- **출력 envelope vendor 표시값** (2026-06-04 ADR): `hp`.
  HPE Compute Scale-up Servers 패밀리(**CSUS 3200 + Superdome Flex**, 둘 다 RMC 관리)는 → `hpCsus`.
  내부 canonical `hpe` 유지, `vendor_output_display`/`adapter_output_display` 로 출력만 매핑.

## Adapter 매핑

| Adapter | priority | 대상 |
|---|---|---|
| `adapters/redfish/hpe_ilo7.yml` | 120 | iLO7 (Gen12, 2026-05-01 신규) |
| `adapters/redfish/hpe_ilo6.yml` | 100 | iLO6 |
| `adapters/redfish/hpe_csus_3200.yml` | 96 | **Compute Scale-up Server 3200 (CSUS 3200) — 2026-05-11 신규, lab 부재** |
| `adapters/redfish/hpe_superdome_flex.yml` | 95 | Superdome Flex / Flex 280 (2026-05-06 신규, lab 부재) |
| `adapters/redfish/hpe_ilo5.yml` | 90 | iLO5 |
| `adapters/redfish/hpe_ilo4.yml` | 50 | iLO4 (Gen9 legacy) |
| `adapters/redfish/hpe_ilo.yml` | 10 | generic HPE fallback |

## Superdome / Compute Scale-up Server 시리즈 (cycle 2026-05-06 / 2026-05-11 추가)

### 모델 / BMC

| 모델 | 출시 | 아키텍처 | management | Redfish | adapter |
|---|---|---|---|---|---|
| **Compute Scale-up Server 3200 (CSUS 3200)** | **2023+** | **x86 (Intel Xeon SP, DDR5)** | **RMC + PDHC + RMP** | **YES (RMC host, 표준)** | **`hpe_csus_3200.yml` (96)** |
| Superdome Flex 280 | 2020+ | x86 (Intel Xeon SP) | RMC + iLO 5 (per node) | YES (RMC host, 표준) | `hpe_superdome_flex.yml` (95) |
| Superdome Flex | 2017+ | x86 (Intel Xeon SP) | eRMC/RMC + iLO 5 (per compute module) | YES (RMC host, 표준) | `hpe_superdome_flex.yml` (95) |
| Superdome 2 (legacy) | 2010~2017 | Itanium / IA-64 | OA (Onboard Administrator) | NO — `redfish_generic.yml` fallback | (N/A) |
| Superdome X (legacy) | 2014~ | x86 (Xeon E7) | iLO 4 + OA | 부분 — `hpe_ilo4.yml` (50) fallback | (legacy) |
| Integrity Superdome (legacy) | ~2010 | Itanium | OA only | NO — `redfish_generic.yml` (N/A) | (N/A) |

### CSUS 3200 특이사항 (lab 부재 — web sources 추정)

- HPE 공식 인용: *"built on the proven HPE Superdome Flex architecture"* (HPE psnow doc/a50009596enw)
- 4-socket × 1~4 chassis 모듈식 (최대 16-socket 단일 시스템)
- 128 GB DDR5 DIMM 기준 128 GB ~ 32 TB shared memory
- 관리 = RMC (primary) + PDHC (per-chassis) + RMP (redundancy). 표준 Redfish API + HPE OneView profile
- Oem.Hpe namespace 공유 (PartitionInfo / FlexNodeInfo / GlobalConfiguration — Superdome Flex 와 동일 가정, lab 실측 시 정정)
- vault profile `hpe` 재사용 — 사용자 명시 승인 시 향후 별도 분리 가능 (NEXT_ACTIONS 등재)
- model regex 확장: `(?i)Superdome|Flex|Compute Scale-up|CSUS` (collect_oem.yml / normalize_oem.yml)

### Redfish 차이 (vs 일반 ProLiant iLO 5)

| Endpoint | 일반 iLO 5 | Superdome Flex | 시그니처 |
|---|---|---|---|
| Systems collection | `/Systems/1` (단일) | `/Systems/Partition0`, `Partition1`, ... | **Multi-partition (nPAR)** — sdflexutils 실측 |
| Managers | `/Managers/1` (iLO) | `/Managers/<RMC_id>` + per-node iLO 5 | **Dual-manager** — RMC primary |
| Chassis | `/Chassis/1` | `/Chassis/<chassis_id>` | RMC aggregation (Base + Expansion 최대 8) |
| FirmwareInventory | 표준 | 표준 + complex/nPar firmware bundles | sdflex-ironic-driver wiki 명시 |
| OEM 키 | `Oem.Hpe` | `Oem.Hpe` | HPE 표준 namespace 재사용 |

### 한계 / 주의

- **Multi-partition (nPAR)**: cycle 2026-05-12 (ADR-2026-05-12) — **전 partition / 전 manager / 전 chassis 수집 정식 지원**. `data.multi_node` Additive 컨테이너로 노출 (기존 `data.system` 등 9 path 는 Partition0 representative 유지).
- **Dual-manager**: RMC = primary AccountService host. per-node iLO 5 는 보조. adapter `vendor_notes.manager_layout` 으로 `bmc.name` 분기 — `rmc_primary` (CSUS 3200) / `rmc_primary_ilo_secondary` (Superdome Flex).
- **Vendor 분류**: HPE sub-line — Manufacturer = "HPE". 별도 vendor 아님 (M-E1 결정 (a)).
- **vault**: `vault/redfish/hpe.yml` 재사용 (별도 vault 불필요).
- **OEM tasks**: `redfish-gather/tasks/vendors/hpe/` 재사용 (Oem.Hpe 동일 namespace).
- **lab**: 부재 — web sources 8건 (CSUS) + 14건 (Superdome Flex) (rule 96 R1-A). 사이트 실측 시 정정 가능.
- **활성화 위험**: HPE community 7200359 — 사이트 RMC Redfish 비활성화 / 라이선스 부재 사례. `diagnosis.details.rmc_activation_check` 메타로 진단 hint. `docs/22_rmc-activation-guide.md` 참조.

### cycle 2026-05-12 (ADR-2026-05-12) — RMC 멀티-노드 정식 지원

| 영역 | 변경 |
|---|---|
| `redfish-gather/library/redfish_gather.py` | `_resolve_all_member_uris` / `gather_systems_multi` / `gather_managers_multi` / `gather_chassis_multi` / `_classify_rmc_label` / `_classify_manager_role` / `_classify_chassis_kind` / `_collect_multi_node_topology` 신설 (Additive). `gather_bmc` 에 `manager_layout` 옵션 인자 |
| envelope | `data.multi_node` Additive 컨테이너 (enabled/layout/summary/partitions[]/managers[]/chassis[]). `diagnosis.details.multi_node_layout` + `rmc_activation_check` Additive |
| adapter | `vendor_notes.multi_node_support: true` (CSUS 3200 + Superdome Flex) |
| schema | `field_dictionary.yml` +9 nice entries (`multi_node.*` + `diagnosis.details.*_check`) |
| docs | `docs/20_json-schema-fields.md` 7-bis 절 + `docs/22_rmc-activation-guide.md` 신규 |
| fixtures | `tests/fixtures/redfish/hpe_csus_3200/` 7 파일 합성 (3-partition × 4-manager × 3-chassis) |
| tests | `tests/unit/test_{classify_rmc_label,resolve_all_members,hpe_csus_multi_node}.py` 29 PASS |

### NEXT_ACTIONS (lab 도입 후)

C1~C8: `docs/ai/NEXT_ACTIONS.md` 참조. 사이트 fixture 캡처 + baseline + lab cycle + vault 결정 + Product/Member ID/OEM schema/활성화 실측.

### 후속 작업 (lab 도입 시)

1. Multi-partition 전수 수집 (별도 cycle — Systems Members[0] 단일 진입 변경)
2. nPAR / `Oem.Hpe.Partition*` 키 식별 (lab 응답 캡처 후)
3. Manufacturer string / Product 시그니처 정정 (web sources 추정 vs 실측)

## OEM 특이사항

- **Smart Storage Administrator path**: HPE OEM `Oem.Hp.Links.SmartStorage`
- **Boot order**: OEM 별도 endpoint
- **Firmware inventory**: 표준 + OEM (Smart Components)
- **Superdome Flex**: complex/nPar firmware bundles (raw passthrough)

## Vault

- 위치: `vault/redfish/hpe.yml`
- 일반적 계정: `Administrator`
- 회전: `rotate-vault` skill

## 검증 이력

- Round 7-10: iLO5 펌웨어 2.x 검증 완료
- Round 11 (2026-04-28): iLO 6 v1.73 (10.50.11.231) Baseline 캡처
- cycle 2026-05-06 (M-E2): Superdome Flex / Flex 280 adapter 추가 (lab 부재, web sources 14건)
- cycle 2026-05-11 (hpe-csus-add): **HPE CSUS 3200 (Compute Scale-up Server 3200) adapter 추가 (lab 부재, web sources 7건)**
- Baseline: `tests/baseline_v1/hpe_ilo5_baseline.json`, `tests/baseline_v1/hpe_baseline.json`
- CSUS 3200 baseline: lab 도입 후 추가 예정 (NEXT_ACTIONS 등재)

## Reference

- `docs/13_redfish-live-validation.md`
- HPE iLO Redfish API guide (외부)
- `docs/ai/catalogs/EXTERNAL_CONTRACTS.md` (M-E1 entry — Superdome Flex 14 sources)
- ticket M-E1 (cycle 2026-05-06 — git history) (web 검색 결과)
- ticket M-E2 (cycle 2026-05-06 — git history) (adapter spec)
