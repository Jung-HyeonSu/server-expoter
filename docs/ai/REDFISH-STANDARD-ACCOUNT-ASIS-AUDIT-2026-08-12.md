# Redfish Standard Gathering Account — AS-IS 코드 전수조사

> **작성일**: 2026-08-12
> **성격**: Read-only Investigation. **코드 / Vault / Jenkins / 실장비를 일절 수정하지 않았다.**
> 설계 제안 · 리팩터링 · 신규 failure_code 추가도 하지 않았다.
> **기준**: 실제 코드. `README` / `docs/` 는 근거로 쓰지 않았고, 코드와 문서가 다른 곳은 20절에 따로 적었다.

## 0. 기준 커밋과 조사 중 발생한 저장소 변경 (먼저 읽을 것)

**[WARN] 조사 도중 다른 세션이 같은 저장소를 커밋했다.**

| 시점 | 상태 |
|---|---|
| 조사 시작 | HEAD `89403d75` + 워킹트리 미커밋 변경 48개 파일 (`vault/common/` untracked 포함) |
| 조사 중 (15:17) | 다른 세션이 **`020e3146` "feat: Redfish 표준 계정 전역화 + 복구 계정 분리"** 커밋 |
| 조사 종료 | HEAD `020e3146` + 워킹트리 변경 5개 파일 |

**본 문서의 모든 라인 번호는 커밋 `020e3146` 기준이다.** 조사 시작 시점에 내가 읽은 미커밋 워킹트리 내용이
그대로 `020e3146` 으로 커밋됐고, 인용한 핵심 파일 7개(`site.yml`, `redfish_gather.py`,
`account_service.yml`, `account_service_try_one.yml`, `collect_standard.yml`, `try_one_account.yml`,
`load_vault.yml`)는 커밋 이후 재확인 시 **라인 번호가 모두 일치**했다(스팟체크 12개 라인).

조사 종료 시점에 `020e3146` 위에 얹혀 있는 워킹트리 변경 5개는 본 조사 범위 밖이며, 그중
`common/tasks/credential/load_one.yml` 변경은 **본 조사가 대상으로 삼은 코드의 실제 버그 2건을
다른 세션이 고친 것**이다(상세 20.5절). 즉 이 영역은 지금도 움직이고 있다.

### 0.1. [ADDENDUM] 조사 종료 직후 추가로 들어온 커밋 2건

문서 작성을 마치는 동안 같은 세션이 2건을 더 커밋했다. **본문 라인 번호 기준(`020e3146`)은 그대로 두고**
영향만 여기 적는다. 핵심 인용 파일 9개
(`site.yml`, `redfish_gather.py`, `account_service.yml`, `account_service_try_one.yml`,
`collect_standard.yml`, `try_one_account.yml`, `load_vault.yml`, `credential_common.py`,
`credential_accounts.py`)는 **두 커밋 모두에서 변경되지 않았다** — 본문 라인 인용은 전부 유효하다.

| 커밋 | 내용 | 본 문서 findings 에 대한 영향 |
|---|---|---|
| `016006f8` "fix: include_vars 대상과 set_fact 이름 충돌로 인증 후보 0개" | `load_one.yml` 의 `include_vars` 대상을 `_cl_vault_data` → `_cl_included` 로 바꾸고, 노출용 `_cl_vault_data` 를 별도 set_fact 로 생성. 또 `_cl_included` 잔존으로 **복구 파일이 없을 때 표준 vault 내용이 복구 후보로 새는** 사고를 차단 | **본 조사 대상 코드의 실제 버그 2건**이다. 전자는 set_fact 우선순위가 include_vars 결과를 영구히 가려 **전 채널 인증 후보 0개**를 만들던 것. 본 문서 17.5절(`credential_set_undecryptable` 도달 불가) 분석은 `failed_when: false` 가 유지되므로 **그대로 유효** |
| `d3e79167` "test: Pilot dry-run 전용 임시 브랜치" | `Jenkinsfile_portal:219` 에 **`-e _rf_account_service_dryrun=true` 추가** | **H-4 를 직접 겨냥한 변경**이다. 다만 커밋 제목이 "Pilot dry-run 전용 **임시**" 라 항구 정책인지 불명확하다. H-4 / D-1 은 **"기본값을 무엇으로 확정할 것인가"** 라는 미결 질문으로 여전히 유효하다 |

### 0.2. 검증 방법

| 방법 | 적용 |
|---|---|
| 파일 직접 읽기 | 전 구간 |
| **production 코드 실제 실행** | `account_service_provision()` 을 HTTP mock 으로 직접 호출해 쓰기 발생 여부 관측 (8절, 20.1절) |
| **production Jinja 템플릿 실제 렌더** | `site.yml` 의 `_rf_auth_rejected` / `_rf_auth_outcome` 을 YAML 에서 추출해 렌더 (6절, 20.2절) |
| **Vault 실복호화** | 37개 redfish vault 를 PBKDF2+AES-CTR 로 직접 복호화해 구조 실측 (3·4절). **비밀번호 값은 출력하지 않았고 sha256 앞 8자리만 대조용으로 사용** |
| pytest 실행 | `pytest tests/unit -k "credential or account" -q` → **229 passed** (조사 시작 시점) |
| Ansible 내부 소스 확인 | `failed_when` 처리 의미 확정을 위해 설치본 `task_executor.py` / `include_vars.py` 확인 |

**하지 않은 것**: 실장비 요청 0건. Account Write 0건. `ansible-playbook` 실행 0건
(Windows 제어노드에서 `ansible-playbook` 이 `os.get_blocking` 부재로 기동 불가 — 그래서 템플릿을
직접 렌더하는 방식으로 대체했다).

---

## 1. Executive Summary

### 1.1. 정책 대비 현재 구현

| 운영 의도 | 현재 코드 | 판정 |
|---|---|---|
| Standard = 모든 Location + 모든 Vendor 공통 1개 | `vault/common/redfish/standard.yml` 상수 경로 1개 | **[OK] 일치** |
| Recovery = Location + Vendor 별 | `vault/<loc>/redfish/<vendor>.yml` | **[OK] 일치** |
| Recovery 로는 수집하지 않는다 | 수집 후보에 recovery 가 들어가는 경로 자체가 없음 | **[OK] 일치** |
| 최종 Gathering 은 반드시 Standard 로 | `primary` 또는 `anonymous`. `recovery` 는 구조적으로 불가 | **[OK] 일치 (단 anonymous 예외 존재 — 11절)** |

**정책 4개 축은 현재 코드가 지키고 있다.** 조사에서 나온 문제는 정책 위반이 아니라
**(a) 실패를 성공처럼 보고하는 진단 결함**, **(b) 잘못된 전제로 쓰기에 진입하는 경로**,
**(c) 9 vendor 중 4종의 실장비 미검증**이다.

### 1.2. 한 줄 결론 8가지

1. Standard 계정은 **진짜로 전역 1개**다. 경로가 함수 인자가 아니라 **모듈 상수**라 Location/Vendor 가
   개입할 여지가 코드에 없다 (`module_utils/credential_common.py:54-55`).
2. Recovery 계정으로 수집하는 경로는 **존재하지 않는다**. `_rf_try_accounts` 는 두 호출지점 모두
   `_rf_standard_accounts` 다 (`site.yml:134`, `:198`).
3. **9 vendor 의 Account 생성 구현은 사실상 3갈래뿐이다** — Dell(빈 슬롯 PATCH) / Cisco(POST+Id+RoleId remap) /
   나머지 7종 공용 POST. Huawei·Inspur·Fujitsu·Quanta 는 vendor 전용 코드가 **0줄**이다.
4. **Account Reconcile 에 Generation / Model / Firmware 축은 전혀 없다.** Adapter 30개가 세대를 정교하게
   구분하지만 그 정보는 계정 코드에 **한 번도 도달하지 않는다**.
5. **Create 경로 8/9 vendor 는 쓰기 후 재인증 검증을 하지 않는다.** `recovered=True` + `verification='none'`
   으로 반환하고, Ansible 실패 게이트가 `'none'` 을 **성공으로 인정**한다.
6. **[CRITICAL] AccountService 는 읽혔지만 Accounts 컬렉션 조회가 실패(403/500/링크 부재)하면
   "계정이 없다"로 오판하고 실제로 계정 생성 쓰기를 수행한다.** production 코드를 직접 실행해 증명했다.
7. **[CRITICAL] 복구 후보가 1개라도 있으면 `auth_success` 가 `false` 로 확정되지 못한다.**
   진단 템플릿이 "시도한 후보 수"를 표준+복구 병합 배열 길이로 세는데 실제 시도는 표준만 하기 때문이다.
   production 템플릿을 실제 렌더해 증명했다.
8. 실장비 검증은 **Dell / HPE / Lenovo / Cisco 4종만** 근거가 있고, **Supermicro / Huawei / Inspur /
   Fujitsu / Quanta 5종은 mock 단위테스트뿐**이다. 그리고 Account Reconcile 을 실행하는
   **fixture-replay 테스트도 live 테스트도 저장소에 0건**이다.

---

## 2. 확정된 현재 Runtime Flow

정본: `redfish-gather/site.yml` (585줄).

```
site.yml:44   init_fragments
site.yml:49   run_precheck                     (TCP/Protocol 진단)
site.yml:57   abort if precheck failed
site.yml:67   detect_vendor                    → _rf_detected_vendor, _rf_probe_facts
site.yml:77   resolve_and_load_redfish.yml     ← Credential 해석 (adapter 선택보다 앞)
site.yml:84   load_vault.yml                   → _rf_standard_accounts / _rf_recovery_accounts
site.yml:92   abort if credential set unavailable
site.yml:105  select adapter (adapter_loader)  → _selected_adapter
site.yml:123  extract manager_layout
──────────────────────────────────────────────── Phase 1
site.yml:131  collect_standard.yml  (_rf_try_accounts = _rf_standard_accounts)
──────────────────────────────────────────────── Reconcile 판정
site.yml:148  _rf_account_reconcile_allowed =
                  (not _rf_collect_ok) AND _rf_primary_auth_rejected
                  AND len(_rf_recovery_accounts) > 0
site.yml:155  account_service.yml   (allowed 일 때만)
                └ loop account_service_try_one.yml over _rf_recovery_accounts
site.yml:163  recovery set unavailable 사실 기록 (복구 후보 0개일 때)
──────────────────────────────────────────────── Phase 3
site.yml:191  collect_standard.yml 재실행 (_rf_try_accounts = _rf_standard_accounts)
                gate: allowed AND meta.recovered AND (not meta.dryrun)
──────────────────────────────────────────────── 종결 판정
site.yml:217  abort if collect completely failed        (when: not _rf_collect_ok)
site.yml:242  abort if final gathering not by standard  (when: used_account.role == 'recovery')
site.yml:252  normalize_standard → OEM(graceful) → build_* → OUTPUT
site.yml:370  rescue → build_failed_output → OUTPUT
site.yml:567  always → OUTPUT (13필드 보장)
```

**중요한 순서 사실**: `abort if collect completely failed` (217) 는 reconcile(155) 과 Phase 3(191)
**뒤에** 있다. 즉 "reconcile 실패 후에도 수집이 계속되는" 창(window)은 없다 — 상세 16절.

---

## 3. Standard Credential Source of Truth

### 3.1. 코드 근거 — 경로가 상수다

`module_utils/credential_common.py`:

```python
54  REDFISH_STANDARD_SCOPE  = "common/redfish/standard"
55  REDFISH_STANDARD_RELPATH = "{0}/{1}.yml".format(VAULT_ROOT, REDFISH_STANDARD_SCOPE)
```

`resolve_redfish_credentials()` (`:175-218`) 는 이 상수를 **그대로** 반환한다. `location` / `vendor` 는
recovery 쪽 `resolve_credential_scope()` 호출(`:204-210`)에만 들어가고 standard 쪽으로는 **전달되지 않는다**:

```python
211  return {
212      "standard_credential_scope": REDFISH_STANDARD_SCOPE,      # ← 인자 미사용
213      "standard_vault_relpath":    REDFISH_STANDARD_RELPATH,    # ← 인자 미사용
214      "recovery_credential_scope": recovery["credential_scope"],
215      "recovery_vault_relpath":    recovery["vault_relpath"],
```

→ **Global 1개다. Location 별도 아니고 Vendor 별도 아니고 (Location × Vendor) 도 아니다.**
`se_location` 값이 무엇이든 standard vault 파일은 언제나 같은 하나다.

### 3.2. 디스크 실측 (vault 실복호화)

37개 redfish vault 전수 복호화 결과. **비밀번호 값은 출력하지 않았다.**

| 파일 | accounts 수 | role 구성 |
|---|---|---|
| `vault/common/redfish/standard.yml` | **1** | `role=primary`, label `common_infraops`, username `infraops` |
| `vault/{ich,chj,yi,git}/redfish/<vendor>.yml` (36개) | 1~4 | **전부 `role=recovery`. `primary` 0건** |

