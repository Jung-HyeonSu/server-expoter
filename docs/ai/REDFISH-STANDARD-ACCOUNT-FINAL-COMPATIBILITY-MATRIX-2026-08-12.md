# Redfish 표준 수집 계정 — 최종 호환성 매트릭스

작성일: 2026-08-12
기준 Commit: `5e72ac05` (변경 전) → 본 cycle 변경 후
입력: 9 Vendor 공식조사 문서 9건 + `docs/ai/REDFISH-STANDARD-ACCOUNT-ASIS-AUDIT-2026-08-12.md` + 현재 HEAD 코드 실측

---

## 0. 이 문서를 읽는 법

### 상태 표기

| 상태 | 의미 |
|---|---|
| `PROVEN` | **실장비에서** Create 또는 Repair → 표준 재인증 → 표준 계정 수집 → 2차 실행 Write 0 까지 확인됨 |
| `PARTIAL` | 공식 문서 또는 실장비 미러로 계약이 확인됐고 코드가 그에 맞게 동작하지만, 실장비 Write E2E 는 미확인 |
| `UNVERIFIED` | 공식 Write 계약을 확보하지 못했다. 현행 generic 경로를 **유지**하되 지원한다고 말하지 않는다 |
| `MISSING` | 해당 Family 를 위한 Strategy 자체가 없다 |
| `BROKEN` | 코드가 공식 계약과 어긋나 있다 |
| `HOLD` | 코드 문제가 아니라 운영 결정이 선행돼야 한다 |

### 이번 cycle 에서 `PROVEN` 이 늘지 않은 이유

**이 작업에서 실장비 요청은 0건이다.** 통제 노드(Windows)에서 BMC 로 나가는 경로가 없고,
사용자 지시 §18 이 요구하는 순서(read-only probe → dry-run → 통제된 1대 Write)는 사용자
환경에서만 수행할 수 있다. 따라서 아래 어떤 Family 도 이번 작업만으로 `PROVEN` 으로
올리지 않았다. 실장비 검증 절차는 `tests/evidence/2026-08-12-redfish-standard-account-final-compatibility.md` §5 에 있다.

### 이번 cycle 에서 실제로 낮아진 불확실성

`tests/reference/redfish/**` 의 **실장비 미러**(Dell 5호스트 / HPE 1 / Lenovo 1 / Cisco 1)를
읽는 회귀 테스트가 종전 0건이었다(audit D-8). 이번에 `tests/integration/test_account_reconcile_replay.py`
로 연결해 **읽기 단계**(Capability Discovery / 계정 존재 판정 / Family 선택)를 실제 응답으로
검증한다. 미러에는 쓰기 응답이 없으므로 쓰기 동작은 여전히 미검증이다.

---

## 1. 전 Vendor 공통 계약 (이번 cycle 확정)

```text
Global Standard Gathering Account = 전역 1개   (vault/common/redfish/standard.yml)
Recovery Account                  = Location × Vendor (vault/<loc>/redfish/<vendor>.yml)
최종 Gathering                    = 반드시 Standard Account
정상 상태 재실행                   = AccountService Write 0건
```

성공 판정:

```text
쓰기 수락(벤더 계약 기준)  →  계정 리소스 재조회  →  상태 확인
  →  Global Standard Credential 재인증  →  표준 계정으로 실제 Gathering
```

`HTTP 2xx` 하나로 성공이라 하지 않는다. `verification='none'` 상태의 쓰기를 성공으로
인정하지 않는다.

### 공통 Capability Discovery (읽기 전용, 쓰기 전 필수)

`redfish_gather.account_service_discover()` 가 수집하는 것:

| 항목 | 용도 |
|---|---|
| ServiceRoot `AccountService.@odata.id` | 실제 AccountService URI (하드코딩 대체) |
| `Accounts.@odata.id` / `Roles.@odata.id` | 실제 컬렉션 URI (쓰기 대상 URI 정본) |
| `Members` + `Members@odata.count` | 열거 완결성 판정 |
| ManagerAccount 별 `Id/UserName/RoleId/Enabled/Locked/AccountTypes/PasswordChangeRequired/@odata.type` | 존재 판정 + 상태 수렴 + Family 근거 |
| `MinPasswordLength / MaxPasswordLength` | 정책 진단(차단 아님) |
| `AccountLockoutThreshold / Duration / CounterResetAfter` | lockout 예산 진단 |
| `SupportedAccountTypes` | 계정 분리 세대 판정 |
| Roles Collection member Id | **RoleId 문자열을 추측하지 않기 위한 정본** |
| Manager `FirmwareVersion / Model / ManagerType` | Firmware 경계 Family 판정 |

