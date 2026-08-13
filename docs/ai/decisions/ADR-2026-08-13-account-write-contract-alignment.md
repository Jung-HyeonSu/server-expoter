# ADR-2026-08-13 — 계정 쓰기를 "추측 후 재시도" 에서 "사전 확정 계약" 으로

상태: Accepted
결정자: hshwang1994 (사용자 결정 3건) + AI 초안
정본 근거: 9 Vendor Account Write Contract Delta Research (2026-08-12) 9건,
`tests/evidence/2026-08-13-account-write-contract-alignment.md`

---

## 1. 컨텍스트 (Why)

직전 cycle 에서 Capability Discovery + Family Strategy 를 도입했고 실장비 4대에서 Case A/B 를
증명했다. 그 위에서 9 Vendor 공식 조사를 수행하니 코드가 여전히 조사 결과와 충돌하는 지점이
셋 남아 있었다.

(a) 추측성 재시도가 남아 있었다. 공식 Write 계약을 확보하지 못한 Family 에서 POST 가
400/405 로 거부되면 `PasswordChangeRequired:false` 를 덧붙여 다시 POST 했고 PATCH 가 속성을
거부하면 그 속성을 빼고 다시 PATCH 했다. 그런데 그 경로에 속한 Vendor 들(Fujitsu, Quanta,
Cisco X-Series, Lenovo IMM2, Supermicro X9, Inspur M5/M7, HPE RMC)이 하나같이 그 재시도를
금지했다(05 §19, 06 §17, 07 §17, 08 §17, 09 §19). 즉 "근거가 없으니 여러 번 시도한다" 는
정반대였다. 근거가 없을수록 한 번만 써야 한다.

(b) 한 장비의 실측이 세대 전체로 번졌다. `hpe_ilo5plus` 하나가 iLO5/6/7 전 Firmware 를
`evidence='proven'` 으로 덮었는데 실제로 재현한 것은 iLO6 v1.73 한 버전이다. HPE
Advisory `a00159600en_us` 는 iLO6 1.73/1.74 + iLO7 1.19/1.20 을 영향 버전으로, iLO6 1.75+ /
iLO7 1.21+ 를 해결 버전으로 명시한다. iLO5 는 어느 쪽 근거도 없다.

(c) 판정 축이 틀렸다. 보호 계정을 slot id 문자열(`'HostBootStrap'`)로 맞히려 했는데
그 값은 collection POST Family 에서는 소비되지 않아 죽은 값이었다. 실제로는
`HostBootstrapAccount` 가 DMTF ManagerAccount 표준 Property 이고 실미러 10.50.11.232 의 계정
3개에 존재한다. XCC3 전용 개념이 아니다.

---

## 2. 결정 (What)

### D1. 무엇을 보낼지는 쓰기 전에 정한다

Family × Operation 별 Property Contract 를 데이터로 선언한다.

```text
writable    쓸 수 있다 (실제 drift 가 있을 때만 보낸다)
read_only   장비가 노출하지만 쓸 수 없다 — 보내지 않고 대조만
verify_only 쓰기 대상이 아니지만 반드시 확인해야 한다
unsupported 이 Family 에 존재하지 않는다
unverified  계약 미확보 — 자동으로 쓰지 않는다
```

표에 없는 Property 의 기본값은 `unverified` 다. 모르는 속성의 writable 가정은 금지다.

### D2. Blind write fallback 을 전부 제거한다

허용되는 다중 쓰기는 둘뿐이고 둘 다 fallback 이 아니다.

```text
(A) ETag 412 concurrency retry — 동일 URI + 동일 Payload + 새 ETag, 1회
(B) Family 가 쓰기 전에 확정한 sequence — HPE Password 단독 → drift 속성만 후속
```

예상하지 못한 거부가 오면 실패로 확정하고 기록한다. 두 번째 쓰기는 없다.

### D3. 동작과 근거를 분리한다 (HPE)

Family 는 하나로 유지한다. 쓰기 동작(Password 단독 PATCH)은 iLO5/6/7 전부 같고 `isolation_basis`
로 근거만 갈린다: `live_proven` / `advisory_derived` / `safety_strategy`.
`safety_strategy` 와 `advisory_derived` 를 Vendor mandatory 나 LIVE-PROVEN 으로 표기하지 않는다.

