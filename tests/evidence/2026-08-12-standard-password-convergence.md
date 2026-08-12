# git Location — Global Standard Password 회전 수렴 + Repair 실증

- 일자: 2026-08-12
- 수행: AI (Claude Code), 사용자 지시로 실행
- 기준 Commit: `26394474`
- 대상 Location: **git 전용**. `chj` / `ich` / `yi` 장비에는 이번 cycle 에서 로그인·수집·계정
  쓰기를 **일절 수행하지 않았다** (Vault 값 변경도 없음).
- 실행 환경: WSL Ubuntu / ansible-core 2.20.7 (Windows 로컬 `ansible-playbook` 은
  `os.get_blocking` 미지원으로 실행 불가)
- **비밀번호 평문은 이 문서 어디에도 없다.** 값은 sha256 앞 8자리로만 지칭한다.

---

## 1. 무엇을 했나

전역 표준 수집 계정(`vault/common/redfish/standard.yml`, `infraops`, `role: primary`)의
비밀번호를 교체하고 git Location 의 Redfish 4대에 수렴시켰다. 그 과정에서
**Repair 경로가 실장비에서 처음으로 완주**했고, HPE iLO 에서 벤더 쓰기 계약 결함이 드러나
수정했다.

Credential Contract 는 그대로다.

- 전역 표준은 `vault/common/redfish/standard.yml` **1벌**뿐 (Location/Vendor 무관)
- Vendor Vault 는 **recovery 전용**
- 최종 수집은 **반드시 표준 계정**으로 수행 (recovery 로 수집 금지)

Vault 검증 (전량):

```
vault 파일 49개 — decrypt 실패 0, YAML 실패 0
Redfish role=primary 항목: 정확히 1개 → vault/common/redfish/standard.yml
Redfish role=recovery 항목: 41개 (Location × Vendor)
flat vault(vault/*.yml, vault/redfish/*): 0개
cross-location / cross-vendor fallback: 코드 경로 부재 (§6 참조)
```

---

## 2. 실행 결과 (제품 코드 그대로, dryrun 아님)

각 대상에 `redfish-gather/site.yml` 을 `-e se_location=git` 으로 실행했다.

### 2.1 1차 / 2차 실행 요약

| 대상 | Vendor / 모델 | 1차 | 2차 | Account Write |
|---|---|---|---|---|
| `10.50.11.232` | Lenovo XCC-7Z73-J30AF7LC | `success` / primary / attempts=1 | `success` / primary / attempts=1 | **0 / 0** |
| `10.50.11.231` | HPE ProLiant DL380 Gen11 (iLO 6) | `success` / primary / attempts=1 | `success` / primary / attempts=1 | **0 / 0** |
| `10.100.15.2` | Cisco C220 / CIMC | `success` / primary / attempts=1 | `success` / primary / attempts=1 | **0 / 0** |
| `10.100.15.34` | Dell PowerEdge R760 (iDRAC9) | `success` / primary / attempts=1 | `success` / primary / attempts=1 | **0 / 0** |

4대 모두:

- `credential_scope = common/redfish/standard`
- `recovery_scope = git/redfish/<vendor>`
- `used_role = primary`, `used_label = common_infraops`
- `auth_success = true`, `failure_stage/code = null`
- `diagnosis.details.account_service` 없음 → **Account Write 0건**
- sections 성공 9/11 (전 대상 동일)

**2차 실행 Write 0 이 4대 모두에서 확인됐다 → Password Convergence 성공.**

### 2.2 Repair 경로 실증 (Lenovo, Case B)

비밀번호 교체 직후 Lenovo 는 표준 자격이 불일치 상태였고, 제품 코드가 Repair 를 완주했다.

```
표준 최초 Auth   : 401 (구조화된 인증 거부)
Recovery 사용    : 예 — git/redfish/lenovo, label=lenovo_current
Account Presence : present
Account Action   : password_sync
Write Method     : patch_existing
Write Count      : 1 (+ Locked 거부로 인한 retry 1 — 아래 3.2 에서 제거됨)
Write 판정       : write_accepted = true
Fresh 표준 Auth  : 성공 (verification = verified)
Final Gathering  : 표준 계정(primary / common_infraops) 으로 수행, status=success
Second Run Write : 0
Family           : lenovo_xcc_accounttypes / create_method=collection_post / evidence=documented
```

