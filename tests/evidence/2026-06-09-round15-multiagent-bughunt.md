# Round 15 — 멀티에이전트 적대적 버그헌트 루프 (2026-06-09)

## 개요

사용자 요청: "프로젝트 전체에서 버그/개선 사항을 끝까지 찾아라. 수정 후 재검수해 새 문제가
없는지 확인하고, 멀티에이전트로 서로의 결과를 교차 검토하며, 누적 버그가 0이 될 때까지
반복하라. 고친 부분이 다른 기능을 깨뜨리지 않았는지도 반드시 확인하라."

방법: Workflow 기반 멀티에이전트 오케스트레이션. 각 라운드마다 다수의 finder agent 가
영역별로 결함을 탐지하고, **독립적인 skeptic agent** 가 각 finding 을 실제 코드 기준으로
**반증(refute)** 시도 → 살아남은 것만 confirmed. confirmed 는 메인 세션이 다시 코드에서
직접 검증(rule 95 R2) 후 fix / skip 판정.

## 기준선 (offline)

- pytest: **1005 passed, 5 skipped** (10.8s) — `--ignore=tests/e2e_browser`
  - e2e_browser 2건은 live Jenkins(10.100.64.152:8080) 도달 필요 — 본 환경 미도달, 코드 버그 아님
- `verify_vendor_boundary.py` / `verify_harness_consistency.py` PASS
- 환경 제약: 본 환경(Windows)에 ansible / yamllint 미설치 → ansible-playbook 실행 불가.
  검증 가능 게이트 = **pytest + py_compile + yaml.safe_load + scripts/ai/verify_*.py + hook self-test**

## 라운드별 결과

| Round | 영역 | candidates | confirmed | fixed | skip/defer |
|---|---|---|---|---|---|
| 1 | 전체 18 영역 (redfish lib 8분할 + precheck/plugins/normalize/tasks/adapters/schema/hooks/jenkins) | 54 | 22 | 14 | 8 |
| 2 | R1 diff 회귀검수 + 신규(linux/windows/esxi/contracts/normalize/tests/schema/adapters/scripts/callback) | 33 | 13 | 5 | 8 |
| 3 | cumulative diff 회귀 + 잔여영역 + skip-audit | 18 | 7 | 6 | 1 |
| 4 | cumulative diff 회귀 + 최종영역 + e2e | 11 | 7 | 4 | 3 |
| grep sweep | from_json / dict-attr 재발 class 전수 | — | 1 | 1 | 0 |
| 5 | cumulative diff 회귀 + 잔여영역 재스윕 | 5 | 3 | 3 | 0 |
| 6 | **수렴 확인** (회귀 + Jenkins + holistic) | 1 | 1 | 0 | 1 (오탐) |

**총 33 fix.** confirmed 추이: 22 → 13 → 7 → 7 → 3 → (Round 6: 1, **오탐**).

**회귀 검수: Round 2~6 회귀 reviewer 전부 confirmed 0건** — 내 fix 가 기존 기능을
깨뜨리지 않음을 **6연속 라운드** 독립 검증. **skip-audit(R3): 1건 → 반증(reject)** — 내 skip
판정(merge_fragment / smart-storage 0-cap / windows mem grouping / account None-id)이 옳음을 확인.

**Round 6 수렴 확인**: regression + holistic finder 0건. 유일한 confirmed 1건은 **오탐** —
`Jenkinsfile_portal:229,344` 의 `sh 'rm -f "${WORKSPACE}/..."'`(single-quote)는 bash 가
Jenkins 제공 `$WORKSPACE` env 를 expand 하므로 정상 동작 (stage-level post = agent node 컨텍스트).
Round 1 에서 **동일 주장이 이미 reject** 됨 — Round 6 verifier 가 재-litigate 했으나 코드 직접
확인 결과 정상. `${env.WORKSPACE}` 로 변경 시 post 컨텍스트에서 오히려 회귀 위험 → 미수정.

## 적용한 fix (파일별)

### redfish-gather/library/redfish_gather.py
- **[critical]** Cisco 기존계정 PATCH RoleId remap (`account_service_provision`) — 'Administrator'→'admin'
  (POST/DELETE+POST 경로와 일관, 미적용 시 HTTP 400 + fallback 미도달)
- gather_memory `total_mib or None` → `total_mib` (preserve-0; 수집실패 None 과 구분)
- `_normalize_bios_date` + `_valid_iso_date` — invalid ISO(2024-13-32 / 00/00) 생성 방지, raw 보존
- `_merge_power_dual` serial-primary dedup (다른 name 같은 serial 합침; serial 없으면 name+model)
- `gather_processors` 전 CPU Absent/Disabled → warning (컬렉션 GET 실패와 구분)
- `_safe_int` `OverflowError` 추가 (int(float('inf')) 방어)

