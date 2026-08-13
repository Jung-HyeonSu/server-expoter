# COMPATIBILITY-MATRIX — 9 vendor × N generation × 10 sections

> rule 28 R1 #12 측정 대상 (TTL 14일). cycle 2026-05-07-all-vendor-coverage Phase 3 M-L3 갱신.
>
> 정본 위치 이동: git history (cycle 2026-05-07 진입 baseline) (cycle 진입 baseline, 보존) → `docs/ai/catalogs/COMPATIBILITY-MATRIX.md` (cycle 종료 결과, 본 파일).

---

## 사이트 검증 4 vendor × 1 generation (Round PASS — cycle 2026-05-06 commit `0a485823`)

> **2026-08-13 정정.** 이 표의 generation 열은 **adapter 오선택 결과를 장비 사실로
> 적어 둔 것**이었다. adapter 선택이 무인증 probe 직후라 model/firmware 가 비었고,
> 빈 fact 는 실격이 아니라 중립이라 priority 최상위가 뽑혔다. 인증 후 재선택을
> 넣고 실측하니 세대가 전부 달랐다.
> 근거: `tests/evidence/2026-08-13-adapter-oem-esxi9-live.md`

| vendor | generation (실측) | 사이트 BMC | adapter file | vault | baseline |
|---|---|---|---|---|---|
| Dell | **iDRAC9** (FW 7.10.70.00) | 5대 | `adapters/redfish/dell_idrac9.yml` (priority=100) | `vault/<loc>/redfish/dell.yml` (encrypted) | `schema/baseline_v1/dell_baseline.json` |
| HPE | **iLO6** (v1.73, DL380 Gen11) | 1대 | `adapters/redfish/hpe_ilo6.yml` (priority=100) | `vault/<loc>/redfish/hpe.yml` (encrypted) | `schema/baseline_v1/hpe_baseline.json` |
| Lenovo | **XCC** (AFBT58B 5.70, SR650 V2) | 1대 | `adapters/redfish/lenovo_xcc.yml` (priority=100) | `vault/<loc>/redfish/lenovo.yml` (encrypted) | `schema/baseline_v1/lenovo_baseline.json` |
| Cisco | **CIMC** (4.1, TA-UNODE-G1) | 1대 | `adapters/redfish/cisco_cimc.yml` (priority=100) | `vault/<loc>/redfish/cisco.yml` (encrypted) | `schema/baseline_v1/cisco_baseline.json` |

OEM tasks 열은 지웠다. vendor OEM task 층은 2026-08-13 에 제거됐다 — 9 vendor 18개
파일이 전부 모듈 출력에 없는 경로를 읽어 기여가 0이었다
(`docs/ai/decisions/ADR-2026-08-13-vendor-oem-task-removal.md`). 지금 OEM 은 라이브러리
`_extract_oem_*` 가 `data.system.oem` / `data.bmc.oem` 으로 내보낸다.

주목할 점 — **baseline 은 처음부터 맞는 값을 갖고 있었다.** `dell_baseline.json` 은
`redfish_dell_idrac9`, `cisco_baseline.json` 은 `redfish_cisco_cimc` 다. 어긋난 것은
라이브 캡처(`schema/output_examples/`)와 이 표였다.

→ **Out of scope (rule 92 R2)**: 위 4 vendor × 1 generation 코드 path **변경 금지** (envelope shape 영향 0).

---

## 9 vendor × N generation 매트릭스 (cycle 2026-05-07 종료 시점)

