# Evidence — Redfish 표준 계정 Reconcile 최종 호환성 작업

작성일: 2026-08-12
기준 Commit: `5e72ac05`
대상: 9 Vendor 공식조사 반영 + `docs/ai/contracts/redfish-account-asis.md` 잔여 결함 해소

---

## 0. 먼저 — 이 작업에서 하지 못한 것

**실장비 요청 0건. Account Write 0건. `ansible-playbook` 실행 0건.**

통제 노드는 Windows 이고 BMC 로 나가는 경로가 없다. Windows 에서는 `ansible-playbook`
CLI 자체가 동작하지 않는다(`os.get_blocking` 미지원). 따라서:

- 실장비 Capability Probe → **하지 못함**
- dry-run 실행 → **하지 못함**
- 통제된 1대 Write → **하지 못함**
- 2차 실행 Write 0 실증 → **하지 못함**

이 네 가지는 §5 에 사용자가 수행할 절차로 정리했다.
**어떤 Family 도 이번 작업만으로 `PROVEN` 으로 올리지 않았다.**

---

## 1. 현재 HEAD 전수조사 결과 (Audit finding 분류)

Audit 은 commit `020e3146` 기준이다. 그 이후 `5e72ac05` 까지 `redfish_gather.py` 변경은
**+88 line 뿐**이며 전부 Dell body-level rejection 처리였다. 직접 확인한 분류:

| ID | 내용 | HEAD 상태 | 처리 |
|---|---|---|---|
| C-1 | Accounts 조회 실패를 "계정 없음" 으로 오판 → 실제 CREATE | STILL_PRESENT | **수정** — 3-상태 열거 + presence 4-상태 |
| C-2 | 복구 후보가 있으면 `auth_success` 가 false 로 확정 불가 | STILL_PRESENT | **수정** — 분모를 `_rf_standard_accounts` 로 |
| H-1 | 8/9 vendor 가 검증 없이 `recovered=true` | STILL_PRESENT | **수정** — 전 경로 재조회+재인증 의무화, 게이트 `verified` 전용 |
| H-2 | `--check` 가 실제 Write | STILL_PRESENT | **수정** — `module.check_mode` 를 dryrun 에 OR |
| H-3 | Capability Discovery 부재 | STILL_PRESENT | **수정** — `account_service_discover()` 신설 |
| H-4 | 운영 기본값이 실쓰기 | **FULLY LIVE** | **변경 안 함** (사용자 결정) — §4 참조 |
| H-5 | `empty_accounts` 가 `GATHER_FAILED` 로 샘 | STILL_PRESENT | **변경 안 함** — Portal 문장 5→4 변경이라 Consumer 결정 필요 |
| H-6 | 문서 3종 모순 | PARTIAL | **수정** — `CLAUDE.md` §6/§8 + 설계문서 정정 |
| H-7 | Phase 3 실행 테스트 0건 | STILL_PRESENT | 부분 완화 — 모듈 계약 테스트는 추가, playbook 실행 테스트는 여전히 0건 |
| H-8 | 복구 후보 loop 무테스트 | STILL_PRESENT | 부분 완화 — backoff 분기 테스트 추가, loop 자체는 여전히 미실행 |
| M-1 | 빈 슬롯 판정이 `UserName` falsy 하나에 의존 | STILL_PRESENT | **수정** — `has_username_key` + `Enabled` 교차 확인 |
| M-2 | Cisco 빈 Id 스캔이 읽기 실패 slot 을 미사용으로 간주 | STILL_PRESENT | **수정** — 열거 complete 일 때만 도달 |
| M-5 | Dell cleanup PATCH 응답 미검사 | STILL_PRESENT | **수정** — 되돌리기 실패를 errors 에 남김 |
| M-7 | POST 응답 body 폐기 | STILL_PRESENT | **수정** — POST 경로도 `write_response_info` 채움 |
| M-8 | `AccountTypes` 미처리 / `role_id` 비교 안 함 | STILL_PRESENT | **수정** — Family 요구 시 수렴, RoleId 는 Roles 에서 선택 |
| M-9 | account 테스트가 `time.sleep` 미차단 (수트 50초 중 48초) | STILL_PRESENT | **수정** — autouse fixture (수트 66s → 18s) |
| L-1 | `_ACCOUNT_CREATE_STRATEGY` 죽은 코드 | STILL_PRESENT | 유지 — 문서용으로 남기고 실제 분기는 `_ACCOUNT_FAMILIES` 로 이관 |
| — | Create POST URI 5곳 하드코딩 (신규 발견) | STILL_PRESENT | **수정** — discovery 의 `accounts_uri` 사용 |
| — | Write payload 재시도 사다리 (연구문서 전 vendor 금지) | STILL_PRESENT | **수정** — 근거 있는 Family 는 단일 payload, UNVERIFIED 만 현행 유지 |
| — | Dell create PATCH 가 body rejection 미검사 (신규 발견) | STILL_PRESENT | **수정** — 생성 경로에도 적용 |

