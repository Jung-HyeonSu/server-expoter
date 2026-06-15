# server-exporter 다음 작업 (NEXT_ACTIONS)

> **본 파일**: 진정 active PENDING 만 유지 (rule 70 R5 / R6 / R7 cycle 자문 정책).
> **lab 매트릭스**: `docs/ai/catalogs/LAB_PENDING_MATRIX.md` (8 vendor × generation × 4 column).
> **archive**: `docs/ai/archive/NEXT_ACTIONS-history-2026-04-to-05.md` (OPS-* + cycle-013/014/015/016 잔여).
> **마지막 정리**: 2026-05-29 (audit-cleanup cycle).

---

## OS 네트워크 본딩/티밍 수집 보강 (2026-06-15) 후속

> 상세·근거: `tests/evidence/2026-06-15-os-network-bond.md`. Linux bond 는 실장비 2대(RHEL 8.10 raw /
> RHEL 9.6 python) 검증 완료·수렴. 아래는 환경 제약으로 미수행한 후속.

- [ ] **[HIGH] Windows Teaming 실장비 검증**: LBFO(Get-NetLbfoTeam)/SET(Get-NetSwitchTeam) 수집은
  코드 + 단위테스트(realistic fixture)만 검증, 실 Windows 호스트 미제공 → 미검증. Windows Server +
  LBFO/SET 구성 호스트에서 `os-gather` 실행 후 `data.network.teams[]` + interfaces team_role 대조 필요.
- [ ] **[MED] bonded OS baseline (full envelope) 생성**: 현재 회귀는 `tests/fixtures/os/net/*` (data.network
  레벨) + 실 YAML 렌더 테스트로 고정. 전체 envelope baseline(`schema/baseline_v1/`)은 lab 호스트에 ansible
  미설치로 미생성 → Jenkins 실 빌드로 RHEL 8.10/9.6 bonded envelope 캡처 후 baseline 추가 권장(rule 13 R4).
- [ ] **[LOW] 추가 bond 모드 실장비 검증**: balance-rr / balance-xor / balance-tlb / balance-alb 는
  단위테스트만. 사이트에 해당 모드 존재 시 capture-site-fixture 로 회귀 fixture 추가.
- [ ] **[LOW] VLAN/teamd 실장비 검증**: VLAN(bond 하위) + Linux teamd 는 코드+단위테스트만(테스트 lab 미구성).

## HPE Compute Scale-up Server 3200 (CSUS 3200) 실 미러 검수 (2026-06-15) 후속

> 상세·근거: `tests/evidence/2026-06-15-hpe-csus3200-mirror-audit.md`. 라이브러리 fix **17건** 적용·수렴.
> 1차 16건(5-round) + 후속 재검수 1건(CSUS-R17, 3-round 재수렴 NEW 0). 회귀 1154 passed. 4 노드(실 RMC) raw 기준.

### 완료 (라이브러리 — 자율 수정, raw 충실 + Additive)

- [x] R1 chassis=System.Links.Chassis / FC1·FC2 FC WWPN / R3 multi_node system / R4 ilo_version / R5 chassis kind
- [x] R6 port_count / R9 PSU fw / R10·R14 power(telemetry 권위) / R11 fan RPM / R12 memory locator
- [x] R8 Ethernet 분류 / R13 FC associated_address=WWPN(전벤더) / R15 _network_meta strip / R16 adapter firmware(PCIeDevice)
- [x] **R17 (재검수 2026-06-15, 커밋 1167e01a)**: `_extract_oem_hpe` 를 OEM `@odata.type` 로 분기 — #HpeH3Npar 면 CSUS
  전용 키(product_id/console_routing/console_routing_current_boot/dcd_version/host_os_*) 추출. 구: all-null iLO 스켈레톤
  날조(missing-looks-valid) + 실 OEM drop. iLO default 불변(Additive). **SYS-OEM gated 항목 해소**. 회귀 +3.

### 잔여 — gated (보호 경로 / Ansible(Linux) / lab 실측 / envelope 계약 — 자율 미수정)

- [ ] **[HIGH] CSUS baseline 실측 교체 (BASE-01)**: `schema/baseline_v1/hpe_csus_3200_baseline.json` 이 구 MOCK
  (가상 3-partition/4-manager, 날조 PSU/WWPN/토폴로지) — 실 4노드와 전면 불일치. 라이브러리는 정상(faithful),
  회귀 기준선 무력. **Ansible control node(Linux) 필요 — 본 Windows 환경 미지원**(DL380 과 동일 제약). 실 site.yml
  실행으로 정규화 envelope 생성 후 교체 (rule 13 R4 — AI 임의 편집 금지). 교체 시 `test_csus_mock_consistency.py` MOCK 가드 동반 갱신.
- [ ] **[MED] field_dictionary drift (FD-01)**: `multi_node.partitions[].boot` / `chassis[].thermal` / `composition` /
  `fabrics` / summary 신필드(resource_block_count/fabric_count) 미문서 (엔진은 이미 emit). 보호 경로 — 사용자 승인.
