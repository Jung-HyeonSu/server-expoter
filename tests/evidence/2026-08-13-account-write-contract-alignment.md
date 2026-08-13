# Redfish 계정 쓰기 계약 정합 — 구현 및 검증 결과

> **작성일**: 2026-08-13
> **계획 정본**: `docs/ai/contracts/redfish-account-write.md`
> **입력**: 9 Vendor Account Write Contract Delta Research (2026-08-12) 9건
> **실행 환경**: WSL ansible-core 2.20.7 (Windows 제어노드에서는 `ansible-playbook` 기동 불가)

---

## 0. 이 문서가 증명하는 것과 증명하지 않는 것

증명한 것:

```text
git Location 실장비 4대 × (Check Mode + 1차 + 2차)
  → 전 실행 status=success
  → 전 실행 used_role=primary (표준 계정)
  → 전 실행 credential_scope=common/redfish/standard
  → 전 실행 Account Write 0
```

**증명하지 않은 것** (조건이 발생하지 않았거나 장비가 없다):

```text
Account CREATE   — 4대 모두 표준 계정이 이미 존재해 presence=absent 가 발생하지 않았다.
                   조건을 만들려면 운영 계정을 지워야 하므로 하지 않았다.
Account REPAIR   — 표준 인증이 4대 모두 성공해 reconcile 게이트 자체가 열리지 않았다.
Supermicro / Huawei / Inspur / Fujitsu / Quanta — 실장비 0대. PROVEN 으로 올리지 않는다.
```

---

## 1. 실장비 검증 결과

### 1.1 대상

| IP | hostname | product | Redfish | adapter |
|---|---|---|---|---|
| 10.100.15.34 | `r760-6.gooddi.lab` | Integrated Dell Remote Access Controller | 1.20.1 | `redfish_dell_idrac10` |
| 10.50.11.231 | `test0004.hynix.com` | ProLiant DL380 Gen11 | 1.20.0 | `redfish_hpe_ilo6` |
| 10.50.11.232 | `XCC-7Z73-J30AF7LC` | (미노출) | 1.15.0 | `redfish_lenovo_xcc3` |
| 10.100.15.2 | `C220-FCH2116V1V0` | TA-UNODE-G1 | 1.2.0 | `redfish_cisco_ucs_xseries` |

### 1.2 실행 결과

| 실행 | 대상 | status | sections | used_role | credential_scope | Account Write |
|---|---|---|---|---|---|---|
| Check Mode | 4대 전부 | success | — (수집 skip) | — | `common/redfish/standard` | **0** |
| 1차 | 4대 전부 | success | 9/11 | `primary` | `common/redfish/standard` | **0** |
| 2차 | 4대 전부 | success | 9/11 | `primary` | `common/redfish/standard` | **0** |

`sections 9/11` 은 `system` / `users` 가 `not_supported` 인 정상 상태다(종전과 동일).

재현 명령:

```bash
export ANSIBLE_CONFIG=ansible.cfg REPO_ROOT=$PWD
export INVENTORY_JSON='[{"bmc_ip":"10.100.15.34"},{"bmc_ip":"10.50.11.231"},
                        {"bmc_ip":"10.50.11.232"},{"bmc_ip":"10.100.15.2"}]'
ansible-playbook redfish-gather/site.yml -i redfish-gather/inventory.sh \
    --vault-password-file=<vault-pass> -e se_location=git [--check]
python3 scripts/ai/summarize_account_run.py <run.log>
```

### 1.3 확인된 계약

- **최종 Gathering 이 표준 계정으로 수행됐다** — 4대 전부 `used_role=primary`,
  `used_label=common_infraops`, `credential_scope=common/redfish/standard`, `fallback_used=false`
- **정상 상태 재실행에서 계정 쓰기 0** — reconcile 게이트가 열리지 않아 `account_service.yml`
  자체가 skip 됐다 (표준 인증 성공 → `_rf_primary_auth_rejected=false`)
- **Check Mode 에서 쓰기 0** — `module.check_mode` 가 dryrun 으로 접힌다
- **Recovery 자격이 최종 수집에 쓰인 경우 0**

---

## 2. 구현 요약

### 2.1 Phase 별 결과

