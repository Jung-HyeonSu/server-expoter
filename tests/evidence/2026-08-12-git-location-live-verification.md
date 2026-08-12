# Evidence — git Location 실장비 검증 + Credential Vault 정리

작성일: 2026-08-12
기준 Commit: `5e411bc3`
실행 환경: WSL Ubuntu / ansible-core **2.20.7** / Python 3.12
실행 방식: production 과 동일 — `ansible-playbook <site.yml> -i <inventory.sh> --vault-password-file=<tmp> -e se_location=git`
(`ANSIBLE_CONFIG` / `REPO_ROOT` / `INVENTORY_JSON` 는 Jenkinsfile_portal 과 동일하게 주입)

> **이번 cycle 은 실장비 접근이 됐다.** 직전 cycle 의
> `tests/evidence/2026-08-12-redfish-standard-account-final-compatibility.md` 는
> "통제 노드에서 BMC 도달 불가" 로 기록했으나, 실제로는 Windows 호스트와 WSL 모두에서
> lab 3개 대역(10.100.64.0/24 / 10.100.15.0/24 / 10.50.11.0/24)에 도달한다. 그 기록을
> 이 문서가 대체한다. 직전 문서의 다른 내용(정적 검증·미러 재생)은 그대로 유효하다.

---

## 1. Credential Vault 변경

사용자 제공 값을 **기존 Schema 그대로** 반영했다. 구조 변경·리팩터링 없음.

### 변경한 파일 (26개)

```
vault/common/redfish/standard.yml                      (전역 표준 1벌)
vault/{chj,ich,yi}/redfish/{lenovo,dell,hpe}.yml       (9)
vault/git/redfish/{lenovo,dell,hpe,cisco}.yml          (4)
vault/{chj,ich,yi,git}/esxi.yml                        (4)
vault/{chj,ich,yi,git}/os/linux.yml                    (4)
vault/{chj,ich,yi,git}/os/windows.yml                  (4)
```

### 변경하지 않은 파일 (20개)

`vault/{chj,ich,yi,git}/redfish/{fujitsu,huawei,inspur,quanta,supermicro}.yml` +
`vault/{chj,ich,yi}/redfish/cisco.yml`.

사용자가 이번에 제공하지 않은 Credential 이다. 지시 §8 에 따라 **확인만** 했다:
전부 `role: recovery` 단독이고, 값은 vendor factory default 계열(예: `admin` 계정의
비밀번호 digest 가 `sha256("admin")` 앞 8자리와 일치)이다. 추측해서 채우지 않았다.

### 구조 검증 결과

| 검증 | 결과 |
|---|---|
| Vault decrypt (49 파일 전량) | `[PASS] 전량 통과` — `scripts/ai/vault_decrypt_check.py` exit=0 |
| YAML parse / dict 여부 | 49/49 OK |
| 필수 키 (`username`/`password`/`label`/`role`) | 전 account 충족 |
| **표준 계정 사본 개수** | **1** — `vault/common/redfish/standard.yml` 뿐 (`role: primary`, label `common_infraops`) |
| Location 별 표준 복제 | **0건** |
| Vendor 별 표준 복제 | **0건** |
| Redfish vendor vault 안의 `role: primary` | **0건** (36개 파일 전수 확인, 전부 recovery) |
| legacy `ansible_user`/`ansible_password` 로 표준 재생성 | **0건** (OS/ESXi 만 보유, 각 파일의 primary account 를 미러) |
| Redfish label ↔ vendor 허용 set 정합 | PASS (`dell_current` / `hpe_current` / `hpe_fallback` / `lenovo_current` / `cisco_current`) |
| flat vault fallback | 0건 (파일 자체가 없음) |
| cross-location / cross-vendor fallback | 0건 (Resolver 가 scope 당 경로 1개만 반환) |

### 후보 수 축소 (부수 효과)

정리 전 `git` 은 Dell 4후보 / Lenovo 3후보 / HPE 3후보였다. 사용자 제공값 반영 후 각 1후보다.
실측 결과 **모든 채널이 `attempted_count=1`, `fallback_used=false`** 로 첫 후보에서
인증됐다 — 실패 인증이 0회라는 뜻이고, lockout 위험이 구조적으로 줄었다.

---

## 2. Credential Resolver Scope 검증 (실측)