열거 상태는 3-상태다: `complete` / `incomplete` / `failed`.
계정 존재는 4-상태다: `present` / `absent` / `unknown` / `ambiguous`.
**`unknown` 에서는 Account Write 0건이다.**

---

## 2. Vendor × Family 매트릭스

### 2.1 Dell

| 항목 | iDRAC7 / iDRAC8 | iDRAC9 | iDRAC10 |
|---|---|---|---|
| AccountService URI | Manager-scoped (`/Managers/<id>/AccountService`) | 세대별 상이 — 실측 `.34` 는 root-scoped | root-scoped 관측 |
| 코드의 URI 결정 | **ServiceRoot 링크 추종** (하드코딩 제거) | 동일 | 동일 |
| Accounts URI | `AccountService.Accounts.@odata.id` | 동일 | 동일 |
| Create | 빈 slot PATCH | 빈 slot PATCH | 빈 slot PATCH |
| Update | ManagerAccount PATCH | 동일 | 동일 |
| Reserved slot | ID 1 (IPMI anonymous) | ID 1 | **ID 1 + ID 2 (default root)** |
| RoleId | Roles Collection 에서 선택 | 동일 | 동일 |
| AccountTypes | 미요구 | 미요구 | 실미러에 존재 — 읽기만 |
| Password | 문서상 max 20 | <4.00 20 / 4~6.x 40 / ≥7.00 127 + Strength Policy | Strength Policy |
| Lockout | IP Blocking | IP Blocking | FailCount 3 / FailWindow 60s / Penalty 60s |
| ETag | 미사용 | 미사용 | 미사용 |
| Write 성공 계약 | 2xx **AND** 본문 거부 없음 | 동일 | **200 + 본문 read-only 거부** 를 실패로 처리 |
| Repository Strategy | `dell_slot_patch` | `dell_slot_patch` | `dell_idrac10_slot_patch` |
| Fixture Evidence | 없음 | 실미러 `10_100_15_27/28/31/33` | 실미러 `10_100_15_34` |
| Live Evidence | 없음 | 수집은 확인 / 계정 Write 미확인 | **Write 시도 2회 — 둘 다 실패(원인 규명됨)** |
| Status | `UNVERIFIED` | `PARTIAL` | **`HOLD`** |
| Remaining Gap | iDRAC7/8 실미러 부재 | Create 실장비 미검증 | 표준 비밀번호가 Security Strengthen Policy 미충족 — **운영 결정(E-6)** |

**iDRAC10 HOLD 사유** (`tests/evidence/2026-08-12-redfish-standard-account-separation.md` §6.1):
장비가 돌려준 문장 그대로 —
`The property Locked is a read only property and cannot be assigned a value.` (1차, 코드로 해결됨)
`Unable to set the password because the password entered does not comply to the Security Strengthen Policy standards.` (2차, **운영 결정 필요**)

코드는 두 층 모두 정확히 관측하고 진단한다. 남은 것은 비밀번호 값 또는 장비 정책 중
어느 쪽을 맞출지의 결정이며, 그것은 이 작업의 범위가 아니다.

### 2.2 HPE

