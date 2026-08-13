# Evidence — Redfish 표준 계정 전역화 + 복구 분리 + Vault Hard Cut (2026-08-12)

> 기준 commit: `adc99570` (+ 이후 문서 commit). Jenkins Job `clovirone-server-gather-vault-pilot`.
> 실 Jenkins + 실 encrypted Vault + 실장비 결과다. Secret 값은 이 문서 어디에도 없다.

## 0. 한눈에

| 항목 | 결과 |
|---|---|
| 표준 계정 전역화 (`vault/common/redfish/standard.yml`) | [PASS] |
| 복구 계정 Location+Vendor 분리 | [PASS] |
| 중복 표준 자격 제거 | [PASS] 36벌 → 1벌 |
| 최종 Gathering 이 표준 계정인가 | [PASS] 6/6, recovery 수집 0건 |
| Dell reconcile 실패 Root Cause | [PASS] 규명 — 2층 원인 |
| 코드 수정 | [PASS] 3건 (아래 §5) |
| Dell 재검증 | **[HOLD]** 코드 원인은 해소, **자격 값 문제 잔존** (§6) |
| flat vault 12개 삭제 | [PASS] |
| runtime flat / cross-scope 참조 | [PASS] 0건 |
| Secret 비노출 | [PASS] |
| HPE | **[HOLD]** BMC 443 timeout (환경) |
| Production 승격 | **[HOLD]** — §11 |

## 1. 표준 계정 전역화

### 왜 전역인가 — 실측 근거

이관 전 9개 vendor vault 의 `role: primary` 를 전수 비교한 결과 **9개가 완전히 동일**했다
(distinct digest 1개). Location 4벌까지 더하면 같은 계정이 **36벌** 중복돼 있었고,
비밀번호를 바꾸려면 36곳을 고쳐야 했다. 축이 하나뿐인 값에 축을 두 개 준 상태였다.

### TO-BE 구조

```
vault/
  common/redfish/standard.yml        ← 표준 수집 계정 (role: primary 1개)  [전역 1벌]
  <loc>/redfish/<vendor>.yml         ← 복구 계정 (role: recovery 만)       [36벌]
  <loc>/os/{linux,windows}.yml       ← 변경 없음
  <loc>/esxi.yml                     ← 변경 없음
  .lab-credentials.yml               ← 유지 (resolver 대상 아님)
```

| | 이관 전 | 이관 후 |
|---|---|---|
| 표준 자격 사본 수 | 36 (9 vendor × 4 loc) | **1** |
| 복구 vault 안의 표준 자격 | 있음 (`accounts[0]` + legacy `ansible_user`) | **없음** |
| vault 파일 수 | 60 (flat 12 + loc 48) | **49** (standard 1 + loc 48) |

legacy `ansible_user`/`ansible_password` 키도 9개 vault 전부에서 표준 계정 복제본이었다.
복구 vault 에서 함께 제거했다 (`normalize_accounts` 가 legacy 를 `role=primary` 로 만들기 때문에
남겨두면 표준 계정 대용으로 쓰일 여지가 생긴다).

### Resolver 계약

```
표준: resolve_redfish_credentials(...) → common/redfish/standard  (상수 — location/vendor 를 보지 않는다)
복구: → <loc>/redfish/<vendor>
```

표준 경로를 **상수**로 둔 이유: 함수 인자로 location/vendor 를 받으면 "언젠가 갈릴 수 있다" 는
여지가 코드에 남고, 그 여지가 36벌 중복의 원인이었다. 상수면 중복이 구조적으로 불가능하다.

## 2. 인증 후보 순서

```
[0] common_infraops   primary    ← vault/common/redfish/standard.yml
[1] dell_fallback_1   recovery   ┐
[2] dell_fallback_2   recovery   │ vault/<loc>/redfish/dell.yml 배열 순서 그대로
[3] dell_current      recovery   │
[4] lab_dell_root     recovery   ┘
```