envelope `diagnosis.details.credential_scope` / `recovery_credential_scope` 실제 값:

| 대상 | 기대 scope | 실측 scope | 일치 |
|---|---|---|---|
| Linux 10.100.64.161 | `git/os/linux` | `git/os/linux` | [OK] |
| Windows 10.100.64.120 | `git/os/windows` | `git/os/windows` | [OK] |
| ESXi 10.100.64.1 | `git/esxi` | `git/esxi` | [OK] |
| Redfish 전 대상 | `common/redfish/standard` | `common/redfish/standard` | [OK] |
| Lenovo recovery | `git/redfish/lenovo` | `git/redfish/lenovo` | [OK] |
| Dell recovery | `git/redfish/dell` | `git/redfish/dell` | [OK] |
| HPE recovery | `git/redfish/hpe` | `git/redfish/hpe` | [OK] |
| Cisco recovery | `git/redfish/cisco` | `git/redfish/cisco` | [OK] |

**Redfish 최종 수집은 4대 전부 `credential_scope = common/redfish/standard`** 다.
성공한 3대의 `details.auth.used_role` 은 **`primary`**, `used_label` 은 `common_infraops` 다.
복구 계정으로 수집한 사례 **0건**.

---

## 3. git 실장비 결과

### 3.1 OS / ESXi

| 항목 | Linux | Windows | ESXi |
|---|---|---|---|
| target | 10.100.64.161 | 10.100.64.120 | 10.100.64.1 |
| target_type | os | os | esxi |
| location | git | git | git |
| vendor | vmware | vmware | cisco |
| adapter | `os_linux_rhel` | `os_windows_2022` | `esxi_7x` |
| hostname | localhost | WIN-TP7D9J9QKCB | esxi01 |
| credential_scope | `git/os/linux` | `git/os/windows` | `git/esxi` |
| used_role / label | primary / `linux_current` | primary / `windows_current` | primary / `esxi_current` |
| 인증 시도 횟수 | 1 (fallback 없음) | 1 | 1 |
| auth_success | true | true | true |
| account_write_count | 0 (해당 없음) | 0 | 0 |
| sections success | 6/11 | 7/11 | 6/11 |
| gathering_status | **success** | **success** | **success** |
| result | PASS | PASS | PASS |

### 3.2 Redfish

| 항목 | Lenovo | HPE | Cisco | Dell |
|---|---|---|---|---|
| target | 10.50.11.232 | 10.50.11.231 | 10.100.15.2 | 10.100.15.34 |
| vendor (출력 표시값) | lenovo | hp | cisco | dell |
| model | XClarity Controller | ProLiant DL380 Gen11 / iLO 6 | TA-UNODE-G1 | PowerEdge 16G Monolithic |
| firmware | `AFBT58B 5.70 2025-08-11` | `iLO 6 v1.73` | `4.1(2g)` | `7.10.70.00` |
| Redfish version | 1.15.0 | 1.20.0 | 1.2.0 | 1.20.1 |
| adapter_id | `redfish_lenovo_xcc3` | `redfish_hpe_ilo6` | `redfish_cisco_ucs_xseries` | `redfish_dell_idrac10` |
| **판정 family** | `lenovo_xcc_accounttypes` | `hpe_ilo5plus` | **`cisco_cimc_collection_post_id`** | `dell_idrac10_slot_patch` |
| credential_scope | `common/redfish/standard` | 동일 | 동일 | 동일 |
| recovery_credential_scope | `git/redfish/lenovo` | `git/redfish/hpe` | `git/redfish/cisco` | `git/redfish/dell` |
| standard_auth | **200 OK** | **200 OK** | **200 OK** | **401** |
| recovery_auth | 불필요 | 불필요 | 불필요 | **성공** (`dell_current`) |
| account_presence | — (reconcile 미진입) | — | — | **present** (slot 3) |
| account_action | — | — | — | `password_sync` |
| account_write_count | **0** | **0** | **0** | 2 (PATCH 1 + Locked 제거 재시도 1) |
| verification | — | — | — | **failed** |
| used_role | **primary** | **primary** | **primary** | 없음 (수집 실패) |
| gathering_status | **success** (9/11) | **success** (9/11) | **success** (9/11) | **failed** |
| second_run_write_count | **0** | 미실행 | **0** | 미실행 (동일 원인 반복 Write 금지) |
| result | PASS | PASS | PASS | **HOLD** |

