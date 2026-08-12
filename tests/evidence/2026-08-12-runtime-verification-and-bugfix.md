# errors.message 개선 실환경 검증 + 후속 버그 수정 (2026-08-12)

기준 SHA: `c7817510c37ca6703dac686c090929ea3d59b087` (main, 검증 시작 시점)
실행 환경: WSL Ubuntu / ansible-core **2.20.7** / Python 3.12.3
검증자: AI (Claude Code) — 사용자 지시 "errors.message 개선 후 실환경 검증 및 후속 버그 수정"

---

## 1. 요약

| 항목 | 결과 |
|---|---|
| 3채널 `ansible-playbook --syntax-check` | [PASS] os/esxi/redfish 모두 exit=0 |
| pytest 전체 | [PASS] 2278 passed, 10 skipped, 7 xfailed |
| 정합 게이트 5종 | [PASS] 전부 exit=0 |
| 실장비 스모크 | [PASS] 6대상 / envelope 6개 (요청 1 → envelope 1) |
| BUG-1 (ESXi listening_ports) | [확인 후 수정] 실장비에서 수정 검증 |
| BUG-2 (Redfish OEM include 경로) | [확인 후 수정] 실제 ansible 실행으로 실패 재현 |
| Jenkins 실제 checkout SHA (§8) | [BLOCKED] 인증 자격증명 없음 |
| Account Write 실제 수행 (§12) | [미수행 — 의도적] dry-run 만 |

---

## 2. BUG-1 — ESXi `listening_ports` 가 항상 빈 배열

### 사실 확인

`esxi-gather/site.yml` 실행 순서: `collect_disks`(:128) → `normalize_system`(:135) → `collect_runtime`(:149).

- `collect_disks.yml:32` 가 `_e_raw_listening_ports` 에 실제 수집값을 담는다
  (firewall.ruleset enabled inbound, `esxi_disks.py:_build_listening_ports`).
- `normalize_system.yml:33` 이 그 값을 `system.runtime.listening_ports` 로 넣는다.
- `collect_runtime.yml:161` 이 **`system.runtime` dict 전체를 다시 만들면서**
  `listening_ports: []` 로 하드코딩했다.

`merge_fragment.yml` 은 깊이 2 에서 dict 를 **통째로 교체**한다. 따라서 나중에 실행되는
`collect_runtime` 의 runtime dict 가 앞의 값을 이긴다.

### 실측 (실제 ansible-core + 저장소의 진짜 `merge_fragment.yml`)

```
STEP1 (normalize_system 상당)  lp=['22', '443', '902']
STEP2 (collect_runtime 상당)   lp=[]                     ← 덮어써짐
      runtime_keys=['firewall_tool','listening_ports','swap_total_mb']
      system_keys=['os_family','runtime']                 ← 형제 키는 보존됨
STEP3 (키 자체를 제거한 경우)   lp=MISSING                ← 키가 사라짐
```

STEP3 이 중요하다 — **키를 빼는 방식은 쓸 수 없다.** envelope 계약상
`system.runtime.listening_ports` 키는 존재해야 하는데(field_dictionary), 키를 빼면
runtime dict 교체로 키 자체가 사라진다.

### 수정

`esxi-gather/tasks/collect_runtime.yml`:

```yaml
listening_ports:  "{{ _e_raw_listening_ports | default([]) }}"
```

`normalize_system.yml` 과 **동일한 원본**을 이어받는다. `collect_disks` 가 먼저 실행되므로
변수는 항상 정의돼 있고, 미수집 시엔 `default([])` 로 양쪽이 같은 값이 된다.

### 실장비 검증 (esxi02 / 10.100.64.2 / Cisco TA-UNODE-G1 / ESXi 7.0.3)

```
data.system.runtime.listening_ports =
  ['22','68','80','161','443','902','5988','5989','8000','8300','8301','8302','9080']
```

수정 전 계약상 항상 `[]` 였던 값이 실제 13개 포트로 채워졌다.

---