- `username` 은 `infraops`, `common_infraops` 는 **label 이지 username 이 아니다.**
- 4개 Location 의 recovery vault 는 **내용이 완전히 동일**하다 (비밀번호 digest 전수 일치).
  이는 `tests/evidence/2026-08-12-location-vault-jenkins-pilot.md` E-4 "4 Location 이 같은 Credential 을
  가리킨 상태" 기록과 일치한다.

### 3.3. 변수 전달 경로 (end-to-end)

| # | 위치 | 변수 |
|---|---|---|
| 1 | `credential_common.py:212` | `standard_vault_relpath` = 상수 |
| 2 | `resolve_and_load_redfish.yml:58-61` | `load_one.yml` 로 `_cl_relpath` 전달 → `_cl_vault_data` |
| 3 | `resolve_and_load_redfish.yml:65` | `_cred_standard_accounts = _cl_vault_data \| credential_standard_accounts` |
| 4 | `load_vault.yml:41` | `_rf_standard_accounts = _cred_standard_accounts` |
| 5 | `site.yml:134`, `:198` | `_rf_try_accounts = _rf_standard_accounts` |
| 6 | `collect_standard.yml:108` | `loop: _rf_try_accounts` → `_try_account` |
| 7 | `try_one_account.yml:27-28` | `redfish_gather(username=_try_account.username, password=…)` |
| 8 | `account_service.yml:38-40` | `_rf_target_account = _rf_standard_accounts \| selectattr('role','eq','primary') \| first` |
| 9 | `account_service_try_one.yml:30-31` | `target_username / target_password` |

### 3.4. `role` 인가 배열 순서인가

**둘 다 쓰이되 역할이 다르다.**

- `role` = **선택 필터**. `standard_accounts_of()` (`credential_common.py:227-230`) 는
  `(role or 'primary') == 'primary'` 인 항목만 남긴다.
- **배열 순서 = 시도 순서**. `normalize_accounts()` 는 `list(accounts)` 얕은 복사만 하고
  정렬하지 않는다 (`:287`). `redfish_candidates()` (`:249-255`) 는 `standard + recovery` 로 이어붙이며
  각 배열 내부 순서를 보존한다.

**[주의] `role` 판정 규칙이 두 곳에서 다르다:**

| 위치 | 규칙 | role 키가 없는 항목 |
|---|---|---|
| `credential_common.py:229` | `(role or 'primary') == 'primary'` | **primary 로 인정** |
| `account_service.yml:39` | `selectattr('role', 'eq', 'primary')` | **탈락** (Undefined ≠ 'primary') |

**[참고] 표준 vault 복호화는 Location 검증보다 먼저 일어난다.**
`resolve_and_load_redfish.yml:58-61` 의 `load_one.yml` 호출에는 `when` 가드가 없어 **무조건 실행**된다.
`se_location` 이 미등록이면 `reason=unknown_location` 이지만, 그 판정으로 play 가 중단되는 지점은
`site.yml:92-102` 로 **표준 vault 를 이미 복호화한 뒤**다. 동작상 문제는 아니나(중단은 정상 발생),
"미등록 Location 이면 vault 를 아예 열지 않는다"는 아니다.

→ standard vault 항목에 `role:` 키를 빠뜨리면 **수집 후보로는 쓰이지만 reconcile 대상으로는 잡히지
않아** "표준 계정 후보 없음" 경로(`account_service.yml:80-97`)로 빠진다. 현재 vault 는 `role: primary` 를
명시하고 있어 실제 사고는 없다 — **잠재 결함**이다 (20절 M-3).

`recovery_accounts_of()` (`:243-246`) 는 **부정 필터** (`!= 'primary'`) 다. 따라서
`role: secondary`, `role: Primary`(대문자 P), 오타 등 **primary 가 아닌 모든 값이 recovery 후보가 되어
계정 쓰기 경로로 들어간다.**

### 3.5. Legacy flat vault

`vault/redfish/*.yml` 9개는 **디스크에 남아 있으나 런타임 참조 0건**이다.
`common/`, `redfish-gather/`, `lookup_plugins/`, `filter_plugins/`, `module_utils/`, `callback_plugins/`
에서 `vault/redfish` 를 참조하는 non-comment 라인은 0줄이다.
`tests/unit/test_credential_load_task.py:231-240` 가 이 hard cut 을 테스트로 고정하고 있다.

**다만 이 파일들은 현재도 유효한 표준 계정 비밀번호를 담고 있다.** 복호화 실측:

| 파일 | top-level 키 | accounts 수 | 표준 비밀번호와 동일한 항목 |
|---|---|---|---|
| `vault/redfish/{cisco,dell,fujitsu,hpe,huawei,inspur,lenovo,quanta,supermicro}.yml` (9개) | `accounts`, `ansible_password`, `ansible_user` | 2~5 | **9개 전부 `common_infraops` 1건** (digest 가 `vault/common/redfish/standard.yml` 의 primary 와 완전 일치) |

⇒ **이관 과정에서 비밀번호 회전은 일어나지 않았다.** 전역화는 "같은 값을 한 곳으로 모은 것"이며,
구 파일 9개에 같은 값이 **그대로 남아 있다** (L-5 / D-7).

---

## 4. Recovery Credential Source of Truth

### 4.1. 선택축

`resolve_credential_scope()` (`credential_common.py:157-172`) 의 redfish 분기:

```python
157  else:  # redfish
158      basis["vendor"] = vdr
160      if not vdr or vdr not in known_vdr or not _PATH_SAFE.match(vdr):
164          return _fail(REASON_VENDOR_UNRESOLVED, basis)
165      parts = (loc, "redfish", vdr)
```

→ 선택축은 **(Location, Vendor) 정확히 둘**이다.
**Generation / Model / Firmware / Adapter 는 선택축이 아니다** — `credential_common.py:16-17` 이
"Generation 을 아는 시점이 인증 이후라 선택축으로 쓰면 순환 의존" 이라고 명시적으로 배제하고 있다.

- `known_locations` = `common/vars/locations.yml` 키 (ich / chj / yi / git)
- `known_vendors` = `common/vars/vendor_aliases.yml` canonical 키 9종
  (cisco, dell, fujitsu, hpe, huawei, inspur, lenovo, quanta, supermicro)
- 다른 Location / 다른 Vendor 로의 fallback 분기는 **코드에 존재하지 않는다** (`:13-15`).

### 4.2. 후보 순서 — Dell 실측

`vault/<loc>/redfish/dell.yml` 의 배열 순서 (= 시도 순서):

| # | label | username |
|---|---|---|
| 1 | `dell_fallback_1` | root |
| 2 | `dell_fallback_2` | root |
| 3 | `dell_current` | root |
| 4 | **`lab_dell_root`** | root |

**4개 모두 username 이 `root` 로 동일하다.** Pilot 에서 성공한 `lab_dell_root` 가 **마지막**이므로,
그 앞의 3개가 먼저 실패한다 → 15절 lockout 분석의 입력값이다.

### 4.3. Adapter 의 `credentials:` 블록은 죽었다

`adapters/redfish/*.yml` 은 여전히 `credentials.profile` / `credentials.fallback_profiles` /
`credentials.recovery_accounts` 를 들고 있으나 (예: `dell_idrac9.yml:74-79`),
**production 에서 이 키를 읽는 코드는 0건**이다. vault 선택은 전부 `credential_resolver` 로 이동했다
(`load_vault.yml:17-21` 이 그 사실을 주석으로 기록).
`adapters/**` 전체에서 `RoleId` / `Privileges` / `AccountTypes` / `target_role` grep 결과도 **0건**이다.

---

## 5. Standard Account 첫 인증 흐름

### 5.1. 호출 체인

```
site.yml:131  collect_standard.yml
  :17  _rf_collect_ok=false, _rf_used_account={} 초기화
       (_rf_auth_statuses / _rf_auth_observations / _rf_primary_auth_rejected /
        _rf_failed_attempt_notes 는 default 로 **누적 보존** — Phase 3 에서 Phase 1 관측이 사라지지 않게)
  :57  vendor_unresolved 일 때만 빈 자격 1회 시도 (anonymous 경로)
  :106 loop _rf_try_accounts → try_one_account.yml
         :25  redfish_gather(mode 기본값 'gather')
         :36  _rf_attempt_ok = (not failed) and status != 'failed'
         :54  _rf_auth_statuses      += [auth_evidence.first_auth_status]
              _rf_auth_observations  += [{role, label, status}]
         :76  성공 시 _rf_collect_ok=true, _rf_used_account={username,label,role}
         :99  실패 시 _rf_failed_attempt_notes += ['role/label: status=… first_auth=… err=…']
         :131 실패 시 sleep 5 (lockout backoff)
  :126 _rf_primary_auth_rejected = (role=primary 관측 중 status==401 이 1개 이상)
```

### 5.2. 첫 번째 후보는 무엇이 정하는가

**배열 순서**다. `_rf_try_accounts` = `_rf_standard_accounts` 이고 그 배열은 vault `accounts` 순서
그대로다. 현재 standard vault 는 항목이 **1개뿐**이라 실질적으로 후보는 1개다.

`role` 은 순서를 정하지 않는다 — **선택(필터)** 만 한다. role 기반 재정렬 코드는 존재하지 않으며
`NEXT_ACTIONS.md` 에 "role 기반 후보 정렬 — 이번에 도입하지 않았다"로 미결로 남아 있다.

### 5.3. `_rf_collect_ok` 는 인증 판정이 아니다

`try_one_account.yml:38-40`:

```yaml
_rf_attempt_ok: "{{ _rf_attempt is not failed and (_rf_attempt.status | default('failed')) != 'failed' }}"
```

이 값은 **전체 수집 결과**다. 인증이 200 으로 통과했어도 시리얼 확정 실패 / 섹션 전멸 등으로
`status='failed'` 이면 `_rf_collect_ok=false` 가 된다.
그래서 **인증 판정은 별도 값** `_rf_primary_auth_rejected` 로 분리되어 있다 (6절).
`site.yml:211-216` 주석이 이 분리 이유를 명시하고 있다.

---

## 6. Account Reconcile 진입 조건 전수조사

### 6.1. 진입 조건 (정본: `site.yml:148-153`)

```yaml
_rf_account_reconcile_allowed:
  (not _rf_collect_ok) AND _rf_primary_auth_rejected AND (len(_rf_recovery_accounts) > 0)
```

`_rf_primary_auth_rejected` 정본 (`collect_standard.yml:126-132`):

```yaml
{{ ((_rf_auth_observations | default([]))
    | selectattr('role',   'eq', 'primary')
    | selectattr('status', 'eq', 401)
    | list | length) > 0 }}
```

### 6.2. `first_auth_status` 기록 규칙

`redfish_gather.py:229-231`:

```python
def _record_auth_status(status):
    if _AUTH_OBSERVATION['first_status'] is None and isinstance(status, int) and status:
        _AUTH_OBSERVATION['first_status'] = status
```

- **호출지점은 단 한 곳** — `_get()` (`:273`). grep 결과 호출 2건(정의 1 + 호출 1).
- ⇒ `_post` / `_patch` / `_delete` 는 **기록하지 않는다.**
- ⇒ `_get_noauth` (`:809`) 와 `_probe_realm_hint` (`:761`) 은 자체 request 를 만들어 **기록하지 않는다.**
- ⇒ `first_status is None` 가드 때문에 **첫 값이 덮이지 않는다.** 인증 통과(200) 후 하위 리소스의
  401 은 기록되지 않는다.
- ⇒ status `0` (timeout / URLError / TLS / DNS) 은 `and status` 진위 검사에서 탈락 → **미기록(None)**.
- `main()` 진입 시 `_reset_auth_observation()` (`:5370`) 로 invocation 단위 초기화.

### 6.3. 상태별 결정표

`_rf_auth_outcome` / `failure_stage` / `failure_code` / `auth_success` 는 `site.yml:430-512` rescue 로직
기준. **표준 후보 1개 + 복구 후보 ≥1** (현재 Dell 실 구성) 을 가정했다.

| BMC 응답 | first_auth_status | `_rf_primary_auth_rejected` | Reconcile 진입 | 진단 (stage / code / auth_success) | 근거 |
|---|---|---|---|---|---|
| **401** | `401` | **True** | **YES** | auth / AUTH_PROBE_FAILED / **null** ※ | EVIDENCE `:229-231`, `:126-132` |
| 403 | `403` | False | NO | auth / AUTH_PROBE_FAILED / null | EVIDENCE |
| 404 | `404` | False | NO | auth / AUTH_PROBE_FAILED / null | EVIDENCE |
| 429 | `429` | False | NO | auth / AUTH_PROBE_FAILED / null | EVIDENCE |
| 500 / 502 / 503 | `5xx` | False | NO | auth / AUTH_PROBE_FAILED / null | EVIDENCE |
| timeout | **None** (status 0) | False | NO | auth / AUTH_PROBE_FAILED / null | EVIDENCE `:306-307` |
| connection refused | **None** (status 0) | False | NO | auth / AUTH_PROBE_FAILED / null | EVIDENCE `:304-305` |
| TLS / SSL 오류 | **None** (status 0) | False | NO | auth / AUTH_PROBE_FAILED / null | EVIDENCE `:308-309` |
| DNS 실패 | **None** (status 0) | False | NO | auth / AUTH_PROBE_FAILED / null | EVIDENCE (IPv4-only라 실 발생 희박) |
| 200 + PasswordChangeRequired | `200` | False | NO | passed 경로 | **미확인** — 아래 |
| AccountDisabled | 미확인 | 미확인 | 미확인 | 미확인 | **미확인** — 아래 |
| AccountLocked | 미확인 | 미확인 | 미확인 | 미확인 | **미확인** — 아래 |
| InsufficientPrivilege | 미확인 | 미확인 | 미확인 | 미확인 | **미확인** — 아래 |