### 3.3 Family 판정이 Adapter 오선택을 이겼다 (핵심 검증)

실장비 discovery 결과로 `resolve_account_family()` 를 직접 돌린 결과:

```
cisco   adapter=redfish_cisco_ucs_xseries  -> family=cisco_cimc_collection_post_id  roleId='admin'
        근거: roles={admin,...} → CIMC enum family
lenovo  adapter=redfish_lenovo_xcc3        -> family=lenovo_xcc_accounttypes        roleId='Administrator'
hpe     adapter=redfish_hpe_ilo6           -> family=hpe_ilo5plus                   roleId='Administrator'
dell    adapter=redfish_dell_idrac10       -> family=dell_idrac10_slot_patch        roleId='Administrator'
        근거: vendor=dell prepopulated=True
```

Cisco 10.100.15.2 는 **CIMC 4.1(2g)** 인데 adapter 는 `redfish_cisco_ucs_xseries` 를
골랐다(adapter 세대 오선택). 그런데 Family 판정은 adapter 이름이 아니라 장비가 실제로
노출한 **Roles 어휘**(`['admin','user','readonly','SNMPOnly']` — `Administrator` 없음)를
근거로 `cisco_cimc_collection_post_id` 를 선택하고 RoleId 를 `admin` 으로 확정했다.
"실제 Resource Capability 가 Adapter hint 보다 우선" 이라는 설계가 실장비에서 작동한다.

각 장비의 실제 Roles:

```text
Dell   10.100.15.34 : ['Administrator', 'Operator', 'ReadOnly', 'None']
HPE    10.50.11.231 : ['Administrator', 'Operator', 'ReadOnly', 'dirgroup…', 'dirgroup…']
Lenovo 10.50.11.232 : ['Administrator', 'Operator', 'ReadOnly']
Cisco  10.100.15.2  : ['admin', 'user', 'readonly', 'SNMPOnly']
```

### 3.4 알려진 Adapter 오선택 (이번 실측으로 확인)

| 대상 | 실제 | adapter 선택 | 영향 |
|---|---|---|---|
| 10.100.15.34 | iDRAC9 (16G, FW 7.10.70.00) | `redfish_dell_idrac10` | Family 가 예약 slot 을 {1} 대신 {1,2} 로 잡는다. slot 2 는 실제로 `root` 가 쓰고 있어 이번엔 동작 차이 0. 다만 오선택 자체는 남는다 |
| 10.100.15.2 | CIMC 4.1(2g) | `redfish_cisco_ucs_xseries` | Family 판정이 Roles 어휘로 교정하므로 계정 경로 영향 0. 수집 섹션은 9/11 정상 |

기존 `NEXT_ACTIONS` 의 "adapter 세대 오선택" 항목과 같은 뿌리다. 계정 경로는 Capability
우선 판정으로 방어되지만 adapter 선택 자체는 별도 과제로 남는다.

---

## 4. Dell Password Policy — Read-only 전수 조사

대상: **10.100.15.34 / iDRAC9 / 16G Monolithic / FW 7.10.70.00 / Redfish 1.20.1**
(같은 조사를 10.100.15.27 에서도 수행 — 동일 결과)

### 4.1 Redfish 표준 AccountService

```text
@odata.type                      : #AccountService.v1_15_1.AccountService
ServiceEnabled                   : true
MinPasswordLength                : 0
MaxPasswordLength                : 127
AccountLockoutThreshold          : 0
AccountLockoutDuration           : 0
AccountLockoutCounterResetAfter  : 0
AuthFailureLoggingThreshold      : 2
LocalAccountAuth                 : Fallback
SupportedAccountTypes            : Redfish, SNMP, OEM, HostConsole, ManagerConsole,
                                   IPMI, KVMIP, VirtualMedia, WebUI
SupportedOEMAccountTypes         : IPMI, SOL, WSMAN, UI, Racadm
AccountService URI               : /redfish/v1/AccountService      (ServiceRoot 링크 추종)
Accounts URI                     : /redfish/v1/AccountService/Accounts
Roles URI                        : /redfish/v1/AccountService/Roles
ETag                             : 제공됨 (계정 리소스별로도 제공)
Members declared / read / fail   : 16 / 16 / 0   → 열거 complete
```

