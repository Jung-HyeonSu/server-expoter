# server-exporter 다음 작업 (NEXT_ACTIONS)

> **본 파일**: 진정 active PENDING 만 유지 (rule 70 R5 / R6 / R7 cycle 자문 정책).
> **lab 매트릭스**: `docs/ai/catalogs/LAB_PENDING_MATRIX.md` (8 vendor × generation × 4 column).
> **archive**: `docs/ai/archive/NEXT_ACTIONS-history-2026-04-to-05.md` (OPS-* + cycle-013/014/015/016 잔여).
> **마지막 정리**: 2026-05-29 (audit-cleanup cycle).

---

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

### 2.4 HBA / InfiniBand 사이트 fixture (lab 부재 — cycle 2026-05-29)

- **trigger**: FC HBA / IB HCA 보유 사이트 BMC/OS/ESXi 접근
- **항목**:
  - FC HBA 보유 Dell/HPE/Lenovo/Cisco BMC → Redfish `storage.hbas` 실측 fixture + baseline (현 4 redfish baseline 은 FC 미보유로 빈)
  - FC HBA 보유 Windows/Linux 호스트 → `Get-InitiatorPort`+`MSFC_*` / sysfs 실측 (현 ubuntu/windows/rhel baseline 빈)
  - IB HCA (Mellanox/NVIDIA) 보유 호스트 → Linux ibstat/sysfs 실측 (IB 정본 채널)
  - ESXi FC SAN 호스트 → vmhba FC speed/wwnn 실측 (현 esxi_baseline 은 offline FC 2)
- **ESXi esxcli-over-SSH fallback (D1-B 재평가)**: SSH 활성 운영·보안 결정 시 `esxcli storage san fc list` / `rdma device list` 보강
- **절차**: `capture-site-fixture` skill + rule 13 R4 (실측 baseline) + EXTERNAL-CONTRACTS 갱신

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