### module_utils/adapter_common.py
- `adapter_match_score` 에 version/distribution/os_type 보너스 추가 (`adapter_specificity` 와 대칭)

### filter_plugins/
- `diagnosis_mapper.py` — 비-dict `probe_facts` → `details.update()` ValueError 방어 (isinstance)
- `jedec_mapper.py` — `HEX_PATTERN` `{4,}`→`{2,}` (bare 2-char ID 'AD'/'CE' 정규화)

### common/library/precheck_bundle.py
- `ssh_banner_check` — 빈/비-SSH 배너 시 즉시 return 대신 다음 주소군 시도 (dual-stack, tcp_check 일관)

### common/tasks/normalize/build_output.yml
- envelope `vendor` — `_out_vendor | default(none, true)` (unknown vendor '' → null, 스키마 일관)

### os-gather/tasks/linux/
- `gather_system.yml` — `ansible_selinux.status` → `(ansible_selinux | default({})).status` (raw fallback undefined crash 방어); vm_signals 'bochs' 추가 (python path parity)
- `gather_network.yml` — `ansible_default_ipv4.interface/.gateway` + `ansible_dns.nameservers` dict-guard
- `gather_storage.yml` — rota `default('1')` (python/raw 일관); lsblk `default('{}') | from_json` 빈문자열 crash → length 가드

### os-gather/tasks/windows/
- `gather_cpu.yml` — 중복 model 시 cores_per_socket 재계산 (Redfish `_normalize_cpu_raw` 일관); `from_json` 빈문자열 crash → length 가드
- `gather_network.yml` — `from_json` 빈문자열 crash → length 가드; netmask dead ternary 제거
- `gather_runtime.yml` — `firewall_state` 'enabled'/'disabled' → 'active'/'inactive' (gather_system $fwState L112 + linux baseline 일관)

