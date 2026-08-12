# ADR-2026-08-12 — Redfish 계정 Write 를 Vendor 분기에서 Family Strategy 로

상태: Accepted
일자: 2026-08-12
결정자: hshwang1994 (사용자 결정 4건) + AI 초안
관련: `docs/ai/REDFISH-STANDARD-ACCOUNT-ASIS-AUDIT-2026-08-12.md`,
      9 Vendor 공식조사 문서 9건,
      `docs/ai/REDFISH-STANDARD-ACCOUNT-FINAL-COMPATIBILITY-MATRIX-2026-08-12.md`

---

## 컨텍스트 (Why)

표준 수집 계정을 **없으면 만들고 망가졌으면 고치는** 기능은 구조는 있었지만 신뢰할 수
없었다. 두 종류의 문제가 겹쳐 있었다.

### (1) 안전 문제 — 감사가 production 코드를 실행해 증명한 것

`account_service_get()` 은 AccountService 는 읽혔지만 Accounts 컬렉션이 403/5xx/timeout
이거나 링크가 없으면 `(root, [], errors)` 를 돌려줬다. 호출자는 `errors` 를 검사하지 않고
`accounts == []` 를 "대상 계정 없음" 으로 읽어 **신규 생성 POST 를 실제로 보냈다.**
이미 있는 계정을 못 본 채 같은 이름으로 만들려 드는 상태다.

또 8/9 vendor 의 생성 경로는 HTTP 2xx 만 보고 `recovered=true` / `verification='none'` 을
반환했고, Ansible 게이트가 `'none'` 을 성공으로 인정했다. 실제로 쓸 수 없는 계정이
"복구됨" 으로 보고될 수 있었다.

### (2) 호환성 문제 — 9 Vendor 공식조사가 드러낸 것

같은 vendor 안에서도 계정 Write 계약이 갈린다.

```text
Lenovo XCC Purley      = 빈 slot PATCH        vs  Whitley/XCC2/XCC3/TSM = Collection POST
Cisco IMC              = RoleId 'admin'       vs  최신 Cisco BMC        = 'Administrator'
Cisco IMC 4.x          = 명시 Id 필요          vs  최신 Cisco BMC        = BMC 가 Id 할당
Supermicro X13 <01.05  = 공유 계정            vs  01.05+                = IPMI/Redfish 분리
HPE iLO4               = Oem/Hp               vs  iLO5+                 = Oem/Hpe
HPE iLO                                        vs  CSUS/Superdome        = RMC (iLO 아님)
Inspur M6              = HTTP 200 + Oem.Public.Status 0, PATCH 는 If-Match
```

코드에는 이 축이 **아예 없었다.** Adapter 43개가 세대를 정교하게 구분하는데 그 정보가
계정 코드에 한 번도 닿지 않았다. 대신 실패하면 다른 payload 로 순차 재시도하는
사다리(표준 POST → `PasswordChangeRequired:false` → `Oem.Hpe.Privileges`)로 때웠다.
9개 조사 문서가 **전부** 이 패턴을 명시적으로 금지했다: "Write 실패 후 다른 Write 방식
무작위 fallback 금지."

---

## 결정 (What)

### D1. 쓰기 전에 읽기로 Family 를 확정하고, 확정된 방식 **하나만** 실행한다

```text
ServiceRoot → AccountService → Accounts → Members → Roles → Manager(Firmware/Model)
    ↓ (읽기만)
Family 확정  (실제 Capability → Vendor → BMC Family → Firmware → Generation → Adapter hint)
    ↓
payload 를 한 번에 구성 → Write 1회 → 벤더 계약으로 응답 해석 → 재조회 → 재인증
```

Family 선택 근거의 우선순위가 핵심이다. **Generation 문자열 하나로 Write URI 를 정하지
않는다.** 예:
- Lenovo Purley 는 adapter 이름이 아니라 **pre-populated 빈 slot 관측**으로 판정한다.
- Cisco 는 **Roles Collection 이 실제로 노출한 RoleId 어휘**로 IMC / 최신 BMC 를 가른다.
- Supermicro 계정 분리 세대는 **AccountTypes 관측 또는 Firmware 경계**로 판정한다.

### D2. 계정 존재를 3-상태로 만든다

```text
enumeration : complete | incomplete | failed
presence    : present | absent | unknown | ambiguous
```

`absent` 는 **완전한 열거에 성공했고 그 안에 없을 때만** 확정한다. 403 / 5xx / timeout /
링크 부재 / member 일부 실패 / `Members@odata.count` 불일치는 전부 `unknown` 이며,
`unknown` 에서는 **Account Write 0건**이다.

### D3. 모든 쓰기 경로에 재조회 + 재인증을 의무화한다

`verification='none'` 은 **쓰기를 하지 않은 경우에만** 남는다. Ansible 게이트를
`verification == 'verified'` 로 좁혔다. Cisco 공식 문서조차 Create 뒤 "Verifying the User"
를 별도 단계로 제시한다.

### D4. 쓰기 성공을 HTTP status 하나로 판정하지 않는다

```text
공통          : 2xx AND 본문에 read-only 거부 없음
Inspur M6     : + Oem.Public.Status == 0
Dell iDRAC10  : 200 + 본문 read-only 거부 → 실패 (생성 경로에도 적용)
```

### D5. RoleId 를 vendor 이름으로 추측하지 않는다

Roles Collection 이 노출한 값 → Family role_map 결과가 그 안에 있음 → 기존 계정이 실제로
쓰는 값(대소문자 무시) → Family role_map → 원본. 순서대로 고른다.

### D6. 근거가 없는 Family 는 **현행 동작을 그대로 둔다** (사용자 결정)

