# ADR-2026-06-04 — HP CSUS 3200 사이트 사고: vendor=hp 오선택 + hardware null fix (A1/B1/B2)

- 상태: Accepted
- 일시: 2026-06-04
- 결정 주체: 사용자(hshwang1994) 명시 승인(B2 priority 변경) + AI(Claude) 진단·구현
- 관련 rule: 12 R1/R2, 50 R3, 92 R2, 96 R1-A/R1-B/R1-C, 25 R7-A-1
- 관련 ADR: `ADR-2026-06-04-vendor-output-display.md` (hpCsus 출력 표시 — 본 ADR 이 그 선택을 *실제로 작동*하게 함)

## 1. 컨텍스트 (Why)

사용자 사이트의 **실 HPE Compute Scale-up Server 3200 (CSUS 3200)** 수집 결과(실측):
- envelope 최상위 `vendor = "hp"` (→ **`hpCsus` 여야 함**)
- `data.hardware.vendor = null`, `data.hardware.model = null`
- `diagnosis.details.product = "Compute Scale-up Server 3200"` (정상 — ServiceRoot.Product 무인증 read 됨)
- 그 외 일부 섹션 null/0/empty

lab 부재(baseline 은 MOCK) → 사용자 실측이 spec/mock 보다 우선(rule 25 R7-A-1). 8-agent 워크플로(web 3 + code 2 + synth + adversarial verify)로 진단.

## 2. 근본 원인 (코드 + 실 adapter 시뮬레이션으로 확정)

**vendor=hp (오선택)** — 2 단 결함:
- **B1 결함**: 무인증 probe 벤더 감지(`_detect_vendor_from_service_root`)에 "Compute Scale-up Server 3200" 시그니처 부재. `_BMC_PRODUCT_HINTS` 는 `ilo`/`proliant`/`superdome` 만 인식.
- **B2 결함 (핵심)**: `hpe_ilo6` adapter 는 `model_patterns` 가 **없어** firmware-only catch-all 로 동작 → 모델 불일치로 절대 실격되지 않음. 점수 공식 `priority×1000 + specificity×10 + match`에서 priority 가 지배적이라, 구 CSUS(96)/Superdome(95) 가 모델을 정확히 매치해도(+25) iLO6(100)에 패배.
  - 실 adapter 시뮬레이션(`tests/unit/test_csus_adapter_priority.py`):
    - model=CSUS, firmware="" → 구: winner=`hpe_ilo6`(100320) → `hp`. (CSUS=96545 패배)
    - model=CSUS, firmware="3.x" → CSUS 승 (iLO6 가 firmware 불일치로 실격) → `hpCsus`. ← firmware 가 facts 에 들어올 때만.
  - **LOAD-BEARING 미지수**: 실 RMC 무인증 ServiceRoot 가 facts.firmware 를 채우는지 여부. 채우면 B1 만으로도 해결, 안 채우면 B2 필요. raw JSON 부재 → 불확정.

**hardware.vendor/model = null (A1)**: `gather_system` 이 `System.Manufacturer/Model` 을 폴백 없이 사용. CSUS Partition0 는 이 값이 비고 Chassis 에만 존재(DMTF ComputerSystem Manufacturer/Model optional+nullable). `gather_system` 은 `service_root`/`product` 미수신이라 ServiceRoot.Product 폴백 불가 — 단 `chassis_data` 는 이미 fetch 중이라 Chassis 폴백 가능.

## 3. 결정 (What) — 3 패치, 모두 Additive only (rule 92 R2)

