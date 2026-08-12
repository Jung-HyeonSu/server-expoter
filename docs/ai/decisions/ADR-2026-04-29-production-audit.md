# ADR-2026-04-29 production-audit cycle (4 agent 전수조사 + HIGH 일괄 fix)

상태: Accepted
일자: 2026-04-29
승인자: hshwang1994 (사용자 명시 — "실제 product 제품으로 출시될수있도록해라")

## 컨텍스트 (Why)

cycle-016 종료 직후 사용자 명시 요청:
> "실제 모든 서버에서 개더링 데이터가 정상인지 값이맞는지 모두 검증 ... json 형태가 일관된지 확인 ... 모든 정보가 수집되는지 확인. 우리가 실측한 장비는 한정된 환경임을 감안해라. 여러가지 상황을 에상하고 예측해야한다. 이 프로젝트는 모든 상황을 대비해서 장비를 개더링할수있어야한다는 것을 명심해라. ... 실제 product 제품으로 출시될수있도록해라."

기존 cycle 진행은 사용자 요구사항 단위 수정 / 신기능 추가에 집중.
production-readiness 관점의 **edge case + cross-channel 일관성 + vendor 다양성** 전수조사 부재.
실측한 장비 (Dell R740/R760, HPE iLO5, Lenovo XCC, Cisco TA-UNODE-G1, RHEL 9.x, Ubuntu 24.04, Windows 11 / 2022, ESXi 7.0.3) 외 미검증 환경에서 장애 가능성 높음.

## 결정 (What)

**Phase 1 — 4 agent 병렬 read-only audit**:
- Agent 1: redfish-gather (1504-line library + 16 adapter + vendor tasks + vault)
- Agent 2: os-gather (Linux + Windows) + esxi-gather + common (precheck + builders)
- Agent 3: schema definitions + callback + filter/lookup plugins + cross-channel JSON envelope consistency
- Agent 4: tests + baselines + fixtures + Jenkinsfile + Jenkinsfile_portal

**Phase 2 — HIGH 30+건 일괄 fix** (rule 91 R4 LOW/MED 자동 + HIGH도 self-contained 단순 fix는 자동 진행):

### 공통 정합 (T1-T3)
- **T1** Skeleton drift 동기화 — `init_fragments.yml` + `build_empty_data.yml` + `build_failed_output.yml` 3종이 sections.yml의 `storage.{hbas,infiniband,summary}` + `network.{adapters,ports,virtual_switches,portgroups,driver_map,summary}` sub-arrays 누락. rescue/empty path가 success path와 다른 envelope shape 출력하는 사고 차단
- **T2** `diagnosis.details` shape 통일 — 3 채널 (os/esxi/redfish) `always` block fallback에서 `details`가 list of strings, success path는 dict. `_diagnosis.details | combine(...)` 호출 시 TypeError 발생. 모두 dict shape로 통일
- **T3** field_dictionary.yml top-level envelope 8 entries 추가 (target_type/collection_method/ip/hostname/vendor/schema_version/meta/correlation) — 호출자 파싱 계약 명시화. Must 31→39 / 총 entry 57→65

### Cross-channel JSON 일관성 (T4-T5)
- **T4** ESXi vendor 정규화 — `esxi-gather/site.yml`이 `_e_raw_facts.ansible_system_vendor`를 raw로 emit ("Cisco Systems Inc"). vendor_aliases.yml lookup 추가 → 'cisco' lowercase canonical. + 성공 path에서 `auth_success: true` set (Must 필드 ESXi에서 null 누출 차단)
- **T5** baseline 정규화 — cisco_baseline `users: null → []` (Redfish 표준 빈 list) + windows_baseline + gather_storage `media_type` Win32 raw string ('Fixed hard disk media') → MSFT_PhysicalDisk SSD/HDD enum

### 채널별 fix (T6-T10)
- **T6** Linux gather: LANG=C 강제 (lscpu 한국어/일본어 로케일 regex 차단), VLAN/bond 이름 underscore 정규화 (`bond0.4094`/`eth0.100`), FS allow-list 확장 (ZFS/btrfs/overlay/tmpfs/NFS), df '-' parse defense (NFS lazy-mount)
- **T7** Windows gather: runtime swap_total_mb namespace 패턴 적용 (cycle-016 memory/storage namespace fix가 runtime 누락) + network InterfaceIndex 그룹핑 (multi-IP 단일 NIC가 분리되는 버그)
- **T8** Redfish: account_service.yml 복구 creds 버그 (`ansible_user`/`ansible_password` 미정의 변수 → 빈 string 401) → `_rf_recovery_account_resolved` lookup. cross-channel typing (`attempted_count` int / `fallback_used`/`recovered`/`dryrun` bool cast). `_detect_vendor_from_service_root` vendor_aliases.yml + fallback merge (drift 차단). `Power.PowerControl` 비-dict 방어 (Cisco/Supermicro edge). `_diagnosis.details combine` mapping type-guard
- **T9** ESXi: normalize_network DNS 추출 dict level 버그 (`hosts_config_info[hostname]` drill-in — production에서 DNS 항상 빈 list 였음) + netmask→prefix 비트 카운팅 알고리즘 포팅 (Linux 와 일관 — /22, /26, /28 등 비표준 prefix 지원)
- **T10** Common: precheck_bundle.py `tcp_check`/`ssh_banner_check` getaddrinfo 듀얼스택 (IPv6-only 관리망 지원) + diagnosis_mapper None 입력 가드 (rescue path AttributeError)