## 3. BUG-2 — Redfish vendor OEM 이 공통 merge_fragment 를 못 찾음

### 사실 확인

`{{ playbook_dir }}` 는 실행된 playbook 의 디렉터리로 해석된다 →
`<repo>/redfish-gather`. 그 아래에는 `common/` 이 없다.

### 실측 (A/B, 실제 ansible-core)

```
A. 현재 코드   include: {{ playbook_dir }}/common/tasks/normalize/merge_fragment.yml
   exit=2   결과: (파일 없음 = merge 미실행)
   [ERROR]: Could not find or access
            '/tmp/se-syntax/redfish-gather/common/tasks/normalize/merge_fragment.yml'

B. 정식 방식   include: {{ lookup('env','REPO_ROOT') }}/common/tasks/normalize/merge_fragment.yml
   exit=0   결과: merged=1 first=일부 제조사 확장 정보를 수집하지 못했습니다. …
```

즉 해당 벤더의 **OEM fragment 가 한 번도 병합되지 않았다.**

### 실제 영향 — fragment 미병합보다 크다 (실측)

문제의 `include_tasks` 는 벤더 task 파일의 **최상위**에 있고, 그 파일을 부르는
`redfish-gather/site.yml:176` 의 OEM block 에는 rescue 가 달려 있다
(`OEM (graceful — 실패해도 표준 섹션 보존)`). site.yml 의 block/rescue 구조를 그대로 옮기고
저장소의 진짜 `merge_fragment.yml` 을 써서 실제 ansible-core 로 관측했다:

```
A. 수정 전 (playbook_dir 기준 — 깨진 경로)
   errors=1
   message=일부 제조사 확장 정보를 수집하지 못했습니다. 대상 상태와 수집 로그를 확인하세요.
   detail=[task: vendor OEM] OEM 수집/정규화 예외
   merged_data_oem=없음                    ← 벤더가 만든 OEM 데이터 소실
   collected=[]

B. 수정 후 (REPO_ROOT 기준)
   errors=0
   merged_data_oem={'serial_number': 'OEM-TEST-1234', 'platform': 'TestPlatform'}
   collected=['hardware']
```

rescue 가 graceful 이라 `status` 는 success/partial 로 남는다. 그래서 **아무도 눈치채지
못한 채, 해당 벤더는 매 수집마다 실제 원인 없는 OEM 오류 1건을 항상 내보내면서 OEM
데이터를 통째로 잃고 있었다.** 이는 직전 작업(2026-08-12 errors.message 4계층 분리)의 목표
중 "정보성/성공 fallback 을 오류로 취급하지 않는다" 와 정면으로 충돌하는 상시 가짜 오류다.

### 영향 파일 (6건 — 전수)

```
redfish-gather/tasks/vendors/cisco/collect_oem.yml
redfish-gather/tasks/vendors/fujitsu/normalize_oem.yml
redfish-gather/tasks/vendors/hpe/normalize_oem.yml
redfish-gather/tasks/vendors/huawei/collect_oem.yml
redfish-gather/tasks/vendors/inspur/collect_oem.yml
redfish-gather/tasks/vendors/quanta/normalize_oem.yml
```

### 어느 adapter 가 실제로 이 파일들을 부르는가 (실측)

| 고친 파일 | 참조 adapter | 실제 영향 |
|---|---|---|
| `hpe/normalize_oem.yml` | `hpe_ilo`, `hpe_ilo4`, `hpe_ilo5`, `hpe_ilo6`, `hpe_ilo7`, `hpe_csus_3200`, `hpe_superdome_flex` (**7종**) | **HPE 전 세대** |
| `fujitsu/normalize_oem.yml` | `fujitsu_irmc` | Fujitsu |
| `huawei/collect_oem.yml` | `huawei_ibmc` | Huawei |
| `inspur/collect_oem.yml` | `inspur_isbmc` | Inspur |
| `quanta/normalize_oem.yml` | `quanta_qct_bmc` | Quanta |
| `cisco/collect_oem.yml` | **없음** | 없음 — 어떤 adapter 의 `oem_tasks` 도 이 파일을 가리키지 않는다 (dead file) |