이것이 **Repair 경로의 첫 실장비 완주 증거**다. 종전 cycle 까지 Repair 는 조건이 발생하지
않아 한 번도 실행된 적이 없었다.

### 2.3 HPE — Repair 가 실패했고, 원인은 제품 결함이었다

HPE 도 같은 조건(표준 401 → recovery 인증 → `present` → `patch_existing`)에 들어갔고
쓰기는 `write_accepted=true` 로 수락됐는데, 표준 자격 재인증이 3회 모두 401 이었다
(`verification=failed`). **2회 연속 실행에서 동일 재현**됐고, 두 번째 실행의 최초 표준 인증도
깨끗한 `HTTP 401` 이었다 — 즉 첫 실행의 쓰기가 실제로는 적용되지 않았다.

원인은 §3 에서 통제 실험으로 확정했다.

---

## 3. 통제 실험 — HPE iLO 쓰기 계약

대상: `10.50.11.231` / iLO 6 / ProLiant DL380 Gen11 / Redfish 1.20.0 /
계정 `/redfish/v1/AccountService/Accounts/4` (`infraops`).

### 3.1 읽기 전용 사전 조사

```
AccountService  : #AccountService.v1_15_0, MinPasswordLength=8
Oem.Hpe         : EnforcePasswordComplexity=False, AuthFailuresBeforeDelay=1,
                  AuthFailureDelayTimeSeconds=10, AuthFailureLoggingThreshold=3
Roles           : Administrator / Operator / ReadOnly / dirgroup*
계정 infraops   : Enabled=true, Locked=(속성 없음), RoleId=Administrator,
                  PasswordChangeRequired=false,
                  AccountTypes=[WebUI, Redfish, SNMP, IPMI]  ← Redfish 포함
Oem.Hpe.Privileges: LoginPriv=true, UserConfigPriv=true, ServiceAccount=false
```

계정 구조에는 문제가 없었다 — 활성, 잠기지 않음, Redfish 로그인 허용, 관리자 권한.

### 3.2 판별 실험

`MinPasswordLength=8` 을 위반하는 값(정책상 수락 불가)을 써서 "Password 가 실제로
처리되는가" 를 갈랐다. 수락될 수 없는 값이므로 계정 상태는 바뀌지 않으며, 실험 후
표준 값으로 복원하고 인증까지 확인했다.

| # | PATCH 본문 | URI | 결과 |
|---|---|---|---|
| T1 | `{Password:<길이위반>}` | 슬래시 있음 | HTTP **400** `iLO.2.36.InvalidPasswordLength` |
| T4 | `{Password:<길이위반>}` | 슬래시 없음 | HTTP **400** `iLO.2.36.InvalidPasswordLength` |
| T2 | `{Password:<길이위반>, Enabled, RoleId}` | 슬래시 있음 | HTTP **200** `Base.1.19.AccountModified` |
| T3 | `{Password:<길이위반>, Enabled, RoleId}` | 슬래시 없음 | HTTP **200** `Base.1.19.AccountModified` |
| E5 | `{Enabled, RoleId}` (Password 없음) | 슬래시 있음 | HTTP **200** `Base.1.19.AccountModified` |
| E1 | `{Password, Enabled, Locked, RoleId}` | 슬래시 있음 | HTTP **400** `PropertyNotWritableOrUnknown ['Locked']` |
| E2 | `{Password}` (정상 값) | 슬래시 있음 | HTTP **200** → 표준 자격 재인증 **200 성공** |

복원 확인: `{Password:<표준값>}` 단독 PATCH → 200 → 재인증 200. 계정 상태(Enabled /
RoleId / AccountTypes) 변화 없음.

### 3.3 확정된 사실

1. **iLO 는 `Password` 가 다른 속성과 같은 PATCH 에 오면 검사도 적용도 하지 않고 버린다.**
   같은 잘못된 값이 단독일 때는 400 으로 걸리고 묶이면 200 으로 통과한다 (T1/T4 vs T2/T3).
   URI 의 후행 슬래시 유무는 무관하다.
2. **`Base.1.19.AccountModified` 는 비밀번호 적용의 증거가 아니다.** 아무 속성도 바뀌지
   않는 본문도 같은 메시지를 준다 (E5). 응답만으로는 성공과 구분할 수 없다.
3. **`Locked` 는 iLO ManagerAccount 에 존재하지 않는 속성**이라, 실으면 요청 전체가
   400 으로 죽는다 (E1).