**※ 401 인데 auth_success 가 null 인 이유는 결함이다 — 20.2절 (C-2).**
표에서 401 행만 reconcile 에 진입하므로 `_rf_accounts` 병합 길이 결함이 정확히 이 행에서 발동한다.

**"미확인" 4행의 의미**: `AccountDisabled` / `AccountLocked` / `InsufficientPrivilege` /
`PasswordChangeRequired` 는 Redfish 에서 **응답 body 의 `MessageId`** 로 전달된다.
현재 코드에서 `MessageId` 를 읽는 곳은 `_extended_info()` (`:485`) **한 곳뿐이고, 거기서도 사람이 읽을
문자열로만 쓰고 의미 분기를 하지 않는다.** 따라서 이 상태들의 동작은 **오직 함께 오는 HTTP status 로만
결정되며, 코드는 이 상태들을 구분할 능력이 없다.** 추측하지 않고 미확인으로 남긴다.

### 6.4. 부속 질문

1. **게이트는 401 전용인가** — 그렇다. `selectattr('status','eq',401)` 정수 비교이며
   `tests/unit/test_account_reconcile_entry_gate.py:238` 이 문자열 `'401'` 이 False 임을 고정한다.
2. **하위 리소스 401 을 인증 거부로 오인할 수 있는가** — 아니다. `first_status is None` 가드가 막는다 (6.2절).
3. **표준 후보가 0개면** — `_rf_auth_observations` 가 비어 `_rf_primary_auth_rejected=False` →
   **reconcile 에 진입할 수 없다.** 따라서 `account_service.yml:80-97` "no primary target" 경로는
   현재 배선에서는 3.4절의 `role` 키 누락 시나리오로만 도달 가능하다.
4. **표준 후보가 2개 이상이고 첫 번째만 401 이면** — `> 0` 조건이라 **게이트는 열린다.**
   현재 vault 는 표준 후보가 1개라 미발생.

---

## 7. Standard Account 존재 여부 확인 방법 (Account Discovery)

### 7.1. 방식 — 전 vendor 동일

`account_service_get()` (`redfish_gather.py:4662-4705`):

```
GET /redfish/v1/AccountService                       ← 경로 하드코딩 (ServiceRoot 미경유)
  → AccountService.Accounts.@odata.id 추출            ← 링크 추종 (discovery)
GET <Accounts 컬렉션>                                  ← 링크 추종
  → Members[].@odata.id 를 _capped(1024) 로 순회
GET <각 slot>                                          ← 링크 추종
  → {slot_uri, id, username, role_id, enabled, locked}
```

검색은 `account_service_find_all_users()` (`:4720-4731`):

```python
return [acc for acc in accounts if (acc.get('username') or '') == target_username]
```

→ **UserName 완전일치, 대소문자 구분.** Account ID / Slot 번호 / OEM API 로 찾지 않는다.
**Vendor 별 차이 없음 — 9 vendor 전부 이 한 함수를 쓴다.**

### 7.2. 상태 구분 능력

| 상황 | 구분하는가 | 근거 |
|---|---|---|
| 존재함 | **[OK]** | `matches[0]` → `patch_existing` (`:4905-4911`) |
| 없음 | **[OK]** | `matches == []` → create 경로 (`:5112`) |
| **동일 username 다중 slot** | **[OK]** | `len(matches) > 1` → `action='ambiguous'`, **쓰기 중단** (`:4892-4903`) |
| 존재하지만 **Disabled** | **[OK] 읽고 errors 에 기록** — 단 **복구는 시도함** | `:4915-4920`. PATCH body 에 `Enabled: True` 포함 |
| 존재하지만 **Locked** | **[OK] 읽고 errors 에 기록** — 단 `Locked` 를 `None` 으로 주는 펌웨어는 "모름"으로 남김 | `:4921-4926`, `:4703` |
| 존재하지만 **Password 불일치** | **[NG] 구분 불가** | 코드가 비밀번호를 비교할 방법이 없다. "인증 실패 + 계정 존재" 로만 추론 |
| 존재하지만 **Role 불일치** | **[NG] 읽기만 하고 판정 안 함** | `role_id` 를 `:4701` 에서 읽지만 **비교하는 코드가 없다.** PATCH 로 덮어쓸 뿐 |

### 7.3. [CRITICAL] 부분 조회 실패를 "계정 없음"으로 오판한다

`account_service_get()` 의 조기 반환 3지점이 **모두 `root_data`(non-None) + 빈 accounts 리스트**를 돌려준다:

| 라인 | 상황 | 반환 |
|---|---|---|
| `:4673-4675` | `AccountService.Accounts` 링크 부재 | `(root_data, [], errors)` |
| `:4677-4679` | Accounts 컬렉션 GET 실패 (403 / 500 / timeout) | `(root_data, [], errors)` |
| `:4689-4691` | 개별 slot GET 실패 → `continue` (그 slot 만 누락) | 부분 리스트 |

그런데 호출자는:

```python
4869  out['auth_ok'] = acct_service is not None       # ← root_data 가 non-None 이므로 True
4881  out['errors'].extend(errs)                      # ← errors 를 담기만 하고 검사하지 않는다
4890  matches = account_service_find_all_users(accounts, target_username)   # ← [] 
4905  existing = matches[0] if matches else None      # ← None
5112  # 3) 신규 생성 — vendor 분기                      # ← CREATE 로 진입
```

**실행으로 증명함** — production `account_service_provision()` 을 HTTP mock 으로 직접 호출:

| 시나리오 | auth_ok | method | action | recovered | 실제 발생한 쓰기 |
|---|---|---|---|---|---|
| Accounts 컬렉션 **403** | True | `post_new` | `create` | **True** | **POST /AccountService/Accounts** |
| Accounts 컬렉션 **500** | True | `post_new` | `create` | **True** | **POST /AccountService/Accounts** |
| Accounts **링크 부재** | True | `post_new` | `create` | **True** | **POST /AccountService/Accounts** |

즉 **"권한이 모자라 계정 목록을 못 읽은 것"과 "계정이 없는 것"을 구분하지 못하고, 실제로 계정 생성
쓰기를 수행하며, `recovered=True` 로 성공 보고까지 한다.**
(Dell 경로만 예외적으로 안전하다 — 빈 accounts 리스트에서 빈 슬롯을 못 찾아 `:5126-5130` 에서
"빈 슬롯 없음" 으로 종료한다.)

---

## 8. Account Create 흐름

### 8.1. 세 갈래뿐이다

`account_service_provision()` 의 vendor 분기 전체 (`:4770-5333`):

| 조건 | 라인 | 경로 |
|---|---|---|
| `vendor == 'dell'` | `:5113` | 빈 슬롯 PATCH |
| `vendor == 'cisco'` | `:5206` | POST + `Id` 필수 + RoleId remap |
| 그 외 전부 | `:5260` | 공용 표준 POST (+ 재시도 사다리) |

`_ACCOUNT_CREATE_STRATEGY` dict (`:4639-4649`) 는 9 vendor 를 나열하지만
**분기 로직이 읽지 않는다.** 유일한 소비 함수 `_account_create_method_for_vendor()` (`:4652-4660`) 는
production 호출자가 **0건**이다 — 문서화 목적임이 `:4654-4656` 주석에 명시돼 있다.

### 8.2. Dell — `patch_empty_slot` (`:5113-5201`)

```
account_service_find_all_empty_slots(accounts, skip_slot_ids={'1'})   # slot 1 = anonymous reserved
  → 빈 슬롯 없으면 errors + return
for slot in empty_slots[:3]:                                          # 최대 3슬롯
    PATCH <slot_uri> {UserName, Password, Enabled:True, RoleId}
    write_response_info = _extended_info(patch_resp)
    2xx 아니면 → 다음 슬롯
    for delay in ACCOUNT_VERIFY_DELAYS(0,1,5):                        # 재인증 검증
        GET /Systems  as (target_username, target_password)
        200 → recovered=True, verification='verified', break
    실패 → errors + **cleanup PATCH {UserName:'', Enabled:False, RoleId:'None'}** → 다음 슬롯
```

- **빈 슬롯 판정**: `not (acc.get('username') or '')` (`:4758`) — **UserName 이 falsy 면 빈 슬롯**.
  `_safe(acc_data,'UserName', default='')` (`:4700`) 는 키 부재와 JSON `null` 을 **모두 `''`** 로 만든다.
  → 펌웨어가 UserName 을 null/생략/마스킹하면 **사용 중인 계정이 빈 슬롯으로 분류된다** (20절 M-1).
- **cleanup PATCH (`:5188-5192`) 는 응답을 검사하지 않는다.** 되돌리기가 실패해도 아무 기록이 없다.
  단 그 슬롯의 실패 자체는 `:5180-5186` 에서 errors 에 남는다.

### 8.3. Cisco — `post_id_role_remap` (`:5206-5252`)

```
RoleId remap: Administrator→admin, Operator→user, ReadOnly→readonly
빈 Id 탐색: used_ids = {a['id'] for a in accounts};  2..15 중 첫 미사용
  없으면 errors + return
POST /AccountService/Accounts {Id, UserName, Password, Enabled:True, RoleId}
2xx → recovered=True, slot_uri
```

→ **재인증 검증 없음.** `verification` 은 초기값 `'none'` 그대로.
→ `used_ids` 는 `account_service_get` 이 **성공적으로 읽은 slot 만** 반영한다. 개별 slot GET 이
401/403/500 으로 `continue` 되면(`:4689-4691`) 그 Id 가 "미사용" 으로 보여 **점유된 Id 로 POST** 할 수 있다.
(실제 BMC 가 이를 400/409 로 거부하는지는 **미확인**.)

### 8.4. 공용 POST — 7 vendor (`:5260-5333`)

```
1차: POST {UserName, Password, Enabled:True, RoleId}
     2xx → recovered=True, return                      ← 검증 없음
2차: 1차가 400/405 일 때만 → POST {…, PasswordChangeRequired:False}   (Lenovo XCC 계열)
     2xx → recovered=True, return                      ← 검증 없음
3차: vendor == 'hpe' 일 때만 → POST {…, Oem.Hpe.Privileges{6개}}
     2xx → recovered=True, return                      ← 검증 없음
전부 실패 → errors
```

→ Huawei / Inspur / Fujitsu / Quanta / Supermicro 는 **1차 + 2차만** 탄다 (3차는 hpe 전용).
→ **vendor 전용 코드 0줄** (Huawei / Inspur / Fujitsu / Quanta).

### 8.5. [핵심] Create 후 검증이 있는 경로는 Dell 뿐이다

`recovered = True` 대입 전체와 그 직전 검증 유무:

| 라인 | 경로 | 직전 재인증 검증 | `verification` 최종값 |
|---|---|---|---|
| `:4996` | `patch_existing` (password_sync) | **있음** (`:4988-4995`) | `'verified'` |
| `:5100` | `delete_repost` | 없음 | `'none'` ※도달 불가 |
| `:5175` | Dell `patch_empty_slot` | **있음** (`:5165-5171`) | `'verified'` |
| `:5244` | Cisco POST | **없음** | `'none'` |
| `:5277` | 공용 POST 1차 | **없음** | `'none'` |
| `:5291` | 공용 POST 2차 | **없음** | `'none'` |
| `:5314` | HPE Oem 3차 | **없음** | `'none'` |

그리고 Ansible 실패 게이트 (`account_service.yml:153-156`):

```yaml
_rf_acct_failed: (not dryrun) and not (recovered and verification in ['verified', 'none'])
```

→ **`verification == 'none'` 을 성공으로 인정한다.** 즉 POST 로 만든 계정은 **한 번도 확인되지 않은 채**
`recovered=true` / 실패 아님 으로 처리된다.
※ 다만 최종 envelope 은 Phase 3 재수집이 다시 표준 계정으로 인증하므로 **틀린 성공 envelope 은 나가지
않는다** (11절). 문제는 **진단이 틀린다는 것**이다.

### 8.6. `target_role` 은 하드코딩이다

`account_service_try_one.yml:32`:

```yaml
target_role:     "Administrator"
```