> **정정**: 처음에 10.100.15.2(Cisco UCS C220 M4)로 A/B 를 돌려 "차이 없음" 이 나왔다.
> 원인은 수정 효과가 없어서가 아니라, 그 대상이 선택하는 adapter(`redfish_cisco_ucs_xseries`)에
> `oem_tasks` 자체가 없어서 **되돌린 파일이 실행되지 않았기** 때문이다. 위 매트릭스는 그 뒤
> adapter YAML 전수를 파싱해 확인한 것이다.

lab 에 HPE / Fujitsu / Huawei / Inspur / Quanta 장비가 없어 **벤더별 실장비 확인은 못 했다.**
위 rescue 재현은 site.yml 과 동일한 구조로 메커니즘을 관측한 것이고, 각 벤더에서 실제로
어떤 OEM 필드가 복구되는지는 장비 확보 후 확인이 필요하다 (NEXT_ACTIONS 등재).

### 수정

저장소의 다른 모든 공통 태스크 호출과 동일하게 `REPO_ROOT` 기준으로 통일했다.
벤더마다 경로를 제각각 하드코딩하지 않았고, 이미 정상 동작하던 벤더
(dell / lenovo / supermicro / esxi / os 채널 전부)의 방식을 그대로 따랐다.

`dell` / `lenovo` / `supermicro` 의 `collect_oem.yml` 은 `_data_fragment: {}` 만 두는
placeholder 라 merge 호출이 없어도 무해하다 (빈 fragment). 이 파일들의
`# - include_tasks: common/...` 은 주석 처리된 템플릿 예시다.

---

## 4. 회귀 테스트 추가

`tests/unit/test_fragment_overwrite_and_include_paths.py` (84 tests)

- `test_esxi_runtime_writers_agree_on_key_set` — `system.runtime` 을 만드는 모든 task 의
  키 집합이 같아야 한다 (다르면 나중 fragment 가 앞 값을 지운다)
- `test_esxi_runtime_listening_ports_not_hardcoded_empty` — BUG-1 재발 차단
- `test_no_playbook_dir_reference_to_common_tasks` — BUG-2 재발 차단
- `test_every_include_target_exists_on_disk` — 정적 include 경로 실존 확인
- `test_repo_root_includes_resolve` — REPO_ROOT 기준 경로 실존 확인

**주입 실험으로 가드 유효성 확인** — 두 버그를 각각 되돌리면 `exit=1` 로 검출된다.

`tests/unit/test_auth_evidence_contract.py` (4 tests) — §4 인증 근거 계약 고정.

---

## 5. §4 인증 근거(Authentication Evidence) 검증

`os-gather/site.yml` 의 rescue diagnosis 는
`_os_auth_ok or (_all_sec_collected | length > 0)` 을 인증 통과 근거로 본다.

**왜 두 번째 항이 필요한가**: `abort if all credentials failed` 는
`when: (_os_accounts | length) > 0` 이다. 자격 후보가 0건이면 abort 하지 않고
inventory 자격으로 수집이 진행된다. 그 경우 `_os_auth_ok` 는 false 로 남는데,
데이터는 실제로 수집된다. 두 번째 항이 없으면 envelope 이
"대상에 접속할 수 없습니다" 라고 말하면서 `data` 에 수집 결과를 담는 자기모순이 된다.

**근거로서 타당한가** — 섹션이 collected 로 표시되는 경로를 전수 확인했다:

| 위험 경로 | 결과 |
|---|---|
| controller-side (`delegate_to: localhost`) task 가 collected 를 채움 | 0건 |
| precheck 단계 task 가 collected 를 채움 | 0건 |
| `_data_fragment` 가 빈 채로 collected 를 채움 | 0건 |

collected 를 채우는 26곳 전부 `os-gather/tasks/{linux,windows}/gather_*.yml` 안에 있고,
그 태스크에 도달하려면 원격 모듈이 실제로 실행돼야 한다. 따라서 간접 근거로 타당하다.
위 3경로를 테스트로 고정했다.