- [ ] **[MED] collect_oem.yml CSUS 실 OEM 필드명 (OEM-01)**: `tasks/vendors/hpe/collect_oem.yml` 이 Superdome Flex
  추정 필드명(PartitionInfo/FlexNodeInfo)을 읽어 CSUS 실 OEM(#HpeH3Npar: ProductId/ConsoleRouting/Physloc)과 불일치
  → OEM fragment 영구 미생성(라이브러리 replay 미노출, 실 파이프라인 silent 누락). 재검수(2026-06-15) 추가 확인: 추출한
  `_hpe_superdome_*` 변수도 step 3 에서 미사용(항상 `_data_fragment:{}`) = dead/no-op. **단 무해** — 라이브러리 CSUS-R17 이
  system OEM 직접 수집. Ansible 환경 미보유로 검증 불가 → 정리(또는 CSUS-R17 정합 재작성) 권장. lab/실 raw 로 HpeH3* 필드명 확인 후 교정.
- [x] ~~**[LOW] system.oem iLO-shaped (SYS-OEM)**~~ — **해소** (재검수 CSUS-R17, 커밋 1167e01a). all-null iLO 스켈레톤 →
  #HpeH3Npar 분기로 실 OEM 추출. 4노드 raw 1:1 검증.
- [ ] **[IMPROVEMENT] Chassis OEM 미수집 (F2)**: `gather_chassis_multi` 가 Chassis #HpeH3Chassis OEM(Physloc /
  OemChassisType / PhysicalLocationString / ProcessorsCompatibilityKey·Compatible) 미보존. enrichment(틀린 값 아님 —
  현재 faithful). multi_node.chassis 는 CSUS/Superdome 전용이라 타 13벤더 무영향. 단 비-schema 신키 추가 = scope/계약 결정
  (multi_node.chassis shape + FD-01 동반). 사용자 결정 대상.
- [ ] **[LOW/latent] memory CapacityMiB 누락→0 (MEM-01)**: `gather_memory`(redfish_gather.py:1942) `_safe(mdata,'CapacityMiB') or 0`
  — 누락 시 0 날조(누락↔0 혼동). **CSUS 미발동**(전 DIMM CapacityMiB 보유) + 범용(전 벤더) 코드 + 실측 trigger 부재라
  rule 25 R7-B 로 자율 미수정. 안전 수정案: `or 0` 제거 + `_safe_int(cap) if cap is not None else None` (실데이터 회귀 0 — 누락 케이스만 변경).
- [ ] **[LOW] network shape (NET-SHAPE) — 재검수: 비-결함 확인**: top-level `data.network`(라이브러리 intermediate)=list 이나
  `normalize_standard.yml`(:444-445,:545-552)가 dict 로 재조립 → **호출자는 dict 수신**. replay(라이브러리 단독) 산출물을
  최종 envelope 로 오인한 finding. 코드 변경 불필요(재검수 3-round 확인). 잔존 시 doc/tooling 주석만.
- [ ] **[LOW] network 섹션 매핑 충돌 (NET-SEC-MAP)**: normalize `_rf_proc_map` 가 network/network_adapters 를 같은
  'network' 로 collapse + build_sections unsupported 우선 → host network 성공이 network_adapters 404 에 가려질 latent
  충돌 (CSUS 수정 후 미발동). build_sections 충돌해소 규칙 명시 (다채널 영향 — 승인).
- [ ] **[LOW] Rmp 관리어댑터 / multi_node.chassis name / ResourceBlock count**: Rmp(관리 NIC, MAC 은 bmc.mac_address 존재)
  placeholder 필터 drop / chassis name 미emit(envelope shape) / ResourceBlock proc·mem count=0(ComputerSystem-type 충실).
- [ ] **[INFO] lab 도입 후 별도 cycle**: `hpe-csus-3200-lab-validation` round — 실 capture-site-fixture + baseline + vault 결정.

## HPE DL380 Gen12 실 미러 검수 (2026-06-15) 후속

> 상세·근거: `tests/evidence/2026-06-15-hpe-dl380-mirror-audit.md`. 라이브러리 fix 7건 적용·수렴(Round4 NEW 0)
> + 사용자 승인 후속 진행. 회귀 1123 passed.

### 완료 (사용자 승인 후 진행 — 2026-06-15)

- [x] **thermal 섹션 배선 (ATX-01/02)** — `build_sections.yml`/`build_failed_output.yml` all_sec +
  3 skeleton 에 thermal 추가 (10→11 섹션). docs/19·20 동반(rule 13 R8). status-scenario 회귀 5건. (commit 7be8cdc0)
- [x] **firmware category 오분류 (SCHEMA-07)** — 'System ROM'→bios + UBM 백플레인 'nvme' 선점 정정.
  + firmware[].category/pending field_dictionary 등록 (122 entries). (commit da215d68)
- [x] **cpu.architecture channel (SCHEMA-05)** — `[os,esxi]`→`[redfish,os,esxi]` + docs/20 동기화. (da215d68)
- [x] **hardware 12 식별필드 field_dictionary 등록 (SCH-1/2, 사용자 승인 — 핵심은 Must)** — vendor/model/
  serial/uuid/bios_version = Must (전 esxi+redfish baseline 보유 실측), 나머지 7 = Nice. (120→134 entries)
- [x] **volumes.total_mb 단위 명명 (RJ-1, 사용자 결정 — total_mb 유지)** — 키/값 유지, "값은 MiB(÷2^20)"를
  field_dictionary + docs/20 에 문서 명시 (rename/재계산은 계약 breaking이라 회피).

### 잔여 — 실측 필요 (자율 수정 불가)