### 9개 Vendor 문서 Finding 분류

모든 문서가 공통으로 지적한 5건(Enumeration / Create Verification / Capability Discovery /
Write fallback / Lockout)은 위 표로 처리됐다. Vendor 고유 지적의 분류:

| Vendor 고유 Finding | 분류 | 처리 |
|---|---|---|
| Dell iDRAC10 Reserved slot 2 | STILL_PRESENT | 수정 (`dell_idrac10_slot_patch`) |
| HPE iLO4 `Oem/Hp` vs `Oem/Hpe` | STILL_PRESENT | 수정 (`hpe_ilo4`) |
| HPE CSUS/Superdome ≠ iLO | STILL_PRESENT | 수정 (generic 으로 분리, iLO payload 차단) |
| Lenovo Purley = 빈 slot PATCH | STILL_PRESENT | 수정 (`lenovo_purley_slot_patch`) |
| Lenovo TSM PasswordChangeRequired default true | STILL_PRESENT | 수정 (POST 에 항상 `false` 명시) |
| Lenovo XCC2/3 AccountTypes | STILL_PRESENT | 수정 (`lenovo_xcc_accounttypes`) |
| Cisco 최신 BMC RoleId = `Administrator` | STILL_PRESENT | 수정 (Roles 어휘 기반 선택) |
| Cisco 최신 BMC Id 를 client 가 정하지 않음 | STILL_PRESENT | 수정 (`needs_explicit_id`) |
| Cisco IMC 3.x instance POST | STILL_PRESENT | **NEEDS_EVIDENCE** — generic 유지 |
| Supermicro X13/X14 계정 분리 | STILL_PRESENT | 수정 (`supermicro_split_account`) |
| Supermicro 최신 `/AccountService` POST | STILL_PRESENT | **NEEDS_EVIDENCE** — Firmware 경계 미확보로 미도입 |
| Inspur `Oem.Public.Status` | STILL_PRESENT | 수정 (`inspur_oem_status`) |
| Inspur PATCH If-Match | STILL_PRESENT | 수정 (Family gated ETag) |
| Inspur PasswordChangeRequired 근거 없음 | STILL_PRESENT | 수정 (근거 있는 Family 만 전송) |
| Huawei Redfish Login Interface | STILL_PRESENT | **NEEDS_EVIDENCE** — OEM 계약 미확보로 미구현 |
| Huawei PasswordChangeRequired 근거 없음 | STILL_PRESENT | 수정 (`huawei_ibmc` 는 보내지 않음) |
| Fujitsu RedfishAdmin Role 체계 | STILL_PRESENT | **NEEDS_EVIDENCE** — RoleId 는 Roles 에서 선택하도록만 개선 |
| Fujitsu / Quanta Create 계약 | 미확보 | **NOT_APPLICABLE (이번 범위)** — 현행 유지 + UNVERIFIED |

---

## 2. 정적 검증 — 실행 결과

### 2.1 테스트

기준선(변경 전, 직접 측정):

```text
tests/unit + tests/regression : 1907 passed, 7 xfailed        (66.55s)
tests/e2e                     :  587 passed, 6 skipped        (13.07s)
tests/integration -m not live :  200 passed, 3 skipped, 1 deselected (1.71s)
합계                          : 2694 passed
```

변경 후:

```text
tests/unit + tests/regression : 1961 passed, 7 xfailed        (18.05s)
tests/e2e                     :  590 passed, 6 skipped        (12.46s)
tests/integration -m not live :  243 passed, 3 skipped, 1 deselected (2.75s)
합계                          : 2794 passed  (+100)
```