---

## 6. §3 중앙 실패 문구 런타임 구조

| 확인 항목 | 결과 |
|---|---|
| 정본 파일 위치 | `common/vars/failure_reasons.yml` (단일) |
| 로딩 방식 | 5개 play 전부 `{{ lookup('env','REPO_ROOT') }}/...` — cwd 비의존 |
| Jenkins 와의 정합 | `Jenkinsfile_portal:128` 이 `REPO_ROOT=${WORKSPACE}` 설정 |
| `section_messages.yml` | redfish 만 로드 / `_sm_*` 참조도 redfish 만 — 정합 |
| 신규 Python 의존성 | 0건 (`errors_normalizer.py` import = `__future__`, `collections`) |
| requirements 변경 | 0건 |
| `failure_code` → 문구 매핑 | 7 code → 6 정본 문장, 미지정 code 는 보수적 1번 문장 |
| 사용자 문구 기술정보 누출 | 0건 (포트/HTTP/timeout/예외/프로토콜명 없음) |

`reason_for_failure_code` 호출 4곳 모두 직전에 닫힌 enum 값을 대입하므로 fallback 경로는
방어용이며 실제로는 도달하지 않는다.

---

## 7. 실장비 스모크 (§9)

대상/채널은 `tests/evidence` + `docs/13` 에 **이미 기록된 매핑만** 사용했다. 새 IP 를
추측하지 않았다. 모두 읽기 전용 수집이며 Account Write 는 `-e _rf_account_service_dryrun=true`
로 시뮬레이션 고정했다.

| 대상 | 채널 | status | envelope | 13필드 | 계약 |
|---|---|---|---|---|---|
| 10.100.64.2 (esxi02, Cisco, ESXi 7.0.3) | esxi | success | 1 | OK | failure_* 전부 null, errors 0 |
| 10.100.15.2 (Cisco UCS C220 M4 / CIMC) | redfish | success | 1 | OK | failure_* 전부 null, errors 0 |
| 10.100.15.27 (Dell R760 / iDRAC 7.10.70.00) | redfish | success | 1 | OK | failure_* 전부 null, errors 0 |
| 10.100.15.1 (Redfish 503 이력) | redfish | failed | 1 | OK | stage/code/reason 전부 존재, errors 1건 |
| 10.100.64.161 (RHEL 8.10) | os | success | 1 | OK | failure_* 전부 null, errors 0 |
| 10.100.64.120 (Windows Server 2022) | os | success | 1 | OK | failure_* 전부 null, errors 0 |

### 실패 경로 실증 — 10.100.15.1

```
status=failed
diagnosis: reachable=true port_open=true protocol_supported=false auth_success=null
failure_stage=protocol  failure_code=PROTOCOL_CHECK_FAILED
failure_reason=관리 포트에는 연결됐지만 서버 정보 수집에 필요한 응답을 확인할 수 없습니다.
               관리 서비스 설정과 상태를 확인하세요.
errors[0].section=redfish_gather
errors[0].message=(failure_reason 과 동일 — 중앙 정의)
errors[0].detail=Redfish ServiceRoot 응답 아님 (HTTP 503) | [task: …] 단계=prot…
```

### 2회차 재현 (동일 6대상, 대상 간 8초 간격)

`esxi02 / rf_cisco / rf_dell / rf_503 / os_rhel / os_win` **6/6 동일 결과**.
요청 1 → envelope 1, 13필드 정합, success 3종의 `failure_*` 전부 null, 503 대상만 failed.

> 1회차 요약 스크립트에서 `rf_dell` 이 "envelope 없음" 으로 보였던 것은 **측정 스크립트의
> 결함**이었다. 필터에 `grep -viE "password|secret|token"` 을 걸어 뒀는데, Dell envelope 이
> `"action":"password_sync"` 를 포함한 **한 줄짜리 JSON** 이라 그 줄이 통째로 지워졌다.
> 단독 재실행과 2회차 모두 정상 envelope 1개다. **수집 코드 문제가 아니다.**