### D4. Repair 기본은 drift-only, full body 는 Family 예외 (사용자 결정)

기본은 `full_body_patch=False`, 실제로 달라진 것만 쓴다. `True` 는 그 Family 에서 writable 로
확인된 상태 Property 를 Password 와 함께 보내야만 하는 예외를 가리킨다. "공통 Property 를 전부
보내라" 는 지시가 아니다. LIVE/공식 근거가 있는 Family 에만 명시한다.

현재 예외는 `lenovo_xcc2_accounttypes` / `lenovo_xcc3_accounttypes` 두 곳뿐이다.
사이트 실측(10.50.11.232)에서 Password 단독 PATCH 시 권한 cache 가 손상됐다.
이 실측을 다른 Vendor/Family 의 기본 동작으로 일반화하지 않는다.
UNVERIFIED Family 에는 이 예외가 없다. `True` 여도 read_only/unsupported/unverified
Property 는 실리지 않는다.

### D5. Create URI 를 Accounts 열거 URI 와 분리한다

`accounts_collection` / `account_service_root` / `account_instance` 세 종류. 어느 경우에도
하나가 실패했다고 다른 URI 로 갈아타는 경로는 없다. Supermicro 최신 계약(`POST /AccountService`)은
Generation + Firmware 를 장비가 준 값으로 확정했을 때만 적용하고 확정하지 못하면 구
Reference Guide 계약 하나만 쓰면서 `unverified` 로 표기한다.

### D6. If-Match 는 Operation 단위 계약이다

Family 공통 boolean 을 `{'create': …, 'repair': …}` 로 바꿨다. Inspur M6 공식 계약은
Create = POST Collection(If-Match 없음) / Repair = PATCH Instance + If-Match 다.
현재 Create 에 If-Match 를 요구하는 Family 는 없다(테스트로 고정).

### D7. 보호 계정은 Resource Property 로 판정한다

`HostBootstrapAccount == true` 를 근거로 `protected` 분류한다. 열거와 진단에는 남기고
Create/Repair 후보에서만 제외한다. 목록에서 지우면 "없는 계정" 이 되어 오히려 생성 쓰기를
유발한다. 표준 계정 이름이 겹치면 `protected_conflict` → **Write 0**.

`reserved_slot_ids` 는 이 판정의 근거가 아니다. 그 값이 정하는 것은 "생성할 때 이 슬롯은
고르지 마라" 까지다. "그 슬롯의 계정은 고칠 수 없다" 는 뜻으로 섞어 쓰면 예약 슬롯에 자리 잡은
표준 계정을 영영 복구하지 못한다.

### D8. 진단은 늘리되 정책은 바꾸지 않는다

Huawei 계정별 Redfish Login Interface, `HTTPBasicAuth` / OEM `AuthMethods`, `policy_conflict`,
계정 잠금 전 검증 중단, 미지원 RoleId 는 전부 읽기·보고 전용이다. Basic Auth 를 켜지도,
잠금 정책을 완화하지도, 비밀번호를 바꾸거나 회전시키지도 않는다.

---

## 3. 결과 (Impact)

### 3.1 코드

| 신규 | `_ACCOUNT_PROP_DEFAULTS` · `account_prop_contract()` · `account_prop_writable()` · `account_if_match()` · `_create_target_uri()` · `write_rejections()` · `hpe_isolation_evidence()` · `account_is_protected()` · `account_auth_budget()` · `_account_login_interfaces()` |
|---|---|
| 제거 | `_ACCOUNT_CREATE_STRATEGY` · `_account_create_method_for_vendor()` · `ACCOUNT_OPTIONAL_PATCH_PROPS` · `legacy_post_retry` · drop-and-retry 사다리 |
| Family | 14 → **17** (`lenovo_xcc2/xcc3` 분리, `cisco_cimc3_instance_post`, `qct_legacy/modern/inhouse_openbmc` 추가) |

### 3.2 계약

- envelope 13 필드 **불변**. 신규 진단은 전부 `diagnosis.details.account_service` 하위(Additive).
- Ansible 성공 게이트(`verification == 'verified'`) 변경 없음.
- 진입 게이트(401 전용) 변경 없음.