vault 필드도, adapter 키도, 변수도 아니다. 모듈 기본값도 `'Administrator'` (`:5349`).
Cisco 만 `admin` 으로 remap 된다 (`:4944-4947`, `:5088-5091`, `:5212-5218`).

---

## 9. Password Sync 흐름 (`patch_existing`)

`:4907-5110`. **9 vendor 공용**이며 vendor 분기는 Cisco RoleId remap (`:4944-4947`) 과
Dell fallback 불가 안내 (`:5061-5067`) 둘뿐이다.

```
method='patch_existing', action='password_sync', account_existed=True, slot_uri=<매칭 slot>
Enabled=false 면 errors 기록 (:4915)   /   Locked=true 면 errors 기록 (:4921)
dryrun 이면 verification='skipped' 로 즉시 return (:4927)
PATCH <slot_uri> {Password, Enabled:True, Locked:False, RoleId}          ← full body 의무
  400/405 면 Locked 빼고 1회 retry (:4952-4963)
write_response_info = _extended_info(patch_resp)                          ← 2xx 여도 확장정보 추출
2xx 아니면 errors + return
for attempt, delay in ACCOUNT_VERIFY_DELAYS(0,1,5):                       ← 총 3회 / 최대 6초
    GET /Systems as (target_username, target_password)
    200 → recovered=True, verification='verified', verify_attempts=n, return
verification='failed'
  allow_delete_recreate 가 False(기본) → errors 2건 기록 후 return         ← 실제 운영 경로
  True → Dell 은 불가 안내 후 return / 그 외는 DELETE + POST 재생성
```

### 9.1. `allow_delete_recreate` 는 운영에서 도달 불가다

- 모듈 인자로는 노출돼 있다 (`:5354`, default `False`; 배선 `:5398`).
- **어떤 playbook 도 이 인자를 넘기지 않는다.** repo 전체 grep 결과 참조는 모듈 본체 5건 + 테스트 3파일뿐.
- `tests/unit/test_account_reconcile_entry_gate.py:475` `test_ansible_layer_never_enables_delete_recreate`
  가 **Ansible 계층에서 켜지지 않을 것을 테스트로 고정**하고 있다.

→ **의도된 설계다.** 결과적으로 `delete_repost` 경로(`:5068-5110`)와 `verification='none'` 반환(`:5103`)은
production 에서 도달 불가다.

---

## 10. Verification / Re-auth

| 항목 | 값 |
|---|---|
| 검증 방법 | `GET /redfish/v1/Systems` 를 **target 자격(새 비밀번호)** 으로 호출 |
| 검증 위치 | `patch_existing` (`:4988-4999`), Dell `patch_empty_slot` (`:5165-5178`) |
| 재시도 | `ACCOUNT_VERIFY_DELAYS = (0, 1, 5)` (`:454`) — t=0 / 1s / 6s, **총 3회, 상한 6초** |
| 새 세션인가 | **그렇다.** HTTP Basic 을 요청마다 새로 실은다 (`:212`, `:282`). urllib opener 재사용 / 쿠키 / 세션 캐시 없음 |
| POST create 후 검증 | **없음** (8.5절) |
| Phase 3 재인증 | `site.yml:191-198` — 모듈 밖 Ansible 계층에서 표준 계정으로 **전체 수집 재실행** |

**주의**: `ACCOUNT_VERIFY_DELAYS` 와 `write_response_info` 는 **2026-08-12 워킹트리에서 새로 들어온 것**이다.
`git log -S "ACCOUNT_VERIFY_DELAYS"` 결과 `020e3146` 이전 커밋 0건. Dell Pilot 이 돌던 시점(HEAD `89403d75`)에는
**검증이 지연 없는 즉시 1회 GET 이었고 PATCH 응답 body 를 버렸다.**

---

## 11. 최종 Gathering Credential

### 11.1. Recovery 로 수집하는 경로는 존재하지 않는다

repo 전체 grep 결과:

- `collect_standard.yml` 을 include 하는 곳은 `site.yml:132` 와 `site.yml:196` **2곳뿐**
  (adapters 의 `standard_tasks:` 키 30건은 **소비 코드가 0건인 죽은 필드**다).
- 두 곳 모두 `_rf_try_accounts: "{{ _rf_standard_accounts | default([]) }}"` (`:134`, `:198`).
- `_rf_standard_accounts` 는 `standard_accounts_of()` 로 `role != primary` 를 전부 버린 배열이다.

⇒ **Recovery 자격이 수집 경로에 들어갈 수 없다.**

### 11.2. `_rf_used_account.role` 이 가질 수 있는 값

| 값 | 대입 위치 | 조건 |
|---|---|---|
| `primary` (또는 role 키 없으면 default) | `try_one_account.yml:81-85` | 표준 후보 수집 성공 |
| `anonymous` | `collect_standard.yml:82-89` | `_cred_reason == 'vendor_unresolved'` 인 빈 자격 수집 성공 |
| `recovery` | **없음** | — |

⇒ `site.yml:242-249` "abort if final gathering not by standard account" 가드는 현재 배선에서
**도달 불가(방어적 dead code)** 다. `site.yml:236-241` 주석이 "향후 누군가 collect_standard 에
복구 후보를 넘기는 순간 조용히 되살아난다. 여기서 못 박는다" 로 그 의도를 밝히고 있다.

### 11.3. [주의] `anonymous` 는 정책상 예외다

`_cred_reason == 'vendor_unresolved'` (vendor 미식별) 이면 **빈 자격 1회 수집**을 시도하고,
성공하면 `role='anonymous'` 로 `status=success` envelope 이 나간다.
"최종 Gathering 은 반드시 Standard Account 로" 라는 정책 문장과 **문자 그대로는 어긋난다.**
`site.yml:88-90` 과 `collect_standard.yml:46-56` 이 이를 **의도된 best-effort** 로 명시하고 있으므로
결함이 아니라 **명시적 예외**로 분류한다. 다만 정책 문장에는 이 예외가 적혀 있지 않다 (23절 D-4).

---

## 12. Vendor별 구현 (코드 기준 전수)

공통 사항 (9 vendor 전부 동일):

| 항목 | 값 |
|---|---|
| AccountService URI | `/redfish/v1/AccountService` — **하드코딩** (`:4668`) |
| Accounts Collection URI | `AccountService.Accounts.@odata.id` **링크 추종** (`:4672`) |
| Account Instance URI | `Members[].@odata.id` **링크 추종** (`:4685-4688`) |
| 계정 탐색 | UserName **완전일치 / 대소문자 구분** (`:4731`) |
| AccountTypes | **전혀 다루지 않음** (grep 0) |
| Password Sync | `patch_existing` 공용 (`:4907-5110`) |
| Sync payload | `{Password, Enabled:True, Locked:False, RoleId}` (400/405 시 Locked 제외 1회 retry) |
| Sync 후 검증 | **있음** (3회 / 6초) |
| DELETE+POST fallback | **운영에서 도달 불가** (9.1절) |
| ETag / If-Match | **미사용** (`:25` 에 의도 명시) |

vendor 별 차이:

| Vendor | Create 방식 | Create URI | Create payload | RoleId | 빈 슬롯 처리 | Create 후 검증 | vendor 전용 코드 |
|---|---|---|---|---|---|---|---|
| **dell** | PATCH 빈 슬롯 | `<slot @odata.id>` | `UserName, Password, Enabled, RoleId` | `Administrator` | **slot 1 skip, 최대 3슬롯 순회, 실패 시 cleanup PATCH** | **있음 (3회/6초)** | `:5061-5067`, `:5113-5201` |
| **cisco** | POST | `AccountService/Accounts` | `Id, UserName, Password, Enabled, RoleId` | **`admin` remap** | Id 2..15 스캔 | **없음** | `:4944-4947`, `:5088-5092`, `:5206-5252` |
| **hpe** | POST (+3차 Oem retry) | `AccountService/Accounts` | 1차 표준 / 2차 +`PasswordChangeRequired:False` / 3차 +`Oem.Hpe.Privileges` | `Administrator` | 해당 없음 | **없음** | `:5301-5322` (3차 retry만) |
| **lenovo** | POST (1·2차) | 〃 | 1차 표준 / 2차 +`PasswordChangeRequired:False` | `Administrator` | 해당 없음 | **없음** | **없음** (2차 retry는 전 vendor 공용) |
| **supermicro** | POST (1·2차) | 〃 | 〃 | `Administrator` | 해당 없음 | **없음** | **없음** |
| **huawei** | POST (1·2차) | 〃 | 〃 | `Administrator` | 해당 없음 | **없음** | **없음 (0줄)** |
| **inspur** | POST (1·2차) | 〃 | 〃 | `Administrator` | 해당 없음 | **없음** | **없음 (0줄)** |
| **fujitsu** | POST (1·2차) | 〃 | 〃 | `Administrator` | 해당 없음 | **없음** | **없음 (0줄)** |
| **quanta** | POST (1·2차) | 〃 | 〃 | `Administrator` | 해당 없음 | **없음** | **없음 (0줄)** |

**AccountService 404** 는 vendor 무관하게 `method='not_supported'` 로 분류하고 종료한다 (`:4854-4861`).

### 12.1. Adapter 목록 (참고)

`adapters/redfish/` 30개. **계정 동작에 기여하는 키는 0건.**

```
cisco_bmc / cisco_cimc / cisco_ucs_xseries
dell_idrac / dell_idrac8 / dell_idrac9 / dell_idrac10
fujitsu_irmc
hpe_csus_3200 / hpe_ilo / hpe_ilo4 / hpe_ilo5 / hpe_ilo6 / hpe_ilo7 / hpe_superdome_flex
huawei_ibmc / inspur_isbmc
lenovo_bmc / lenovo_imm2 / lenovo_xcc / lenovo_xcc3
quanta_qct_bmc / redfish_generic
supermicro_ars / supermicro_bmc / supermicro_x9 / x10 / x11 / x12 / x13 / x14
```

---

## 13. Generation / Model / Firmware 분기 전수조사

### 13.1. 결론: Account Reconcile 에 세대 축은 **전혀 없다**

`account_service_provision()` 시그니처 (`:4770-4774`):

```python
def account_service_provision(
    bmc_ip, vendor, current_username, current_password,
    target_username, target_password, target_role,
    timeout, verify_ssl, dryrun=True, allow_delete_recreate=False,
):
```

→ **vendor 문자열이 유일한 vendor-축 입력이다. generation / model / firmware 인자가 없다.**

함수 본문 `:4770-5333` 안의 vendor-축 조건문 전체: `vendor == 'cisco'` (`:4944`, `:5088`, `:5206`),
`vendor == 'dell'` (`:5061`, `:5113`), `vendor == 'hpe'` (`:5301`). **끝이다.**
그 범위에 등장하는 세대 토큰(iDRAC9, XCC, iLO5/6, iRMC S5/S6, CIMC)은 **전부 주석 또는 에러 메시지
문자열**이며 분기 조건이 아니다.

### 13.2. Adapter 는 세대를 정교하게 구분하지만 계정 코드에 닿지 않는다

adapter 30개 중 24개가 `model_patterns` 또는 `firmware_patterns` 로 세대를 인코딩한다:

| Vendor | 세대 구분 adapter | priority |
|---|---|---|
| Dell | `dell_idrac`(10) / `idrac8`(50) / `idrac9`(100) / `idrac10`(120) | fw `iDRAC.*8` / `iDRAC.*9` / `iDRAC.*10` |
| HPE | `hpe_ilo`(10) / `ilo4`(50) / `ilo5`(90) / `ilo6`(100) / `ilo7`(120) / `csus_3200`(102) / `superdome_flex`(101) | fw `iLO.*4~7` |
| Lenovo | `lenovo_bmc`(10) / `imm2`(50) / `xcc`(100) / `xcc3`(120) | fw `IMM2` / `XCC` / `XCC3` |
| Supermicro | `x9`(50) / `x10`(75) / `x11`(100) / `x12`(100) / `x13`(100) / `x14`(110) / `ars`(80) / `bmc`(10) | model `X9`~`X14` |
| Cisco | `cisco_bmc`(10) / `cimc`(100) / `ucs_xseries`(110) | fw `^[4-6]\.` |
| Fujitsu | `irmc`(80) | fw `iRMC.*S2/S4/…` |
| Huawei / Inspur / Quanta | 각 1개 (80) | model 패턴만 |

**그러나** `_selected_adapter` 는 `site.yml` 에서 12회 이상 참조되지만
`account_service.yml` / `account_service_try_one.yml` 에서 **참조 0건**이다.
adapter 선택(`site.yml:105`)이 account_service(`:155`)보다 **먼저** 실행되어 변수가 스코프에 있음에도
그렇다. 즉 **의도적으로 끊겨 있다.**

### 13.3. account_provision 모드의 vendor 는 어디서 오는가

`account_service_try_one.yml:22-33` 은 모듈에 **vendor 인자를 넘기지 않는다.**
모듈이 스스로 다시 감지한다 (`main()`, `:5391-5393`):