| 항목 | iLO4 | iLO5 / 6 / 7 | CSUS 3200 RMC | Superdome Flex 280 RMC |
|---|---|---|---|---|
| OEM namespace | **`Oem/Hp`** | `Oem/Hpe` | RMC 별도 | RMC 별도 |
| Create | Collection POST + `Oem.Hp.Privileges` | Collection POST (RoleId) | POST 지원은 목차로 확인, **payload 미확보** | 상세 미확보 |
| Update | ManagerAccount PATCH | 동일 | Password PATCH 확인 | 미확보 |
| RoleId | OEM Privilege 중심 | Administrator/Operator/ReadOnly | Administrator/Operator/ReadOnly/CustomCli | Administrator/Operator/ReadOnly |
| AccountTypes | 없음 | iLO6 1.64+ / iLO7 지원 | 미확인 | 미확인 |
| Password | max 39 | max 39 (+ iLO7 EnforcePasswordComplexity) | 6~64, 기본 min 10 | 6~40, class 수에 따라 min 변동 |
| Lockout | — | AccountLockoutThreshold/Duration/CounterResetAfter | AccountLockoutDuration PATCH 가능 | 미확인 |
| Repository Strategy | `hpe_ilo4` | `hpe_ilo5plus` | `generic_collection_post` | `generic_collection_post` |
| Fixture Evidence | 없음 | 실미러 `10_50_11_231` (iLO6) + 에뮬레이터 | fixture 만 (mock) | fixture 만 (mock) |
| Live Evidence | 없음 | 수집 확인 / 계정 Write 미확인 | 없음 | 없음 |
| Status | `PARTIAL` | `PARTIAL` | `UNVERIFIED` | `UNVERIFIED` |
| Remaining Gap | iLO4 실장비/미러 부재 | Create 실장비 미검증 | RMC ServiceRoot 실미러 + create payload | 동일 |

이번 변경의 핵심: **CSUS / Superdome 을 iLO 로 처리하지 않는다.** adapter hint 가
`csus` / `superdome` 이면 iLO payload(`Oem.Hpe.Privileges`)를 쓰지 않고 generic 으로 남긴다.

### 2.3 Lenovo