### 3.3 테스트

2843 → **3063 passed**. 신규 3파일:
`test_account_no_write_fallback.py`(27) / `test_account_diagnosis_axes.py`(15) /
`test_account_write_contract_invariants.py`(146, Family 표 전수).

반전한 테스트 2건은 제거 대상 동작을 고정하고 있었다:
`test_unverified_family_keeps_the_legacy_post_retry` → `..._writes_once_and_never_retries`,
`test_m_b3_inspur_isbmc_post_400_then_retry` → `..._writes_once_and_fails`.

### 3.4 실장비

git 4대 × (Check Mode + 1차 + 2차) 전부 `success` / `used_role=primary` / **Account Write 0**.
Create / Repair 는 조건이 발생하지 않아 미증명이다. 4대 모두 표준 계정이 이미 정상이고
조건을 만들려면 운영 계정을 지워야 하므로 하지 않았다.

Supermicro / Huawei / Inspur / Fujitsu / Quanta 는 실장비 0대다. 어느 Family 도 PROVEN 으로
올리지 않았다.

---

## 4. 대안 비교 (Considered)

| # | 대안 | 채택 | 이유 |
|---|---|---|---|
| A1 | UNVERIFIED Family 의 재시도를 그대로 유지 (직전 cycle 결정) | **아니오** | 9 Vendor 조사가 바로 그 Family 들에 대해 재시도를 명시적으로 금지했다. 결정의 전제가 바뀌었다 |
| A2 | HPE 를 Firmware 별 4 Family 로 분할 | **아니오** | 쓰기 동작이 같은데 Family 를 쪼개면 표만 커지고 회귀 위험이 는다. 갈리는 것은 근거뿐이라 metadata 로 분리했다 |
| A3 | drift-only 를 포기하고 full body 를 기본으로 | **아니오** (사용자 결정) | Lenovo XCC 실측은 그 Family 의 예외지 다른 Vendor 의 기본이 아니다. 한 Family 실측을 일반화하지 않는다 |
| A4 | `PasswordChangeRequired` 를 droppable 목록에 넣어 거부 시 제거 | **아니오** | 그것도 "보내 보고 거부되면 뺀다" 는 추측성 재시도다. read_only 면 처음부터 보내지 않는 것이 정답 |
| A5 | Supermicro 최신 Create URI 를 즉시 전환 | **아니오** | 어느 Firmware 부터 유효한지 확정하지 못했다. 축만 만들고 장비값 근거가 있을 때만 전환한다 |
| A6 | 보호 계정을 열거 결과에서 제거 | **아니오** | 목록에서 지우면 "없는 계정" 이 되어 오히려 생성 쓰기를 유발한다. 후보에서만 뺀다 |
| A7 | Huawei Redfish Login Interface 를 자동 복구 | **아니오** | 켜는 OEM payload 가 공식 자료에서 확인되지 않았다. 추측해서 쓰지 않는다 |
| A8 | `account_service_provision()` 을 `module_utils/` 로 분리 | **보류** | `redfish_gather.py` 가 6,900줄을 넘어 rule 10 R3 관점에서 분리가 맞지만 Jenkins agent import 경로가 미검증이라 별도 작업으로 남긴다 |

---

## 5. 남긴 것

- **Account CREATE 실장비 증명** — 조건을 인위적으로 만들지 않는다(운영 계정 삭제 금지).
- **실장비 부재 5 Vendor** — Supermicro / Huawei / Inspur / Fujitsu / Quanta.
- **조사 필요** — Fujitsu API Pack 원문, Supermicro `/AccountService` POST Firmware 경계,
  Huawei Login Interface OEM field, Cisco IMC allowable Id 범위.
- **Adapter 세대 오선택(PWC-4)** — 계정 경로는 Firmware 로 판정해 영향받지 않지만 `adapter_id`
  자체는 여전히 틀린다.
- **Global Password 정책 교집합** — Cisco Strong(max 14) ↔ Inspur min(최대 16)이 수학적으로
  충돌할 수 있다. 코드는 `policy_conflict` 로 보고만 하며 정책 선택은 운영/아키텍트 결정이다.