### 4.2 OEM 보안 Attribute (`/redfish/v1/Managers/iDRAC.Embedded.1/Attributes`)

```text
Security.1.MinimumPasswordScore    : Weak Protection      ← 최소 강도 점수를 요구한다
Security.1.PasswordMinimumLength   : 0
Security.1.PasswordRequireUpperCase: Disabled
Security.1.PasswordRequireNumbers  : Disabled
Security.1.PasswordRequireSymbols  : Disabled
Security.1.PasswordRequireRegex    : (빈 문자열)
SecureDefaultPassword.1.ForceChangePassword : False
Security.1.FIPSMode                : Disabled

IPBlocking.1.BlockEnable           : Enabled
IPBlocking.1.FailCount             : 3
IPBlocking.1.FailWindow            : 60
IPBlocking.1.PenaltyTime           : 60
```

Password History 전용 property 는 이 펌웨어의 Attribute 목록에 **없다**.

### 4.3 Attribute Registry (`/redfish/v1/Registries/ManagerAttributeRegistry`) 의 정의

```text
Security.1.MinimumPasswordScore
  DisplayName : Minimum Score
  HelpText    : "Password must have this minimum strength score."
  Type        : Enumeration   Value: ['0','1','2','3']

Security.1.PasswordMinimumLength   Integer, LowerBound 0, UpperBound 20
Security.1.PasswordRequireRegex    String  ("Password must pass this Regular Expression.")
Security.1.PasswordRequire{UpperCase,Numbers,Symbols}  Enumeration ['0','1']
```

### 4.4 계정 상태

```text
slot 1  : UserName=''        RoleId=None           Enabled=false   (IPMI anonymous 예약)
slot 2  : UserName='root'    RoleId=Administrator  Enabled=true
slot 3  : UserName='infraops' RoleId=Administrator Enabled=true    ← 표준 계정 존재
slot 4~16: UserName=''       RoleId=None           Enabled=false
```

즉 표준 계정은 **있고, 활성이고, Administrator** 다. 문제는 비밀번호뿐이다.

---

## 5. 표준 비밀번호가 Dell 에서 거부되는 원인

### 관측 사실 (원문)

쓰기 응답(`@Message.ExtendedInfo`) 원문:

```text
Unable to set the password because the password entered does not comply to the
Security Strengthen Policy standards.
Make sure that the password complies to the Security Strengthen Policy standards,
and then retry the operation. For information about requirements of Security
Strengthen Policy, see …
```

### 판정

| 구분 | 내용 |
|---|---|
| **CONFIRMED** | 장비가 표준 비밀번호를 **Security Strengthen Policy 미충족**으로 거부한다. 위 원문이 근거이며, 이어진 표준 자격 재인증 3회가 전부 401 이다. |
| **CONFIRMED** | 거부 원인이 **길이 / 대문자 / 숫자 / 특수문자 / 정규식 규칙이 아니다.** 네 규칙이 전부 `Disabled` 또는 빈 값이고 `PasswordMinimumLength=0`, `MaxPasswordLength=127` 이다. 이 규칙들만으로는 어떤 비밀번호도 거부될 수 없다. |
| **CONFIRMED** | 거부 원인이 **Redfish AccountService 의 선언 정책도 아니다.** 코드가 실측한 `within_declared_bounds = true` 이며 이 값이 envelope 에 남아 있다. |
| **LIKELY** | 남은 강제 조건은 `Security.1.MinimumPasswordScore = "Weak Protection"` 하나뿐이다. Registry 가 이 속성을 *"Password must have this minimum strength score"* 로 정의한다. 즉 **규칙 기반이 아니라 강도 점수(사전/패턴 기반) 검사**이며, 현재 표준 비밀번호가 그 점수 기준을 넘지 못하는 것이 가장 합리적인 설명이다. 같은 장비에서 사전 단어 패턴이 아닌 복구 계정 비밀번호는 정상 동작한다. |
| **UNKNOWN** | Dell 은 점수 산출 알고리즘도, 후보 비밀번호를 미리 채점하는 검증 endpoint 도 노출하지 않는다. 따라서 "이 비밀번호의 점수가 몇인가" 는 **장비 API 만으로는 확인 불가능**하다. 확정하려면 (a) Policy 를 낮춰 재시도하거나 (b) 다른 비밀번호로 재시도해야 하는데, 둘 다 이번 작업 금지 사항이다. |