- 실패 0건. 기준선 대비 감소 0.
- unit+regression 실행 시간이 **66.55s → 18.05s** 로 줄었다 — audit M-9(계정 테스트가
  `time.sleep` 을 monkeypatch 하지 않아 8개 테스트가 각 6초 블로킹)의 부수 효과다.
- **디렉터리를 분리 호출해야 한다.** `tests/e2e` 와 `tests/integration` 이 같은 top-level
  모듈명 `conftest` 를 쓰기 때문에 한 번에 부르면 collection error 가 난다
  (`Jenkinsfile:234-236` 와 같은 이유). 실제로 한 번에 불러 6 errors 를 재현했다.

### 2.2 Ansible syntax-check (WSL Ubuntu, ansible-core 2.20.7)

```text
os-gather/site.yml       exit=0
esxi-gather/site.yml     exit=0
redfish-gather/site.yml  exit=0
```

Windows 로컬에는 `ansible-playbook` 이 동작하지 않는다(`AttributeError: module 'os' has
no attribute 'get_blocking'`). WSL 의 ansible-core 2.20.7 로 수행했다.

### 2.3 게이트

```text
python -m py_compile redfish-gather/library/redfish_gather.py   OK
python scripts/ai/verify_vendor_boundary.py                     exit=0  (13건 nosec rule12-r1 표기 후)
python scripts/ai/verify_harness_consistency.py                 exit=0  (rules 28 / skills 51 / agents 60 / policies 10)
python scripts/ai/hooks/output_schema_drift_check.py            exit=0  (sections=11 fd_paths=176)
python tests/validate_field_dictionary.py                       PASS    (10 checks, 8 passed, 0 failed)
python scripts/ai/vault_decrypt_check.py --layout-only          exit=0  (4 location × 12/12)
```

`verify_vendor_boundary` 는 처음에 **13건 위반**을 보고했다 — 새 `resolve_account_family()`
안의 vendor 이름이다. rule 12 R1 의 Allowed 방식대로 각 라인에 `# nosec rule12-r1` 을
붙였다. 이 위치는 기존 `_ACCOUNT_CREATE_STRATEGY` / vendor 분기와 같은 성격의 경계다.

### 2.4 Secret 검사

- `vault/` 변경 0건 (`git status --short -- vault/` 비어 있음)
- 변경/신규 파일에 평문 password 패턴 0건
- `vault_decrypt_check.py` 전체 모드는 **마스터 키가 없어 실행 불가**(exit 2, `[ERROR] 마스터
  키를 찾지 못했다`). `--layout-only` 로만 확인했다. 이 작업은 vault 를 건드리지 않았다.
- 새 진단 필드에 비밀번호를 담지 않는다. **길이도 담지 않는다** — `within_declared_bounds`
  boolean 만 남긴다(길이는 탐색 공간을 줄여 주는 약한 누출이다). 이를 고정하는 테스트:
  `test_policy_never_records_password_length`.

---

## 3. 실장비 미러 재생 (Fixture Replay) — 이번에 새로 얻은 근거

audit D-8: `tests/reference/redfish/**/redfish_v1_accountservice*.json` 을 읽는 테스트가
**0건**이었다. 계정 동작이 전부 손으로 쓴 mock 으로만 검증되고 있었다.

`tests/integration/test_account_reconcile_replay.py` 로 연결했다. 실제로 재생한 호스트:

| Vendor | 미러 호스트 | 확인된 것 |
|---|---|---|
| Dell | `10_100_15_27`, `_28`, `_31`, `_33`, `_34` | AccountService(16 slot, `Members@odata.count=16`) 완전 열거, `MinPasswordLength=0/Max=127`, slot PATCH Family 확정, reserved slot 1 보호 |
| HPE | `10_50_11_231` (iLO6) | 완전 열거, Family = `hpe_ilo5plus` |
| Lenovo | `10_50_11_232` (XCC 1.15) | 완전 열거, Family 결정성 |
| Cisco | `10_100_15_2` (CIMC v1_6_0) | 완전 열거, **Roles 어휘 기반 RoleId 선택이 장비 지원 값 안에 든다** |