```python
vendor, _, _, _, det_errors, _ = detect_vendor(bmc_ip, username, password, timeout, verify_ssl)
```

여기서 `username/password` 는 **현재 시도 중인 recovery 자격**이다. 즉:

- account_provision 모드는 **recovery 자격으로 vendor 를 재감지**한다.
- `detect_vendor` 는 ServiceRoot 를 **무인증 우선**(`_get_noauth`, `:922`)으로 읽으므로 보통은 무인증으로
  vendor 를 얻고, 그 뒤 Systems 컬렉션을 **인증 GET** 한다 (`:1196`).
- ⇒ recovery 자격이 틀리면 Systems GET 이 401 → `system_uri` 없음 → **조기 return** (`:1201-1203`).
  그 다음 `account_service_get` 의 AccountService GET 이 두 번째 401.
  ⇒ **후보 1개당 실패 인증 2회** (15절 lockout 분석 입력).

### 13.4. 세대 관련 테스트

**0건.** 9 vendor 어느 것에도 generation-specific account 테스트가 없다 (17절 매트릭스).

---

## 14. Capability Discovery

### 14.1. 거의 없다

| 대상 | 읽는가 | 근거 |
|---|---|---|
| ServiceRoot → `AccountService.@odata.id` | **[NG] 미사용** | `:4668` 이 리터럴 `'AccountService'` 로 직행. ServiceRoot 를 GET 하지 않는다 |
| `AccountService.Accounts.@odata.id` | **[OK] 추종** | `:4672` |
| `Members[].@odata.id` | **[OK] 추종** | `:4685-4688` |
| HTTP `Allow` 헤더 | **[NG] 0건** | 4개 HTTP 헬퍼 어디서도 `getheader` 를 부르지 않는다. 유일한 헤더 판독은 `WWW-Authenticate` (`:781`) |
| `Actions` | **[NG] grep 0** | |
| `Roles` 컬렉션 | **[NG] grep 0** | RoleId 유효성을 대상 장비에 물어보지 않는다 |
| `AccountTypes` | **[NG] grep 0** | 보내지도 읽지도 않는다 |
| `MinPasswordLength` / `MaxPasswordLength` | **[NG] grep 0** | |
| `AccountLockoutThreshold` / `AccountLockoutDuration` | **[NG] grep 0** | |
| `@Message.ExtendedInfo` | **[OK] 부분** | `_extended_info()` (`:457-489`). **PATCH 응답에만** 적용 (`:4968`, `:5150`). POST / DELETE 응답 body 는 버린다 |
| `MessageId` | **[△] 표시용만** | `:485` 에서 사람이 읽을 문자열로만. **의미 분기 없음** |
| `ETag` / `If-Match` | **[NG] 의도적 미사용** | `:25` "bmcweb 일부 펌웨어의 If-Match crash 회피" |

### 14.2. URL 구성

```python
url = f'https://{bmc_ip}/redfish/v1/{path.lstrip("/")}'
```
`_get_impl:278`, `_post:313`, `_delete:346`, `_patch:369`, `_get_noauth:811` — **scheme / port / `/redfish/v1`
루트가 전부 하드코딩**이다. `_p()` (`:399-411`) 는 `@odata.id` 에서 같은 접두사를 떼어내 호출자가 다시
붙이게 하는 정규화 함수다.

⇒ **결과**: 코드는 "쓰기가 금지된 것"과 "쓰기가 거부된 것"을 구분할 수단이 없고, 그 자리를
**재시도 사다리**로 메운다. 그 재시도는 전부 인증 요청이라 **lockout 예산을 소모**한다.

---

## 15. Idempotency

### 15.1. 정상 상태 재실행 — 쓰기 0건 [OK]

표준 계정이 정상이면:

```
Phase 1 수집 성공 → _rf_collect_ok = true
  → _rf_primary_auth_rejected = false (401 관측 없음)
  → _rf_account_reconcile_allowed = false   (site.yml:150-153)
  → account_service.yml include 자체가 skip  (site.yml:156)
```

`AccountService` GET 이 일어나는 유일한 지점은 `redfish_gather.py:4668` 이고, 그것은
`mode == 'account_provision'` (`:5379`) 에서만 도달한다. ⇒ **AccountService 요청 0건, 쓰기 0건.**
`tests/unit/test_account_reconcile_entry_gate.py:145-163` (case B / C) 가 이를 고정한다.

### 15.2. 지속 상태(persistent state)는 어디에도 없다 — 양날

| 근거 | 값 |
|---|---|
| `ansible.cfg:47` | `gathering = explicit`, fact cache 미설정 |
| `load_one.yml` | `cacheable` **0건** (rule 27 R6 준수) |
| `ansible.cfg:54` | `retry_files_enabled = False` |
| 모듈 파일 I/O | 읽기 1곳(`:711` vendor_aliases)뿐, 쓰기 0건 |

⇒ **run 간 시도 횟수 제한도, backoff 도, 성공/실패 기억도 없다.**

**결과**: vault 비밀번호가 BMC 에 실제 적용된 값과 계속 불일치하면
(= Dell Pilot E-2 가 정확히 그 상태), **매 수집마다 reconcile 게이트가 열리고 같은 PATCH 가 다시 나간다.**
`NEXT_ACTIONS.md` E-3 의 "방치하면 매 Redfish 수집마다 reconcile write 가 시도된다" 는 코드로 확인된다.

### 15.3. 중복 계정 생성 위험

| 시나리오 | 결과 |
|---|---|
| 정상 재실행 | `find_all_users` 가 기존 계정을 찾아 `patch_existing` → **중복 없음** |
| BMC 가 UserName 대소문자를 바꿔 저장 | `:4731` 완전일치 실패 → **create 경로 → 중복 생성 시도** |
| Accounts 컬렉션 조회 실패 (403/500) | **create 경로 → 중복 생성 시도** (7.3절, 실행으로 증명) |

### 15.4. `ambiguous` 경로는 안전한 무진행 루프 [OK]

같은 username 이 2개 이상 slot 에 있으면 `:4892-4903` 에서 **읽기만 하고 쓰기 없이** 종료한다.
매 실행 동일하게 반복되며 상태를 악화시키지 않는다.

### 15.5. Dell 경로의 인증 소모량

| 경로 | 계정 쓰기 | 실패 인증(표준 자격) |
|---|---|---|
| `patch_existing` 실패 | PATCH 1회 (+400/405 시 1회 더) | 검증 GET **3회** |
| Dell `patch_empty_slot` 전 슬롯 실패 | PATCH 최대 3회 + cleanup PATCH 최대 3회 | 검증 GET **최대 9회** (3슬롯 × 3회) |

Dell 빈 슬롯 경로는 **동일한 target_password 로** 최대 3슬롯을 순회한다 (body 는 `:5137-5142` 에서
한 번 만들어지고 변경되지 않는다). 즉 **이미 거부된 비밀번호를 그대로 최대 9회 다시 시도**한다.
저장소가 스스로 기록한 lockout 임계(Dell 5회/5분, HPE 3회, Lenovo 5회 — `try_one_account.yml:124-127`)와
비교하면 **표준 계정 lockout 을 유발할 수 있는 양**이다. (실장비에서 발생하는지는 **미확인**.)

recovery 쪽도 마찬가지다: Dell recovery 후보 4개 전부 username `root` 이고, 실패 후보당 인증 2회
(13.3절) + 후보 간 5초 backoff. 성공 후보 `lab_dell_root` 가 **4번째**라 앞의 3개에서
**`root` 로 6회 실패 인증**이 발생한다. Pilot 에서는 결과적으로 성공했으므로 해당 장비에서
lockout 이 걸리지 않았다는 사실만 확인된다 — 임계를 넘지 않는다는 보장은 **미확인**.

---

## 16. Failure Handling — Reconcile 실패 후 실행 지속 여부

### 16.1. 결론: 수집이 계속되는 경로는 없다 [OK]

`abort if collect completely failed` (`site.yml:217-234`, `when: not (_rf_collect_ok | bool)`) 는
reconcile(155) 과 Phase 3(191) **뒤에** 있다.
`_rf_collect_ok` 는 `collect_standard.yml:17-20` 에서 매 실행 `false` 로 초기화되고
`try_one_account.yml:76-80` 또는 anonymous 경로(`collect_standard.yml:72-77`)에서만 true 가 된다.

| 시나리오 | Phase 3 실행 | 최종 `_rf_collect_ok` | 결과 |
|---|---|---|---|
| A. reconcile 쓰기 실패 (`recovered=false`) | **skip** (gate 불충족) | false (Phase 1 값) | abort → rescue → **status=failed** |
| B. reconcile 성공 + Phase 3 재수집 실패 | 실행됨 | false (재초기화 후 실패) | abort → rescue → **status=failed** |
| C. `recovered=true` + `verification='none'` | **실행됨** | Phase 3 결과에 따름 | **envelope 은 안전**. 단 진단은 틀림 (16.2절) |
| D. dryrun 유효 | skip | false | abort → **status=failed**. dryrun 은 성공으로 오인되지 않음 (`:4927`, `:5134`, `:5209`, `:5262` 전부 `recovered=False`) |
| E. `used_account.role == 'recovery'` | — | — | **도달 불가** (11.2절) |
| F. anonymous 수집 성공 | — | true | **status=success 가능** (11.3절 — 명시적 예외) |
| G. account_service errors + 수집 성공 | — | true | status 는 **섹션 기준**이라 강등되지 않음 (16.3절) |

### 16.2. [문제] `verification='none'` 을 성공으로 인정하는 게이트

`account_service.yml:153-156` 이 `'none'` 을 실패로 보지 않으므로, POST create 경로(8 vendor)는
**account_service 에러 fragment 를 만들지 않는다.**
Phase 3 가 실패하면 envelope 자체는 failed 로 나가지만,
`diagnosis.details.account_service` 에는 **`recovered: true`** 가 실린다.
⇒ **"계정 복구는 성공했는데 수집이 실패했다"** 로 읽히지만 실제로는 계정 복구가 확인된 적이 없다.

### 16.3. status 판정은 errors 를 보지 않는다

`build_status.yml:62-77` 은 `_norm_sections` 만 본다 (4 시나리오 매트릭스 `:24-31`).
account_service 에러 fragment 는 `_sections_failed_fragment: []` 로 **failed 섹션을 추가하지 않는다**
(`account_service.yml:163`, `:88`). ⇒ **account_service 에러만으로 status 가 강등되지 않는다.**
이는 rule 13 R8 시나리오 B 의 의도된 동작이다.

다만 16.1절대로 account_service 에러가 존재하면서 수집이 성공하는 조합은 현재 배선에서 발생하기 어렵다
(`recovered=false` → Phase 3 skip → abort).

### 16.4. 실패 근거는 보존된다 [OK]

- `try_one_account.yml:99-110` 이 후보별 실패 근거를 `_rf_failed_attempt_notes` 에 누적
- `site.yml:541-557` rescue 가 이를 `_fail_error_detail` 로 합류 (상한 3건)
- `build_failed_output.yml:95-122` 가 `_all_errors` 를 errors[] 에 병합 (상한 10건 + 절단 사실 기록)
- `errors[].message` 는 5문장 정본만, 기술 근거는 `detail` 로 (rule 20 / Portal 계약 준수)

---

## 17. Test / Fixture Coverage

### 17.1. 성격

**account reconcile 을 실행하는 테스트는 전부 monkeypatch 기반 모듈 단위테스트다.**
fixture-replay 테스트도, live/integration 테스트도 **0건**이다.

관련 테스트 파일 7개 (`020e3146` 기준):

| 파일 | 성격 |
|---|---|
| `test_account_provision_f49_vendor_compat.py` | 모듈 단위 (monkeypatch `_get`/`_post`/`_patch`) |
| `test_account_provision_m_b3_new_vendors.py` | 모듈 단위 (monkeypatch) |
| `test_account_service_unsupported_f13.py` | 모듈 단위 (monkeypatch) |
| `test_account_reconcile_entry_gate.py` | **production Jinja 템플릿 렌더** + 모듈 단위 |
| `test_account_service_error_wiring.py` | production 템플릿 렌더 |
| `test_credential_load_task.py` | production 템플릿 렌더 |
| `test_redfish_standard_recovery_contract.py` | **`020e3146` 에서 신규 추가** (475줄). 모듈 단위 케이스는 **Dell 전용** |

**강점**: Ansible 계층 테스트가 production YAML 에서 템플릿을 추출해 렌더한다 (합성 fixture 아님).
**약점**: 그 테스트들은 **게이트만** 검증하고 reconcile **실행**은 검증하지 않는다.

### 17.2. Vendor × 항목 매트릭스