| vendor | generation | adapter (priority) | vault | OEM tasks | mock fixture | 사이트 검증 |
|---|---|---|---|---|---|---|
| **Dell** | iDRAC (legacy 7) | `dell_idrac.yml` (10) | dell.yml | tasks/vendors/dell/ | M-H1 mock | × |
| Dell | iDRAC8 | `dell_idrac8.yml` (50) | dell.yml | tasks/vendors/dell/ | M-H1 mock | × |
| Dell | iDRAC9 (3.x/5.x/7.x) | `dell_idrac9.yml` (100) | dell.yml | tasks/vendors/dell/ | 일부 + M-H1 mock | × |
| Dell | **iDRAC10** | `dell_idrac10.yml` (**120**) | dell.yml | tasks/vendors/dell/ | 일부 | **[PASS]** |
| **HPE** | iLO (legacy 1/2/3) | `hpe_ilo.yml` (10) | hpe.yml | tasks/vendors/hpe/ | (graceful) | × |
| HPE | iLO4 | `hpe_ilo4.yml` (50) | hpe.yml | tasks/vendors/hpe/ | M-H2 mock | × |
| HPE | iLO5 | `hpe_ilo5.yml` (90) | hpe.yml | tasks/vendors/hpe/ | 일부 + M-H2 mock | × |
| HPE | iLO6 | `hpe_ilo6.yml` (100) | hpe.yml | tasks/vendors/hpe/ | 일부 + Round 11 + 사이트 Gen12 | partial |
| HPE | **iLO7** | `hpe_ilo7.yml` (**120**) | hpe.yml | tasks/vendors/hpe/ | 일부 | **[PASS]** |
| HPE | Superdome Flex (Gen 1/2 + 280) | `hpe_superdome_flex.yml` (95) | hpe.yml | tasks/vendors/hpe/ (M-G1 분기 보강) | M-G2 mock + cycle 2026-05-12 multi-partition 보강 권장 | × (lab 부재) — **multi_node_support: true** (cycle 2026-05-12 ADR-2026-05-12) |
| HPE | **Compute Scale-up Server 3200 (CSUS)** | `hpe_csus_3200.yml` (96) | hpe.yml | tasks/vendors/hpe/ (model regex Superdome\|Flex\|Compute Scale-up\|CSUS) | cycle 2026-05-12 mock fixture 합성 (3-partition × 4-manager × 3-chassis) | × (lab 부재) — **multi_node_support: true / manager_layout: rmc_primary** (cycle 2026-05-12) |
| **Lenovo** | BMC (IBM legacy) | `lenovo_bmc.yml` (10) | lenovo.yml | tasks/vendors/lenovo/ | (graceful) | × |
| Lenovo | IMM (legacy) | (lenovo_bmc fallback) | lenovo.yml | tasks/vendors/lenovo/ | (graceful) | × |
| Lenovo | IMM2 | `lenovo_imm2.yml` (50) | lenovo.yml | tasks/vendors/lenovo/ | M-H3 mock | × |
| Lenovo | XCC + XCC2 | `lenovo_xcc.yml` (100, firmware_patterns) | lenovo.yml | tasks/vendors/lenovo/ | 일부 + M-H3 mock | × |
| Lenovo | **XCC3** | `lenovo_xcc3.yml` (**120**) | lenovo.yml | tasks/vendors/lenovo/ | 일부 (Accept-only header 정책) | **[PASS]** |
| **Cisco** | BMC (legacy) | `cisco_bmc.yml` (10) | cisco.yml | **tasks/vendors/cisco/ (M-J1)** | (graceful) | × |
| Cisco | CIMC C-series 1.x ~ 4.x + S-series + B-series | `cisco_cimc.yml` (100, firmware_patterns + model_patterns) | cisco.yml | tasks/vendors/cisco/ | M-H4 mock (4 variants) | M4 lab tested 10.100.15.2 |
| Cisco | **UCS X-series (standalone CIMC)** | `cisco_ucs_xseries.yml` (**110**) | cisco.yml | tasks/vendors/cisco/ | 일부 | **[PASS]** |
| Cisco | UCS X-series (Intersight IMM) | (server-exporter 범위 외) | — | — | — | (별도 cycle) |
| **Supermicro** | BMC (legacy) | `supermicro_bmc.yml` (10) | supermicro.yml | tasks/vendors/supermicro/ | (graceful) | × |
| Supermicro | X9 | `supermicro_x9.yml` (50) | supermicro.yml | tasks/vendors/supermicro/ | M-B2 mock | × |
| Supermicro | **X10 (신설)** | `supermicro_x10.yml` (**75 — M-B1**) | supermicro.yml | tasks/vendors/supermicro/ | M-B4 mock | × |
| Supermicro | X11 + H11 (AMD, AST2500) | `supermicro_x11.yml` (100, M-B3 model_patterns 확장) | supermicro.yml | tasks/vendors/supermicro/ | M-B2 mock | × |
| Supermicro | X12 + H12 (AST2600) | `supermicro_x12.yml` (90) | supermicro.yml | tasks/vendors/supermicro/ | M-B2 mock | × |
| Supermicro | X13 + H13 + B13 | `supermicro_x13.yml` (100) | supermicro.yml | tasks/vendors/supermicro/ | M-B2 mock | × |
| Supermicro | X14 + H14 (Redfish 1.21.0) | `supermicro_x14.yml` (110) | supermicro.yml | tasks/vendors/supermicro/ | M-B2 mock | × |
| Supermicro | **ARS (ARM, 신설)** | `supermicro_ars.yml` (**80 — M-B3**) | supermicro.yml | tasks/vendors/supermicro/ | M-B4 mock | × |
| **Huawei** | iBMC 1.x ~ 5.x + Atlas | `huawei_ibmc.yml` (80, firmware_patterns + model_patterns) | **huawei.yml (M-A1 신설)** | **tasks/vendors/huawei/ (M-C2 신설)** | M-C3 mock (3 generation) | × (lab 부재 cycle 2026-05-01) |
| **Inspur** | ISBMC (NF/TS) | `inspur_isbmc.yml` (80) | **inspur.yml (M-A2 신설)** | **tasks/vendors/inspur/ (M-D1 신설)** | M-D2 mock | × (lab 부재 cycle 2026-05-01) |
| **Fujitsu** | iRMC S2/S4/S5/S6 + PRIMEQUEST | `fujitsu_irmc.yml` (80, firmware_patterns + model_patterns) | **fujitsu.yml (M-A3 신설)** | **tasks/vendors/fujitsu/ (M-E2 신설)** | M-E3 mock | × (lab 부재 cycle 2026-05-01) |
| **Quanta** | QCT BMC (OpenBMC, S/D/T/J) | `quanta_qct_bmc.yml` (80) | **quanta.yml (M-A4 신설)** | **tasks/vendors/quanta/ (M-F1 신설)** | M-F2 mock | × (lab 부재 cycle 2026-05-01) |