두 배열 **내부** 순서는 각각 그대로다. role 기반 재정렬은 하지 않았다.
9 vendor 의 recovery 순서가 이관 전후 동일함을 복호화 대조로 확인했다.

## 3. 최종 Gathering 주체 — Contract 강제

### AS-IS 의 결함 (2026-08-12 Pilot 실사고)

Dell 10.100.15.34 에서 표준 계정이 401 인데 **recovery 계정으로 9개 섹션을 수집**하고
`status=success` 를 냈다. 계정 정리는 실패(`verification=failed`)했는데도 결과는 성공이었다.
`_rf_collect_ok` 가 "누구로든 수집이 됐다" 만 뜻했기 때문이다.

### TO-BE 흐름

```
Phase 1  표준 계정으로 수집          → 성공하면 끝
   ↓ (표준 401 로 명시 거부 + 복구 후보 있음)
Phase 2  복구 계정으로 인증 + 계정 정리   ← 수집하지 않는다
   ↓ (recovered=true AND dryrun=false)
Phase 3  표준 계정으로 재인증 + 재수집
   ↓
최종 수집 주체 검증: role == 'recovery' 면 실패 처리
```

구조적 보장 3중:
1. `collect_standard.yml` 에 넘기는 후보는 항상 `_rf_standard_accounts` 뿐이다
2. 복구 경로(`account_service*.yml`)에는 `mode: account_provision` 호출만 있고 수집이 없다
3. `abort if final gathering not by standard account` — `role == 'recovery'` 면 실패

셋 다 테스트로 고정했다 (`test_redfish_standard_recovery_contract.py`).

### 관측되는 변화

| | 이관 전 | 이관 후 |
|---|---|---|
| Lenovo 인증 시도 수 | 4 | **1** |
| Cisco 인증 시도 수 | 3 | **1** |
| Dell (표준 401) 결과 | `success` / 9 sections / recovery 수집 | **`failed`** / 0 sections |

표준 계정이 후보 [0] 이 되면서 정상 장비는 1회 인증으로 끝난다 (lockout 위험 감소).

## 4. Dell reconcile 실패 Root Cause (§8 14항목)

**추측이 아니라 장비가 직접 말한 문장으로 규명했다.** 그 문장을 얻기 위해 먼저
"버려지던 응답 본문" 을 살려야 했다.

### 4.1 조사 결과

| # | 확인 항목 | 결과 |
|---|---|---|
| 1 | 표준 계정이 슬롯 3 에 실제 존재하는가 | 예 (`account_existed: true`, `slot_uri=/Accounts/3`) |
| 2 | 슬롯 선택 기준 | `account_service_find_all_users()` — **username 완전일치**, 다중 매칭이면 중단 |
| 3 | username 기준인가 ID/slot 기준인가 | username 기준. slot 은 결과일 뿐 |
| 4 | PATCH 대상 URI | 장비가 준 `@odata.id` 그대로 — 정확 |
| 5 | PATCH body | `{Password, Enabled, Locked, RoleId}` — **`Locked` 가 문제였다 (§4.2)** |
| 6 | Password 변경에 별도 Apply/Job 이 필요한가 | 아니다. 거부는 즉시 응답 본문으로 온다 |
| 7 | **HTTP 2xx 가 적용 완료를 뜻하는가** | **아니다.** iDRAC10 은 200 과 함께 본문으로 거부한다 |
| 8 | 재인증 전 지연이 필요한가 | 이번 사례는 아니었다. 그래도 유한 재시도(0/1/5초)를 넣었다 |
| 9 | 세션/커넥션 캐시 영향 | 없음 — 매 요청 새 연결 + Basic 인증 |
| 10 | 기존 Password 가 정책에 걸리는가 | **그렇다 (§4.3)** |
| 11 | 거부 증거가 Response 에 있었는가 | **있었다.** 코드가 버리고 있었다 |
| 12 | verification 로직이 타당한가 | 판정 자체는 옳았다. 다만 결과가 최종 status 에 반영되지 않았다 (§3) |
| 13 | 2xx 응답 본문에 추가 상태 정보가 있는가 | **있다.** `@Message.ExtendedInfo` — 버려지고 있었다 |
| 14 | 다른 필드(Enabled/RoleId 등) 영향 | **`Locked` 가 read-only 라 요청 전체가 거부됐다** |