| Phase | 내용 | commit | pytest |
|---|---|---|---|
| P0 | baseline 검증 → 커밋 | `6a964a43` `eb6caf8f` `042571af` | 2843 |
| P1 | 표현력 도입 (행동 변화 0) | `1600cfb6` | 2843 |
| P2 | 계약 충돌 교정 | `91e74b49` | 2869 |
| P3 | HPE Firmware Evidence 분리 | `b5fca92e` | 2886 |
| G-10 | drift-only 기본 + full body 예외 한정 | `5a069abb` | 2890 |
| P4 | Family 세분화 + 보호 계정 | `a28a01fd` | 2902 |
| P5 | 진단 축 보강 | `d33597bf` | 2917 |
| P6 | 계약 불변식 전수 고정 | `69f6688a` | **3063** |

### 2.2 도입한 표현력 4종

| 축 | 위치 | 왜 |
|---|---|---|
| Property Contract (`props`) | `_ACCOUNT_PROP_DEFAULTS`, `account_prop_contract()` | 같은 Property 라도 Family 마다 writable/read_only/verify_only/unsupported/unverified 가 다르다 |
| Create URI 종류 (`create_uri`) | `_create_target_uri()` | Accounts 열거 URI 와 Create URI 는 다른 개념이다 (Supermicro 최신 = AccountService 루트, Cisco IMC 3.x = Instance) |
| Operation 단위 If-Match (`if_match`) | `account_if_match()` | Inspur M6 는 Create 에 If-Match 를 쓰지 않고 Repair 에만 쓴다 |
| Firmware Evidence (`isolation_basis`) | `hpe_isolation_evidence()` | 한 Firmware 실측이 세대 전체로 번지지 않게 한다 |

### 2.3 제거한 것

| 제거 | 근거 |
|---|---|
| `PasswordChangeRequired` 추가 후 2차 POST | 05 §19 · 06 §17 · 07 §17 · 08 §17 · 09 §19 가 모두 금지 |
| 거부 속성 drop 후 재PATCH 사다리 | 같은 종류의 추측성 재시도. 무엇을 보낼지는 쓰기 **전에** 정한다 |
| `ACCOUNT_OPTIONAL_PATCH_PROPS` | "거부되면 빼도 되는 속성" 이라는 개념 자체가 추측을 전제한다 |
| `_ACCOUNT_CREATE_STRATEGY` | 소비자 0건인데 Family 표와 **다른 답**을 담고 있었다 |

허용되는 다중 쓰기는 두 가지뿐이며 둘 다 fallback 이 아니다:
**(A)** ETag 412 재시도 — 동일 URI + 동일 payload + 새 ETag, 1회.
**(B)** Family 가 쓰기 전에 확정한 sequence — HPE Password 단독 PATCH → drift 속성만 후속 PATCH.

---

## 3. Vendor 별 반영

| Vendor | 반영 | 근거 |
|---|---|---|
| **Dell** | `Locked` read_only, `PasswordChangeRequired` 미전송, `SYS474` 계열 정책 거부를 200 응답에서 포착 | 02 §8/§9/§11/§12 + 실측 10.100.15.34 |
| **HPE** | Password 단독 PATCH 유지, Evidence 만 Firmware 별 분리 (1.73=live_proven / 1.74·iLO7 1.19·1.20=advisory_derived / 그 외=safety_strategy) | 01 §4.1/§14/§17 + Advisory a00159600en_us |
| **Lenovo** | XCC2/XCC3 분리(XCC3 는 PCR 미지원), capability-first 판정, Purley 부정 신호, `HostBootstrapAccount` 보호 | 03 §7~§11/§14~§16 |
| **Cisco** | IMC 3.x Instance POST 분리, BMC 1.1 `Locked` writable + PCR read-only | 04 §4.2/§10.3/§25 |
| **Supermicro** | Superchip(01.04+) 경계 추가, Create URI 를 **장비값 Generation+Firmware 확정 시에만** 최신 계약으로 전환 | 05 §9/§10/§31/§34 |
| **Inspur** | Create 에 If-Match 없음 / Repair 에만 있음을 계약으로 고정 | 06 §5/§11/§29 |
| **Huawei** | `Locked` writable 유지(제거하지 않음), 계정별 Redfish Login Interface 관측 | 07 §5.1/§10/§12 |
| **Fujitsu** | 재시도 제거, 미지원 RoleId 진단, 나머지 UNVERIFIED 유지 | 08 §9/§17/§29/§32 |
| **Quanta** | Legacy/Modern/Inhouse OpenBMC 3분할(동작 동일), AccountTypes 미전송 고정 | 09 §5/§6/§9/§44 |

---

## 4. 계약 불변식 (테스트로 고정)