- **A1** (`redfish_gather.py` `gather_system`): `result['manufacturer']`/`['model']` 이 `None` 일 때만 `chassis_data.Manufacturer/Model` 로 보충. `_strip_or_none` 정규화(빈문자열→None 불변식 유지). 정상 13 vendor 는 System 값 보유 → 미발동.
- **B1** (`redfish_gather.py` `_BMC_PRODUCT_HINTS`): **복합 키만** 추가 — `'compute scale-up server': 'hpe'`, `'csus 3200': 'hpe'`. (단독 `'csus'`/`'compute'` 는 `if hint in p` plain-substring 충돌 위험이라 제외 — adversarial 검증 권고.) probe 벤더 감지 강건성 향상.
- **B2** (adapter priority — **사용자 승인 필요, 승인됨 2026-06-04**): `hpe_csus_3200` 96→**102**, `hpe_superdome_flex` 95→**101**. 신 순서: iLO7(120) > CSUS(102) > Superdome(101) > iLO6(100) > iLO5(90). scale-up 2 종을 iLO6 catch-all 위로 올려 **모델 매치가 우선권**을 갖게 함. firmware 무관하게 `hpCsus` 보장.

## 4. 결과 (Impact)

| 영역 | 변경 |
|---|---|
| `redfish-gather/library/redfish_gather.py` | A1 Chassis 폴백 + B1 `_BMC_PRODUCT_HINTS` 2 복합 키 |
| `adapters/redfish/hpe_csus_3200.yml` | priority 96→102 + 차등 주석 갱신 |
| `adapters/redfish/hpe_superdome_flex.yml` | priority 95→101 + 차등 주석 갱신 |
| `.claude/policy/vendor-boundary-map.yaml` | superdome priority 95→101 + **csus_3200 sub_line 신설**(누락 보강) |
| `tests/unit/test_hpe_superdome_flex_m_e2.py` | priority assertion 95→101 (구 설계 인코딩 갱신) |
| `tests/unit/test_csus_adapter_priority.py` | **신규** 13 회귀 (A1/B1/B2 lock-in) |
| `tests/fixtures/redfish/hpe_superdome_flex/README.md` | 문서 priority 95→101 stale 정정 |

**무회귀 검증(실 코드/시뮬레이션)**: 정상 ProLiant Gen11→iLO6/`hp`, Gen12→iLO7/`hp`, empty facts→iLO7(불변), Dell→idrac9/`dell`. envelope 13 필드 shape 불변.

## 5. 검증 ([OK] 확인한 층 / [NG] 못 한 층 — 정직 보고)

- [OK] pytest **762 pass**(e2e_browser 2 제외 — 내부망 Jenkins 환경 제약) / vendor-boundary PASS / harness-consistency PASS / py_compile PASS.
- [OK] 실 adapter_common + 실 adapter YAML 시뮬레이션: model=CSUS/fw="" → `hpCsus`(post-B2), 무회귀 대조군 통과.
- [OK] 실 `gather_system`(monkeypatch _get): System null → Chassis 폴백으로 hardware.vendor/model 채움.
- [NG] **실 CSUS 장비 end-to-end**: 장비/raw JSON 부재 → 이 환경에서 확인 불가. 사용자 사이트 재실행으로 확인 필요.

## 6. 미해결 (NEXT_ACTIONS 등재 — rule 96 R1-C)

- **Bug C (각종 null/0/empty counts)**: 실 장비 구조 의존 → 추측 수정 금지(다른 vendor 회귀 위험). raw Redfish JSON(ServiceRoot + Systems/Partition0 + Chassis + Managers/RMC) 확보 후 정밀 수정 + sanitize 회귀 fixture.
- **LOAD-BEARING 확인**: 실 RMC 가 facts.firmware 를 채우는지 → B1 단독 충분 여부 확정.
- **실 baseline 교체**: 현 MOCK baseline → 사이트 fixture 캡처(capture-site-fixture) 후 실측 baseline.

## 7. 대안 비교 (Considered)

| 대안 | 결과 |
|---|---|
| **B2 priority 상향 (채택)** | scale-up 2 종을 iLO6 위로. firmware 무관 `hpCsus`. 무회귀 검증. rule 12 R2 승인. |
| B1 단독 | firmware 가 facts 에 들어와야만 작동(불확정). 단독 불충분 — 시뮬레이션 S2='hp'. (안전 hardening 으로는 유지) |
| iLO6 에 model_patterns 추가 | iLO6 가 모델 known-mismatch 시 실격 → 모델 미열거 Gen11 회귀 위험. 거절. |
| A1 에 ServiceRoot.Product 폴백 | gather_system 이 product 미수신 + Dell/Lenovo 는 Product=BMC명 → 회귀 위험. Chassis 폴백만 채택, product 폴백은 DEFERRED. |