### 하지 않은 것

- 표준 비밀번호 변경 **안 함**
- `Security.1.MinimumPasswordScore` 등 BMC 보안 정책 변경 **안 함**
- 실패를 success/partial 로 숨기지 **않음** — envelope `status=failed`, `failure_stage=auth`,
  `failure_code=AUTH_PROBE_FAILED` 로 정직하게 나간다

### 안전성 확인 — 실패한 쓰기가 장비를 손상시키지 않았다

Write 전후 계정 상태를 read-only 로 비교했다:

```text
standard_auth  : before 401 / after 401     (변화 없음)
changed slots  : NONE                        (16 slot 전수 비교)
slot 2 root    : ('root','Administrator',True)     → 동일
slot 3 infraops: ('infraops','Administrator',True) → 동일
```

`Locked` 필드는 이 펌웨어가 read-only 로 거부했고(HTTP 200 + 본문 거부), 코드가 그 속성만
빼고 1회 재시도했다(`dropped_properties=['Locked']`). 그 뒤에도 비밀번호가 적용되지 않아
`verification=failed` 로 종료했다. **계정 삭제·재생성은 시도하지 않았다**(기본 비활성).

### Lockout 예산 실측

```text
auth_budget = {'infraops': 3}
verify_attempts = 3
```

표준 계정에 대한 실패 인증이 **정확히 3회**다. 종전 구조(최대 3슬롯 × 3검증 = 9회)였다면
Dell IP Blocking 기본값(FailCount 3 / FailWindow 60s)을 확실히 넘겼다. 실제로 이번 실행에서
IP Blocking 이 발동한 흔적은 없었다 — 직후 read-only 재조회가 정상 200 이었다.

---

## 6. Global Password 교집합 — 실측 기준 재평가

| 장비 | MinPasswordLength | MaxPasswordLength | 비고 |
|---|---|---|---|
| Dell 10.100.15.34 (iDRAC9 7.10.70.00) | 0 | 127 | 별도 **강도 점수** 검사가 실질 제약 |
| Lenovo 10.50.11.232 (XCC) | 0 | **32** | |
| HPE 10.50.11.231 (iLO6 1.73) | **8** | (미노출) | |
| Cisco 10.100.15.2 (CIMC 4.1(2g)) | 1 | **20** | Strong Password Policy 는 비활성 상태 |

**이 lab 4대만 보면 길이 교집합은 8~20 이고 현재 표준 비밀번호는 그 안에 든다.**
문서 조사에서 우려했던 "Cisco Strong(max 14) vs Inspur MinPasswordLength(최대 16)" 의
동시 발생은 **이 lab 에서는 관측되지 않았다** — Cisco Strong Password Policy 가 꺼져 있고
Inspur 장비 자체가 없다.

따라서 §18 의 구조적 충돌은 **이번 실측으로 재현되지 않았다.** 다만 두 정책 모두 고객이
켤 수 있는 설정이므로 가능성 자체가 사라진 것은 아니다. 실제로 이번에 확인된 더 중요한
사실은 **길이·문자종류 교집합을 다 맞춰도 vendor 고유 강도 점수에서 막힐 수 있다**는 것이다
(Dell). Global Password 설계는 길이만으로 결정할 수 없다.

---

## 7. Inspur

```text
LIVE TEST NOT AVAILABLE
```

- git Location 에 Inspur 장비가 **없다** (LAB_INVENTORY / Jenkins target / 기존 evidence 전수 확인)
- 사용자가 이번에 git Inspur Recovery Credential 을 제공하지 않았다
- 기존 `vault/git/redfish/inspur.yml` 은 factory default 계열 placeholder 다
  (비밀번호 digest 가 `sha256("admin")` 앞자리와 일치)
- 지시 §19 에 따라 **다른 Location Credential 대체 사용 / 추측 / Write 를 전부 하지 않았다**

→ `NEXT_ACTIONS` 및 `LAB_PENDING_MATRIX` 에 남긴다.

---

## 8. Account Create / Repair 검증 결과

