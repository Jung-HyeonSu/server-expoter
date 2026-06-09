# Round 17~20 — 멀티에이전트 적대적 버그헌트 수렴 루프 (2026-06-10)

## 개요

사용자 요청: "프로젝트 전체에서 버그/개선점을 깊게 점검하라. 한 번 고치고 끝내지 말고 수정 후
다시 검수해 새로 생긴 문제·놓친 문제까지 찾아라. 멀티에이전트로 서로의 결과를 교차 검토하고,
더 이상 문제가 없을 때만 완료로 판단하라. 누적 버그 0 + 수정으로 인한 추가 문제 없음이 검증된
경우에만 완료."

방법: Workflow 기반 멀티에이전트 오케스트레이션. 각 Round 마다 영역별 finder agent 가 결함을
탐지하고 **독립 skeptic agent** 가 각 finding 을 실제 코드로 **반증(refute)** 시도 → 살아남은
것만 confirmed. confirmed 는 메인 세션이 코드에서 직접 재검증(rule 95 R2) + Jinja2 렌더 /
Python 실행으로 동작 확인(verification.md) 후 fix. 다음 Round 는 직전 Round 의 **diff 를
적대적으로 재검수**(회귀 검출) + 신규 영역 탐색을 함께 수행. 0 confirmed 까지 반복.

## 기준선 (offline)

- pytest: **1029 passed, 5 skipped (시작)** → **1074 passed, 5 skipped (종료; +45 회귀 테스트)**
  - 명령: `pytest tests/ --ignore=tests/e2e_browser`
  - e2e_browser 2건은 live Jenkins(10.100.64.152:8080) 도달 필요 — 본 환경 미도달, **코드 버그 아님**
- 환경 제약: 본 환경(Windows)에 `ansible-playbook` / Jenkins CLI 부재 → playbook·CI 런타임 검증은
  Jenkins Agent 위임. 검증 가능 게이트 = **pytest + py_compile + yaml.safe_load + Jinja2 직접 렌더
  + validate_field_dictionary.py + verify_vendor_boundary.py + verify_harness_consistency.py**

## Round 별 결과 (수렴)

| Round | 영역 | candidates | confirmed | fixed | deferred(lab/LOW) | 내 회귀 검출 |
|---|---|---|---|---|---|---|
| 17 (find+verify) | 14 finder 전영역 | 41 | 23 | **18** | 5 (OEM cluster) | — |
| 18 (회귀 재스캔) | R17 diff 회귀 + 12 finder 재스윕 | 9 | 4 | **2** | 2 (R18-3/R18-4 LOW) | **1** (R18-1) |
| 19 (수렴 확인) | R18 diff 회귀 + 6 finder | 3→2 distinct | 2 | **2** | 0 | **1** (R19-2/3) |
| 20 (최종 수렴) | R19 diff 회귀 + loop-scope sweep + 5 finder | **0** | **0** | 0 | 0 | 0 |

confirmed 추이: **23 → 4 → 2 → 0 (수렴)**. 총 **22 fix** (회귀 2건 포함) + **7 lab/LOW deferred**.
**핵심**: 매 Round 가 직전 Round 의 수정이 만든 회귀를 자가검출 — R18 이 내 speed 수정의 inf/nan
crash(R18-1)를, R19 가 내 R18 수정의 fractional-Gbps truncation(R19-2/3)을 잡아냄. Round 20 은
회귀 0 + 신규 0 으로 **수렴 확정**.

## Round 17 — 18 fix (3 batch)

| # | 심각도 | 위치 | 요지 | 회귀 테스트 |
|---|---|---|---|---|
| 1 | HIGH | module_utils/adapter_common.py | 비-dict `match:`(list/scalar YAML 오타) → `{}` 강제. truthy non-dict 가 `.get` AttributeError 로 전체 adapter lookup abort 되던 것 차단 | test_adapter_common_robustness (4 param) |
| 5 | MED | module_utils/adapter_common.py | normalize_vendor substring fallback 오탐 — 짧은 alias('hp')·역방향 매칭 제거(forward+whole-word-token+longest) | 동 파일 (5) + 전 alias 무오탐 실측 |
| 3 | MED | redfish_gather.py | Ports-only 어댑터(신 Port resource) speed_mbps Gbps 역산(`_normalize_port_speed`) — 25/100GbE null 유실 | test_redfish_pure_helpers (7) + HPE golden 재생성 |
| 18 | LOW | redfish_gather.py | `_get`/`_get_noauth` 200+빈/비-JSON body 처리 (빈→{} tolerant, 비-JSON→err) — status 0 오보 차단 | 동 (1) |
| 2 | HIGH | esxi try_one_credential.yml | probe 가 `failed_when:false` + `is not failed` 라 항상 성공 → 다중 자격 fallback 무력화. `ansible_facts is defined` 추가 | sibling 4태스크 대조 |
| 8 | MED | windows gather_cpu.yml | PS5.1 단일소켓 ConvertTo-Json collapse(dict) 시 summary corrupt — `is mapping` wrap | test_windows_cpu_summary_collapse_r17 (3, 실 Jinja 렌더) |
| 11 | MED | schema/examples/redfish_failed.json | collection_method `redfish`→`redfish_api` (enum 위반) | validate_field_dictionary PASS |
| 12 | MED | schema/examples/os_partial.json | system.runtime 중첩 shape → 9-필드 flat 계약 | 동 |
| 6 | MED | linux gather_runtime.yml | rescue all-null runtime 이 gather_system 수집분 wholesale 덮음(데이터 유실) → rescue `{}` | test_merge_fragment_empty_frag_r17 (3) |
| 7 | MED | linux gather_system.yml | listening_ports int[] → str[](계약) | test_linux_runtime_ports_str_r17 (3) |
| 19 | LOW | linux gather_runtime.yml | swap `free -m` NR==3 + LANG=C 누락 → label-match + LANG=C | (raw shell — lab smoke owed) |
| 20 | LOW | linux gather_runtime.yml | firewall_state '' → none 정규화(gather_system 일치) | (Jinja — lab smoke owed) |
| 9 | MED | esxi-gather/site.yml | adapter 선택이 collect_facts 前 facts={} → version_patterns dead, esxi_8x 항상 선택. collect 後로 이동 + 실 version 전달 | test_adapter_selection_facts_r17 (13, 실 캡처 grounding) |
| 10 | MED | os-gather/site.yml | windows adapter 선택이 SKU(ansible_os_product_type) 전달 → generation 전멸. ansible_kernel(build) 전달 | 동 |
| 4 | MED | common/tasks/precheck/run_precheck.yml | `_precheck_timeout`(caller=30) dead var → protocol/auth fallback wire(port 제외) + docs/11 정정 | test_precheck_robustness |
| 21 | LOW | os-gather try_one_credential.yml | windows probe `is not failed` → `ping == 'pong'`(positive evidence) | — |
| 22 | LOW | adapters/redfish/cisco_cimc.yml | model_patterns 공백형만 → `[ -]`(하이픈형 실 System.Model 수용) | test_adapter_selection_facts_r17 cisco (4) |
| 23 | LOW | Jenkinsfile_portal | Stage 3 validator venv 미활성화 → `/opt/ansible-env` 활성화(메인 Jenkinsfile 일치) | — |