---

## sections × vendor 변형 매트릭스 (10 sections)

본 cycle M-I 영역 작업 — vendor / generation 별 응답 형식 변형 + fallback.

### sections 목록 (10)

| section | 표준 path (DMTF Redfish) | 변형 영역 |
|---|---|---|
| system | `/redfish/v1/Systems/{id}` | 표준 가까움 (M-I5) |
| hardware | `/redfish/v1/Chassis/{id}` | 표준 가까움 (M-I5) |
| bmc | `/redfish/v1/Managers/{id}` | vendor OEM namespace 노출 (M-I3) |
| cpu | `/redfish/v1/Systems/{id}/Processors/{id}` | 표준 가까움 (M-I5) |
| memory | `/redfish/v1/Systems/{id}/Memory/{id}` | 표준 가까움 (M-I5) |
| storage | `/redfish/v1/Systems/{id}/Storage/{id}/Volumes` + `/Drives` | **PLDM RDE / SmartStorage / OEM** 분기 큼 (M-I1) |
| network | `/redfish/v1/Systems/{id}/EthernetInterfaces` 또는 `/Chassis/{id}/NetworkAdapters` | NIC OEM driver / SR-IOV / OCP (M-I4) |
| firmware | `/redfish/v1/UpdateService/FirmwareInventory` | vendor OEM namespace 노출 (M-I3) |
| users | `/redfish/v1/AccountService/Accounts` | 표준 가까움 (M-I5) |
| power | `/redfish/v1/Chassis/{id}/Power` 또는 `/PowerSubsystem` | **Power deprecated → PowerSubsystem 마이그레이션** (M-I2) |

### Storage 변형 매트릭스 (M-I1)

| strategy | 적용 vendor / generation |
|---|---|
| pldm_rde_only | Dell iDRAC10, iDRAC9 6.x+ |
| pldm_rde_with_standard_fallback | Dell iDRAC9 5.x |
| smart_storage_only | HPE iLO4 |
| smart_storage_with_standard_dual | HPE iLO5 |
| standard_with_smart_storage_fallback | HPE iLO6 |
| standard | HPE iLO7, Lenovo XCC/XCC2/XCC3, Cisco UCS X-series, Supermicro X11+, Huawei iBMC 2.x+, Inspur, Fujitsu iRMC S4+, Quanta |
| simple_storage_only | Dell iDRAC7, Lenovo IMM2, Cisco CIMC 1.x-2.x, Supermicro X9-X10, Huawei iBMC 1.x |
| (graceful fail — Redfish 미지원) | HPE iLO legacy, Fujitsu iRMC S2, Cisco BMC legacy |

### Power 변형 매트릭스 (M-I2)

| strategy | 적용 vendor / generation |
|---|---|
| subsystem_only | Dell iDRAC10, HPE iLO7, Cisco UCS X-series |
| subsystem_with_legacy_dual | Dell iDRAC9 5.x+, HPE iLO5/6, Lenovo XCC3, Supermicro X12-X14 |
| subsystem_with_legacy_fallback | Cisco CIMC 4.x, Huawei iBMC 3.x+, Fujitsu iRMC S6+ |
| legacy_only | 그 외 모든 generation |

### bmc / firmware OEM namespace (M-I3 / M-J1 — 9 vendor 통합)

| vendor | namespace 우선 | namespace fallback |
|---|---|---|
| Dell | `Oem.Dell` | (없음) |
| HPE | `Oem.Hpe` | `Oem.Hp` (iLO4 legacy) |
| Lenovo | `Oem.Lenovo` | (없음) |
| Cisco | `Oem.Cisco` | `Oem.Cisco_RackUnit` |
| Supermicro | `Oem.Supermicro` | (없음) |
| Huawei | `Oem.Huawei` | (없음) |
| Inspur | `Oem.Inspur` | `Oem.Inspur_System` |
| Fujitsu | `Oem.ts_fujitsu` | `Oem.Fujitsu` |
| Quanta | `Oem.Quanta_Computer_Inc` | `Oem.QCT` |