이 한 건이 다음을 동시에 실증한다:
- P0-2 `status=failed` + `failure_reason` 존재
- P0-3 `failed` + `errors` 비어있지 않음
- 사용자 문구는 정본 3번 문장, **HTTP 503 은 `detail` 에만**
- `auth_success=null` — 인증을 시도하지 못했으므로 false 가 아님
- 요청 1 → envelope 1

---

## 8. §12 Redfish Account Reconciliation — dry-run 검증

**Write Gate** (`redfish-gather/site.yml:154`):

```
_rf_account_reconcile_allowed =
     used_account.role == 'recovery'
 AND _rf_collect_ok
 AND _rf_primary_auth_rejected
```

`_rf_primary_auth_rejected` (`collect_standard.yml:99`) 는
`_rf_auth_observations` 중 `role == 'primary'` 이면서 **`status == 401` 정확 일치**가
1건 이상일 때만 true. timeout / TLS / 5xx / 403 은 status 가 다르므로 진입하지 못한다.
Standard Account 는 `role: primary` 기준이며 username 하드코딩은 0건이다
(`infraops` 문자열은 주석/docstring 예시 2곳뿐).

### 실장비 dry-run 결과 (10.100.15.27, Dell iDRAC)

```json
"auth": {"attempted_count":5, "used_label":"lab_dell_root", "used_role":"recovery",
         "fallback_used":true},
"account_service": {"attempted":true, "recovered":false, "method":"patch_existing",
                    "action":"password_sync", "account_existed":true,
                    "verification":"skipped", "dryrun":true,
                    "slot_uri":"/redfish/v1/AccountService/Accounts/3", "vendor":"dell"}
```

- Recovery 자격으로 진입 → 예정 Action(`password_sync`, slot 3)만 보고
- `dryrun: true` → **실제 Account Write 0건**
- 그럼에도 `status=success`, `errors=[]` → **P0-7 (성공한 fallback 을 오류/partial 로
  만들지 않는다) 실장비 검증**

실제 Write 는 수행하지 않았다. 지시서 §12 의 "기존 승인/검증 정책이 명확한 경우에만"
조건을 이 세션에서 확인할 수 없었기 때문이다.

---

## 9. Blocked / 미수행

| 항목 | 상태 | 사유 |
|---|---|---|
| §8 Jenkins 실제 checkout SHA | **BLOCKED** | `http://10.100.64.153:8080` 응답(Jenkins 2.541.2, Jetty 12.1.5)하지만 `/api/json` 이 **HTTP 403** — 이 환경에 Jenkins 자격증명이 없다. Job 의 Repository/Branch/Checkout SHA 를 확인하지 못했다. |
| §12 실제 Account Write | **미수행 (의도적)** | dry-run 만 수행. 승인/검증 정책 확인 불가. |

> 정정: 초기에 GitLab internal 을 "도달 불가" 로 적었으나 **틀렸다.** 포트 80 을 확인했는데
> remote 는 `https://10.100.64.156` (443) 이다. `git push origin main` 이 GitHub + GitLab
> **양쪽 모두 성공**했고 `git ls-remote` 로 세 곳 SHA 일치를 확인했다.

### §8 대체 확인

- `Jenkinsfile_portal` 은 Gather / Validate Schema stage 에서 기본 SCM checkout 을 사용하고,
  Validate / Callback stage 는 checkout 을 생략한다 (repo 파일 미사용).
- 따라서 Jenkins 가 받는 SHA 는 Job 의 SCM 설정에 달려 있으며, **push 성공만으로 Jenkins
  반영을 단정할 수 없다** (CLAUDE.md §14). 실제 Job 의 Repository / Branch / Checkout SHA
  확인은 사용자 측에서 수행해야 한다.

---

## 10. 재현 방법