| Vendor | 표준인증 성공 | 복구인증 성공 | Create | Password Sync | Verification | Re-auth(Phase3) | 실패경로 | Idempotency | 세대별 | 성격 |
|---|---|---|---|---|---|---|---|---|---|---|
| dell | MISSING | MISSING | `f49:test_provision_dell_skip_reserved_slot1_and_retry` | `m_b3:test_m_b3_dell_patch_verify_401_no_fallback` | `f49:test_provision_dell_silent_fail_verify_detects` | MISSING | `f49:test_provision_dell_no_empty_slots_after_skip` | MISSING | MISSING | mock |
| hpe | MISSING | MISSING | `f49:test_provision_hpe_third_retry_with_oem_privileges` | MISSING | MISSING | MISSING | `f13:test_provision_hpe_404_returns_not_supported` | MISSING | MISSING | mock |
| lenovo | MISSING | MISSING | `f49:test_provision_lenovo_400_retry_with_password_change_required` | `f49:test_provision_lenovo_patch_verify_fail_default_does_not_delete` | 〃 | MISSING | `f49:test_provision_lenovo_500_no_retry` | MISSING | MISSING | mock |
| cisco | MISSING | MISSING | `f13:test_provision_cisco_post_with_id_field_succeeds` | MISSING | MISSING | MISSING | `f13:test_provision_cisco_no_empty_id_returns_error` | MISSING | MISSING | mock |
| supermicro | MISSING | MISSING | `f49:test_provision_supermicro_first_attempt_success_no_retry` | MISSING | MISSING | MISSING | MISSING | MISSING | MISSING | mock |
| huawei | MISSING | MISSING | `m_b3:test_m_b3_huawei_ibmc_post_200_standard` | `m_b3:test_m_b3_huawei_patch_verify_401_delete_repost_fallback` | MISSING | MISSING | `m_b3:test_m_b3_huawei_post_400_405_no_hpe_retry` | MISSING | MISSING | mock |
| inspur | MISSING | MISSING | `m_b3:test_m_b3_inspur_isbmc_post_400_then_retry` | MISSING | MISSING | MISSING | MISSING | MISSING | MISSING | mock |
| fujitsu | MISSING | MISSING | `m_b3:test_m_b3_fujitsu_irmc_post_200_standard` | MISSING | MISSING | MISSING | MISSING | MISSING | MISSING | mock |
| quanta | MISSING | MISSING | `m_b3:test_m_b3_quanta_qct_bmc_post_201_openbmc` | MISSING | MISSING | MISSING | MISSING | MISSING | MISSING | mock |

**전 vendor 공통 MISSING**: 표준 인증 성공 · 복구 인증 성공(loop) · Phase 3 재인증 실행 · Idempotency · 세대별.

### 17.3. 쓰이지 않는 fixture 자산

- `tests/fixtures/redfish/*/account_service.json` — 9 vendor 디렉터리에 존재
- `tests/reference/redfish/{dell×5, hpe, lenovo, cisco}/…/redfish_v1_accountservice*.json` — 실장비 미러

**이 자산들을 로드하는 테스트가 0건이다.** 실장비 미러가 있는데 회귀에 쓰이지 않는다.

### 17.4. 실행 결과

```
pytest tests/unit -k "credential or account" -q
→ 229 passed, 1457 deselected in 49.91s      (조사 시작 시점, HEAD 89403d75 + 워킹트리)
```
조사 종료 시점(`020e3146`)에는 신규 테스트 파일 추가로 232건으로 늘었다(에이전트 실측).

**[주의] 실행 시간의 대부분이 `time.sleep` 대기다.** `ACCOUNT_VERIFY_DELAYS = (0,1,5)` 도입 후
기존 3개 테스트 파일이 `time.sleep` 을 monkeypatch 하지 않아, 검증 실패 경로를 타는 테스트마다
정확히 6.00초씩 블로킹된다 (8개 테스트 × 6초 ≈ 48초).

### 17.5. `test_credential_load_task.py` 의 사각

`test_undecryptable_vault` (`:135-136`) 는 `_cl_load = {"failed": True}` 를 **합성으로 주입**해
템플릿만 렌더한다. 그런데 production 태스크는 `failed_when: false` 를 달고 있고
(`load_one.yml:50`, 그리고 같은 파일 `test_task_never_hard_fails:300` 이 그것을 **강제**한다),
Ansible 은 `failed_when` 을 리스트 attribute 로 취급해 `[False]` 가 truthy 이므로
`result['failed']` 를 **False 로 덮어쓴다** (`task_executor.py:716-717` 실물 확인).
`include_vars` 는 vault 복호화 실패를 `AnsibleError` 로 잡아 `result['failed']=True` 를 **반환**할 뿐
raise 하지 않는다 (`include_vars.py:130-134`, `:141-143`).

⇒ **`_cl_load is failed` 는 런타임에서 항상 False → `credential_set_undecryptable` 은 도달 불가**로
보인다. 테스트는 통과하지만 런타임 값을 재현하지 않는다.
**[미확인]** Ansible 을 실제 실행해 확인하지는 못했다(Windows 제어노드 제약). 소스 판독 기반 결론이다.

---

## 18. Vendor + Generation Coverage Matrix

Status 정의: `PROVEN`=실장비 근거 있음 / `PARTIAL`=일부만 / `UNVERIFIED`=mock 만 / `MISSING`=구현 없음 / `BROKEN`=결함 확인

| Vendor | BMC Family | Generation adapter | Detect | Standard Auth | Recovery Auth | Create | Password Sync | Verify | Re-auth | 최종 Standard 수집 | Test Evidence | Status |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **dell** | iDRAC | idrac / 8 / 9 / 10 | PROVEN | **PROVEN (401 실측)** | **PROVEN** | UNVERIFIED (mock) | **BROKEN (Pilot: PATCH 2xx → 검증 실패)** | PROVEN (구현+mock) | **MISSING (테스트 0)** | **BROKEN (Pilot 미달성)** | mock 6 + Pilot 실측 | **BROKEN** |
| **hpe** | iLO | ilo / 4 / 5 / 6 / 7 / csus_3200 / superdome_flex | PROVEN | UNVERIFIED | UNVERIFIED | PARTIAL (2026-05-06 커밋 근거) | UNVERIFIED | **MISSING (POST 검증 없음)** | MISSING | UNVERIFIED | mock 3 | **PARTIAL** |
| **lenovo** | IMM2 / XCC / XCC3 | bmc / imm2 / xcc / xcc3 | PROVEN | UNVERIFIED | UNVERIFIED | PARTIAL (2026-05-06) | PARTIAL (권한 cache 실측) | **MISSING (POST 검증 없음)** | MISSING | UNVERIFIED | mock 4 | **PARTIAL** |
| **cisco** | CIMC | bmc / cimc / ucs_xseries | PROVEN | UNVERIFIED | UNVERIFIED | PARTIAL (2026-05-06 10.100.15.2 실측 POST 201) | UNVERIFIED | **MISSING** | MISSING | UNVERIFIED | mock 4 | **PARTIAL** |
| **supermicro** | AMI MegaRAC | bmc / x9~x14 / ars | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED (mock) | UNVERIFIED | **MISSING** | MISSING | UNVERIFIED | mock 1 | **UNVERIFIED** |
| **huawei** | iBMC | ibmc | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED (mock) | UNVERIFIED | **MISSING** | MISSING | UNVERIFIED | mock 3 | **UNVERIFIED** |
| **inspur** | isBMC | isbmc | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED (mock) | UNVERIFIED | **MISSING** | MISSING | UNVERIFIED | mock 1 | **UNVERIFIED** |
| **fujitsu** | iRMC S5/S6 | irmc | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED (mock) | UNVERIFIED | **MISSING** | MISSING | UNVERIFIED | mock 1 | **UNVERIFIED** |
| **quanta** | OpenBMC bmcweb | qct_bmc | UNVERIFIED | UNVERIFIED | UNVERIFIED | UNVERIFIED (mock) | UNVERIFIED | **MISSING** | MISSING | UNVERIFIED | mock 1 | **UNVERIFIED** |

**Generation 열이 없는 이유**: 13절대로 Account Reconcile 에 세대 축이 없으므로 세대별 행을 나눌 근거가
코드에 존재하지 않는다. Detect / 수집에서만 세대가 갈린다.

**`PROVEN` 을 쓴 곳은 3칸뿐**이며, 전부 Dell Pilot 실측(2026-08-12)과 detect 계열이다.
2026-05-06 커밋 메시지 기반 Create 근거는 **커밋 메시지 진술이지 저장소 내 실행 산출물이 아니므로**
`PARTIAL` 로 낮췄다.

---

## 19. Dell 10.100.15.34 Pilot Trace

### 19.1. 저장소 기록 (실재함)

