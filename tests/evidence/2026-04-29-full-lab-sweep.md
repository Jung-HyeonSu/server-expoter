# Full Lab Sweep — 2026-04-29

> production-audit (2026-04-29) + cycle-016 직후 실 lab 18대 전수 회귀 + JSON envelope 13 필드 검증.
> Jenkins master 10.100.64.152 (운영) / Job: hshwang-gather / Agent: jenkins-agent-ops (10.100.64.154) / loc: ich.

## 0. 결론 요약

| 항목 | 결과 |
|---|---|
| **빌드 결과** | **3/3 SUCCESS** (redfish #114 / os #115 / esxi #116) |
| **Envelope 13 필드 정합** | **18/18 PASS** (rule 13 R5) |
| **Host 단위 status** | **17 success / 0 partial / 1 failed** |
| **차단된 lab 4대** | 사전 식별 (Win10 WinRM / Cisco-down 2 / AMI-vendor 모호) |
| **신규 발견 drift** | 1건 (rule 13 R5 example value drift) |
| **신규 발견 사고** | 1건 (Dell R740 10.50.11.162 인증/연결 실패) |

**판정**: production-audit 후 lab 환경의 main branch 빌드 안정적. 공통 JSON envelope (13 필드) 정합 100%. 단 Dell R740 1대 follow-up 필요.

## 1. 목적

| 검증 | 정본 | 결과 |
|---|---|---|
| 1. Lab 18대 gather 실행 가능 여부 | hshwang-gather Jenkinsfile (4-Stage) | 3/3 빌드 SUCCESS |
| 2. 문제 (errors / failed sections) 식별 | callback `errors` + `sections` | 1 host failed (Dell R740) |
| 3. 공통 JSON envelope (rule 13 R5) 13 필드 정합 | `common/tasks/normalize/build_output.yml` + 채널 `inject schema_version` | 18/18 envelope PASS |

## 2. Lab Inventory

> 출처: `tests/evidence/2026-04-28-reference-collection.md` + `tests/scripts/targets.sample.json` + `_inventory.json`.

| 채널 | 활성 | 차단 | 비고 |
|---|---|---|---|
| Redfish | 9대 (Dell×6 / HPE×1 / Lenovo×1 / Cisco×1) | 3 (Cisco-2 down + AMI vendor 모호) | F2/F3 |
| OS | 6대 (RHEL bare + RHEL 8.10/9.2/9.6 + Rocky 9.6 + Ubuntu 24.04) | 1 (Win10 WinRM) | F4 |
| ESXi | 3대 (.1/.2/.3) | 0 | F5 |
| **합계** | **18** | 4 | — |

상세 host list: `_inventory.json` 참조.

## 3. 빌드 실행 결과

| 채널 | Build # | Result | Duration | Hosts | 비고 |
|---|---|---|---|---|---|
| Redfish | #114 | SUCCESS | 561.2s | 9 | 8/9 host success |
| OS | #115 | SUCCESS | 64.1s | 6 | 6/6 host success |
| ESXi | #116 | SUCCESS | 29.6s | 3 | 3/3 host success |

> Jenkinsfile 4-Stage 모두 통과 (Validate / Gather / Validate Schema / E2E Regression).
> 자세한 console: `_console_redfish.txt` (154KB) / `_console_os.txt` (54KB) / `_console_esxi.txt` (39KB).

## 4. JSON Envelope 13 필드 검증

### 4.1 13 필드 정의 (rule 13 R5)

```
target_type, collection_method, ip, hostname, vendor,
status, sections, diagnosis, meta, correlation, errors, data,
schema_version
```

타입:
- str: target_type, collection_method, ip, hostname, status, schema_version
- str | null: vendor
- dict: sections, data
- dict | null: diagnosis, meta, correlation
- list: errors

상태 enum: `success | partial | failed`.

### 4.2 검증 결과

| 채널 | Envelopes 발견 | Expected | 13 필드 PASS | 13 필드 FAIL | Missing IPs | Extra IPs |
|---|---|---|---|---|---|---|
| Redfish | 9 | 9 | 9 | 0 | 0 | 0 |
| OS | 6 | 6 | 6 | 0 | 0 | 0 |
| ESXi | 3 | 3 | 3 | 0 | 0 | 0 |
| **합계** | **18** | **18** | **18** | **0** | **0** | **0** |

상세: `_envelope_verification.json`.

## 5. Per-Host Status / 문제 식별

### 5.1 Redfish (9대)

| IP | Vendor | Status | Sections (success / failed / not_supported) | Errors | Hostname |
|---|---|---|---|---|---|
| 10.100.15.27 | dell | [OK] success | 8 / 0 / 2 (system, users) | 0 | r760-1.gooddi.lab |
| 10.100.15.28 | dell | [OK] success | 8 / 0 / 2 | 0 | r760-2.gooddi.lab |
| 10.100.15.31 | dell | [OK] success | 8 / 0 / 2 | 0 | r760-3.gooddi.lab |
| 10.100.15.33 | dell | [OK] success | 8 / 0 / 2 | 0 | r760-5.gooddi.lab |
| 10.100.15.34 | dell | [OK] success | 8 / 0 / 2 | 0 | r760-6.gooddi.lab |
| 10.50.11.231 | hpe  | [OK] success | 8 / 0 / 2 | 0 | test0004.hynix.com |
| 10.50.11.232 | lenovo | [OK] success | 8 / 0 / 2 | 0 | XCC-7Z73-J30AF7LC |
| 10.100.15.2  | cisco | [OK] success | 8 / 0 / 2 | 0 | C220-FCH2116V1V0 |
| **10.50.11.162** | **dell** | **[NG] failed** | **0 / 9 / 1** | **1** | (resolution failed — IP만) |

### 5.2 OS (6대)

| IP | Distro hint | Status | Sections (success / fail / ns) | Errors | Hostname |
|---|---|---|---|---|---|
| 10.100.64.96  | RHEL bare-metal | [OK] success | 6 / 0 / 4 | 0 | r760-6 |
| 10.100.64.161 | RHEL 8.10 (raw fallback) | [OK] success | 6 / 0 / 4 | 0 | localhost |
| 10.100.64.163 | RHEL 9.2 | [OK] success | 6 / 0 / 4 | 0 | localhost.localdomain |
| 10.100.64.165 | RHEL 9.6 | [OK] success | 6 / 0 / 4 | 0 | localhost.localdomain |
| 10.100.64.169 | Rocky 9.6 | [OK] success | 6 / 0 / 4 | 0 | localhost.localdomain |
| 10.100.64.167 | Ubuntu 24.04 | [OK] success | 6 / 0 / 4 | 0 | gathertest-ubuntu2404 |

### 5.3 ESXi (3대)

| IP | Status | Sections (success / fail / ns) | Errors | Hostname |
|---|---|---|---|---|
| 10.100.64.1 | [OK] success | 6 / 0 / 4 | 0 | esxi01 |
| 10.100.64.2 | [OK] success | 6 / 0 / 4 | 0 | esxi02 |
| 10.100.64.3 | [OK] success | 6 / 0 / 4 | 0 | esxi03 |

> 상세: `_problem_summary.txt` / `_problem_analysis.json`.

## 6. 발견 사항

### 6.1 [DRIFT 후보] rule 13 R5 example value vs 실제 코드 enum

- **rule 13 R5 example**: `"sections": { "system": "supported", "cpu": "not_supported", ... }`
- **실제 코드 enum** (`common/tasks/normalize/build_sections.yml` line 13): `success | failed | not_supported`
- **영향**: rule 23 / 검증 도구 / 문서 reader 혼동 가능. 회귀에는 영향 없음 (envelope 13 필드 정합 PASS, sections dict 자체는 모두 dict 타입)
- **분류**: rule 70 R8 trigger 1 (rule 본문 의미 변경) 해당 — but 본 sweep은 코드 변경 아닌 발견. drift 등록만.
- **후속**: `docs/ai/catalogs/CONVENTION_DRIFT.md`에 DRIFT entry append + rule 13 R5 example 정정 (별도 PR)

### 6.2 [SITE 사고] Dell R740 (10.50.11.162) 인증/연결 실패

- **현상**:
  - status=failed, 9 sections all failed, errors 1건
  - error message: "Redfish 수집 완전 실패 — BMC 연결 또는 인증 문제. BMC IP/포트(443) 접근, 방화벽 규칙, Redfish 서비스 활성화 여부, 자격증명(vault)을 확인하세요."
  - hostname resolution도 실패 (envelope의 hostname=ip 그대로)
  - diagnosis.precheck = null, diagnosis.details에 adapter_candidate / channel / checked_ports / product / redfish_version / selected_port / systems_uri 키만
- **원인 후보**:
  1. R740 자격증명이 R760의 root/__REDACTED__와 다름 (`vault/<loc>/redfish/dell.yml` 단일 자격이라 R740만 다른 자격이면 실패)
  2. R740 BMC 환경 (방화벽 / Redfish off / 모델 차이)
  3. R740 펌웨어 버전 차이 (iDRAC9 vs iDRAC8)
- **확인 필요** (rule 96 R2 — 외부 계약 디버깅 시 사용자 질의 우선):
  - R740 (10.50.11.162) BMC 자격증명 (root vs admin vs other)
  - 가능하면 펌웨어 버전 + Redfish 활성화 상태
- **rule 95 R1 #11 (외부 계약 drift) 가능성**: R740 펌웨어가 우리 dell adapter (iDRAC9) range 외일 수 있음
- **분류**: site 환경 + 외부 계약. server-exporter 코드 변경 불필요 (현재로서는)

### 6.3 [INFO] Section 분포 패턴

- **Redfish 8 success / 2 not_supported**: 모든 vendor에서 `system` (OS), `users` 2개가 not_supported. 정상 — Redfish가 OS는 못 봄, users는 vendor별 capability matrix 영향
- **OS 6 success / 4 not_supported**: bmc / firmware / users / power 4개 not_supported. 정상 — OS gather 영역 외
- **ESXi 6 success / 4 not_supported**: 동일 패턴, ESXi 영역
- 5 vendor 모두 동일 패턴 → schema/sections.yml + adapter capabilities 일관성 PASS

### 6.4 [INFO] ESXi vendor 표기

- ESXi 3대 모두 `vendor=cisco` — 물리 서버가 Cisco UCS C220 추정. ESXi-on-Cisco-UCS는 정상 (vendor 정규화는 host hardware 기반)

## 7. 환경

| 항목 | 값 |
|---|---|
| Jenkins | 2.541.2 (master 10.100.64.152, ubuntu 24.04.4) |
| Agent | jenkins-agent-ops (10.100.64.154, labels: ich/chj/yi/git) |
| Repo branch | main |
| Commits | production-audit (2026-04-29) + cycle-016 + cycle-015 grafana 제거 직후 |
| Vault | server-gather-vault-password (Jenkins credentials store) |
| Java / Ansible | OpenJDK 21.0.10 / `/opt/ansible-env/` venv |

## 8. 후속 작업

| # | 작업 | 우선순위 | 차단 사유 |
|---|---|---|---|
| F-A | rule 13 R5 example value 정정 (`"supported"` → `"success"`) + DRIFT entry | LOW | 사용자 PR 검토 (rule 70 R8 trigger 1) |
| F-B | Dell R740 (10.50.11.162) 자격증명 / BMC 상태 사용자 확인 | MED | 외부 환경 (rule 96 R2) — site 점검 필요 |
| F-C | (선택) `vault/<loc>/redfish/dell.yml`을 host별 자격 분리 구조 검토 | LOW | F-B 결과 기반 |
| F-D | (이전 reference-collection의 잔여) Cisco down 2대 / Win10 WinRM 환경 | LOW/MED | site/사용자 결정 |

## 9. 부속 파일

| 파일 | 용도 |
|---|---|
| `2026-04-29-full-lab-sweep/_inventory.json` | 18대 lab 장비 + 4대 차단 정보 |
| `2026-04-29-full-lab-sweep/_runner_ssh_check.py` | master/agent SSH probe |
| `2026-04-29-full-lab-sweep/_runner_jenkins_discover.py` | Jenkins URL/version/anonymous 권한 확인 |
| `2026-04-29-full-lab-sweep/_runner_jenkins_auth.py` | cloviradmin 인증 + jobs 목록 |
| `2026-04-29-full-lab-sweep/_runner_jenkins_jobinfo.py` | 3 gather job 파라미터 + 마지막 빌드 |
| `2026-04-29-full-lab-sweep/_runner_jenkins_nodes.py` | agent label 매핑 |
| `2026-04-29-full-lab-sweep/_runner_trigger_sweep.py` | 3 채널 sequential trigger + 결과 수집 |
| `2026-04-29-full-lab-sweep/_runner_envelope_verify.py` | 13 필드 정합 검증 |
| `2026-04-29-full-lab-sweep/_runner_problem_analysis.py` | per-host status / errors / sections 분석 |
| `2026-04-29-full-lab-sweep/_runner_status_check.py` | 빌드 진행 폴링 |
| `2026-04-29-full-lab-sweep/_jobinfo.json`, `_nodes.json` | 발견 결과 |
| `2026-04-29-full-lab-sweep/_console_redfish.txt`, `_console_os.txt`, `_console_esxi.txt` | 빌드 console 전체 |
| `2026-04-29-full-lab-sweep/_sweep_summary.json` | 빌드 결과 요약 |
| `2026-04-29-full-lab-sweep/_envelope_verification.json` | per-host 13 필드 검증 결과 |
| `2026-04-29-full-lab-sweep/_problem_analysis.json`, `_problem_summary.txt` | per-host 문제 분석 |
| `2026-04-29-full-lab-sweep/_trigger_log.txt` | trigger 실행 로그 (561s + 64s + 30s 진행) |
| `2026-04-29-full-lab-sweep/_inspect.txt` | 검증 중 sections 값 enum 인스펙션 |

## 10. 관련 문서

- rule 13 (output-schema-fields), 20 (output-json-callback), 31 (integration-callback), 80 (ci-jenkins-policy), 96 (external-contract-integrity)
- `docs/contract/02-output-envelope.md`, `docs/operate/04-pipeline-runtime.md`
- 정본: `common/tasks/normalize/build_output.yml`, `common/tasks/normalize/build_sections.yml`
- 이전 cycle-015 cleanup (grafana 파이프라인(제거됨) 제거), production-audit (2026-04-29)