### 4.2 1층 원인 — `Locked` read-only, 그런데 HTTP 200

수정 후 실장비(10.100.15.34 / iDRAC10 / Redfish 1.20.1) 가 돌려준 본문:

```
Base.1.12.GeneralError | A general error has occurred. …
The property Locked is a read only property and cannot be assigned a value.
Remove the property from the request body and retry.
```

- 상태 코드는 **200** 이었다. 코드는 성공으로 보고 넘어갔고 Password 도 적용되지 않았다.
- 종전에도 "Locked 빼고 재시도" 경로는 있었지만 **HTTP 400/405 에서만** 켜졌다.
  200 으로 거부하는 펌웨어에는 도달하지 않았다.
- 종전 코드는 `code, _, err = _patch(...)` 로 **본문을 통째로 버렸다.** 그래서 이 문장을
  아무도 볼 수 없었고, 남는 정보는 "401" 뿐이었다.

### 4.3 2층 원인 — 표준 계정 비밀번호가 장비 정책 미달

`Locked` 를 빼고 재시도하자 장비가 진짜 이유를 말했다:

```
Unable to set the password because the password entered does not comply to the
Security Strengthen Policy standards.
```

표준 계정 비밀번호(12자)가 이 iDRAC 의 Security Strengthen Policy 를 충족하지 못한다.
**이것은 코드 결함이 아니라 자격 값 문제**이고, 값을 바꾸면 모든 Location · 모든 Vendor 의
BMC 에 영향이 가므로 운영 결정이 필요하다 (§9 HOLD-1).

## 5. 수정 내용

| # | 수정 | 근거 |
|---|---|---|
| 1 | 쓰기 응답의 `@Message.ExtendedInfo` 를 살려 `write_response` / `errors[].detail` 로 노출 | §4.2 — 유일한 단서를 버리고 있었다 |
| 2 | 응답이 지목한 속성(`Locked` 등)을 빼고 재시도. **상태 코드와 무관하게** 본문 거부를 인식 | §4.2 — 200 거부에 재시도가 안 걸렸다 |
| 3 | 재시도 후에도 본문이 거부면 **쓰기 실패로 종료** (재인증 3회를 헛돌지 않는다) | 원인 보존 |
| 4 | 복구 자격이 AccountService 인증에 실패하면 **아무것도 쓰지 않고 종료** (`auth_ok`) | 종전엔 401 이어도 진행해 `accounts=[]` → "계정 없음" 으로 오인, 생성 경로 진입 가능 |
| 5 | 쓰기 후 재인증을 유한 재시도(0/1/5초, 상한 6초) | 비동기 반영 흡수. 무한 대기 없음 |
| 6 | 기존 계정 경로에도 암호 정책 힌트 error 추가 (빈 슬롯 경로에만 있던 비대칭 해소) | 같은 실패 모양인데 한쪽에만 단서가 있었다 |
| 7 | 실패 envelope 에도 `account_service` / `auth` 노출 | 복구 실패 원인이 결과에 안 남아 콘솔을 봐야 했다 (콘솔은 json_only 가 억제) |

**Account Write 기능 자체는 그대로다.** 기본 차단하지 않았다.

### 5.1 검증 중 스스로 만든 결함 1건 (실장비가 잡았다)