각 호스트에 대해 4종 검증 × 8 호스트 + Dell/Cisco 고유 2건 + fixture 정책 파싱 9건
= **43 tests passed**.

가장 중요한 재생 결과: **컬렉션 GET 만 403 으로 바꾸면 8/8 호스트 전부 `presence=unknown`**
이 된다. 종전 코드는 같은 상황에서 `accounts=[]` → "계정 없음" → **실제 생성 POST** 로
갔다(audit C-1 이 production 함수를 직접 실행해 증명한 그 경로다).

lab 부재 vendor(Supermicro / Huawei / Inspur / Fujitsu / Quanta)는 `account_service.json`
mock fixture 9건의 **정책 필드 파싱만** 확인했다. 이것은 동작 증명이 아니다.

---

## 4. 운영 위험 — 그대로 남겨 둔 것

사용자 결정(2026-08-12)에 따라 **쓰기 기본값을 바꾸지 않았다.**

확인된 사실:
- `Jenkinsfile_portal:219` 는 `-e se_location="${env.SE_LOCATION}"` 만 넘긴다.
- dry-run override 를 추가했던 `d3e79167` 은 **어느 브랜치에도 없다**
  (`git branch -a --contains d3e79167` 결과 없음 — dangling commit).
- `account_service.yml` 은 `_rf_account_service_dryrun` 이 정의되지 않으면
  `dryrun = not _rf_account_reconcile_allowed` 로 계산하고, 이 파일은 allowed 일 때만
  실행되므로 **실행되는 순간 항상 실쓰기**다.

⇒ **게이트(표준 401 + 복구 후보 존재)가 열리면 운영에서 실제 BMC 계정 Write 가 나간다.**
이번 변경 후에도 그대로다. 안전은 dry-run 이 아니라 다음으로 확보된다:

- 계정 목록을 완전히 읽지 못하면 쓰기 0건 (presence unknown)
- 쓰기 방식은 읽기로 확정한 뒤 하나만 실행 (무작위 fallback 제거)
- 쓰기 후 재조회 + 재인증을 통과해야만 성공
- 표준 계정 실패 인증이 run 당 최대 9회 → 3회

수동 실행에서 안전하게 보려면 `-e _rf_account_service_dryrun=true` 또는
`ansible-playbook --check` 를 쓴다. `--check` 는 이번에 실제로 쓰기를 막도록 연결됐다.

---

## 5. 사용자가 수행해야 하는 검증 (이 환경에서 불가)

순서를 지킨다. 앞 단계가 통과하지 않으면 다음으로 가지 않는다.

### 5-1. Read-only Capability Probe (Write 0건)

```bash
# 대상 1대, dry-run 강제. 계정 쓰기가 한 건도 나가지 않는다.
ansible-playbook redfish-gather/site.yml -i <inventory> \
  --vault-password-file <file> \
  -e se_location=<loc> -e _rf_account_service_dryrun=true
```

envelope 에서 확인:

```text
diagnosis.details.account_service.presence      → present | absent  (unknown 이면 여기서 중단)
diagnosis.details.account_service.family        → 어떤 Family 로 판정했는가
diagnosis.details.account_service.evidence      → proven | documented | unverified
diagnosis.details.account_service.create_method → slot_patch | collection_post | ...
diagnosis.details.account_service.policy        → 장비가 선언한 길이/lockout
diagnosis.details.account_service.dryrun        → true
diagnosis.details.account_service.verification  → skipped
```

`presence=unknown` 이면 복구 계정의 사용자 관리 권한부터 확인한다. **이 상태에서 실쓰기로
넘어가면 안 된다.**

### 5-2. `--check` 가 쓰기를 막는지 확인

```bash
ansible-playbook redfish-gather/site.yml -i <inventory> --check ... 
```
`diagnosis.details.account_service.dryrun_reason == "check_mode"` 이고 계정 쓰기 0건이어야 한다.

### 5-3. 통제된 1대 실쓰기

```bash
ansible-playbook redfish-gather/site.yml -i <inventory> \
  --vault-password-file <file> \
  -e se_location=<loc> -e _rf_account_service_dryrun=false
```

성공 판정:

