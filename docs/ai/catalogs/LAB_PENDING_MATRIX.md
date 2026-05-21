# LAB_PENDING_MATRIX — lab 도입 후 별도 cycle 권장 매트릭스

> **목적**: lab 부재 vendor / generation 의 후속 작업 추적. lab 도입 시 entrypoint 제공.
> **TTL**: 14 일 (rule 28 R1 #12 COMPATIBILITY-MATRIX 와 동일 TTL)
> **무효화 trigger**: vendor adapter 추가 / 펌웨어 업그레이드 / 사이트 fixture 캡처 완료
> **출처**: cycle 2026-05-07 all-vendor-coverage Phase 3 W5 + cycle 2026-05-11 hpe-csus-add + cycle 2026-05-12 hpe-csus-rmc-multi-node
> **상태 표기** (rule 23 R8 ASCII 태그):
> - `[DONE]` = lab 검증 완료
> - `[PARTIAL]` = 일부 검증
> - `[PENDING]` = lab 부재
> - `[SKIP]` = Redfish 미지원 또는 server-exporter 범위 외

---

## 7 단계 후속 cycle 진입 절차 (공통)

1. lab 도입 vendor / generation 결정 (사용자 협의)
2. `capture-site-fixture` skill 로 사이트 fixture 캡처
3. probe_redfish.py 또는 deep_probe_redfish.py 로 실장비 검증
4. baseline_v1/{vendor}_baseline.json 생성 (rule 13 R4)
5. tests/evidence/<날짜>-<vendor>-<generation>.md 작성
6. docs/13_redfish-live-validation.md Round 갱신
7. 본 매트릭스 [PENDING] → [DONE] 갱신

---

## Vendor × Generation × 4 Column 매트릭스

### Dell (iDRAC10 외 — 3 generation lab 미도입)

| generation | fixture | baseline | lab cycle | vault |
|---|---|---|---|---|
| iDRAC7 (legacy) | [PENDING] | [PENDING] | [PENDING] — "Dell iDRAC7 lab 검증" | [PENDING] |
| iDRAC8 | [PENDING] | [PENDING] | [PENDING] — "Dell iDRAC8 lab 검증" (PowerSubsystem fallback W1) | [PENDING] |
| iDRAC9 | [PENDING] | [PENDING] | [PENDING] — "Dell iDRAC9 lab 검증" (3 variants — 3.x / 5.x / 7.x) | [PENDING] |
| iDRAC10 (R770 포함) | [DONE] | [DONE] | [DONE] (사이트 검증 commit `0a485823`) | [DONE] (M-A5 primary infraops/Password123! + recovery root/calvin) |

### HPE (iLO7 외 — 4 generation lab 미도입 + Superdome + CSUS)

| generation | fixture | baseline | lab cycle | vault |
|---|---|---|---|---|
| iLO (legacy 1/2/3) | [SKIP] | [SKIP] | [SKIP] — IPMI fallback 별도 검토 | [SKIP] |
| iLO4 | [PENDING] | [PENDING] | [PENDING] — "HPE iLO4 lab 검증" (SimpleStorage W2 + Power W3) | [PENDING] |
| iLO5 | [PENDING] | [PENDING] | [PENDING] | [PENDING] |
| iLO6 | [PARTIAL] (Round 11 DL380 Gen11 + 사이트 Gen12) | [PENDING] | [PENDING] — PowerSubsystem dual + SmartStorage fallback | [PENDING] |
| iLO7 | [DONE] | [DONE] | [DONE] (commit `1387b505` 2-part firmware fix) | [DONE] (M-A5 primary infraops + recovery admin/admin) |
| Superdome Flex (Gen 1/2 + 280) | [PENDING] | [PENDING] | [PENDING] — "HPE Superdome Flex lab 검증" (RMC + Partition0 + iLO5 dual-manager) | [PENDING] |
| **CSUS 3200 (Compute Scale-up Server)** | **[PENDING]** | **[PENDING]** | **[PENDING] — "HPE CSUS 3200 lab 검증" (RMC + PDHC + Partition0 + nPAR + DDR5)** | **[PENDING] (hpe 재사용 / 사용자 명시 시 별도 hpe_csus.yml)** |

#### HPE CSUS 3200 / Superdome Flex RMC 상세 후속 (8 항목 — ADR-2026-05-12)

| # | 항목 | trigger | skill / 파일 |
|---|---|---|---|
| C1 | 사이트 fixture 캡처 (CSUS 3200 / Superdome Flex 각 1대) | RMC IP 확보 + Redfish 활성화 (`docs/22_rmc-activation-guide.md` 4 절) | `capture-site-fixture` — `tests/fixtures/redfish/hpe_csus_3200/` 17 파일 |
| C2 | baseline JSON 추가 (`hpe_csus_3200_baseline.json` + `hpe_superdome_flex_baseline.json`) | C1 완료 | `update-vendor-baseline` (rule 13 R4) |
| C3 | lab cycle `hpe-csus-rmc-lab-validation` round | C1 + C2 완료 | 신 round — mock fixture 정정 + adapter origin 갱신 |
| C4 | vault 분리 결정 (`vault/redfish/hpe_csus.yml`) | 사용자 명시 승인 + 사이트 자격증명 정책 | rule 50 R2 단계 4 |
| C5 | ServiceRoot.Product 실측 — 정확 model 문자열 | C1 | adapter `model_patterns` 정밀화 |
| C6 | Managers / Systems / Chassis Member 개수 + ID 패턴 실측 | C1 | mock fixture RMC / PDHC0~N / Bay1.iLO5 / Partition0~N 검증 |
| C7 | `Oem.Hpe.PartitionInfo` / `FlexNodeInfo` / `GlobalConfiguration` schema 실측 | C1 | `redfish-gather/tasks/vendors/hpe/normalize_oem.yml` `default({})` 정정 |
| C8 | RMC 활성화 / Subscription License / 펌웨어 요구 실측 | C1 + C4 | `docs/22_rmc-activation-guide.md` 4 절 정정 |

### Lenovo (XCC3 외 — 3 generation lab 미도입 + 2 SKIP)

| generation | fixture | baseline | lab cycle | vault |
|---|---|---|---|---|
| BMC (IBM 시기) | [SKIP] | [SKIP] | [SKIP] | [SKIP] |
| IMM (legacy) | [SKIP] | [SKIP] | [SKIP] | [SKIP] |
| IMM2 | [PENDING] | [PENDING] | [PENDING] (SimpleStorage W4 + Power W5) | [PENDING] |
| XCC | [PENDING] | [PENDING] | [PENDING] | [PENDING] |
| XCC2 | [PENDING] | [PENDING] | [PENDING] | [PENDING] |
| XCC3 | [DONE] | [DONE] | [DONE] (Accept-only header — cycle 2026-04-30 reverse regression) | [DONE] (M-A5 primary infraops + recovery USERID/PASSW0RD) |

### Cisco (UCS X-series 외 — 3 generation lab 미도입 + 1 SKIP)

| generation | fixture | baseline | lab cycle | vault |
|---|---|---|---|---|
| BMC (legacy) | [SKIP] | [SKIP] | [SKIP] | [SKIP] |
| CIMC C-series 1.x ~ 4.x | [PARTIAL] (M4 lab 10.100.15.2) | [PARTIAL] | [PENDING] (M5~M8 web sources only) | [PENDING] |
| UCS S-series | [PENDING] | [PENDING] | [PENDING] (M-H4 model_patterns 추가 — Storage 강화) | [PENDING] |
| UCS B-series | [SKIP] (UCS Manager 매개) | [SKIP] | [PENDING] — "Cisco UCS Manager 통합 cycle" | [SKIP] |
| UCS X-series (standalone CIMC) | [DONE] | [DONE] | [DONE] (commit `0a485823`) | [DONE] (M-A5 primary infraops + recovery admin/password) |
| UCS X-series (Intersight IMM) | [SKIP] (server-exporter 범위 외) | [SKIP] | [PENDING] — "Intersight 통합 cycle" | [SKIP] |
| Cisco OEM tasks (vendor task) | [NEW] M-J1 신설 | (placeholder — 표준 strategy) | [PENDING] — UCS X-series 사이트 회귀 후 `standard+oem` 검토 | — |

### Supermicro (사이트 BMC 0대 — cycle 2026-05-07 Q2)

| generation | fixture | baseline | lab cycle | vault |
|---|---|---|---|---|
| BMC (legacy) | [PENDING] | [PENDING] | [PENDING] — "Supermicro lab 도입 cycle" | [PENDING] |
| X9 | [PENDING] | [PENDING] | [PENDING] | [PENDING] |
| X10 | [PENDING] (M-B1 신설) | [PENDING] | [PENDING] | [PENDING] |
| X11 + H11 | [PENDING] | [PENDING] | [PENDING] | [PENDING] |
| X12 + H12 (Whitley/Tatlow + AST2600) | [PENDING] | [PENDING] | [PENDING] | [PENDING] |
| X13 + H13 + B13 (Eagle + Sapphire Rapids + Genoa) | [PENDING] | [PENDING] | [PENDING] | [PENDING] |
| X14 + H14 (Granite Rapids + Turin + Redfish 1.21.0) | [PENDING] | [PENDING] | [PENDING] | [PENDING] |
| ARS (ARM) | [PENDING] | [PENDING] | [PENDING] | [PENDING] |

> **참고**: Supermicro X11~X14 firmware_patterns 추가 (Phase 2) 는 사이트 BMC 1대 이상 확보 시 진입. web sources 가설 부정확 위험으로 보류 (DRIFT-015 open).

### Huawei iBMC (lab 부재 — cycle 2026-05-01 사용자 명시)

| generation | fixture | baseline | lab cycle | vault |
|---|---|---|---|---|
| iBMC 1.x (2014-2016) | [PENDING] (Redfish 약함) | [PENDING] | [PENDING] | [PENDING] |
| iBMC 2.x (2016-2019) | [PENDING] | [PENDING] | [PENDING] | [PENDING] |
| iBMC 3.x (2019-2021) | [PENDING] | [PENDING] | [PENDING] | [PENDING] |
| iBMC 4.x (2021-2023) | [PENDING] | [PENDING] | [PENDING] | [PENDING] |
| iBMC 5.x (2023+) | [PENDING] | [PENDING] | [PENDING] | [PENDING] |
| Atlas AI 서버 | [PENDING] | [PENDING] | [PENDING] | [PENDING] |

### Inspur ISBMC (lab 부재)

| generation | fixture | baseline | lab cycle | vault |
|---|---|---|---|---|
| ISBMC (NF/TS) | [PENDING] | [PENDING] | [PENDING] (Oem.Inspur vs Oem.Inspur_System fallback) | [PENDING] (M-A2 primary infraops + recovery admin/admin) |

### Fujitsu iRMC (lab 부재)

| generation | fixture | baseline | lab cycle | vault |
|---|---|---|---|---|
| iRMC S2 | [SKIP] (Redfish 미지원 가능성) | [SKIP] | [SKIP] | [SKIP] |
| iRMC S4 | [PENDING] | [PENDING] | [PENDING] | [PENDING] (M-A3 primary infraops + recovery admin/admin) |
| iRMC S5 (PRIMERGY M5) | [PENDING] | [PENDING] | [PENDING] | [PENDING] |
| iRMC S6 (PRIMERGY M6/M7 + PRIMEQUEST) | [PENDING] | [PENDING] | [PENDING] | [PENDING] |

### Quanta QCT (lab 부재)

| generation | fixture | baseline | lab cycle | vault |
|---|---|---|---|---|
| QCT BMC (S/D/T/J series) | [PENDING] | [PENDING] | [PENDING] — OpenBMC bmcweb + Oem.Quanta_Computer_Inc vs Oem.QCT fallback | [PENDING] (M-A4 primary infraops + recovery admin/admin) |

---

## 우선순위 (사용자 명시 Q3 — 2026-05-07)

- lab 도입 timeline 장기 미정
- 사이트 BMC 도입 가능 vendor 우선 (사용자 협의 후 결정)
- Supermicro / Huawei / Inspur / Fujitsu / Quanta — 사이트 도입 미정 (코드 path 만 깔림)

---

## 관련

- rule: `50-vendor-adapter-policy` R2 단계 10, `96-external-contract-integrity` R1-A / R1-B / R1-C, `13-output-schema-fields` R4
- skill: `capture-site-fixture`, `update-vendor-baseline`, `add-new-vendor`, `add-vendor-no-lab`
- catalog: `COMPATIBILITY-MATRIX.md`, `VENDOR_ADAPTERS.md`, `EXTERNAL_CONTRACTS.md`
- 정본: `docs/13_redfish-live-validation.md`, `docs/14_add-new-gather.md`, `docs/22_rmc-activation-guide.md`
- ADR: `ADR-2026-05-12-csus-rmc-multi-node.md`