`include_vars` 의 `name:` 과 `set_fact` 대상 이름을 같게 썼다. Ansible 우선순위에서
set_fact 가 더 높아 초기화 `{}` 가 로딩 결과를 **영구히 가렸고**, OS/ESXi/Redfish
**전 채널의 인증 후보가 0개**가 됐다. OS 는 자격 없이 접속을 시도해 host unreachable 로
envelope 까지 잃었다.

문법 검사·렌더 테스트로는 잡히지 않는 종류라, **이름 충돌 자체를 금지하는 테스트**를 넣었다
(`test_include_vars_target_is_never_set_fact`).

## 6. 실장비 결과 (최종 코드 `adc99570`, flat vault 삭제 후)

| Build | loc | 대상 | type | status | `credential_scope` | `recovery_credential_scope` | 최종 계정 role | sections | errors |
|---|---|---|---|---|---|---|---|---|---|
| #25 | ich | 10.100.64.96 | os | success | `ich/os/linux` | — | secondary | 6 | 0 |
| #26 | chj | 10.100.64.120 | os | success | `chj/os/windows` | — | secondary | 7 | 0 |
| #27 | yi | 10.100.64.1 | esxi | success | `yi/esxi` | — | secondary | 6 | 0 |
| #28 | chj | 10.50.11.232 | redfish | success | **`common/redfish/standard`** | `chj/redfish/lenovo` | **primary** | 9 | 0 |
| #29 | yi | 10.100.15.2 | redfish | success | **`common/redfish/standard`** | `yi/redfish/cisco` | **primary** | 9 | 0 |
| #30 | git | 10.50.11.232 | redfish | success | **`common/redfish/standard`** | `git/redfish/lenovo` | **primary** | 9 | 0 |

**최종 수집이 복구 계정으로 수행된 사례: 0건** (§18 FAIL 조건 미해당).

#28 과 #30 은 **같은 BMC** 다. 표준 scope 는 동일하고 복구 scope 만 Location 을 따라 갈린다 —
설계 의도가 그대로 관측된다.

OS/ESXi 의 `secondary` 는 **같은 vault 파일 안**의 다음 후보다 (Location/Vendor 를 넘지 않는다).
OS/ESXi 에는 복구 개념 자체가 없다.

### 6.1 Dell (10.100.15.34) — Before / Write / After

Secret 은 기록하지 않는다. 상태와 응답 요지만 남긴다.

| 단계 | 표준 인증 | 복구 인증 | 계정 존재 | write | verification | 최종 |
|---|---|---|---|---|---|---|
| **Before** (dry-run 강제) | 401 | ok (`lab_dell_root`) | 예 (slot 3) | **0건** (`verification: skipped`) | — | `failed` / 0 sections |
| **Write #1** (수정 전) | 401 | ok | 예 | PATCH → **200 인데 본문은 거부** (`Locked` read-only) | failed | `failed` / 0 sections |
| **Write #2** (수정 후) | 401 | ok | 예 | `Locked` 빼고 재시도 → 장비가 **암호 정책 미달** 통보 | failed | `failed` / 0 sections |

- 세 번 모두 **복구 계정으로 수집하지 않았다** — 이것이 이번 Contract 의 핵심이다.
- delete/recreate 는 계속 비활성이라 계정을 지우지 않았다.
- 표준 계정 생성/동기화는 **성공하지 못했다.** 따라서 Dell 은 아직 표준 계정으로
  수집할 수 없다 (§9 HOLD-1).
- 이전 Pilot 대비 달라진 것: 원인이 **장비의 문장 그대로** 결과에 남는다.

## 7. Secret 비노출

콘솔 로그 34개 전량 × vault 49개 복호화 값 대조.

| 대상 | 결과 |
|---|---|
| 고유값 비밀번호 14종 | **0건** (토큰 경계 일치) |
| Vault 마스터 키 | **0건** |
| Jenkins 계정 비밀번호 | **0건** |
| envelope 33건 내부 | **0건** |
| 사전 단어형 공장 기본값 2종 | 10건 — 전부 영어 산문 `password` (Dell 오류 문장 + 진단 문구). 문맥 8종 전수 확인 |