```bash
# 3채널 syntax-check (vault 암호 필요)
REPO_ROOT=$PWD ANSIBLE_CONFIG=$PWD/ansible.cfg INVENTORY_JSON='[{"ip":"192.0.2.10"}]' \
  ansible-playbook os-gather/site.yml -i os-gather/inventory.sh --syntax-check

# 회귀
python -m pytest tests/ -q
python tests/validate_field_dictionary.py
python scripts/ai/hooks/output_schema_drift_check.py
python scripts/ai/verify_vendor_boundary.py
python scripts/ai/verify_harness_consistency.py
python scripts/ai/hooks/pre_commit_jinja_compile_check.py

# 실장비 스모크 (읽기 전용 + 계정쓰기 금지)
INVENTORY_JSON='[{"ip":"10.100.64.2"}]' \
  ansible-playbook esxi-gather/site.yml -i esxi-gather/inventory.sh \
  --vault-password-file <pw> -e _rf_account_service_dryrun=true
```

---

## 11. Phase 종료 상태 (2026-08-12, 사용자 지시로 확정)

`errors.message` 개선 및 Runtime 검증 Phase는 여기서 **종료**한다.
추가 Gathering 코드 수정 / 전수조사는 이 Phase 범위가 아니다.

| 항목 | 상태 |
|---|---|
| errors.message 개선 | 완료 |
| Contract Bug 수정 | 완료 |
| ESXi `listening_ports` 수정 | 완료 |
| Redfish OEM include 수정 | 완료 |
| 3채널 syntax-check | PASS |
| 전체 pytest | PASS |
| 실장비 Smoke | PASS |
| Redfish 실패 경로 실증 | PASS |
| Account Recovery dry-run | PASS |
| 실제 Account Write | 미검증 |
| Jenkins Checkout SHA | BLOCKED |
| 벤더별 OEM 실장비 | 일부 미검증 |
| `docs/19` production 승격 | 대기 |

> pytest PASS 는 **본 Phase 커밋(`be97e407`) 트리를 격리 추출해 실행한 결과**다
> (2275 passed / 0 failed). 같은 시각 작업 트리에서 관측된
> `tests/unit/test_vault_dynamic_loading_m_c3.py` 3건 실패는 **다른 세션의
> Location Credential Resolver 작업에서 비롯된 것이며 본 Phase 의 회귀가 아니다.**
> 해당 Test 를 우회하거나 수정하지 않았다.

### docs/19 승격 대기 사유 (판정 근거)

종료 시점 실측:

```
main HEAD            117c5190  (origin/main = 3e8bad1c — 다른 세션의 미push 커밋 1개 존재)
production HEAD      b574841e  (origin/production 과 동일)
working tree         clean
Credential Resolver  main 에 commit 됨 (70744c76 feat / 3e8bad1c harness / 117c5190 fix)
Resolver production 승격 승인·검증  본 세션에서 확인 불가 — 해당 작업 세션 소관
```

`main -> production` 승격 대상 순수 코드 **32 파일** 중 **31 파일이 Resolver 소유**이고,
본 Phase 소유는 `docs/19_decision-log.md` **1 파일**뿐이다.

`scripts/ai/promote_to_production.sh` 는 `origin/production ↔ main` 의 순수 코드 차이를
**전량** 승격한다. 파일 선택 인자가 없고, 저장소에 다른 공식 선택 승격 경로도 없다.
따라서 `docs/19` 하나를 넣으려면 Resolver 코드 31 파일이 함께 올라간다.

→ **경우 2 로 판정하고 `docs/19` 는 계속 대기**시킨다.
`git merge main -> production` / force push / history rewrite 는 사용하지 않았다.

본 Phase 의 **게더링 코드 변경은 이미 production(`b574841e`)에 전부 반영**돼 있다
(ESXi `listening_ports`, Redfish OEM include 6건, 회귀 테스트 2건).
대기 중인 것은 `docs/19` 문서 교정 1건뿐이며 운영 동작에 영향이 없다.

Resolver 의 완료·검증·commit·production 승격 판단은 **해당 작업 세션 소관**이다.
그 세션이 승격을 수행하면 `docs/19` 도 같은 승격에 자연히 포함된다.