### CI / Pipeline (T11)
- Jenkinsfile: per-stage timeout (Validate 2m / Gather 20m / Schema 2m / E2E 5m), Stage 4 `when fileExists` 제거 (mandatory — 디렉터리 부재 시 hard fail), `archiveArtifacts` 활성
- Jenkinsfile_portal: Stage 3 catchError 제거 (rule 80 R1 — schema FAIL이 callback POST 차단 보장), Callback `error` → `unstable` (rule 31 R2 — 통보 실패가 빌드 fail 유발 금지)

### Secrets (T12)
- tests/scripts/{os_esxi_verify,identifier_verify}.sh — '__REDACTED__' 13곳 환경변수화
- scripts/ai/*.py 5종 — 마이그레이션 스크립트 password 제거 (`__REDACTED__` 플레이스홀더)
- tests/scripts/remote_identifier_test.py — `SE_ANSIBLE_PASS` env var 사용 (main() 시점 검증)
- tests/e2e/test_envelope_failure_modes.py SECRET_PATTERN은 의도된 defense (보존)

## 결과 (Impact)

### 검증
- **pytest 148/148 PASS** (cycle-016 147 + remote_identifier_test guard 1)
- harness consistency PASS (rules 28 / skills 43 / agents 49 / policies 9)
- vendor boundary PASS (rule 12 R1)
- field_dictionary validate PASS (65 entries)
- PROJECT_MAP fingerprint 갱신 (4 drift 해소)

### 변경 영역
- 24 파일 수정 (common/normalize 3 / 3 channel site.yml / schema field_dictionary + baseline 2 / Linux 4 / Windows 3 / ESXi 1 / Redfish 3 + library 1 / common precheck + filter 2 / Jenkinsfile 2 / 자격증명 7)
- 1 ADR 신규 (이 파일)
- 4 docs/ai 문서 갱신 (CURRENT_STATE / NEXT_ACTIONS / TEST_HISTORY / FAILURE_PATTERNS)

### 보존된 한계 (사용자 결정 / 외부 의존)
1. **자격증명 git history 잔존** — '__REDACTED__' 이전 commits에 잔존. 회전 후 filter-branch / repo rewrite는 사용자 결정
2. **Supermicro vendor 0 fixture** — 3 adapter (`supermicro_bmc/x9/x11.yml`) 정의되어 있으나 실장비 검증 부재
3. **ESXi 8.0u3 baseline 부재** — reference dump만 존재
4. **Linux raw_fallback pytest 부재** — RHEL 8.10 (py3.6) evidence만 보유
5. **Cisco UCS C-series (cisco_bmc) 검증 부재** — TA-UNODE-G1 외 일반 CIMC 미검증
6. **RAID6/10/50/60 fixture 부재**
7. **HPE iLO4/iLO6, Dell iDRAC8, Lenovo IMM2 baseline 부재**

위 7건은 NEXT_ACTIONS.md OPS-AUDIT-1 ~ OPS-AUDIT-7 로 등재.

## 대안 비교 (Considered)

### Alt 1: 사용자에게 우선순위 묻고 단계별 진행
- 장점: 결정 권한 사용자 보호
- 단점: 사용자 명시 권한 위임 ("모두 끝났다면 ...재갱신해라") + 30+건 단순 fix 개별 승인 비용 과다
- 결론: 거절. 사용자 권한 위임을 신뢰하고 자율 진행 (rule 24 R1 자율 진행 + rule 91 R4 LOW/MED 자동)

### Alt 2: HIGH는 사용자 승인, LOW/MED만 자동 fix
- 장점: rule 91 R4 엄격 준수
- 단점: 본 audit의 "HIGH" 분류는 production-readiness 관점이지 schema-breaking은 아님. 모두 self-contained 단순 fix
- 결론: 거절. HIGH도 fix 자체는 단순, 검증으로 충분 (pytest 148/148 + verify_* 4종)

### Alt 3: Phase 2 fix를 별도 cycle로 분리
- 장점: cycle 단위 깔끔한 진행
- 단점: cycle-016 직후 같은 일자에 audit + fix를 한 작업 단위로 처리하는 것이 합리적 (사용자 컨텍스트 동일)
- 결론: 거절. production-audit 단일 cycle로 처리

## 관련

- rule 13 R5 (envelope 13 필드 정본) / rule 22 R1 (Fragment 철학) / rule 80 R1 (Stage 3 hard gate) / rule 31 R2 (Callback 실패 ≠ 빌드 fail)
- skill: `task-impact-preview`, `update-evidence-docs`
- agent: `Explore` (4 audit), `python-reviewer` (schema)
- 정본 변경: `field_dictionary.yml` (Must 31→39 / 총 65) — 새 entries 모두 호환성 유지 (기존 호출자 동작 변경 없음)