Fujitsu S4/S5/S6, Quanta 전 세대, Cisco UCS X-Series, Lenovo IMM2, Supermicro X9,
Inspur M5/M7, HPE CSUS/Superdome RMC 는 `generic_collection_post` 로 접히고 종전 POST +
400/405 retry 를 유지한다. 매트릭스에는 `UNVERIFIED` 로 표기한다.

### D7. Lockout 은 쓰기측을 줄이고 후보 backoff 를 늘린다 (사용자 결정)

| | 종전 | 현재 |
|---|---|---|
| Dell 생성 슬롯 순회 | 3 | 1 |
| 표준 계정 실패 인증/run | 최대 9 | 최대 3 |
| 후보 간 backoff | 항상 5초 | **401 이면 65초**, transport 오류는 5초 |

BMC 의 Lockout 정책 자체는 **읽기만** 하고 바꾸지 않는다.

### D8. Password Policy 는 진단만 하고 차단하지 않는다 (사용자 결정)

정책을 읽어 `within_declared_bounds` 를 남기고 경고하되 쓰기는 시도한다. 거부되면
장비가 준 문장으로 원인을 확정한다. **비밀번호 길이 자체는 기록하지 않는다.**

### D9. ETag/If-Match 는 Family 가 요구할 때만 쓴다

기본은 계속 미사용이다(모듈 상단의 bmcweb If-Match crash 회피 근거 유지). Inspur M6 만
`etag_required=True` 이고, 412 를 받으면 ETag 재획득 후 **1회만** 재시도한다.

---

## 결과 (Impact)

### 코드

| 영역 | 변화 |
|---|---|
| 신규 | `account_service_discover` / `account_presence` / `_ACCOUNT_FAMILIES` / `resolve_account_family` / `choose_role_id` / `interpret_write_response` / `build_create_payload` / `_confirm_account_state` / `_accounts_write_uri` / `_get_response_etag` / `_patch_account` |
| 변경 | `account_service_get` 이 discover 의 얇은 wrapper 로 (3-tuple 계약 유지), `account_service_provision` 의 vendor 분기 → Family 분기 |
| 제거 | 생성 POST URI 하드코딩 5곳, HPE 전용 3차 retry, 전 Cisco RoleId 고정 remap |
| Ansible | `account_service.yml` 게이트 `verified` 전용 + meta 11 키 추가, `account_service_try_one.yml` adapter_id 전달 + 조건부 backoff, `try_one_account.yml` 조건부 backoff, `site.yml` C-2 분모 교정 |

### Contract

- **envelope 13 필드 / sections / field_dictionary 의미 변경 0** (rule 96 R1-B Additive only)
- 추가는 전부 `diagnosis.details.account_service` 하위
- 새 `failure_code` 없음 — Portal 5문장 집합 불변

### 테스트

2694 → 2794 passed (+100). 그중 43건은 **실장비 미러 재생**으로, 종전 0건이던 영역이다.

### 남은 것

실장비 Write E2E 는 여전히 미검증이다. 어떤 Family 도 `PROVEN` 이 아니다.

---

## 대안 비교 (Considered)

### A1. UNVERIFIED Family 의 CREATE 를 차단 — 채택 안 함

가장 안전하고, 조사 문서들의 "추측 Write 금지" 에 가장 충실하다. 그러나 현재 generic
POST 로 동작하던 장비가 있다면 그 자동 복구가 조용히 멈춘다. 근거 없이 **끄는 것**도
근거 없이 켜는 것과 같은 종류의 변경이다. 사용자가 "현행 유지 + UNVERIFIED 라벨" 을
선택했다.

### A2. Family 를 Adapter YAML 로 표현 — 채택 안 함

vendor 경계 원칙(rule 12)에는 더 맞는다. 그러나 (a) Family 판정에는 런타임 Resource
관측이 필요한데 Adapter 는 수집 시점 이전에 선택되고, (b) Adapter 의 `credentials:` /
`standard_tasks:` 키가 이미 죽은 필드로 남아 있어(audit L-2/L-3) 같은 실수를 반복할
위험이 있다. 대신 Adapter id 를 **hint 로만** 모듈에 넘기고, 판정 정본은 런타임 관측에 뒀다.

### A3. 계정 코드를 `module_utils/` 로 분리 — 이번에는 채택 안 함

`redfish_gather.py` 가 5,800줄을 넘어 rule 10 R3 관점에서 분리가 맞다. 그러나 이 모듈은
지금까지 `module_utils` 를 import 한 적이 없고, Jenkins agent 에서 그 import 경로가
동작하는지 이 환경에서 증명할 수 없다. 계정 기능을 고치는 작업에 배포 실패 위험을 얹지
않는다. `NEXT_ACTIONS` 의 기존 분할 항목으로 남긴다.

### A4. Write 기본값을 dry-run 으로 전환 — 채택 안 함 (사용자 결정)

운영 Job 에 dry-run override 가 없다는 사실(§ `d3e79167` dangling)을 알린 뒤 사용자가
"현재 기본값 유지" 를 선택했다. 안전은 dry-run 이 아니라 D2/D3/D7 로 확보한다.

### A5. Password 비호환 시 새 failure_code 신설 — 채택 안 함 (사용자 결정)

`CREDENTIAL_SET_UNAVAILABLE` 선례를 따라 `ACCOUNT_POLICY_INCOMPATIBLE` 을 추가하고
Portal 문장은 4번을 재사용하는 안을 제시했으나, 사용자가 "차단하지 않고 시도 후 응답
해석" 을 선택했다. 차단하지 않으므로 top-level 계약을 늘릴 이유가 없어졌다.