```text
diagnosis.details.account_service.write_accepted == true
diagnosis.details.account_service.verification   == "verified"
diagnosis.details.account_service.post_write_state 의 username/enabled/role 이 기대와 일치
status == "success"  이고  최종 수집이 표준 계정으로 수행됨
```

### 5-4. 2차 실행 Write 0 (idempotency)

같은 대상에 5-3 을 한 번 더 실행한다. 표준 인증이 성공하므로 게이트가 닫힌다:

```text
diagnosis.details.account_service.attempted == false  (또는 account_service 키 자체가 없음)
Account Write 0건
status == "success"
```

### 5-5. Family 확장

한 Family 가 5-1~5-4 를 통과하면 그 Family 만 `PROVEN` 으로 올린다.
다른 Family 는 같은 절차를 처음부터 다시 밟는다.

### 5-6. Dell 은 HOLD 유지

Dell 표준 비밀번호가 iDRAC Security Strengthen Policy 를 만족하지 못하는 상태(E-6)가
해소되기 전에는 5-3 을 Dell 에서 수행하지 않는다.

---

## 6. Production 승격

**하지 않았다.**

사용자 지시 §20 의 승격 조건 중 미충족:

| 조건 | 상태 |
|---|---|
| 전체 테스트 PASS | ✅ 2794 passed |
| 기존 Credential Contract 회귀 없음 | ✅ 기준선 대비 감소 0 |
| Recovery final Gathering 0건 | ✅ 구조적으로 불가 (기존 계약 유지, 테스트로 고정) |
| P0 Enumeration 안전성 증명 | ✅ 실미러 8호스트 + 단위 테스트 |
| Vendor Strategy 선택 deterministic | ✅ 실미러 재생으로 고정 |
| 검증 없는 Write success 0건 | ✅ 게이트가 `verified` 만 인정 |
| **Controlled Pilot PASS** | ❌ 실장비 접근 불가 |
| **2차 실행 Write 0 증명** | ❌ 실장비 접근 불가 |
| **Dell HOLD 운영 결정** | ❌ 미결정 (E-6) |

승격은 §5 절차가 끝난 뒤 `bash scripts/ai/promote_to_production.sh` 로 수행한다.

---

## 7. 이번 작업이 만든 새 위험 (정직 기록)

1. **UNVERIFIED Family 의 동작을 바꾸지 않기로 한 결과**, Fujitsu / Quanta / X-Series /
   IMM2 / Supermicro X9 / Inspur M5·M7 / HPE RMC 는 여전히 근거 없는 generic POST 를 쓴다.
   지금까지와 같으므로 회귀는 아니지만 "지원한다" 고 말할 수 없다.
2. **후보 backoff 를 5초 → 65초로 늘렸다** (401 일 때만). Dell 복구 후보 4개가 전부 실패하는
   최악의 경우 약 3분이 추가된다. Jenkins Gather stage timeout(60분) 대비 여유가 있으나
   실측하지 않았다. `-e _rf_auth_backoff_seconds=<n>` 으로 조절할 수 있다.
3. **Dell 생성 시 슬롯 순회를 3 → 1 로 줄였다.** 첫 빈 슬롯이 PATCH 를 거부하는 펌웨어가
   있으면 종전에는 다음 슬롯에서 성공했을 수 있다. lockout 위험(최대 9회 실패 인증)과
   맞바꾼 결정이며, 실패 시 어느 슬롯이 왜 거부했는지가 `errors[].detail` 에 남는다.
4. **`rejected_patch_properties` 를 MessageId 기준으로 좁혔다.** 좁힌 목록에 없는
   MessageId 로 read-only 거부를 표현하는 펌웨어가 있으면 놓칠 수 있다. 다만 문장
   정규식(`property X is a read only`) 경로는 그대로라 Dell 실측 사례는 계속 잡힌다.

---

## 8. 관련 문서

- `docs/ai/contracts/redfish-account-compat-matrix.md` — Vendor × Family 매트릭스
- `docs/ai/decisions/ADR-2026-08-12-account-family-strategy.md` — 설계 결정과 대안
- `docs/ai/contracts/redfish-account-asis.md` — 본 작업의 입력이 된 전수조사
- `tests/evidence/2026-08-12-redfish-standard-account-separation.md` — 직전 cycle 실장비 결과 (Dell 2층 원인)