| 위치 | 내용 |
|---|---|
| `tests/evidence/2026-08-12-location-vault-jenkins-pilot.md:207-272` | §7 "Redfish Account Write — P16 위반 1건" |
| 〃 `:216-217` | `account_existed: true`, `slot_uri: "/redfish/v1/AccountService/Accounts/3"`, `dryrun: false`, `verification: "failed"`, `recovered: false`, `vendor: "dell"` |
| 〃 `:220` | `HTTP 401: Unauthorized; slot=3; delete_recreate=disabled` |
| 〃 `:226-228` | `PATCH /redfish/v1/AccountService/Accounts/3` (body: Password / Enabled / Locked / RoleId) → 2xx → `GET /Systems` 재인증 **401** |
| 〃 `:247-249` | "primary 인증은 write 전에도 후에도 401, recovery 는 전후 모두 성공. 즉 PATCH 는 HTTP 로는 수락(2xx)됐지만 vault 의 비밀번호가 실효 적용되지는 않았다" |
| 〃 `:260-265` | 총 실제 Account Write = 1건 (빌드 #3), 나머지 13빌드 0건 |
| `docs/ai/NEXT_ACTIONS.md:813-830` | E-2 (Dell primary credential drift), E-3 (Pilot 중 실제 Write 1건) |

### 19.2. 어느 분기였는가 — 확정

**`patch_existing` (`:4907-5110`) 이다. Dell 빈 슬롯 경로가 아니다.**

근거: 기록된 모듈 산출값이 `method: "patch_existing"`, `account_existed: true`,
`action: "password_sync"` 다. 이 조합은 `find_all_users` 가 **정확히 1개** 매칭했을 때만 나온다
(`:4890`, `:4892`, `:4905`, `:4907-4911`).

⇒ **slot 3 에는 target_username(`infraops`)과 완전일치하는 계정이 이미 있었다.**
⇒ Dell 빈 슬롯 경로(`:5113-5201`)는 진입하지 않았고, 따라서 그 안의
**cleanup PATCH(`:5188-5192`)는 실행될 수 없었다 — 계정이 지워졌을 가능성은 없다.**
⇒ `delete_recreate=disabled` 기록대로 `:5022` 에서 return 했다.

### 19.3. [중요] Pilot 은 지금 코드가 아니라 이전 코드에서 돌았다

`ACCOUNT_VERIFY_DELAYS` 와 `write_response_info` 는 `git log -S` 결과 `020e3146` 이전 커밋이 **0건**이다.
Pilot 시점(HEAD `89403d75`)의 검증은 **지연 없는 즉시 1회 GET** 이었고 **PATCH 응답 body 를 버렸다**.

⇒ **Pilot 산출물만으로는 근본 원인을 구조적으로 특정할 수 없다.**
`@Message.ExtendedInfo` 가 애초에 수집되지 않았기 때문이다.
현재 워킹트리/`020e3146` 의 변경(재시도 3회·6초 + ExtendedInfo 보존)은 **이 사고에 대한 대응**으로 보인다.

### 19.4. Root Cause 후보

| # | 후보 | 판정 | 근거 / 발동 라인 |
|---|---|---|---|
| 1 | **Dell Security Strengthen Policy silent-fail** (정책 미달 비밀번호를 200 으로 수락하고 미적용) | **가장 유력 — 단 이 장비에 대해서는 추론** | 코드가 이 현상을 명시적으로 문서화 (`:5114-5122`, `:5183-5184`). `docs/ai/catalogs/EXTERNAL_CONTRACTS.md:583-587` 에 사이트 실측 기록 존재. **단 그 실측은 10.100.15.27/31 (iDRAC9 7.10.70.00) 이라 .34 로의 귀속은 추론** |
| 2 | vault 값과 장비 값 불일치 (drift) | **EVIDENCE — 단 이건 401 의 원인이지 PATCH 무효의 원인이 아님** | `NEXT_ACTIONS.md:813-816` E-2 가 drift 를 명시 |
| 3 | **비동기 반영 지연이 검증 창을 초과** | **당시 코드 기준 배제 불가 (HYPOTHESIS)** | Pilot 시점 검증은 지연 0 + 1회. 현재 코드는 0/1/6초 3회로 확장됨 |
| 4 | 잘못된 slot 을 고침 | **배제** | `account_existed: true` + 단일 매칭 (19.2절). 이름이 일치하는 그 계정을 고쳤다 |
| 5 | 세션/연결 캐시 | **배제** | HTTP Basic 을 요청마다 새로 실음 (`:212`, `:282-287`). opener 재사용·쿠키 없음 |
| 6 | 검증 엔드포인트 부적절 (`GET /Systems`) | **부분 유효 (HYPOTHESIS)** | 계정이 살아 있어도 `/Systems` 권한이 없으면 401/403 이 날 수 있다. 다만 Pilot 은 primary 재인증도 계속 401 이라 이것만으로는 설명 부족 |
| 7 | `Locked` / `Enabled` / `RoleId` 미복구 | **배제 (PATCH body 에 포함됨)** | body 가 `{Password, Enabled:True, Locked:False, RoleId}` (`:4935-4940`) |
| 8 | verification 로직 버그 | **배제** | `GET /Systems` 200 판정은 단순하고, primary 재인증도 독립적으로 401 이었다 |
| 9 | **Password history 정책** (같은 비밀번호 재사용 거부) | **HYPOTHESIS — 코드가 전혀 다루지 않음** | grep 0. `:5040-5049` 가 "암호 정책" 힌트를 errors 로 남기지만 판정하지는 않음 |

**결론**: 코드상 가장 정합적인 설명은 **#1(비밀번호가 장비 암호 정책을 통과하지 못해 200 과 함께 미적용)**
이며, `#3`·`#6`·`#9` 를 배제할 근거는 Pilot 산출물에 없다.
**다음에 같은 일이 나면 `write_response_info`(현재 코드) 에 담기는 `@Message.ExtendedInfo` 가 결정적 단서가 된다.**

---

## 20. Issues

### CRITICAL

#### C-1. AccountService 부분 조회 실패를 "계정 없음"으로 오판하고 실제로 생성 쓰기를 수행한다

- **위치**: `redfish_gather.py:4673-4679`, `:4869`, `:4881`, `:4890`, `:4905`, `:5112`
- **시나리오**: recovery 계정이 AccountService 는 읽을 수 있으나 Accounts 컬렉션에 권한이 없다(403).
  또는 컬렉션 GET 이 500/timeout. 또는 펌웨어가 `Accounts` 링크를 주지 않는다.
- **동작**: `account_service_get` 이 `(root_data, [], errors)` 반환 → `auth_ok=True` →
  `matches=[]` → **CREATE 경로 → POST 실제 발생 → `recovered=True` 보고**
- **증명**: production `account_service_provision()` 직접 실행. 3개 시나리오 모두
  `method=post_new / action=create / recovered=True` + 실제 POST 발생 관측 (7.3절 표).
- **왜 위험한가**: 이미 존재하는 계정을 못 본 상태에서 같은 이름으로 생성을 시도한다. 또한
  `errors` 를 `extend` 만 하고 **검사하지 않아** 잘못된 전제가 그대로 쓰기로 이어진다.
- **적대적 검증**: CONFIRMED (경로 전부 독립 확인). 검증자는 severity 를 MEDIUM 으로 낮췄으나,
  **실제 쓰기가 발생함을 실행으로 확인**했으므로 본 문서는 CRITICAL 로 유지한다.

#### C-2. 복구 후보가 1개라도 있으면 `auth_success` 가 `false` 로 확정될 수 없다

- **위치**: `site.yml:403-408` (특히 `:405`)
- **코드**:
  ```jinja
  {%- set statuses  = _rf_auth_statuses | default([]) -%}
  {%- set attempted = (_rf_accounts | default([])) | length -%}     ← 병합 배열(표준+복구)
  {{ attempted > 0 and (statuses | length) == attempted and … }}
  ```
- **불일치**: `_rf_accounts` 는 **표준+복구 병합**(`load_vault.yml:43` ← `resolve_and_load_redfish.yml:92-94`
  ← `credential_common.py:255`)인데, `_rf_auth_statuses` 는 **표준 후보에서만** 쌓인다
  (`try_one_account.yml:56-59`, loop 대상은 `_rf_try_accounts` = `_rf_standard_accounts`).
- **증명**: production `site.yml` 에서 템플릿을 추출해 실제 렌더:

  | 구성 | `len(_rf_accounts)` | `len(_rf_auth_statuses)` | `_rf_auth_rejected` | `_rf_auth_outcome` | `auth_success` |
  |---|---|---|---|---|---|
  | 표준1 + Dell recovery 4 (**실 구성**) | 5 | 1 | **False** | `unknown` | **null** |
  | 표준1 + recovery 0 | 1 | 1 | True | `rejected` | `false` |

- **결과**: **reconcile 이 가능한 상황(=복구 후보 존재)에서만 401 증거가 소실된다.**
  계정 쓰기를 정당화한 바로 그 401 이 envelope 에 `auth_success=false` 로 남지 않는다.
  Phase 5-A / 6-B 에서 공들여 만든 "인증 거부 실증" 설계가 실 구성에서 무력화된다.
- **주의**: reconcile **진입** 게이트(`collect_standard.yml:126-132`)는 이 결함의 영향을 받지 않는다.
  영향은 **rescue 의 진단 산출**에 한정된다. 즉 잘못된 쓰기를 유발하지는 않는다.
- **적대적 검증**: CONFIRMED. 검증자 severity MEDIUM. 본 문서는 진단 계약의 핵심 필드가
  구조적으로 틀린다는 점에서 CRITICAL 로 유지한다.

### HIGH

#### H-1. Create 경로 8/9 vendor 가 검증 없이 `recovered=true` 를 반환하고, 게이트가 그것을 성공으로 인정한다

- **위치**: `redfish_gather.py:5244`, `:5277`, `:5291`, `:5314` + `account_service.yml:153-156`
- Dell 외 전 vendor 의 POST create 는 재인증 검증이 없고 `verification` 이 `'none'` 으로 남는다.
- `_rf_acct_failed` 가 `verification in ['verified','none']` 를 성공으로 판정한다.
- **결과**: 계정이 실제로 동작하지 않아도 account_service 에러 fragment 가 만들어지지 않고
  `diagnosis.details.account_service.recovered=true` 가 나간다. `changed=true` 도 보고된다.
- **완화**: Phase 3 재수집이 실패하면 envelope 자체는 failed 다 (16.1절 C).

#### H-2. `--check` 가 실제 쓰기를 수행한다

- **위치**: `redfish_gather.py:5362` `supports_check_mode=True`
- 모듈은 `module.check_mode` 를 **한 번도 읽지 않는다**. 쓰기 차단은 오직 `dryrun` 인자
  (`:4927`, `:5134`, `:5209`, `:5262`)에 달려 있다.
- `supports_check_mode=True` 를 선언했으므로 Ansible 은 태스크를 skip 하지 않고 모듈을 실행한다.
- reconcile 진입 시 `dryrun_effective=false` (`account_service.yml:42-45`) 이므로
  **`ansible-playbook --check` 로 실제 PATCH/POST 가 나간다.**
- repo YAML 어디에도 `check_mode` 가드가 없다.

#### H-3. Capability Discovery 부재를 재시도로 메우고, 그 재시도가 인증 예산을 소모한다

- **위치**: `:4668-4672` 및 14절 표 전체
- Allow / Actions / Roles / AccountTypes / 암호정책 필드를 **하나도 읽지 않는다**.
- 그래서 "허용되지 않음"과 "거부됨"을 구분하지 못하고 POST 재시도 사다리(1→2→3차)로 대응한다.
- Dell 빈 슬롯 경로는 **동일 비밀번호로 최대 3슬롯 × 검증 3회 = 표준 계정 실패 인증 최대 9회**를
  약 20초에 발생시킨다 (`:5145`, `:5165-5171`).
- 저장소가 기록한 lockout 임계 (Dell 5/5분, HPE 3, Lenovo 5 — `try_one_account.yml:124-127`) 대비 과다.
- **실장비 lockout 발생 여부는 미확인.**

#### H-4. 운영에서 Account Write 가 기본 활성이다 — *(조사 종료 직후 `d3e79167` 로 부분 완화됨, 0.1절)*

- **기준 커밋 `020e3146` 시점 사실**: `_rf_account_service_dryrun` 을 정의하는 곳이
  **repo 전체에 없었다** (`account_service.yml` 주석 제외).
- `Jenkinsfile_portal:219` 는 `-e se_location=…` 만 넘기고 dryrun 을 넘기지 않았다.
  (→ `d3e79167` 에서 `-e _rf_account_service_dryrun=true` 가 추가됐다. 단 커밋 제목이
  "Pilot dry-run 전용 **임시**" 이므로 **항구 정책 여부는 미확정** — D-1 참조.)
- **코드 자체의 기본값은 여전히 실쓰기다.** Jenkins 파라미터가 빠지는 경로
  (다른 Jenkinsfile / 수동 `ansible-playbook` 실행 / 이 임시 조치 철회)에서는 그대로 재현된다.
- ⇒ `dryrun_effective = not _rf_account_reconcile_allowed` 이고, account_service.yml 은
  **allowed 일 때만 실행**되므로 **실행되는 순간 항상 `dryrun=false`(실쓰기)** 다.
- Pilot 의 P16 위반(실제 Write 1건)은 절차 실수이자 **이 기본값의 결과**이기도 하다.

#### H-5. `empty_accounts` 가 abort 게이트에도 credential_unavailable 목록에도 없다

- **위치**: `site.yml:99-102`, `:446-449`
- 표준 vault 는 열렸는데 `role=primary` 항목이 0개면 `_cred_standard_outcome='empty_accounts'`
  (`resolve_and_load_redfish.yml:66-70`).
- abort 조건은 `['credential_set_missing','credential_set_undecryptable']` 만 본다 → **중단하지 않는다.**
- rescue 의 `cred_na` 판정(`:446-449`)도 같은 2개만 본다 → `CREDENTIAL_SET_UNAVAILABLE` 이 아니라
  **`GATHER_FAILED` / 5번 문장**("대상 접속은 확인됐지만 정보 수집에 실패했습니다")으로 보고된다.
- ⇒ **자격증명 미배치를 수집 실패로 오진**한다. 운영자가 엉뚱한 곳을 본다.
- 17.5절이 맞다면 **`credential_set_undecryptable` 자체도 도달 불가**라 같은 오진 경로로 합류한다.

#### H-6. 문서 3종이 현재 코드와 모순된다

| 문서 | 문서 내용 | 실제 코드 |
|---|---|---|
| `docs/21_vault-operations.md:38`, `:50`, `:293` | `Redfish = location + vendor → vault/<location>/redfish/<vendor>.yml` | 표준은 `vault/common/redfish/standard.yml` 전역 상수 (`credential_common.py:54`) |
| `CLAUDE.md:46`, `:57` | "Vendor 확인 후 해당 Vendor Credential Profile 을 로드하는 2단계 구조", "Standard Account 는 선택된 Vendor Credential Profile 의 `role: primary`" | 표준은 vendor 와 무관. `load_vault.yml:49-56` 이 vendor 미식별에도 표준을 시도한다고 명시 |
| `docs/ai/VAULT-CREDENTIAL-RESOLVER-DESIGN-2026-08-12.md:336`, `:415` | Redfish scope 1개 (`location + vendor`) | scope 2개 (standard 전역 / recovery location+vendor) |

- **실질 위험**: `docs/21` §3.1 을 따라 새 Location 을 구성하면 `vault/<loc>/redfish/<vendor>.yml` 에
  `role: primary` 를 넣게 되는데, `recovery_accounts_of()` 가 그것을 **버린다** →
  복구 후보 0개 → 표준 인증 실패 시 복구 불가.

#### H-7. Phase 3 재인증·재수집을 실행하는 테스트가 0건이다

- 2026-08-12 계약의 핵심("최종 수집은 반드시 표준 계정으로")이 **구조 검사로만** 덮여 있다.
- `test_redfish_standard_recovery_contract.py:262-263` 은 when 절 문자열에 `'recovered'`/`'dryrun'` 이
  들어 있는지만 확인한다. 실행 검증이 아니다.
- repo 전체에 `ansible-playbook` 을 호출하는 테스트가 없다.

#### H-8. 복구 후보 loop 자체가 무테스트다

- `account_service.yml:116-122` + `account_service_try_one.yml:19` 의 break 시뮬레이션,
  후보 순서, `:72-76` 의 5초 lockout backoff — **어느 것도 테스트가 없다.**
- Dell 은 recovery 후보가 4개이고 성공 후보가 마지막이라(4.2절) 이 loop 동작이 실제로 중요하다.

### MEDIUM

| # | 문제 | 위치 |
|---|---|---|
| M-1 | 빈 슬롯 판정이 `UserName` falsy 하나에만 의존. `_safe` 가 키 부재 / JSON `null` / 비-dict 를 모두 `''` 로 접어 **사용 중인 계정을 빈 슬롯으로 분류**할 수 있다. 이미 읽어 둔 `enabled` / `role_id` 를 교차 확인하지 않는다 | `:4700`, `:4758`, `:5123-5125` |
| M-2 | Cisco 빈 Id 스캔이 **읽기에 실패한 slot 을 미사용으로 간주**한다. 개별 slot GET 실패는 `continue` 로 조용히 빠진다 | `:4688-4691`, `:5220-5225` |
| M-3 | `role` 판정 규칙이 두 곳에서 다르다. `credential_common.py:229` 는 role 키 부재를 primary 로 인정하고, `account_service.yml:39` 의 `selectattr('role','eq','primary')` 는 탈락시킨다 | 3.4절 |
| M-4 | `recovery_accounts_of()` 가 **부정 필터**라 `role: secondary` / `Primary`(대문자) / 오타가 전부 **복구 후보**가 되어 계정 쓰기 경로로 들어간다 | `credential_common.py:243-246` |
| M-5 | Dell 빈 슬롯 cleanup PATCH 의 응답을 검사하지 않는다. 되돌리기 실패가 어디에도 남지 않는다 | `:5188-5192` |
| M-6 | run 간 시도 제한·backoff·기억이 전혀 없다. 고착된 불일치 상태에서 매 수집마다 같은 쓰기를 반복한다 | 15.2절 |
| M-7 | POST / DELETE 응답 body 를 버려 `@Message.ExtendedInfo` 를 못 남긴다. PATCH 에만 적용돼 있다 | `:4968`, `:5150` vs `:5239-5251`, `:5272-5275` |
| M-8 | `RoleId` / `Enabled` / `Locked` 만 덮어쓰고 `AccountTypes` 는 다루지 않으며, 현재 `role_id` 를 **읽지만 비교하지 않는다** | `:4701`, `:4935-4940` |
| M-9 | 기존 3개 account 테스트 파일이 `time.sleep` 을 monkeypatch 하지 않아 8개 테스트가 각 6초 블로킹 (수트 50초 중 48초) | `:454` |

### LOW

| # | 문제 | 위치 |
|---|---|---|
| L-1 | `_ACCOUNT_CREATE_STRATEGY` 와 `_account_create_method_for_vendor()` 는 production 소비자가 0건인 문서용 죽은 코드 | `:4639-4660` |
| L-2 | adapter 30개의 `standard_tasks:` 키를 읽는 코드가 0건 | `adapters/redfish/*.yml` |
| L-3 | adapter 30개의 `credentials.profile` / `fallback_profiles` / `recovery_accounts` 가 전부 죽은 필드 | 4.3절 |
| L-4 | `account_service_find_user()` (첫 매칭만) 가 production 미사용 (전부 `find_all_users` 사용) | `:4708-4717` |
| L-5 | legacy `vault/redfish/*.yml` 9개가 유효한 표준 비밀번호를 담은 채 방치 (런타임 참조 0건) | 3.5절 |

---

## 21. 현재 코드로 **보장되는** 것

1. **최종 수집이 복구 계정으로 수행되지 않는다.** `_rf_try_accounts` 가 두 호출지점 모두
   `_rf_standard_accounts` 이고, 그 배열은 `role != primary` 를 제거한 결과다. (11.1절)
2. **표준 계정은 Location / Vendor 와 무관하게 하나다.** 경로가 함수 인자가 아니라 모듈 상수다. (3.1절)
3. **다른 Location / 다른 Vendor 자격으로의 fallback 이 없다.** 분기 자체가 코드에 없다. (4.1절)
4. **정상 상태 재실행에서 계정 쓰기 0건, AccountService 요청 0건.** (15.1절)
5. **reconcile 진입은 401 전용이다.** 403 / 404 / 429 / 5xx / timeout / TLS / transport 는 진입하지 않는다.
   status 는 정수 비교이며 문자열 파싱이 아니다. (6절)
6. **복구 자격이 인증되지 않으면 어떤 쓰기도 하지 않는다.** `auth_ok=false` 면 즉시 return. (`:4869-4879`)
7. **동일 username 다중 slot 이면 쓰기를 중단한다.** (`:4892-4903`)
8. **dryrun 이 성공으로 오인되지 않는다.** 모든 dryrun 분기가 `recovered=False` 로 반환한다.
9. **reconcile 실패 후 수집이 계속되지 않는다.** abort 게이트가 reconcile·Phase 3 뒤에 있다. (16.1절)
10. **실패해도 envelope 13필드가 보존된다.** rescue + always 2중 방어. 실패 근거도 errors[].detail 로 보존.
11. **Secret 이 결과에 새지 않는다.** `_rf_used_account` 에 password 미포함, meta 에 password 미포함,
    Secret 취급 태스크 전부 `no_log: true` (테스트로 고정).
12. **vault 변경이 다음 실행에 자동 반영된다.** `cacheable` 0건, fact cache 미사용 (rule 27 R6).

## 22. 현재 코드로 **보장되지 않는** 것

1. **계정 생성이 실제로 성공했다는 것** — 8/9 vendor 는 확인하지 않는다. (H-1)
2. **"계정이 없다"는 판정이 옳다는 것** — 권한 부족/5xx/링크 부재를 부재로 오판한다. (C-1)
3. **401 이었다는 사실이 결과에 남는다는 것** — 복구 후보가 있으면 `auth_success=null` 이 된다. (C-2)
4. **`--check` 가 안전하다는 것** — 실제 쓰기가 나간다. (H-2)
5. **표준 계정이 lockout 되지 않는다는 것** — 최대 9회 실패 인증 / run, run 간 제한 없음. (H-3, M-6)
6. **자격증명 미배치가 자격증명 문제로 보고된다는 것** — `empty_accounts` 는 GATHER_FAILED 로 샌다. (H-5)
7. **Role / Enabled / Locked / AccountTypes 가 올바른 상태로 복구된다는 것** — Password 외 상태를
   **비교**하지 않고 덮어쓰기만 한다. `AccountTypes` 는 아예 다루지 않는다. (M-8)
8. **Supermicro / Huawei / Inspur / Fujitsu / Quanta 에서 생성·동기화가 동작한다는 것** — mock 만 있다. (18절)
9. **세대(iDRAC8 vs 9 vs 10, iLO4 vs 7, XCC vs XCC3 …)별 차이가 처리된다는 것** — 축 자체가 없다. (13절)
10. **암호 정책 / slot full / 429 / 412 / password history / 동시 실행 이 처리된다는 것** — 미처리. (19.4절, 14절)
11. **`credential_set_undecryptable` 이 실제로 보고된다는 것** — 도달 불가로 보인다(코드 판독 기준). (17.5절)
12. **Phase 3 가 의도대로 동작한다는 것** — 실행 테스트가 0건이다. (H-7)

## 23. 수정 전에 반드시 결정해야 할 사항

| # | 결정 사항 | 왜 지금 결정해야 하나 | 결정 주체 |
|---|---|---|---|
| D-1 | **`d3e79167` 의 `-e _rf_account_service_dryrun=true` 를 항구 정책으로 확정할 것인가** | 커밋 제목이 "Pilot dry-run 전용 **임시**" 다. 임시로 두면 철회 시 H-4 가 그대로 재현된다. 또한 **dryrun=true 인 동안에는 표준 계정 자동 복구 기능 자체가 동작하지 않는다** (`recovered=False` → Phase 3 skip → 항상 failed). "복구를 켤 것인가 / 끌 것인가" 를 정면으로 결정해야 한다. 코드 기본값(`account_service.yml:42-45`)을 바꿀지도 함께 | 운영 담당자 + 아키텍트 |
| D-2 | **Dell 10.100.15.34 의 vault 값과 장비 값 중 어느 쪽을 맞출 것인가** | E-2 미해결 상태에서 코드만 고치면 같은 PATCH 가 계속 나간다. 장비 비밀번호를 vault 에 맞출지, vault 를 장비에 맞출지가 선행 | 운영 담당자 |
| D-3 | **`verification='none'` 을 성공으로 볼 것인가** | 이 한 줄(`account_service.yml:155`)이 8 vendor 의 create 결과 해석을 결정한다. "검증 없음"을 실패로 바꾸면 POST create 는 전부 실패 보고가 된다 — Phase 3 가 진짜 검증이라는 설계를 유지할지 결정 필요 | 아키텍트 |
| D-4 | **`anonymous` 수집을 정책상 허용할 것인가** | "최종 Gathering 은 반드시 Standard Account 로" 문장과 코드가 문자 그대로는 어긋난다. 예외를 정책 문서에 명시할지, 코드에서 제거할지 | 아키텍트 |
| D-5 | **lockout 예산을 몇으로 잡을 것인가** | Dell recovery 후보 4개(전부 `root`) × 실패당 2회 + 표준 검증 최대 9회. 후보 수를 줄일지, 검증 횟수를 줄일지, run 간 backoff 를 도입할지가 서로 상충 | 운영 담당자 + 아키텍트 |
| D-6 | **문서 3종(`docs/21`, `CLAUDE.md` §6/§8, 설계 문서)을 코드에 맞춰 갱신할 것인가** | 현재 문서를 따라 새 Location 을 구성하면 복구 후보가 0개가 된다 (H-6). Location 추가 작업 전에 선행 필요 | 아키텍트 |
| D-7 | **legacy `vault/redfish/*.yml` 9개를 제거할 것인가** | 런타임 참조는 0건이지만 유효한 표준 비밀번호를 담고 있다. `NEXT_ACTIONS.md` P9 가 "E-1~E-3 해소 후"로 보류 중 | 운영 담당자 |
| D-8 | **실장비 미러 fixture 를 회귀에 연결할 것인가** | `tests/reference/redfish/**/accountservice*.json` 이 이미 있는데 로드하는 테스트가 0건이다. 5 vendor 의 UNVERIFIED 를 lab 없이 낮출 수 있는 유일한 수단 | 아키텍트 |

---

## 24. 조사한 파일 목록

### 코드 (정독)

```
redfish-gather/site.yml                             (585줄, 전문)
redfish-gather/library/redfish_gather.py            (5517줄 — 1~560, 900~1010, 1175~1260, 4629~5517 정독)
redfish-gather/tasks/load_vault.yml
redfish-gather/tasks/collect_standard.yml
redfish-gather/tasks/try_one_account.yml
redfish-gather/tasks/account_service.yml
redfish-gather/tasks/account_service_try_one.yml
redfish-gather/tasks/detect_vendor.yml
common/tasks/credential/resolve_and_load.yml
common/tasks/credential/resolve_and_load_redfish.yml
common/tasks/credential/load_one.yml
common/tasks/normalize/build_status.yml
common/tasks/normalize/build_failed_output.yml
common/tasks/normalize/merge_fragment.yml
module_utils/credential_common.py                   (299줄, 전문)
lookup_plugins/credential_resolver.py               (172줄, 전문)
filter_plugins/credential_accounts.py               (97줄, 전문)
common/vars/locations.yml
common/vars/vendor_aliases.yml
ansible.cfg
Jenkinsfile_portal                                  (vault / se_location / dryrun 구간)
adapters/redfish/*.yml                              (30개 — match / priority / credentials 키 스캔)
```

### Vault (복호화 실측 — 값 미출력)

```
vault/common/redfish/standard.yml
vault/{ich,chj,yi,git}/redfish/{cisco,dell,fujitsu,hpe,huawei,inspur,lenovo,quanta,supermicro}.yml   (36개)
vault/redfish/*.yml                                 (legacy 9개)
```

### 테스트

```
tests/unit/test_account_provision_f49_vendor_compat.py
tests/unit/test_account_provision_m_b3_new_vendors.py
tests/unit/test_account_reconcile_entry_gate.py
tests/unit/test_account_service_error_wiring.py
tests/unit/test_account_service_unsupported_f13.py
tests/unit/test_credential_load_task.py             (전문)
tests/unit/test_redfish_standard_recovery_contract.py   (020e3146 신규)
tests/fixtures/redfish/*/account_service.json       (존재 확인 — 소비 테스트 0건)
tests/reference/redfish/**/redfish_v1_accountservice*.json  (존재 확인 — 소비 테스트 0건)
```

### 문서 / Evidence

```
tests/evidence/2026-08-12-location-vault-jenkins-pilot.md   (§7 Account Write)
docs/ai/NEXT_ACTIONS.md                             (E-1~E-5, F, G)
docs/ai/VAULT-CREDENTIAL-SELECTION-TRACE-2026-08-12.md
docs/ai/VAULT-CREDENTIAL-RESOLVER-DESIGN-2026-08-12.md
docs/ai/catalogs/EXTERNAL_CONTRACTS.md              (Dell Security Strengthen Policy)
docs/ai/catalogs/LAB_INVENTORY.md
docs/21_vault-operations.md
CLAUDE.md                                           (§6 / §8)
```

### 외부 (동작 의미 확정용)

```
site-packages/ansible/executor/task_executor.py     (failed_when 적용 지점 :716-717)
site-packages/ansible/plugins/action/include_vars.py (vault 실패 처리 :130-134, :141-143)
site-packages/ansible/playbook/task.py              (failed_when isa='list' :87)
```

### git

```
git log --oneline -60 / --stat 89403d75 / --stat 020e3146
git log -S "ACCOUNT_VERIFY_DELAYS" / -S "account_service_provision" / -S "recovery_accounts"
git diff -- common/tasks/credential/
```