## 8. Amendment 2026-06-04 — web 캡처 JSON 으로 Bug C 근본 원인 확인 + cpu.model 부분 fix

### 컨텍스트
사용자 질의 "CSUS raw JSON 을 너가 찾아볼 수 없어?" → AI web hunt (5 source 병렬). HPE 자체 repo `HewlettPackard/sdflexutils` 테스트 픽스처에서 **실 Superdome Flex RMC Redfish 캡처** 확보 (CSUS 3200 의 전신, 동일 RMC 스택). AI 가 raw URL 직접 fetch 로 검증 (subagent 보고 신뢰 안 함 — rule 25 R7-A).

### 검증된 사실 ([REAL-JSON], 출처 verbatim fetch)
- `.../json_samples/root.json` (ServiceRoot): `Product`/`Vendor`/`Oem` **전부 부재**, RedfishVersion `1.0.2` (구). → 단 **사용자 CSUS 는 `details.product="Compute Scale-up Server 3200"` 노출** = 더 신 펌웨어 (전신보다 rich). 사용자 장비 우선 (rule 25 R7-A-1).
- `.../json_samples/system.json` (ComputerSystem `Partition1`, SystemType `PhysicallyPartitioned`):
  - **`Manufacturer`/`Model`/`SerialNumber` 부재** → **Bug A 확정** (A1 Chassis 폴백이 정답).
  - **`Processors`/`Memory`/`Storage`/`EthernetInterfaces` drill-in sub-collection 전부 부재**, `ProcessorSummary`(Count=4/LogicalProcessorCount=64/Model="Xeon Gold 6142") + `MemorySummary`(735 GiB) **만 존재** → **Bug C 근본 원인 확정**.
  - `Oem.Hpe`=`#HpeNpar`, `Links.ManagedBy`→`/Managers/RMC`, `Links.Chassis`→`/Chassis/r001i01b`.
- source: `https://raw.githubusercontent.com/HewlettPackard/sdflexutils/master/sdflexutils/tests/unit/redfish/json_samples/{root,system}.json`

### Bug C 재해석 (대부분 이미 처리됨)
top-level `normalize_standard.yml` 이 **이미** summary fallback 보유:
- `cpu.sockets` ← `ProcessorSummary.Count` (L473) / `cores_physical` ← `CoreCount` (L477, BUG-13) / `logical_threads` ← `LogicalProcessorCount` (L480) / `memory.total_mb` ← `MemorySummary.TotalSystemMemoryGiB×1024` (L494, BUG-14).
- → 사용자 CSUS 의 socket/thread/메모리총량 은 **이미 0 이 아닐 가능성 높음** (gather_system 이 System 읽었다면).
- **유일한 명확 누락**: `cpu.model` 이 per-processor list 만 보고 `ProcessorSummary.Model` fallback 부재 → **본 amendment 에서 추가** (L483, Additive — 정상 vendor per-proc 우선).
- **B2 의 간접 Bug C 효과**: B2 가 CSUS adapter 를 선택 → `manager_layout=rmc_primary` → `_collect_multi_node_topology` 활성 → `data.multi_node.partitions[]` 에 **전 partition 별 cpu/memory/storage/network** 수집. 구(오선택 ilo6)에서는 multi_node=null 이라 이 rich 데이터 자체가 미수집이었음.

### 남은 한계 (실 장비 필요 — rule 25 R7-A-1)
- `memory.slots[]` / `storage.physical_disks[]` / `network.interfaces[]` 의 top-level **상세**: partition System drill-in 부재라 summary 로 대체 불가. 데이터는 `data.multi_node` (B2 활성) 또는 Chassis/NetworkAdapters 에 있을 수 있음. **사용자 newer 펌웨어가 drill-in 을 노출하는지는 실 envelope 확인 필요** (전신 캡처는 미노출, 사용자 장비는 ServiceRoot.Product 노출하는 신 펌웨어라 다를 수 있음).