`tests/unit/test_account_write_contract_invariants.py` 가 **Family 표 전수**(17 Family)에 대해
146건을 검사한다. 시나리오 테스트는 "새로 추가한 Family 가 규칙을 어기는 경우" 를 못 막기 때문이다.

| 불변식 | 검사 |
|---|---|
| 6 Property × 2 Operation 이 5-상태 중 하나로 확정 | 전 Family |
| `writable` 이 아니면 쓰기 0 | 전 Family |
| 표에 없는 Property 기본값 = `unverified` | ✓ |
| 생성 payload 에 비-writable 속성 미포함 | 전 Family |
| UNVERIFIED Family 는 full body 예외 미상속 | 전 UNVERIFIED |
| UNVERIFIED Family 는 AccountTypes 미전송 (StrictAccountTypes 회피) | 전 UNVERIFIED |
| full body 예외 = `lenovo_xcc2/xcc3_accounttypes` 두 곳뿐 | ✓ |
| Create 에 If-Match 요구하는 Family 0 | 전 Family |
| UNKNOWN / ambiguous / protected 에서 Write 0 | ✓ |
| dry-run Write 0 | 9 Vendor |
| Fresh Auth 실패 시 `recovered=true` 0 | 9 Vendor |
| 복구 자격 인증 실패 시 Write 0 | 9 Vendor |
| 결과에 비밀번호 미포함 | ✓ |

추가 파일: `test_account_no_write_fallback.py`(27) — blind fallback 0 과 허용 예외 2종의 경계.
`test_account_diagnosis_axes.py`(15) — 쓰지 않고 알려주는 축.

---

## 5. 검증 결과

| 항목 | 결과 |
|---|---|
| `pytest tests/` | **3063 passed**, 10 skipped, 7 xfailed |
| `ansible-playbook --syntax-check` ×3 (redfish/os/esxi) | PASS (WSL ansible-core 2.20.7) |
| `output_schema_drift_check.py` | exit 0 — envelope 13 필드 불변 |
| `verify_vendor_boundary.py` | exit 0 |
| `verify_harness_consistency.py` | exit 0 |
| `verify_no_plaintext_secret.py` | exit 0 |
| `check_project_map_drift.py` | exit 0 |
| baseline / replay / envelope 회귀 | 385 passed |
| e2e | 590 passed |
| 실장비 Check Mode / 1차 / 2차 | 4대 전부 success, Write 0 |

신규 진단 필드는 전부 `diagnosis.details.account_service` 하위다 — **envelope 13 필드는 변하지 않았다.**

---

## 6. 남은 것

### 6.1 조건 미발생 (실장비가 있어도 못 함)

| 항목 | 왜 |
|---|---|
| Account CREATE 실증 | 4대 모두 표준 계정이 이미 존재. 조건을 만들려면 계정을 지워야 한다 |
| Account REPAIR 실증 (수정 후) | 표준 인증이 4대 모두 성공해 게이트가 열리지 않는다 |

두 경우 모두 **운영 계정을 삭제하거나 비밀번호를 망가뜨려 조건을 만들지 않았다.**

### 6.2 실장비 부재

Supermicro / Huawei / Inspur / Fujitsu / Quanta — 장비 0대. 코드 경로와 계약 표만 정비했고
어느 Family 도 PROVEN 으로 올리지 않았다.

### 6.3 조사 필요 (구현 대상 아님)

| 대상 | 얻는 것 |
|---|---|
| Fujitsu `iRMC RESTful API Specification pack` (2026-01-13) 원문 | S4/S5/S6 AccountService Method Table |
| Supermicro `/AccountService` POST 의 Firmware 경계 | `create_uri` 전환 근거 |
| Huawei Redfish Login Interface OEM field/action | 복구 payload (확보 전 구현 금지) |
| Cisco IMC allowable Account Id 범위 공식 근거 | `id_range` 확정 |

### 6.4 알려진 제약

- `scripts/ai/verify_no_plaintext_secret.py` 는 기본 Windows 콘솔(cp949)에서
  `UnicodeEncodeError` 로 exit 1 이 된다. 검출 결과는 정상(`PYTHONUTF8=1` 로 확인 시 exit 0)이며
  스크립트의 출력 인코딩 문제다 — 본 작업 범위 밖이라 고치지 않았다.
- Adapter 세대 오선택(PWC-4)은 그대로 남아 있다. Dell `10.100.15.34` 는 iDRAC9 인데 adapter 가
  `redfish_dell_idrac10` 을 고른다. **계정 경로는 Firmware major 로 판정**하므로 영향받지 않지만,
  adapter_id 자체는 여전히 틀린다.