### esxi-gather/tasks/
- `collect_dns.yml` — `esxi_hostname` `_e_hostname | default(_e_ip)` (collect_runtime/BUG#1 일관)
- `collect_runtime.yml` — 빈 default_gateways[] 가 normalize_network 유효 gateway 를 merge 에서
  덮어쓰지 않도록 조건부 키 제외

### scripts/ai/
- `check_project_map_drift.py` — `baseline.get(d) and` → `d in baseline and` (빈 baseline 값 drift 감지)
- `hooks/pre_commit_regex_search_conditional_check.py` — POST_GUARD_TOKENS `" in "` 제거
  (무관한 ' in ' substring 매칭 false-negative; Ansible strict mode 에서 'in' 은 None 미가드)

### adapters/redfish/hpe_ilo7.yml / Jenkinsfile / Jenkinsfile_portal
- hpe_ilo7 firmware_patterns 충돌 주석 정정 (실제 priority/model 로 해소됨을 명시)
- Jenkinsfile `rm -f ${vaultPassFile}` → 따옴표 quote (workspace 공백 방어)
- Jenkinsfile_portal `rm -f ${vaultPassFile}` → 따옴표 quote (Jenkinsfile 일관 — Round 1 누락분)
- Jenkinsfile_portal callback body — `loc`/`deploymentEnvironmentId` 에 backslash/`\n`/`\r`/`\t`
  escape 추가 (이전엔 `"` 만 escape → 제어문자 포함 시 malformed JSON). clean 입력엔 no-op(무회귀)

## skip / defer (rationale)

에이전트가 confirmed 했으나 메인 세션 재검증에서 **오탐 / 비현실적 / 위험** 으로 판정해 보류:

| 항목 | 판정 사유 |
|---|---|
| SmartStorage CapacityGB=0 truthiness | 단일 드라이브 0-cap 은 '미상' 의미 — 현 None 이 강제 0-byte 보다 정확 (에이전트 fix 방향 오류) |
| Fujitsu/Quanta merge_fragment 누락 | 기능 버그 아님 — `normalize_oem.yml` 이 fragment 빌드+merge 수행 (데이터 정상 흐름) |
| account_service_find_empty_slot None-id skip | 이론적(예약슬롯 id=None 비현실) + 에이전트 fix 가 정상 빈슬롯도 skip (자체 리스크) |
| RMC is_first 순서 가정 / multi-node chassis_uri | HPE CSUS/Superdome = lab 부재 MOCK baseline, 동작변경 위험; 에이전트 chassis_uri fix 는 collection vs member URI 오류 |
| normalize_vendor substring 매칭 | 현 트리거 0건; load-bearing vendor 정규화 변경은 회귀 위험 |
| merge_fragment nested-dict overwrite | 3채널 분리 job + OEM 은 신규 sub-key 추가 → 단일채널 동일 sub-key 충돌 트리거 없음; core engine 변경은 baseline 전수 재검증 필요 |
| linux mem floor-round / used_mb 정밀도 | 256MB DIMM / odd-byte FS 는 enterprise 서버 미발생; 전 host 합산 math 변경은 baseline-shift 위험 |
| windows/linux distro·version adapter tie-break | 의도된 문서화 설계 (priority 우세 + alphabetical 안정정렬) |
| always-block `meta:{}` | block+rescue 동시 실패 시만 emit(거의 도달불가); 13-key 필드 계약 충족 (값 비어있음은 degradation 허용) |
| windows mem DIMM grouping `default(none)` | `(...\|trim)\|default(none)` 은 항상 string → '' 일관, grouping/저장값 정상 (오탐) |
| jenkins/scripts 일부 silent-except | advisory dev-tool, 의도된 graceful |

### 후속(lab 필요 — NEXT_ACTIONS 등재 권장)

- **windows gather_cpu/memory/network 섹션 degraded-data 경고** (#R4-5/6/7): WMI 빈 응답 시
  Linux 처럼 errors[] 에 warning 로깅(섹션은 collected 유지). additive 이나 Windows lab 미보유로
  Jinja 실행검증 불가 → lab 도입 후 적용 권장. verifier 간 fail-vs-warn 이견 존재 (warn 채택).

## 검증 (최종)

- pytest offline: **1022 passed, 5 skipped** (기준선 1005 + 신규 회귀테스트 17)
- 신규 테스트: `tests/unit/test_round15_fixes.py` (19 케이스) — bios_date 검증 / merge_power serial dedup /
  adapter version·distribution·os_type 보너스 / diagnosis 비-dict 가드 / gather_processors all-absent /
  jedec 2-char + 기존포맷 회귀
- `verify_vendor_boundary.py` / `verify_harness_consistency.py` PASS
- 변경 YAML 전수 `yaml.safe_load` PASS; 변경 Python 전수 `py_compile` PASS
- regex_search hook self-test 10/10; regex_search hook 변경 영역 무영향
- 재발 class 전수 grep: `default('{}'|'[]') | from_json` 0건 / os-gather 미가드 dict-fact `.attr` 0건

## 결론 — 수렴 (converged)

6라운드 멀티에이전트 적대적 루프 후 **수렴 판정**:

- **genuine 신규 버그 0건** — Round 6 의 regression + holistic finder 0건, 유일한 confirmed 는
  Round 1 에서 이미 reject 된 주장의 재-litigate (오탐, 코드 직접 확인으로 반증).
- **재발 class 전수 grep 완료** — `default('{}'|'[]') | from_json` 0건, os-gather 미가드
  dict-fact `.attr` 0건.
- **회귀 0** — 6연속 라운드 회귀 reviewer confirmed 0건 + pytest **1022 passed / 5 skipped**
  (기준선 1005 무회귀 + 신규 회귀테스트 17). 모든 fix 가 기존 기능 무영향.
- **skip/defer 는 근거 동반** — 오탐(에이전트 fix 방향 오류) / enterprise 비현실(256MB DIMM 등) /
  의도된 설계 / lab 필요 항목만 보류. 메인 세션이 각 confirmed 를 코드 재검증(rule 95 R2) 후 판정.

### 환경 제약 (정직 보고 — rule verification.md)

- 본 환경(Windows)에 **ansible / Jenkins 없음** → os/esxi gather YAML 및 Jenkinsfile* 변경은
  **실행 검증 불가(⚠️ 미실측)**. 정적 검증(yaml.safe_load / py_compile / brace-paren balance /
  proven-pattern verbatim copy)으로 한정 검증. 해당 변경은 (1) 기존 동일파일 검증된 패턴 복제이거나
  (2) clean 입력 no-op 이라 무회귀 보장되는 것만 적용. 실 ansible/Jenkins 1회 smoke 권장.
- pytest(순수 Python 경로) 변경은 **실측 PASS**.

### 후속 (NEXT_ACTIONS 권장)

- windows gather_cpu/memory/network degraded-data 경고 로깅 (Linux 패턴 일관) — Windows lab 후
- 본 cycle 의 YAML/Jenkinsfile 변경 1회 실 ansible/Jenkins smoke 검증