### 검증
- [OK] AI 가 raw JSON 2개 직접 fetch (root.json/system.json) — subagent 보고와 일치 확인.
- [OK] `cpu.model` fallback jinja2 3.1.6 render: CSUS→summary.Model / 정상→per-proc 우선 / 둘다없음→None.
- [OK] pytest `test_csus_adapter_priority.py` 15 (cpu.model 2 guard 포함).
- [NG] 실 CSUS 장비 end-to-end (cpu.model + multi_node 채워지는지): 장비 부재 — 사용자 확인 필요.

## 9. Amendment 2026-06-04 (2) — CSUS-3200 전용 web 증거 (check_redfish 소스) + A1b model fallback

### 컨텍스트
사용자 "CSUS 3200 (전신 아니라 그 모델) raw JSON 웹에 정말 없나?" → AI 직접 검색 (워크플로는 동시-에이전트 rate-limit 으로 0 토큰 실패 → 수동 fetch 로 전환).

### 결과 (CSUS-3200 *전용* 소스 — [CODE]/[DOC-PROSE])
- **verbatim CSUS-3200 *장비* JSON 덤프는 공개 웹에 없음** (rare 2023+ 머신). 단 CSUS-3200 *전용* 도구/문서 다수:
  - `check_redfish` (github.com/bb-Ricardo/check_redfish) issue #168 → CSUS 3200 / Superdome Flex / BullSequana SH120 지원. 소스 `cr_module/system_chassis.py` [CODE]:
    `manufacturer = system.Manufacturer or rf.vendor` / `if model is None: model = connection.root.get("Product")` (ServiceRoot.Product fallback).
    `cr_module/proc.py` [CODE]: `/Processors` 컬렉션 GET → 부재 시 issue 후 **종료** (ProcessorSummary 는 health/count 만). 즉 도구가 CSUS 3200 에 **/Processors drill-in 존재를 전제**.
  - OpsRamp(HPE GreenLake) SUS 3200 통합 [DOC-PROSE]: Processor/Memory/Drives/NetworkAdapter 를 개별 리소스로 모니터링.
- **Q3 추정 (드릴인 존재 여부)**: 신형 CSUS 3200 펌웨어는 **/Processors·/Memory·/Storage drill-in 컬렉션을 노출할 가능성 높음** (전신 Superdome Flex 280 [REAL-JSON] 은 미노출이었으나, OpsRamp + check_redfish 가 drill-in 전제). → 사용자의 cpu/memory null 원인이 "drill-in 부재"가 **아닐 수도** 있음 (partition 선택 / adapter 전략 / 섹션 실패 등). **실 envelope 으로만 확정** (rule 25 R7-A-1).

### A1b 결정 (web-evidenced)
`gather_system` 에 `product_hint=ServiceRoot.Product` 전달 → `System.Model` 부재 시 **ServiceRoot.Product 우선 fallback** (Chassis.Model 보다 우선 — check_redfish 동일 패턴). 사용자 CSUS 는 ServiceRoot.Product="Compute Scale-up Server 3200" 노출 → 깨끗한 `hardware.model` (Chassis 의 "... Base" 접미사 회피). Additive — 정상 vendor 는 System.Model 보유 → 미발동.

### 검증
- [OK] pytest 766 / test_csus_adapter_priority.py 17 (A1b 2 추가) / vendor-boundary PASS / py_compile PASS.
- [OK] A1b: System.Model None + product_hint → model=product_hint (Chassis 보다 우선) / 정상 Dell System.Model 존재 → product_hint(BMC명) 무시.
- [NG] 실 CSUS 장비: drill-in 실제 노출 여부 + cpu/memory/storage 채워짐 — 사용자 envelope 필요.