`write_response` 에 담기는 것은 벤더 오류 문장뿐이며 계정 값이 아니다.

## 8. runtime fallback / flat 참조

| 검사 | 결과 |
|---|---|
| production 코드의 flat vault 경로 참조 | **0건** (남은 언급 1건은 "종전에는…" AS-IS 서술 주석) |
| 표준 vault 부재 → vendor vault primary 사용 | 경로 없음 (`recovery_accounts_of` 가 primary 를 제외) |
| Location A 실패 → Location B 시도 | 경로 없음 (resolver 가 scope 당 경로 1개만 반환) |
| Vendor A 실패 → Vendor B 시도 | 경로 없음 (`fallback_profiles` 삭제 상태 유지) |
| flat vault 12개 | **삭제 완료** (`.lab-credentials.yml` 유지) |

flat 삭제 후 실장비 6대가 정상 수집됐다 — flat 이 runtime 에 쓰이지 않았다는 실증이다.

## 9. 남은 HOLD

- **HOLD-1 Dell 표준 계정 비밀번호 정책 미달** — 값 변경은 모든 Location·Vendor 에 영향.
  선택지: (a) 표준 비밀번호 강화 후 전 BMC 재동기화 (b) 해당 iDRAC 정책 완화.
  **운영 결정 필요.**
- **HOLD-2 HPE 10.50.11.231** — TCP 443 timeout 지속. 같은 대역 Lenovo 정상 → BMC 자체 문제.
- **HOLD-3 표준 계정 생성 경로(계정 부재 시 create)** — 실장비 미검증. 이번 대상은 전부
  계정이 이미 있었다 (`account_existed: true`). 모듈 단위 테스트로만 확인.
- **HOLD-4 Location 별 값 분리** — 4 Location 이 아직 같은 복구 자격을 가리킨다.
- **HOLD-5 물리 Runner 분리** — `ich/chj/yi/git` 4 label 이 단일 노드에 붙어 있다.
- **HOLD-6 Adapter `credentials:` Phase B 제거** — 더 이상 읽지 않지만 YAML 에 남아 있다.

## 10. 검증 게이트

| 게이트 | 결과 |
|---|---|
| `ansible-playbook --syntax-check` × 3 | exit=0 |
| `pytest tests/` | **2697 passed** / 10 skipped / 7 xfailed |
| `tests/validate_field_dictionary.py` | RESULT: PASS |
| `scripts/ai/hooks/output_schema_drift_check.py` | exit=0 (`fd_paths=176`) |
| `scripts/ai/verify_vendor_boundary.py` | exit=0 |
| `scripts/ai/verify_harness_consistency.py` | 통과 |
| `scripts/ai/vault_decrypt_check.py` | [PASS] 전량 (49 파일) |

신규 계약 테스트 `tests/unit/test_redfish_standard_recovery_contract.py` 46건 —
§16 의 20개 요구 케이스를 모두 포함한다.

## 11. Production 승격 판단

**아직 아니다.** Dell 표준 계정이 복구되지 않은 상태(HOLD-1)에서 승격하면 Dell 5대가
전부 `failed` 로 나간다. 이관 전에는 (잘못이지만) recovery 수집으로 `success` 였으므로
**Portal 에서 보이는 결과가 달라진다.** 그 변화를 운영이 인지하고 받아들이는 것이 먼저다.

Dell 자격 값 결정(HOLD-1) 후 재검증 → 승격 순서를 권한다.

## 12. 관련

- 설계: `docs/ai/contracts/vault-credential-resolver.md`
- AS-IS 조사: `docs/ai/contracts/redfish-account-asis.md`
- 직전 Pilot: `tests/evidence/2026-08-12-location-vault-jenkins-pilot.md`
- 운영 절차: `docs/operate/05-vault.md`
- 후속: `docs/ai/NEXT_ACTIONS.md`