여기서 제품이 **성공으로 보고하지 않고 실패로 남긴 것은 설계대로 동작한 것**이다
(audit H-1 의 "검증 없이 recovered=true 금지"). 검증 의무화가 없었다면 이 결함은
"쓰기 성공" 으로 보고된 채 수집만 실패했을 것이다.

---

## 4. 반영한 수정

| # | 결함 | 수정 | 테스트 |
|---|---|---|---|
| 1 | `Password` 를 다른 속성과 묶어 PATCH → iLO 가 조용히 버림 | Family 필드 `isolated_write_patch` 신설. `hpe_ilo5plus` 는 비밀번호를 **단독 PATCH** 로 쓰고, 나머지 속성은 **실제로 달라진 것만** 뒤이어 쓴다 (무작위 재시도 사다리가 아니라 쓰기 전에 확정하는 Family 계약) | `test_account_password_isolation_and_verify_pacing.py` 8건 |
| 2 | `Locked: false` 를 무조건 전송 → iLO 400 / XCC read-only 거부 → 매번 retry 1회 추가 | **실제로 잠겨 있을 때만** 전송 | 같은 파일 3건 |
| 3 | 재인증 확인 간격이 고정 `(0,1,5)`=6초 → 장비가 선언한 패널티(iLO 10초)보다 짧아 옳은 쓰기도 401 | `account_verify_delays(policy)` 로 장비 선언값에서 간격을 끌어옴 (상한 45초). `AuthFailureDelayTimeSeconds` 는 **Oem namespace 이름을 보지 않고 키 이름으로만** 읽는다 (rule 12 R1) | 같은 파일 11건 |
| 4 | Dell 세대를 **adapter hint 단독**으로 판정 (§5) | Firmware major 우선, Model 보조, hint 는 최후 | `test_account_family_and_write_contract.py` 4건 |
| 5 | Cisco capability-over-hint 계약이 **테스트로 고정돼 있지 않음** | 어휘와 hint 가 충돌하는 실측 시나리오 3건 추가 | 같은 파일 3건 |
| 6 | 미등록 `se_location` 차단 절이 **무테스트** | `test_14b_unknown_location_aborts_before_gathering` | 1건 |

수정 1~3 은 전부 **이 장비에서 관측한 사실**에 근거한다. 근거 없는 vendor 예외는 넣지
않았다 — 예컨대 `hpe_ilo4` 는 실측이 없으므로 종전 동작을 유지했다.

---

## 5. Dell — Adapter / Family 세대 오판정

실제 장비는 **iDRAC9 / PowerEdge R760 / FW 7.10.70.00 / Redfish 1.20.1** 인데
Adapter 는 `redfish_dell_idrac10` 을, Family 는 `dell_idrac10_slot_patch` 를 골랐다.

**원인 (a) — Adapter 오선택.** Adapter 선택이 무인증 probe 단계라 `model` / `firmware`
fact 가 비어 있다. 빈 fact 는 실격이 아니라 skip 이므로 점수가 priority 로 수렴한다.

| Adapter | priority | 빈 fact 점수 | fact 채운 점수 |
|---|---:|---:|---:|
| `dell_idrac` | 10 | 10120 | — |
| `dell_idrac8` | 50 | 50320 | **-9999 (실격)** |
| `dell_idrac9` | 100 | 100320 | **100345 (승)** |
| `dell_idrac10` | 120 | **120520 (승)** | **-9999 (실격)** |

즉 adapter YAML 은 옳고, **무인증 probe 가 근본 원인**이다.

**원인 (b) — Family 가 그 hint 를 그대로 신뢰.** `gen10 = 'idrac10' in hint or 'idrac10' in
Manager.Model` 인데, Dell 의 `Manager.Model` 은 `<NN>G Monolithic` 형태(이 장비는 `16G`)라
`idrac10` 이 들어갈 수 없다 → 죽은 조건. 결국 **adapter hint 단독으로** Family 가 정해졌고,
이는 이 함수 자신의 계약("hint 는 마지막 순위") 위반이다.

**이름만의 문제가 아니다.** 두 Family 는 `reserved_slot_ids` 가 `{1}` vs `{1,2}` 로 달라
빈 슬롯이 2번일 때 **PATCH 대상 슬롯 URI 가 갈린다**. 이번 장비에서 차이가 드러나지 않은
것은 slot 2 를 `root` 가 점유하고 있었기 때문이지 동작이 같아서가 아니다.
`create_method` / payload / role 처리 / etag 는 동일하다.