- [ ] **[MED] HPE baseline 재캡처 (SCHEMA-01/04/06)**: hpe_baseline.json(iLO5 구캡처)에 thermal·network.
  adapters·ports·storage.hbas·multi_node + sections.thermal 누락 — 라이브러리는 정상(faithful), 회귀 커버리지 공백.
  **차단**: 본 검수 환경(Windows)은 ansible control node 미지원(`os.get_blocking` 부재 — 검증함). faithful baseline 은
  Linux control node 또는 lab Jenkins 의 실 site.yml 실행 필요 (rule 13 R4 — AI 임의 편집 금지).
  → **절차**: `_serve_fixtures_as_redfish.py` (TLS 래핑) 로 미러 서빙 → `ansible-playbook redfish-gather/site.yml`
  (REPO_ROOT + vault/redfish/hpe.yml + inventory) → json_only 출력을 schema/baseline_v1/hpe_dl380_gen12_baseline.json
  (신 iLO7 baseline, 기존 iLO5 보존) + test_redfish_baseline.py 케이스 추가.

## Round 15 (2026-06-09 멀티에이전트 버그헌트) 후속

> 상세: `tests/evidence/2026-06-09-round15-multiagent-bughunt.md`. 본 cycle 33 fix 적용·검증 완료.
> 아래는 **lab/실행 환경 필요로 보류**한 항목.

| 우선 | 항목 | 분류 | 결정 주체 |
|---|---|---|---|
| MED | 본 cycle os/esxi YAML + Jenkinsfile·_portal 변경 1회 실 ansible/Jenkins **smoke 검증** (본 환경 ansible/Jenkins 부재로 미실측) | `[LAB][CI]` | 사용자+lab |
| MED | windows gather_cpu/memory/network — WMI 빈 응답 시 degraded-data **warning 로깅**(섹션 collected 유지, Linux gather_memory 패턴 일관). additive, Windows lab 후 적용 | `[ANSIBLE][LAB]` | lab |

## Round 16 (2026-06-09 멀티에이전트 버그헌트 — 5 pass 수렴) 후속

> 상세: `tests/evidence/2026-06-09-round16-multiagent-bughunt.md`. 15 fix 적용·검증 완료
> (confirmed 추이 10→1→2→2→0, pass5 CONVERGED). 아래는 lab/하네스 필요로 보류.

| 우선 | 항목 | 분류 | 결정 주체 |
|---|---|---|---|
| MED | 본 cycle os/esxi/redfish YAML 변경 1회 실 ansible-playbook **smoke 검증** (본 환경 CLI 부재 → Jinja2 렌더로만 검증) | `[ANSIBLE][LAB]` | 사용자+lab |
| LOW | vendor `tasks/vendors/*/collect_oem.yml`·`normalize_oem.yml` — 어떤 include 도 없는 **미wiring placeholder**. 내부 `when: _rf_raw_collect.systems`(모듈 미emit 키)라 wiring 시에도 dead. OEM 확장 시 모듈서 raw Oem 보존 + repoint 필요 | `[CONTRACT][LAB]` | 사용자 |
| LOW | Ansible **Jinja 템플릿 회귀 하네스** 도입 — windows cpu/storage/network null-가드 fix 는 Jinja2 직접 렌더로 검증, 영속 회귀는 baseline 의존(null-field fixture 부재) | `[QA]` | qa |

## Round 17 (2026-06-10 멀티에이전트 버그헌트) 후속

> 상세: `tests/evidence/2026-06-10-round17-multiagent-bughunt.md`. 23 confirmed 중 18 적용·검증
> 완료(batch1/2). 아래는 **lab/실행 환경 필요로 보류**(검증 불가 → 정직 보고).