추가: HPE 에뮬레이터 golden 10건 재생성 (speed_mbps null→25000/100000/10000) — diff 가 speed 필드에만
국한됨을 검증(옛 버그값이 골든에 박혀 있었음).

## Round 18 — 2 fix

- **R18-1 (MED, 내 회귀)**: `_normalize_port_speed` 의 raw `int(gbps*1000)` 이 JSON Infinity/NaN
  (json.loads 기본 허용)에서 OverflowError/ValueError → network_adapters 섹션 전체 drop. `_safe_int`
  경유로 수정. (Round 17 #3 가 만든 회귀를 Round 18 이 검출)
- **R18-2 (MED, 선재)**: Windows gather_runtime rescue 가 gather_system runtime 을 덮는 Linux #6 의
  Windows twin (미수정). rescue `{}` + gather_system listening_ports str[]. test_windows_runtime_ports_str_r18 (2).

deferred: R18-3 (runtime dual-collector success-path clobber, LOW 선재), R18-4 (link_status enum drift,
LOW lab-blocked) → NEXT_ACTIONS.

## Round 19 — 2 fix

- **R19-2/3 (LOW, 내 회귀)**: R18-1 의 `_safe_int` 라우팅이 fractional Gbps(2.5→2) truncate — 이전
  robustness 루프가 4회 기각한 변경 재발. `_safe_num`(유한 float 보존, inf/nan→None) 신설. (Round 18
  수정이 만든 회귀를 Round 19 가 검출). test_redfish_pure_helpers fractional + _safe_num (2).
- **R19-1 (MED, 선재)**: Windows firewall_state 가 plain-set-in-loop(Jinja 미전파)로 항상 'inactive'
  오보(보안 필드). namespace 패턴으로 수정. test_windows_firewall_state_r19 (2).

## Round 20 — 0 confirmed (수렴 확정)

5 finder (R19 회귀검수 + **loop-scoping anti-pattern 전수 sweep** + redfish/yml/adapters 최종 3 pass)
→ candidates 0. 신규 버그 0 + 회귀 0. **메인 세션 독립 grep 교차검증**: `set X = X` / `set flag=true/false`
in-loop 전수 → 유일 실 anti-pattern 은 이미 수정된 firewall_state. normalize_standard.yml `is_pri` 는
same-iteration read(L88) + cross-iteration 은 `ns.primary_marked`(namespace) → 정상(false positive 배제).

## lab/실행 환경 필요로 보류 (정직 보고 — 검증 불가)

> 정본: `docs/ai/NEXT_ACTIONS.md` Round 17/18 후속 절.

1. **vendor OEM 추출 cluster (#13~17)** — huawei/inspur/fujitsu/quanta/hpe-superdome `collect_oem.yml`
   이 모듈 미emit 경로(`_rf_raw_collect.systems[0]` / `data.system.Oem` 대문자 / `data.chassis`)를 읽어
   항상 빈 OEM. graceful(crash/envelope 위반 없음). 4종은 `_OEM_EXTRACTORS` 미등록이라 경로만 고쳐도
   데이터 없음 → 라이브러리 추출기 + 사이트 fixture 필요(lab 부재). path-only fix 는 검증 불가하여 미적용.
2. **R17 os/esxi/precheck YAML + Jenkinsfile_portal 1회 실 ansible/Jenkins smoke** — 본 환경 부재.
3. **R18-3 runtime dual-collector success-path clobber** (LOW 선재 — 구조 변경 실측 필요).
4. **R18-4 link_status enum drift** (LOW — baseline 재생성 실장비 필요, rule 13 R4).

## 검증 종합

- pytest **1074 passed, 5 skipped** (+45 회귀 테스트)
- validate_field_dictionary.py **PASS (0 failed)** / verify_vendor_boundary.py **PASS** /
  verify_harness_consistency.py **PASS** / py_compile **OK** / 편집 YAML 전체 parse **OK**
- confirmed 추이 **23 → 4 → 2 → 0**, 회귀 자가검출·수정 2건, Round 20 수렴 확정