**조치**: Family 세대 근거를 Firmware major(iDRAC9 = 4~7.x, iDRAC10 = 1.x)로 바꿨다.
Model 은 보조, hint 는 근거가 없을 때만. 회귀 4건 추가.
**Adapter 오선택 자체는 남아 있다** — 인증 후 adapter 재선택이 필요한 별도 변경이라
이번 cycle 범위 밖. `docs/ai/NEXT_ACTIONS.md` 등재.

---

## 6. Cisco — capability > adapter hint 회귀 확인

`10.100.15.2` 는 Adapter 가 `redfish_cisco_ucs_xseries` 로 **오선택**됐지만 Family 는
**장비가 준 Roles 어휘**로 옳게 정해졌다.

```
Roles Collection : admin / user / readonly / SNMPOnly   ← 'Administrator' 없음
→ Family         : cisco_cimc_collection_post_id  (needs_explicit_id=true)
→ RoleId         : admin   (target_role='Administrator' 를 장비 어휘로 매핑)
기존 계정 infraops: Id=2, Enabled=true, RoleId=admin, AccountTypes=[Redfish, null]
```

코드 경로도 재확인했다: `resolve_account_family` 의 Cisco 분기는 **discovery 의 실제
Roles 어휘 → 기존 계정의 RoleId → adapter hint → generic** 순이며, `choose_role_id` 도
장비가 지원하는 값을 family `role_map` 보다 우선한다. `cisco_bmc_dynamic` 에는 `role_map`
자체가 없어 `Administrator` 를 노출하는 최신 BMC 는 `Administrator` 를 그대로 받는다.
**과거처럼 모든 Cisco 에 `admin` 을 강제하는 구조로 회귀하지 않았다.**

다만 이 계약이 **테스트로 고정돼 있지 않았다** — 기존 테스트는 (어휘 + hint 없음) 또는
(hint + 어휘 없음) 뿐이라, hint 검사를 어휘 검사보다 위로 옮겨도 전 테스트가 통과했다.
충돌 시나리오 3건을 추가해 막았다.

---

## 7. Account Write 안전성

- **CREATE 는 이번에도 실행되지 않았다.** 4대 모두 표준 계정이 이미 존재해
  `presence=absent` 조건이 발생하지 않았다. 조건을 만들려면 운영 계정을 지워야 하므로
  하지 않았다 (사용자 지시 §9).
- **DELETE 는 0건.** 계정 삭제/재생성 fallback 은 기본 비활성이며 이번에 켜지 않았다.
- **chj / ich / yi 는 무접촉.** 로그인·수집·쓰기 모두 0건.
- 실패 인증 예산: HPE 실패 실행에서 `auth_budget = {infraops: 3}` (iLO 임계 3). 수정 후
  1·2차 실행 모두 실패 인증 0.

---

## 8. 재현 방법

```bash
# WSL Ubuntu
cd /mnt/c/github/server-exporter
export REPO_ROOT="$PWD" ANSIBLE_CONFIG="$PWD/ansible.cfg"
export INVENTORY_JSON='[{"bmc_ip": "10.50.11.232"}]'
ansible-playbook redfish-gather/site.yml -i redfish-gather/inventory.sh \
    --vault-password-file <경로> -e se_location=git
```

읽기 전용 Capability 확인만 하려면 `-e _rf_account_service_dryrun=true` 를 붙인다
(쓰기 0건 보장 — `--check` 도 동일하게 쓰기를 막는다).

---

## 9. 이 문서가 증명하지 않는 것

- Account **CREATE** 경로 (어느 Vendor 도 미검증)
- `chj` / `ich` / `yi` 의 어떤 것도 (이번 cycle 무접촉)
- HPE 의 **Repair 완주** — 결함 수정 후 재현하려면 계정을 다시 불일치 상태로 만들어야
  하는데, 조건을 인위적으로 만들지 않았다. 수정 근거는 §3 의 실장비 통제 실험과
  그 동작을 그대로 흉내 낸 회귀 테스트다.
- lab 부재 Vendor (Supermicro / Fujitsu / Huawei / Inspur / Quanta) 의 어떤 것도