| 우선 | 항목 | 분류 | 결정 주체 |
|---|---|---|---|
| MED | **vendor OEM 추출 cluster (#13~#17)** — huawei/inspur/fujitsu/quanta/hpe-superdome `collect_oem.yml` 이 `_rf_raw_collect.systems[0]`(모듈 미emit) 또는 `data.system.Oem`(대문자, 실제는 소문자 `data.system.oem`)·`data.chassis`(미존재) 를 읽어 **항상 빈 OEM**. wiring 됨(adapter `oem_tasks`)이나 dead. graceful(crash/envelope 위반 없음). 진짜 fix = ① huawei/inspur/fujitsu/quanta 를 `_OEM_EXTRACTORS` 에 추가(라이브러리) + ② raw Oem 보존 또는 path repoint(`data.system.oem`) + ③ 사이트 fixture. 4종 lab 부재라 추출기 추가해도 검증 불가 → 사이트 fixture 선행 필요 | `[CONTRACT][LAB]` | 사용자+lab |
| MED | 본 cycle os/esxi/redfish/precheck **YAML + Jenkinsfile_portal 변경 1회 실 ansible-playbook/Jenkins smoke 검증** (본 환경 ansible/Jenkins 부재 → Jinja2 렌더 + pytest 로만 검증). 대상: gather_runtime/gather_system(#6/#7/#19/#20), esxi/os site.yml adapter 선택(#9/#10), run_precheck(#4), try_one_credential(#2/#21), Jenkinsfile_portal Stage3(#23) | `[ANSIBLE][CI][LAB]` | 사용자+lab |
| LOW | **precheck timeout 동작 변경 확인** — `_precheck_timeout`(redfish=_rf_timeout, esxi=30) 이 이제 protocol/auth 에 반영(기존 15/8 → 30). 느린 BMC false-negative 해소하나 실패 호스트 precheck 시간 증가. 운영 배치에서 허용 가능 확인 | `[LAB]` | 사용자 |
| LOW | cisco `collect_oem.yml` 도 `data.system.Oem`(대문자) 읽어 supplement dead — 단 cisco 는 `_OEM_EXTRACTORS` 라 라이브러리가 `data.system.oem`(소문자) 채움(부분 동작). lab 후 path 정정 + 회귀 | `[CONTRACT][LAB]` | lab |

### Round 18 재스캔 후속 (R17 수정 회귀검수 — 4 confirmed 중 2 적용, 2 보류)

> R18-1(회귀: _normalize_port_speed inf/nan crash) + R18-2(Windows runtime rescue clobber) 적용·검증 완료.
> 아래 2건은 LOW + 선재(pre-existing) + 실측/lab 검증 필요로 보류 (verification.md — 검증 불가 변경 자제).

| 우선 | 항목 | 분류 | 결정 주체 |
|---|---|---|---|
| LOW | **runtime dual-collector success-path clobber (R18-3)** — gather_runtime(Linux+Windows) 가 success 경로에서도 gather_system 의 더 견고한 runtime(chronyd loop / nftables / systemctl firewall / become:true)을 inferior 값으로 덮음. 선재(F5 commit f2ccea36). 근본 fix = gather_runtime 의 runtime 생산 제거(gather_system 단일 정본화) — site.yml include 제거 + 파일 삭제. 구조 변경이라 실 ansible smoke 후 적용 권장 | `[ANSIBLE][LAB]` | 사용자+lab |
| DONE | ~~**network.interfaces[].link_status enum drift (R18-4)**~~ — **해결 cycle 2026-06-14** (branch feature/r740-audit-fixes). field_dictionary enum→`up/down/unknown` 통일 + 3채널 코드 통일(os-linux/os-windows/esxi-interfaces+adapters+hbas; redfish 기존 canonical) + dell/hpe/lenovo baseline `network.interfaces[].link_status` 결정론적 마이그레이션(linkup→up 등; hpe/lenovo 미러 replay 로 코드 출력 일치 검증) + docs/20+docs/09+예시/fixture. **잔여(lab)**: 전 baseline 의 link_status 외 필드 stale 가능 → 실장비 full 재캡처 권장(rule 13 R4) | `[SCHEMA][LAB]` | 사용자+lab |

## 0. 2026-05-29 audit-cleanup 후속 (전수 audit 결과 — 미적용 backlog)

> 정본: `docs/ai/AUDIT-2026-05-29.md` (전체 권고 + 정확 file:line + diff).

| 우선 | 항목 | 분류 | 결정 주체 |
|---|---|---|---|
| **[CRIT]** | vault 마스터 암호(`Goodmit0802!`) + 자격 회전 + (선택) git 히스토리 purge | 보안 | **사용자** — `docs/ai/policy/SECRET-ROTATION-RUNBOOK.md` |
| **[HIGH]** | BMC/AD lockout 회피 (detect 선인증 4-GET / OS backoff 부재 / account_service dryrun=false) | `[AUTH][LAB]` | 사용자+lab — AUDIT §1 |
| MED | esxi vendor 정규화 substring fallback 누락 (`vendor` 필드 divergence 버그) | `[ANSIBLE]` | AUDIT §4 AR-1 |
| MED | perf: CSUS 대표 partition 2회 fetch / firmware fetch-then-discard / SSL ctx 재생성 | `[LAB]` | AUDIT §2 |
| MED | refactor: `account_service_provision` 381줄 분할 / HTTP verb 통합 / status 문자열매칭→숫자 | `[AUTH][CONTRACT]` | AUDIT §3 |
| LOW | JEDEC 테이블 단일화 / registry.yml 문서 명확화 / build_output 명명 / vendor debug dead var | `[ANSIBLE]` | AUDIT §4 |

> 본 cycle 미적용 사유: 본 환경에 **ansible-playbook CLI 부재**(playbook syntax/런타임 검증 불가) + 일부는 **실장비/인증 동작** 변경 (사용자 "운영 깨지면 안됨, 특히 인증"). ansible YAML 적용은 Jenkins agent(ansible-playbook+lab) 에서 검증 후.
>
> **2026-06-04 환경 정정**: ansible **라이브러리** 2.19.9 는 설치되어 있어 (`import ansible` OK) Python 모듈/필터/플러그인은 **pytest 로 로컬 검증 가능** (704 pass). 단 `ansible-playbook` **CLI 는 PATH 부재**(rc=127) — playbook syntax-check/런타임은 여전히 Jenkins Agent 위임. 따라서 §0 의 `[ANSIBLE]` 태그 항목(YAML/playbook 변경)은 계속 보류, Python-only 항목(R-4 등)은 본 환경에서 진행 가능.

### 0.9 (2026-06-09 견고화 사이클) merge_fragment 가드 Jenkins 통합 검증 [PENDING — Jenkins Agent]

- **항목**: `common/tasks/normalize/merge_fragment.yml` 의 data 병합 concat 분기 `is not mapping` 가드(커밋 `6378453`) — list↔dict 오염 시 `bv+fv` TypeError 를 else(fv 우선)로 graceful 강등.
- **로컬 검증 완료(✅)**: 실 YAML 식을 추출해 Jinja2 로 렌더(`tests/unit/test_merge_fragment_render.py` 5건) — 정상 list+list concat 불변 + 오염 list↔dict graceful 확인.
- **잔여(Jenkins)**: 전체 ansible set_fact 통합(실 `union` 필터 + `no_log` + 3-채널 gather 흐름)에서 회귀 0 확인. 분류 `[ANSIBLE]`. 정상 입력 결과 불변이라 위험 낮음(Additive).

### 0.11 (2026-06-09 적대적 robustness 루프 R1~R14 수렴) 잔여

> 14 라운드 수렴 완료(genuine 0). 아래는 의도적 보류:
- **[CONTRACT 결정대기]** SimpleStorage empty-bay 필터링 방향 (dmtf golden 빈베이 포함) — 사용자 설계 결정 (R1 #12).
- **[ANSIBLE/Jenkins]** OS/ESXi YAML 가드(merge_fragment list+dict / normalize_storage·system | string·default) — Jinja2 렌더 검증 완료, 전체 ansible 통합은 Jenkins Agent.
- **[INFRA]** gitlab(10.100.64.156) push — 네트워크 미도달, 연결 환경서 `git push origin main`. e2e_browser(10.100.64.152 Jenkins master)도 도달 환경 재실행.
- **[CONSISTENCY]** link_speed_gbps 채널간 타입(redfish float vs OS/ESXi int) — redfish float이 정확(fractional Gbps), CSUS mock baseline int은 실데이터로 교체 시 정정. 통일 시 OS/ESXi를 float로(int cast 제거) — 별도 cycle.

### 0.10 (2026-06-09 Round 1 멀티에이전트 hunt) 미적용/결정대기 항목

> Round 1 = 9 finder + 3-lens 적대적 검증 → 26 confirmed. 24건 수정 완료(커밋 cc39beb~0f5e45e).
> 아래 2건만 미적용:

- **[CONTRACT 결정대기] #12 SimpleStorage empty-bay 필터링**: 표준 storage 경로(`_extract_storage_drives`)는 빈 베이(cap 0/null)를 필터링하는데, SimpleStorage(`_gather_simple_storage`)는 안 함 → cross-path 불일치. **그러나** dmtf golden 이 빈 베이(SATA Bay 3, 전 필드 null)를 **포함**하고 있어 필터링 적용 시 golden 변경 + envelope 계약 변경(빈 베이 노출 여부). **방향(필터 vs null 포함)은 설계/사용자 결정 필요** — DSP2043 mockup 은 의도적으로 빈 베이를 모델링. 결정 시 golden 재생성 필요.
- **[WONTFIX] #14 PowerSubsystem watt float 보존**: EnvironmentMetrics PowerWatts.Reading 가 float(12.5W) 가능하나 `_safe_int` 가 truncate. **의도적 유지** — /Power 경로(golden)는 watt 를 int 로 emit 하므로 PowerSubsystem 도 int 로 통일해야 envelope 타입 일관(rule 13). 소수 watt 는 운영상 무의미. #21 에서 두 경로 모두 int 통일.
- **[INFO] #7 Dell PATCH 3-slot 제한**: 의도된 동작(코드 주석 'up to 3'). 버그 아님 — account_service_provision 은 빈 슬롯 최대 3개만 시도. 향후 커버리지 테스트 추가 권장(코드 변경 불요).

---

## 0.5 HP CSUS 3200 사이트 사고 후속 — Bug C 잔여 [PENDING — 실 envelope 필요]

> 2026-06-04 사이트 사고. A1/B1/B2 + cpu.model fallback 적용·검증 완료 (ADR-2026-06-04-csus-adapter-priority §8).
> web hunt 로 HPE `sdflexutils` 실 캡처 JSON 확보·검증 → Bug C 근본 원인 확정 + 대부분 기존 코드로 이미 처리됨 판명.

**확정 (web 실측 — sdflexutils root.json/system.json)**: Superdome/CSUS partition System 은 Manufacturer/Model 부재 + Processors/Memory/Storage/EthernetInterfaces drill-in **부재**, ProcessorSummary/MemorySummary 만 존재.

| 항목 | 상태 | 비고 |
|---|---|---|
| cpu.sockets/cores/threads, memory.total | ✅ 기존 BUG-13/14 fallback 으로 이미 summary 채움 | 추가 작업 불요 |
| cpu.model | ✅ 2026-06-04 fallback 추가 (normalize_standard.yml L483) | jinja2 render 검증 |
| data.multi_node (전 partition 상세) | ✅ B2 가 CSUS adapter 선택 → manager_layout → 수집 활성 (구 ilo6 오선택 시 null 이었음) | 실 장비 확인 권장 |
| **memory.slots / storage.physical_disks / network.interfaces 의 top-level 상세** | ⚠️ partition System drill-in 부재라 summary 대체 불가. multi_node/Chassis 에 있을 수 있음 | **실 envelope 필요** — 사용자 newer 펌웨어가 drill-in 노출하는지 확인 |
| **실 envelope/raw JSON 1회 캡처** | trigger 충족 | 사용자 — 가장 정확. `capture-site-fixture`, sanitize 후 fixture |
| 실 baseline 교체 (현 MOCK) | 보류 (rule 96 R1-C) | 사용자 실측 후 (rule 13 R4) |
| **end-to-end 확인** (vendor=hpCsus + hardware + cpu.model + multi_node 채워짐) | ❌ 이 환경 확인 불가 | 사용자 사이트 재실행 |

> 전신(Superdome Flex 280) 캡처는 ServiceRoot.Product 부재였으나 **사용자 CSUS 는 노출** = 신 펌웨어. 사용자 장비가 정본(rule 25 R7-A-1) — 실 envelope 으로 잔여 null 필드 확정 필요.

---

## 0.7 DMTF 표준 mockup 오프라인 회귀 후속 (2026-06-08 — rackmount1 편입 후)

> 2026-06-08 DMTF `public-rackmount1`(DSP2043, BSD-3)을 표준 경로 오프라인 fixture 로 편입 완료(`tests/fixtures/redfish/dmtf_rackmount1/`). 아래는 그 후속 후보.

| # | 항목 | 분류 | trigger / 차단 | 결정 주체 |
|---|---|---|---|---|
| D1 | 2nd mockup **local-storage(1821)** 편입 — modern Storage/Drives/Volumes 표준 순수 데이터 회귀(현 fixture 는 SimpleStorage 만 커버) | `[FIXTURE]` | **DSP2043 번들 다운로드 차단**(dmtf.org 403 / Wayback 503/404). 사용자 망/수동 zip 또는 번들 미러 확보 시 `convert_dmtf_mockup.py` 로 즉시 편입 | 사용자(번들 확보) |
| D2 | 2nd mockup **bladed(1820)** 편입 | `[FIXTURE]` | 동일 번들 차단 + **본 라이브러리 하네스에서 multi_node 미활성**(manager_layout=None → `_collect_multi_node_topology`=None). 가치 재평가 필요 — 편입해도 first-member 단일 수집(rackmount 대비 한계 marginal) | 사용자 |
| D3 | **storage fallback 분류 재검토** — SimpleStorage/SmartStorage fallback 성공 시 storage 를 `failed` 대신 degraded/collected 로 분류 (FAILURE_PATTERNS 2026-06-08) | `[CONTRACT]` | status 의미론 변경(rule 13 R8 — 4-시나리오 매트릭스 + docs/19/20 + 영향 vendor fixture 동반) + 호출자 계약 영향. HPE iLO4 SmartStorage 포함 전 fallback 영향 | **사용자** — rule 13 R8 승인 필요 |
| D4 | **신규 섹션** Thermal/ThermalSubsystem(1828) / Cables(1835) / CXL(1839) / CDU(1840) — DMTF 미수집 리소스 | `[SCHEMA]` | schema 버전 변경(rule 13 R3) + 실장비 baseline + 사용자 명시 승인. mockup URL = web sources(rule 96 R1-A) | **사용자** — rule 13 R3 |

> D1/D2 진입 절차: DSP2043 zip 확보 → `public-<name>/` 추출 → `python tests/integration/convert_dmtf_mockup.py --mockup-dir <경로> --name dmtf_<name> ...` → golden 비판적 리뷰(rule 95 R3) → pytest.

---

## 0.8 AR-1 esxi vendor 정규화 substring fallback — [PARTIAL] (Jenkins Agent 후속)

> AUDIT-2026-05-29 AR-1. **실 버그**: `vendor` envelope 필드 채널 divergence.
> 2026-06-08 — redfish reference 측 단위 테스트 고정 완료(`tests/unit/test_vendor_normalize_aliases.py` 16 케이스). esxi YAML 수정은 **이 환경에서 미적용**(ansible-playbook CLI = Windows POSIX-only 미동작 / yamllint 부재 / rule §0 `[ANSIBLE]` defer 정책 / "운영 깨지면 안됨").

**근본 원인** (실측):
- redfish `_normalize_vendor_from_aliases`(:467): 정확매칭 → **substring fallback** → 'unknown'.
- esxi inline Jinja2(`esxi-gather/site.yml:162-175`): **정확매칭만**, substring 없음, default=raw.
- 결과: "Dell Inc"(마침표 없음) → redfish='dell' ↔ esxi=raw('Dell Inc'). vendor 필드 불일치.

**Jenkins Agent 적용 recipe** (택1, 적용 후 esxi baseline 회귀로 검증 — rule 40):
- **(권장) 공유 filter**: `filter_plugins/normalize_vendor.py` 신설(redfish `_normalize_vendor_from_aliases` 로직 mirror — jedec_mapper.py 패턴) → esxi `_e_vendor_normalized` 를 `{{ (_e_raw_facts.ansible_system_vendor | default('')) | trim | lower | normalize_vendor(_e_vendor_aliases_map) }}` 로 교체(14줄 fragile Jinja2 제거). + JEDEC 식 redfish↔filter parity 가드 test 추가.
- **(최소 diff) inline 확장**: 현 Jinja2 loop 뒤에 substring pass 추가(`{%- if a|lower in raw_lower or raw_lower in a|lower -%}`) + default `none`→`'unknown'`.
- **주의**: default 를 raw→'unknown' 로 바꾸면 미지 vendor 의 esxi `vendor` 값이 변함 → esxi baseline 영향 가능(VMware 는 alias 매칭이라 무영향 예상). baseline 재검증 의무.
- 기준선: redfish 동작 = `test_vendor_normalize_aliases.py`. esxi 수정 후 동일 입력 동일 canonical 이어야 함.

---

## 1. AI 환경에서 즉시 가능 — F6 OS baseline expansion (사용자 access 제공 완료)

| 항목 | 상태 | 진입 |
|---|---|---|
| rhel920 / rhel960 / rocky960 baseline 3건 신설 | **trigger 충족** (사용자 IP 제공 2026-05-11) | `docs/ai/handoff/2026-05-21-os-baseline-expansion.md` cold-start |

- 3 IP: 10.100.64.163 / 10.100.64.165 / 10.100.64.169
- F5 system.runtime 9 필드 빌더 실측 검증 포함
- Jenkins Agent 환경 필요 (ansible-playbook 실 수집)

---

## 2. 외부 trigger 대기 PENDING (lab / 사이트 / 운영 환경)

### 2.1 baseline 확장 (lab 도입 시)

| # | 항목 | trigger |
|---|---|---|
| F3 | Supermicro baseline | 사이트 BMC IP 확보 |
| F4 | Windows + 베어메탈 OS baseline | winrm/sudo 환경 도입 |

각 진입 시: `update-vendor-baseline` skill + rule 13 R4 절차.

### 2.2 HPE CSUS 3200 / Superdome Flex RMC (lab 부재)

- **trigger**: RMC IP 확보 + Redfish 활성화 (`docs/22_rmc-activation-guide.md` 4 절)
- **상세 8 항목 (C1~C8)**: `docs/ai/catalogs/LAB_PENDING_MATRIX.md` HPE 행
- **handoff 후보 A**: `docs/ai/handoff/2026-05-11-next-cycles.md` "후보 A — HPE CSUS 3200 lab 검증"
- **ADR**: `docs/ai/decisions/ADR-2026-05-12-csus-rmc-multi-node.md`, `ADR-2026-05-29-hba-ib-csus.md`
- **cycle 2026-05-29 (hba-ib-csus)**: baseline 을 전 공통 섹션 realistic mock 으로 채움 (FC HBA + RAID1 SATA + DDR5 + 3 partition canonical). 여전히 **mock** — C1 사이트 fixture 캡처 후 실 baseline 으로 교체 의무 ("검증됨" 주장 금지 — rule 25 R7-B).
- **2026-06-08 에뮬레이터 범위 명시**: HPE 공식 iLO 에뮬레이터는 **CSUS/Superdome mockup 부재** → 본 항목(CSUS/Superdome)은 에뮬레이터로 못 메움. 실장비/사이트 fixture 가 유일 경로. (에뮬레이터는 iLO5/iLO6/Gen12 ProLiant 만 — `tests/integration/test_hpe_emulator_replay.py` 오프라인 회귀로 별도 커버.)
- **cycle 2026-06-09 (ADR-2026-06-09)**: CSUS 3200 Redfish 모델 검수 → 누락 5종 (boot / thermal / log_services / composition(ResourceBlocks) / fabrics(FlexGrid)) Additive 구현 + mock fixture/baseline/테스트. 여전히 **mock** — 아래 C9~C14 사이트 실측 정정 의무 (rule 96 R1-C):
  - **C9**: CompositionService/ResourceBlock 실 schema (RB↔chassis 매핑 / Processors·Memory 표현)
  - **C10**: Fabrics/FlexGrid 실 FabricType (NUMAlink 표기) / Switch.SwitchType / Endpoint.EndpointProtocol
  - **C11**: Chassis Thermal 실 sensor 명 / `/Thermal` vs `/ThermalSubsystem` 펌웨어 분기
  - **C12**: RMC LogServices 실 ID (IML/IEL 추정) / OverWritePolicy
  - **C13**: per-partition `Boot.BootOrder` 실 표현
  - **C14**: (최적화) `gather_boot` / `gather_manager_logs` 재-GET 제거 — `gather_system`/`gather_bmc` raw 재사용 (현재 partition/manager 당 1회 추가 round-trip)

### 2.4 HBA / InfiniBand 사이트 fixture (lab 부재 — cycle 2026-05-29)

- **trigger**: FC HBA / IB HCA 보유 사이트 BMC/OS/ESXi 접근
- **항목**:
  - FC HBA 보유 Dell/HPE/Lenovo/Cisco BMC → Redfish `storage.hbas` 실측 fixture + baseline (현 4 redfish baseline 은 FC 미보유로 빈)
  - FC HBA 보유 Windows/Linux 호스트 → `Get-InitiatorPort`+`MSFC_*` / sysfs 실측 (현 ubuntu/windows/rhel baseline 빈)
  - IB HCA (Mellanox/NVIDIA) 보유 호스트 → Linux ibstat/sysfs 실측 (IB 정본 채널)
  - ESXi FC SAN 호스트 → vmhba FC speed/wwnn 실측 (현 esxi_baseline 은 offline FC 2)
- **ESXi esxcli-over-SSH fallback (D1-B 재평가)**: SSH 활성 운영·보안 결정 시 `esxcli storage san fc list` / `rdma device list` 보강
- **절차**: `capture-site-fixture` skill + rule 13 R4 (실측 baseline) + EXTERNAL-CONTRACTS 갱신

### 2.5 에뮬레이터 하네스 CI 편입 [DONE 2026-06-08 — agent 검증만 대기]

- **상태**: 사용자 승인(2026-06-08) 후 구현 완료. Jenkins Stage 4(E2E Regression)가 e2e 회귀 + `tests/integration/ -m "not live"`(HPE 에뮬레이터 오프라인 회귀)를 별도 invocation 으로 실행, 둘 중 하나라도 FAIL 시 stage 실패. 동반 갱신(docs/17 / rule 80 R1-A / JENKINS_PIPELINES) 완료.
- **구현 노트**: tests/e2e 와 tests/integration 이 둘 다 top-level `conftest` module 을 써서 단일 멀티-디렉터리 호출 시 ImportError → **별도 pytest 호출 + RC 합산**으로 해결 (Jenkinsfile L217-231). integration conftest 의 전역 `sys.path.insert` 도 제거(e2e conftest shadow 방지).
- **잔여 (⚠️ AI 환경 밖)**: 실제 Jenkins agent 에서 1회 green 확인 — `/opt/ansible-env` venv 가 redfish_gather(stdlib + ansible stub) import 가능한지. 로컬에선 동일 셸 로직 시뮬레이션 PASS(e2e 157 + integration 44, FINAL_RC=0) 확인했으나 **실 agent 실행은 미확인**. 첫 빌드 모니터링 필요.

### 2.3 8 vendor × generation 후속 매트릭스

→ `docs/ai/catalogs/LAB_PENDING_MATRIX.md` 정본 참조.

진행 가능한 generation 우선:
- Dell iDRAC8 / iDRAC9 (lab 미도입)
- HPE iLO5 / iLO6 / Superdome Flex
- Lenovo IMM2 / XCC / XCC2
- Cisco CIMC M5~M8 / UCS S-series
- Supermicro 전체 generation (사이트 BMC 0대)
- Huawei / Inspur / Fujitsu / Quanta 전체 (lab 부재)

---

## 3. 운영 / 보안 추적 (사용자 결정 대기)

위 archive 의 OPS-* 잔여 항목 trigger 발생 시 archive 에서 본 파일로 복원:

| 카테고리 | 추적 위치 |
|---|---|
| 보안 회전 (Goodmit0802! / vault) | archive OPS-AUDIT-1 / OPS-DELL-VAULT-1 |
| 운영팀 결정 (vault timing / repo private / dryrun OFF) | archive OPS-3 / OPS-5 / OPS-9 |
| 실 hardware 점검 (Lenovo PSU1) | archive OPS-LENOVO-PSU1 |
| WinRM / Win Server 2022 안정성 | archive AI-22 reopen / OPS-RESIDUAL-1 |
| baseline 재수집 (HPE iLO6 / Cisco / Dell) | archive OPS-HPE-REVIEW-1/2 / OPS-CISCO-REVIEW-1/2 |

---

## 4. 정기 추적 (분기 / 연간)

| 항목 | 주기 | 정본 |
|---|---|---|
| DMTF Redfish release 매트릭스 | 분기 | `EXTERNAL_CONTRACTS.md` |
| vendor EOL / CVE / errata | 분기 | `EXTERNAL_CONTRACTS.md` |
| community.vmware collection 업그레이드 | 연간 | `REQUIREMENTS.md` |
| 펌웨어 매트릭스 drift | TTL 90일 (rule 28 R1 #11) | adapter origin 주석 |
| COMPATIBILITY-MATRIX | TTL 14일 (rule 28 R1 #12) | `COMPATIBILITY-MATRIX.md` |
| LAB_PENDING_MATRIX | TTL 14일 (rule 28 R1 #12 와 동일) | `LAB_PENDING_MATRIX.md` |

---

## 5. AI 자율 진행 가능 (lab 없이 즉시)

| 작업 | skill / agent |
|---|---|
| harness 자기개선 cycle | `/harness-cycle` (6단계 파이프라인) |
| rule 28 측정 11종 drift 검사 | `measure-reality-snapshot` skill |
| repo 정리 (죽은 코드 / 중복 / archive 후보) | `repo-hygiene-planner` agent |
| `docs/ai/handoff/2026-05-11-next-cycles.md` 후보 B/C/D | handoff 후보 참조 |

---

## 6. repo-hygiene 후보 (2026-06-04 스캔 — 실측 검증됨, 미적용 / 계획만)

> D 작업: read-only 스캔 + 실측 참조 카운트 검증 (rule 25 R7-A). 제거/archive 는 사용자 결정 대기 (수정 안 함).

| 우선 | 후보 | 검증 결과 | 권고 |
|---|---|---|---|
| **[HIGH]** | `scripts/ai/bug_tracker/verify_all_tickets.py` | 외부 참조 **0건**, `verify_v2.py` 로 대체 (v1 field 명명 오류 수정본) | 삭제 또는 `scripts/ai/archive/one_off/` |
| MED | `esxi-gather/tasks/normalize_sections.yml` | esxi-gather 내 include 참조 **0건**, deprecated 쉼 (의도적 no-op) | archive 또는 삭제 (rule 70 R6) |
| LOW | `scripts/ai/bug_tracker/capture_raw_redfish.py` | 참조 **2건** (문서 — 완전 dead 아님), 2026-04-29 ticket cycle one-off | archive 후보 (sister: generate_tickets/verify_v2) |
| LOW | `module_utils/adapter_common.py::_flatten_aliases` | 1회 호출 (line 79, dead 아님 — inline 후보) | 저우선 cleanup |
| 중복 | JEDEC 매핑 (`jedec_mapper.py` ↔ `_JEDEC_VENDORS`) | 2026-06-04 **drift-guard 테스트로 보호** (`test_jedec_drift_guard.py`) | 통합 대신 가드 유지 (rule 10 stdlib 제약상 통합 비용 큼) |
| 중복 | HTTP/SSL 유틸 3중 (`precheck_bundle.py` / `redfish_gather.py` / `capture_raw_redfish.py`) | `_ctx`/`_auth`/`_get` 등 재구현 | `module_utils/` 공유 모듈 통합 — 별도 cycle (rule 10 stdlib 준수 + 회귀 큼) |

---

## 관련

- rule: `70-docs-and-evidence-policy` R5 / R6 / R7 (보존 / archive / cycle 자문)
- catalog: `LAB_PENDING_MATRIX.md`, `COMPATIBILITY-MATRIX.md`, `VENDOR_ADAPTERS.md`, `EXTERNAL_CONTRACTS.md`
- archive: `docs/ai/archive/NEXT_ACTIONS-history-2026-04-to-05.md`
- handoff: `docs/ai/handoff/2026-05-21-os-baseline-expansion.md` (F6), `docs/ai/handoff/2026-05-11-next-cycles.md` (4 후보)
- ADR: `docs/ai/decisions/ADR-2026-05-12-csus-rmc-multi-node.md`