정본 위치: `redfish-gather/library/redfish_gather.py` `_OEM_NAMESPACE_FALLBACK_CHAIN` + `_extract_oem_unified(data, expected_vendor)`.

### Network 변형 매트릭스 (M-I4)

| 영역 | 적용 |
|---|---|
| OCP slot 식별 | Phase 2 helper `_detect_nic_ocp_slot` (Supermicro / Quanta / Fujitsu OCP NIC) |
| SR-IOV capable | Phase 2 helper `_detect_nic_sriov_capable` |
| OEM driver namespace | adapter 별 `Oem.<vendor>.NIC*` (Dell / HPE / Lenovo 위주) |

---

## cycle 산출 차이 (2026-05-07 진입 → 종료)

| 항목 | 진입 | 종료 | 증감 |
|---|---|---|---|
| adapter (Redfish) | 28 | **30** (+supermicro_x10 / +supermicro_ars) | +2 |
| vault encrypted (Redfish) | 5 | 9 (+huawei/inspur/fujitsu/quanta) | +4 |
| vendor OEM tasks | 4 | **9** (+cisco/huawei/inspur/fujitsu/quanta) | +5 |
| mock fixture (vendor 별) | 4 (사이트 검증) | 22+ generation | +18 |
| baseline_v1 (Redfish) | 4 (사이트 검증) | 4 | 0 (lab 부재 vendor SKIP — rule 13 R4) |
| EXTERNAL_CONTRACTS row | 일부 | 30+ row (9 vendor × N gen) | 대폭 |
| OEM namespace 매트릭스 | 5 vendor | 9 vendor (M-I3 + M-J1) | +4 |
| origin 주석 일관성 (M-K1) | 일부 | **30/30 PASS** | — |
| catalog 갱신 | — | 4종 (NEXT_ACTIONS / VENDOR_ADAPTERS / COMPATIBILITY-MATRIX / EXTERNAL_CONTRACTS) + `docs/reference/live-validation.md` | — |
| pytest | 484 | 497 (Phase 2 후) | +13 |
| ticket | 0 → 38 | 38/38 DONE | — |
| schema/sections.yml + field_dictionary.yml | (불변) | (변경 0) | 0 (Q7 정책) |

---

## Phase 2 helpers (cycle 2026-05-07 정착)

cycle 2026-05-07 Phase 2 신설 helper 7종 (`redfish_gather.py` +338 lines, stdlib only — rule 10 R2):

| helper | 영역 | rule |
|---|---|---|
| `_gather_smart_storage` | HPE iLO4 SmartStorage legacy fallback | rule 92 R2 Additive |
| `_merge_power_dual` | Power + PowerSubsystem dual (subsystem_with_legacy_dual strategy) | rule 92 R2 Additive |
| `_extract_oem_unified` | 9 vendor OEM namespace 통합 추출 (M-I3) | rule 12 R1 Allowed |
| `_detect_nic_ocp_slot` | NIC OCP slot 식별 (M-I4) | rule 12 R1 Allowed |
| `_detect_nic_sriov_capable` | NIC SR-IOV capable 검출 (M-I4) | rule 12 R1 Allowed |
| `_normalize_role_id` | AccountService role 정규화 | rule 12 R1 Allowed |
| `_normalize_dimm_label` | DIMM label 정규화 | rule 92 R2 Additive |

---

## 다음 측정 시점 (rule 28 R1 #12 TTL 14일)

- 다음 측정: 2026-05-25 또는 trigger (adapter capabilities 변경 / 새 vendor / 펌웨어 업그레이드) 발생 시
- 측정 명령:
  ```bash
  ls adapters/redfish/*.yml | wc -l
  ls adapters/esxi/*.yml | wc -l
  python adapter origin 검사(제거됨) --all --redfish-only
  ```

---

## 관련

- ticket: git history (cycle 2026-05-07 진입 baseline) (cycle 진입 baseline 보존)
- rule 13 R4 (baseline 실측 기반)
- rule 28 R1 #12 (COMPATIBILITY-MATRIX 측정 대상)
- rule 50 R2 (vendor 추가 9단계 + 단계 10 lab 부재)
- rule 96 R1+R1-A+R1-C (외부 계약 origin / web sources / NEXT_ACTIONS 등재)
- INDEX.md / DEPENDENCIES.md / fixes/INDEX.md
- `docs/ai/catalogs/VENDOR_ADAPTERS.md` (30 adapter 매트릭스 — M-L2)
- `docs/ai/catalogs/EXTERNAL_CONTRACTS.md` (9 vendor × N gen × source URL — M-K2)
- `docs/ai/NEXT_ACTIONS.md` (lab 도입 후 별도 cycle 매트릭스 — M-L1)