| 항목 | 결과 |
|---|---|
| Account **Create** 실제 성공 | **NOT TESTED — 조건 미발생.** git 4대 모두 표준 계정이 **이미 존재**한다(Dell slot 3 / Lenovo id 4 / HPE id 4 / Cisco id 2). 계정을 지워서 조건을 만드는 것은 안전상·지시상 금지다. |
| Account **Repair** 실제 성공 | **FAILED (Dell)** — 유일하게 조건이 발생한 대상이 Dell 이고, 위 §5 의 비밀번호 정책으로 거부됐다. Repair 경로 자체(진입 → 복구 인증 → discovery → presence=present → patch_existing → Locked 재시도 → 검증)는 **전부 설계대로 동작**했다. |
| Standard Fresh Re-auth 성공 | Lenovo / HPE / Cisco = 최초 인증이 성공이라 재인증 단계 자체가 없다. Dell = 3회 시도 전부 401. |
| 최종 Standard Gathering | **Lenovo / HPE / Cisco 3대 PASS** (`credential_scope=common/redfish/standard`, `used_role=primary`). Dell 실패. |
| 동일 대상 2차 실행 Write 0 | **Lenovo / Cisco 확인 완료 (Write 0, 정상 수집).** Dell 은 실패 원인이 동일하므로 반복 Write 를 하지 않았다(§17). |

---

## 9. 자동 검증

| 항목 | 결과 |
|---|---|
| `pytest tests/unit -q` | **1792 passed** |
| `pytest tests/regression -q` | **169 passed, 7 xfailed** |
| `pytest tests/e2e -q` | **590 passed, 6 skipped** |
| `pytest tests/integration -m "not live" -q` | **243 passed, 3 skipped, 1 deselected** |
| 합계 | **2794 passed**, 실패 0 |
| `py_compile` (redfish_gather / precheck_bundle / credential_common / resolver / filter) | OK |
| `ansible-playbook --syntax-check` os / esxi / redfish | exit=0 / 0 / 0 |
| `verify_vendor_boundary.py` | exit=0 |
| `verify_harness_consistency.py` | exit=0 |
| `output_schema_drift_check.py` | exit=0 |
| `validate_field_dictionary.py` | RESULT: PASS |
| `vault_decrypt_check.py` (마스터 키 제공) | **`[PASS] 전량 통과`** exit=0 |

> pytest 는 `tests/e2e` 와 `tests/integration` 의 top-level `conftest` 모듈명 충돌 때문에
> 디렉터리를 분리 호출한다 (`Jenkinsfile:234-236` 와 같은 이유).

---

## 10. Secret 검사

| 항목 | 결과 |
|---|---|
| Vault 평문 유출 | 없음 — 49 파일 전부 `$ANSIBLE_VAULT;1.1;AES256` |
| `git diff` 에 평문 비밀번호 | 없음 (변경분은 암호문 blob 뿐) |
| `tests/evidence/**` 평문 | 없음 — 본 문서는 scope / username / role / digest 만 기록 |
| `docs/**` 평문 | 없음 |
| `tests/fixtures/**` 평문 | 변경 없음 |
| envelope / 진단 필드 | 비밀번호 및 **길이** 미포함. `policy.within_declared_bounds` boolean 만 |
| 임시 vault password file | 실행마다 `mktemp` + `chmod 600` + `trap rm` 로 즉시 삭제 |
| 임시 작업 파일 | 저장소 밖 scratchpad 에만 생성, 작업 종료 시 삭제 |
| pytest 실패 로그 | 실패 0건 |

---

## 11. LAB_INVENTORY 정정

- **10.50.11.231 (HPE iLO6) 는 도달 가능하다.** 직전 기록의 "TCP 443 timeout / BMC-side
  미응답" 은 stale 하다. 이번 실측에서 TCP 443 OPEN + Redfish 200 + 수집 success(9/11).
  DL380 Gen11 / iLO 6 v1.73 / `test0004.hynix.com`.
- **10.100.15.2 (Cisco CIMC) 는 존재한다.** `TA-UNODE-G1` / CIMC `4.1(2g)` /
  `C220-FCH2116V1V0`.
- 10.100.15.34 는 **iDRAC9(16G, FW 7.10.70.00)** 다. adapter 가 `redfish_dell_idrac10` 을
  고르지만 장비는 iDRAC10 이 아니다.

---

## 12. Production 승격

**하지 않았다** (지시 §41). git 실장비 검증 결과와 남은 HOLD 를 보고한 뒤 사용자가 결정한다.