| 항목 | IMM2 | XCC1 Purley | XCC1 Whitley / AMD | XCC2 | XCC3 | TSM |
|---|---|---|---|---|---|---|
| Create | **미확인** | 빈 slot **PATCH** (1~12 pre-populated) | Collection POST | Collection POST | Collection POST | Collection POST |
| Update | 미확인 | Slot PATCH | Slot PATCH | Slot PATCH | Slot PATCH | Instance PATCH |
| PasswordChangeRequired | 미확인 | **미제공** | 지원 | 지원 | Resource 에는 존재 | **미지정 시 default true** |
| AccountTypes | 미확인 | 없음 | 없음 | Redfish/SNMP/ManagerConsole/IPMI/WebUI | 동일 | 미확인 |
| Reserved | 미확인 | — | — | — | `HostBootStrap` | ID 1~4 (HostAutoFW/HostAutoOS 등) |
| Password | 미확인 | API 8~20 (UI 문서는 32) | 동일 | API max 255 / UI 8~32 | API max 255 / CLI 8~32 | 8~20 |
| Repository Strategy | `generic_collection_post` | `lenovo_purley_slot_patch` | `lenovo_collection_post` | `lenovo_xcc_accounttypes` | `lenovo_xcc_accounttypes` | `lenovo_collection_post` |
| Family 판정 근거 | adapter hint | **pre-populated 빈 slot 관측** | dynamic members | adapter hint `xcc2` | adapter hint `xcc3` | (TSM 전용 hint 없음 — POST + PCR=false 로 공통) |
| Fixture Evidence | 없음 | 없음 | 실미러 `10_50_11_232` (XCC 1.15) | 없음 | 없음 | 없음 |
| Status | `UNVERIFIED` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` | `PARTIAL` |
| Remaining Gap | Redfish AccountService 지원 근거 자체가 없음 | Purley 실미러 | Create 실장비 | XCC2 실미러 | XCC3 실미러 | TSM 실미러 + 특수 ID 보호 실측 |

핵심 변경: **Purley 를 Collection POST 로 만들던 것을 빈 slot PATCH 로 바로잡았다.**
판정은 이름이 아니라 **관측**(pre-populated 빈 slot 존재)으로 한다.
그리고 Lenovo POST 는 처음부터 `PasswordChangeRequired:false` 를 실어 보낸다 — TSM 이
미지정 시 `true` 로 만들어 생성 직후 접근이 막히기 때문이다.

### 2.4 Cisco

| 항목 | IMC 3.x | IMC 4.1 / 4.2 / 6.0 | BMC 1.x / 2.0 / 4.0 | UCS X-Series |
|---|---|---|---|---|
| Create | `POST /Accounts/<ID>` (instance) | `POST /Accounts` + body `Id` | `POST /Accounts` (Id 는 BMC 할당) | **미확인** |
| RoleId | `admin` | `admin` | `Administrator` | 미확인 |
| Account Id semantics | numeric slot | numeric slot | username 기반 또는 자동 numeric | 미확인 |
| AccountTypes | — | 6.0 노출 | 노출 | 미확인 |
| PasswordChangeRequired | 세대별 | 6.0 지원 | 4.0 은 생성 후 `true` | 미확인 |
| Password | max 20 (Strong 시 8~14) | 동일 | 8~20 | 미확인 |
| ETag | — | — | 4.0 은 `@odata.etag` 노출, PATCH 예에 `If-Match: *` | 미확인 |
| Repository Strategy | `generic_collection_post` | `cisco_cimc_collection_post_id` | `cisco_bmc_dynamic` | `generic_collection_post` |
| Family 판정 근거 | — | **Roles 어휘에 `admin`** | **Roles 어휘에 `Administrator`** | 근거 없음 → generic |
| Fixture Evidence | 없음 | 실미러 `10_100_15_2` (CIMC v1_6_0) | 없음 | 없음 |
| Live Evidence | 없음 | **Create 201 + 신규 자격 인증 200 (2026-05-06 실측)** | 없음 | 없음 |
| Status | `UNVERIFIED` | `PARTIAL` (실측 있음, 현 코드로 재검증 필요) | `PARTIAL` | `UNVERIFIED` |
| Remaining Gap | instance POST 실측 | 현 Family 코드로 재실측 | 실미러 + RoleId 실측 | AccountService 계약 자체 |

핵심 변경: **전 Cisco 에 `Administrator→admin` remap + Id 2..15 스캔을 적용하던 것을 끊었다.**
`admin` 은 IMC 의 어휘이고 최신 Cisco BMC 는 `Administrator` 를 쓴다. 이제 RoleId 는
**Roles Collection 이 실제로 노출한 값**에서 고르고, Id 는 Family 가 요구할 때만 보낸다.

### 2.5 Supermicro

| 항목 | X9 | X10 / X11 / H11 | X12 / H12 | X13·H13 (<01.05) | X13 01.05+ / X14 01.02+ / NVIDIA Superchip 01.04+ |
|---|---|---|---|---|---|
| Redfish 지원 | **공식 범위 밖** | 지원 | 지원 (Reference Guide 적용 시작) | 지원 | 지원 |
| Create | 미확인 | `/AccountService/Accounts` POST | 동일 | 동일 | 최신 매뉴얼은 `/AccountService` POST 도 문서화 |
| AccountTypes | 미확인 | 공유 계정 | 세부 확인 필요 | 분리 전 | **IPMI / Redfish 분리** — Redfish 필요 |
| RoleId | 미확인 | Administrator/Operator/ReadOnly | 동일 | 동일 | 동일 |
| Repository Strategy | `generic_collection_post` | `supermicro_legacy` | `supermicro_legacy` | `supermicro_legacy` | `supermicro_split_account` |
| Family 판정 근거 | — | — | — | Firmware < 경계 | **AccountTypes 관측 또는 SupportedAccountTypes 또는 Firmware ≥ 경계** |
| Fixture Evidence | 없음 | fixture `supermicro_x10` (mock) | fixture `supermicro_x12` (mock) | 없음 | fixture `supermicro_x14` (mock) |
| Live Evidence | 없음 (lab 0대) | 없음 | 없음 | 없음 | 없음 |
| Status | `UNVERIFIED` | `UNVERIFIED` | `PARTIAL` | `UNVERIFIED` | `PARTIAL` |
| Remaining Gap | Redfish 지원 여부 자체 | 실미러 | 실미러 | Firmware 경계 실측 | `/AccountService` POST 가 어느 Firmware 부터인지 |

**Create URI 는 아직 `/AccountService/Accounts` 를 쓴다.** 최신 매뉴얼의 `/AccountService` POST 는
어느 Firmware 부터 실제 동작하는지 확인하지 못했고, 두 경로에 순차로 써 보는 것은 금지된
Write fallback 이다. 실미러 확보 후 Family 를 하나 더 나눈다.

### 2.6 Fujitsu iRMC

| 항목 | S4 | S5 | S6 |
|---|---|---|---|
| Redfish API 존재 | 공식 확인 | 공식 확인 (3.39~3.60P) | 공식 확인 (1.15S / 2.72S) |
| Create Method | **미확보** | **미확보** | **미확보** |
| Redfish Role | `RedfishAdmin` / `RedfishOperator` / `RedfishReadOnly` 체계 존재 | 동일 | 동일 |
| Repository Strategy | `generic_collection_post` (현행 유지) | 동일 | 동일 |
| Fixture Evidence | 없음 | fixture `fujitsu_irmc_s5` (mock) | fixture `fujitsu_irmc_s6` (mock) |
| Status | `UNVERIFIED` | `UNVERIFIED` | `UNVERIFIED` |
| Remaining Gap | iRMC RESTful API Specification pack 원문 + 실미러 | 동일 | 동일 |

`RoleId=Administrator` 가 Fujitsu 에서 맞는지 확정되지 않았다. 다만 이번 변경으로 RoleId 는
Roles Collection 에 `Administrator` 가 없고 `RedfishAdmin` 이 있으면 **대소문자 무시 일치**로
넘어가지는 않는다(다른 이름이므로). 이 부분은 실미러 확보 후 Family 를 추가해야 한다.

### 2.7 Huawei iBMC

| 항목 | V3 / V5 / Kunpeng / MM920·MM921 |
|---|---|
| Create | `POST /redfish/v1/AccountService/Accounts` — 2019 MM920 문서와 2025 Kunpeng 문서 양쪽 공식 |
| Update | ManagerAccount PATCH (`UserName/Password/RoleId/Locked/Enabled`) |
| RoleId | Roles Collection + PrivilegeMap 제공 → **실제 값에서 선택** |
| AccountTypes | 표준 속성으로 확인되지 않음 → **보내지 않는다** |
| PasswordChangeRequired | 표준 속성으로 확인되지 않음 → **보내지 않는다** (종전 retry payload 제거) |
| Password | Complexity 활성 시 8~20, username/역순 금지, weak dictionary |
| Lockout | 5회 연속 실패 → 5분 잠금 |
| Redfish Login Interface | **Local User 별로 Redfish 가 빠져 있을 수 있다** |
| Repository Strategy | `huawei_ibmc` |
| Fixture Evidence | fixture `huawei_ibmc_v2` (mock) |
| Status | `PARTIAL` |
| Remaining Gap | **Redfish Login Interface 를 Redfish API 로 켜는 OEM field/action 미확보** + 실미러 |

Login Interface 는 이번에 구현하지 않았다. 그것을 켜는 OEM 필드나 Action 이 공식 자료에서
확인되지 않았고, 추측해서 쓰는 것은 금지 사항이다. 대신 계정이 있고 권한도 맞는데 인증이
안 되는 상태가 `post_write_state` 와 `errors[].detail` 로 드러나므로 운영자가 이 원인을
식별할 수 있다.

### 2.8 Inspur

| 항목 | M5 | M6 / ISBMC Whitley | M7 |
|---|---|---|---|
| Create | 미확인 | `POST /AccountService/Accounts`, `Id` optional (생략 시 자동 할당) | 미확인 |
| Update | 미확인 | `PATCH /AccountService/Accounts/<id>` + **`If-Match` 공식 요구** | 미확인 |
| Write 성공 계약 | 미확인 | **HTTP 200 + `Oem.Public.Status == 0`** | 미확인 |
| RoleId | 미확인 | Administrator/Operator/User/Noaccess/OEM1~4 | 미확인 |
| Password | 미확인 | max 20, MinPasswordLength **고객이 8~16 으로 설정 가능** | 미확인 |
| Lockout | 미확인 | Threshold 0~5 / Duration 5~60분 | 미확인 |
| Repository Strategy | `generic_collection_post` | `inspur_m6` | `generic_collection_post` |
| Fixture Evidence | 없음 | fixture `inspur_isbmc` (mock) | 없음 |
| Status | `UNVERIFIED` | `PARTIAL` | `UNVERIFIED` |
| Remaining Gap | 공식 자료 | 실미러 + ETag 실동작 + Status error code 전체 목록 | 공식 자료 |

### 2.9 Quanta / QCT

| 항목 | Legacy (Redfish v1.1) | Modern (Redfish v1.11) | Inhouse OpenBMC (Xeon 6) |
|---|---|---|---|
| Redfish 존재 | 공식 확인 | 공식 확인 | 공식 확인 |
| Create / Update | **미확인** | **미확인** | upstream bmcweb 구조가 후보이나 QCT Firmware 미확인 |
| AccountTypes | 미확인 | 미확인 | upstream 에는 존재 |
| Repository Strategy | `generic_collection_post` | `generic_collection_post` | `generic_collection_post` |
| Fixture Evidence | 없음 | 없음 | fixture `quanta_qct` (mock) |
| Status | `UNVERIFIED` | `UNVERIFIED` | `UNVERIFIED` |
| Remaining Gap | 실미러 3 Family 전부 | 동일 | upstream ≠ QCT custom build |

---

## 3. 요약 매트릭스

| Vendor | Family 수 | PROVEN | PARTIAL | UNVERIFIED | HOLD |
|---|---:|---:|---:|---:|---:|
| Dell | 3 | 0 | 1 (iDRAC9) | 1 (iDRAC7/8) | 1 (iDRAC10) |
| HPE | 4 | 0 | 2 (iLO4, iLO5+) | 2 (CSUS, Superdome) | 0 |
| Lenovo | 6 | 0 | 5 | 1 (IMM2) | 0 |
| Cisco | 4 | 0 | 2 | 2 (IMC 3.x, X-Series) | 0 |
| Supermicro | 5 | 0 | 2 | 3 | 0 |
| Fujitsu | 3 | 0 | 0 | 3 | 0 |
| Huawei | 1 | 0 | 1 | 0 | 0 |
| Inspur | 3 | 0 | 1 (M6) | 2 | 0 |
| Quanta | 3 | 0 | 0 | 3 | 0 |
| **합계** | **32** | **0** | **14** | **17** | **1** |

`PROVEN` 이 0인 것이 이 매트릭스의 가장 중요한 사실이다. 실장비 계정 생성 경로는
아직 어느 Family 에서도 E2E 로 증명되지 않았다.

---

## 4. Global Standard Password 정책 — 구조적 충돌

9 Vendor 조사에서 확인된 길이 상한(가장 보수적):

| 근거 | 상한 / 하한 |
|---|---|
| Dell iDRAC7/8, iDRAC9 <4.00 | max 20 |
| Lenovo XCC Redfish AccountService, TSM | max 20 |
| Cisco IMC | max 20 |
| Huawei iBMC (Complexity 활성) | 8~20 |
| Inspur M6 | max 20 |
| **Cisco IMC Strong Password Policy 활성** | **8~14** |
| **Inspur MinPasswordLength (고객 설정 가능)** | **최대 16 까지 상향 가능** |

⚠️ **교집합이 빌 수 있다.** 어떤 사이트가 Cisco Strong Password(max 14)와 Inspur
MinPasswordLength=16 을 동시에 운영하면, 두 정책을 모두 만족하는 **단일 비밀번호가
수학적으로 존재하지 않는다.** 이것은 코드 버그가 아니라 제품 Contract 의 문제다.

현재 Dell HOLD 도 같은 종류다 — 코드가 아니라 값과 정책의 문제다.

### 이번 cycle 의 처리 (사용자 결정 2026-08-12)

**차단하지 않는다.** 장비가 선언한 `MinPasswordLength` / `MaxPasswordLength` 를 읽어
진단(`diagnosis.details.account_service.policy`)에 남기고, 범위를 벗어나면 경고를
`errors[]` 에 남긴 뒤 **쓰기는 그대로 시도**한다. 거부되면 장비가 준 문장
(`write_response_info`, `vendor_status`)으로 원인을 확정한다.

비밀번호 길이 자체는 기록하지 않는다 — `within_declared_bounds` boolean 만 남긴다.

### 남은 아키텍처 결정 (운영/아키텍트 몫)

```text
A. 지원 대상 BMC Password Policy 범위를 제품 사전조건으로 정의
B. 비호환을 감지하면 운영 승인 하에서만 BMC Policy 를 표준화
C. "모든 Vendor 동일 Password 1개" 정책 자체를 재검토
D. 상호 모순되는 Security Policy 조합을 지원 Matrix 에서 명시적으로 제외
```

---

## 5. Lockout 안전성

| Vendor | 공식 기준 | 종전 코드 | 현재 코드 |
|---|---|---|---|
| Dell iDRAC10 | IP Blocking FailCount 3 / FailWindow 60s / Penalty 60s | 후보 간 5초 | **401 일 때 65초**(설정 가능), transport 오류는 5초 |
| HPE iLO | Threshold 3 | 동일 | 동일 |
| Lenovo XCC | 기본 5회 / 60분 | 동일 | 동일 |
| Huawei iBMC | 5회 → 5분 잠금 | 동일 | 동일 |
| Inspur | Retry 0~5 / Lock 5~60분 | 동일 | 동일 |

쓰기측 축소 (사용자 결정 = "쓰기측 축소 + 후보루프 backoff 확대"):

| 항목 | 종전 | 현재 |
|---|---|---|
| Dell 빈 슬롯 생성 시도 | 최대 3 슬롯 | **1 슬롯** |
| 표준 계정 실패 인증 / run (Dell 생성 경로) | **최대 9회 / 약 20초** | **최대 3회** |
| POST 생성 요청 수 (근거 있는 Family) | 최대 3회 (payload 사다리) | **1회** |
| POST 생성 요청 수 (UNVERIFIED Family) | 최대 3회 | **최대 2회** (현행 유지 결정 — HPE 전용 3차만 제거) |
| username 별 실패 인증 카운터 | 없음 | `diagnosis.details.account_service.auth_budget` |

BMC 의 Lockout 정책 자체는 **변경하지 않는다.** 읽기만 한다.

---

## 6. 현재 Repository Strategy 구현 지점

| 대상 | 위치 |
|---|---|
| Capability Discovery | `redfish_gather.account_service_discover()` |
| 존재 3-상태 판정 | `redfish_gather.account_presence()` |
| Family 표 | `redfish_gather._ACCOUNT_FAMILIES` |
| Family 선택 | `redfish_gather.resolve_account_family()` |
| RoleId 선택 | `redfish_gather.choose_role_id()` |
| 쓰기 성공 해석 | `redfish_gather.interpret_write_response()` |
| 생성 payload | `redfish_gather.build_create_payload()` |
| 쓰기 후 상태 확인 | `redfish_gather._confirm_account_state()` |
| 쓰기 대상 URI | `redfish_gather._accounts_write_uri()` (discovery 결과) |
| 진입 게이트 | `redfish-gather/site.yml:148-153` (401 전용, 변경 없음) |
| 성공 판정 게이트 | `redfish-gather/tasks/account_service.yml` (`verification == 'verified'`) |
| 진단 노출 | `diagnosis.details.account_service` (Additive — envelope 13 필드 불변) |

---

## 7. 남은 Gap (우선순위)

### 운영 결정 필요

1. **Dell 표준 비밀번호 vs iDRAC Security Strengthen Policy** (E-6) — 해소 전까지 Dell 은 `HOLD`
2. **Global Password 정책 교집합** — §4 의 A/B/C/D 중 선택
3. `_rf_account_service_dryrun` 항구 정책 여부 (현재 운영 Job 에 override 없음 = 게이트가 열리면 실쓰기)

### 실장비 / 실미러 필요 (lab 부재)

| 우선순위 | 대상 | 얻는 것 |
|---|---|---|
| HIGH | Dell iDRAC7/8 read-only 미러 | Manager-scoped AccountService 실증 |
| HIGH | Lenovo Purley 미러 | pre-populated slot 판정 실증 |
| HIGH | Cisco 최신 BMC 미러 | `Administrator` RoleId + Id semantics 실증 |
| MED | Supermicro X13/X14 미러 (분리 전후 Firmware 각 1) | 계정 분리 경계 실증 |
| MED | Inspur M6 미러 + ETag/If-Match 실동작 | OEM Status / ETag 계약 실증 |
| MED | Huawei 미러 + Redfish Login Interface 상태 | Login Interface 복구 방법 |
| LOW | Fujitsu API Pack 원문 | S4/S5/S6 Create 계약 |
| LOW | Quanta 3 Family 미러 | Legacy/Modern/OpenBMC 구분 |

### 코드에 남긴 것 (의도적)

- UNVERIFIED Family 의 generic POST 경로와 400/405 retry — **현행 유지** (사용자 결정)
- Huawei Redfish Login Interface 자동 활성화 — OEM 계약 미확보로 미구현
- Supermicro `/AccountService` POST — Firmware 경계 미확보로 미도입
- `empty_accounts` → `CREDENTIAL_SET_UNAVAILABLE` (audit H-5) — Portal 사용자 문장이
  5번→4번으로 바뀌므로 Consumer 결정 필요. **보고만 하고 변경하지 않았다.**
