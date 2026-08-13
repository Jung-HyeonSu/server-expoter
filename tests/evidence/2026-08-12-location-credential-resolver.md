# Location 기반 Credential Resolver — 구현 검증 증거

- **일시**: 2026-08-12
- **대상 commit**: `70744c76` (feat) + `117c5190` (fix: OS credential_scope 누락 보완)
- **설계 정본**: `docs/ai/contracts/vault-credential-resolver.md`
- **검증 환경**: Windows 11 (pytest) + WSL Ubuntu 24.04 (ansible-core 2.19.12, venv `~/.se-ansible`)
  - Windows 의 `ansible-playbook` 은 `os.get_blocking` 부재로 실행 불가 → WSL 사용

---

## 1. 정적 검증

| 항목 | 결과 | 증거 |
|---|---|---|
| `ansible-playbook --syntax-check` × 3 채널 | [PASS] | os/esxi/redfish 모두 `exit=0` (WSL) |
| `pytest tests/` | [PASS] | 2618 passed / 10 skipped / 7 xfailed |
| `output_schema_drift_check.py` | [PASS] | `sections=11 fd_paths=175 fd_section_prefixes=18` |
| `tests/validate_field_dictionary.py` | [PASS] | `10 checks, 8 passed, 0 failed` |
| `verify_vendor_boundary.py` | [PASS] | vendor 하드코딩 0건 |
| `verify_harness_consistency.py` | [PASS] | 모든 참조 정합 |
| `py_compile` (신규/수정 Python 7종) | [PASS] | — |

---

## 2. Vendor 정규화 SoT 통합 (Phase 1)

**동치 증명 대상**: `tests/fixtures/**` 에서 추출한 실측 Manufacturer/vendor 문자열
62종 ∪ `vendor_aliases.yml` alias 전량 ∪ canonical 9종 ∪ 경계값 = **103 입력**

| 구현 | 결과 |
|---|---|
| `redfish_gather._normalize_vendor_from_aliases` | 기준 |
| `detect_vendor.yml` 인라인 Jinja (제거 대상) | 103/103 동일 |
| `adapter_common.normalize_vendor` + `canonical_vendor` 필터 (신규) | 103/103 동일 |

**단 1건 불일치 발견 → 실제 버그였다.**

- 입력 `''` (빈 문자열)에서 라이브러리만 `'dell'` 을 반환했다.
- 원인: 부분 매칭의 `mfr_lower in key` 가 `mfr_lower=''` 이면 **모든 key 에 대해 참** →
  dict 첫 항목 vendor 로 확정. 빈 alias 방어(`if key and ...`)는 있었으나 빈 **입력** 방어가 없었다.
- 도달 경로 실재: `redfish_gather.py` 의 Chassis/Managers/Systems Manufacturer fallback 이
  `mfr.strip().lower()` 로 호출 → Manufacturer 가 `"   "` 이면 빈 문자열이 된다.
- 영향: 종전에는 adapter 오선택에 그쳤으나, vault 경로가 vendor 에서 파생되면
  **다른 vendor 의 자격증명을 시도**하는 결과로 이어진다.
- 조치: 빈 입력 가드 추가 + 회귀 테스트 고정
  (`test_vendor_normalizer_sot.py::test_empty_manufacturer_does_not_become_a_vendor`)

`_FALLBACK_VENDOR_MAP` ↔ `vendor_aliases.yml`: alias 38종 양방향 차집합 0, 값 충돌 0 (테스트로 고정).

---

## 3. 런타임 검증 (WSL, mock BMC)

### 3.1 Resolver 단위 흐름

`-e se_location=ich` 로 `resolve_and_load.yml` 직접 호출:

| 케이스 | scope | reason | outcome |
|---|---|---|---|
| redfish + dell (vault 존재) | `ich/redfish/dell` | resolved | `loaded` (accounts 2) |
| redfish + vendor 미상 | (없음) | `vendor_unresolved` | `not_resolved` |
| os + linux (vault 부재) | `ich/os/linux` | resolved | `credential_set_missing` |
| esxi (vault 부재) | `ich/esxi` | resolved | `credential_set_missing` |
| `se_location=no-such-dc` | (없음) | `unknown_location` | `not_resolved` |
| `se_location` **미전달** | (없음) | `unknown_location` | `not_resolved` |

마지막 행이 extra-vars 채택 이유의 실증이다 — 환경변수였다면 조용히 `''` 가 되어
잘못된(또는 없는) vault 를 가리켰을 것이다.

**후보 순서 보존 확인**: vault 에 `[recovery, primary]` 순으로 넣었을 때 출력도
`['dell_recovery', 'dell_primary']` — 재정렬 없음.

**vendor 필터 실행 결과**:
`['Dell Inc.','HPE','Hewlett Packard Enterprise','Contoso','','   ','Super Micro Computer, Inc.']`
→ `['dell','hpe','hpe','unknown','unknown','unknown','supermicro']`

### 3.2 채널 E2E — envelope cardinality (rule 11)

TEST-NET(RFC 5737) 2개 대상 → **envelope 정확히 2개**. 둘 다
`status=failed / stage=reachable / code=TCP_CONNECT_FAILED / credential_scope=null`
(precheck 가 credential 단계 이전에 멈추므로 scope 가 없는 것이 정상).

### 3.3 신규 실패 Contract — 같은 대상, credential set 유무만 다르게

로컬 mock BMC (`ServiceRoot` 200 + `Vendor: Dell`, 그 외 401), `se_location=ich`:

| `vault/ich/redfish/dell.yml` | `failure_stage` | `failure_code` | `auth_success` | `credential_scope` |
|---|---|---|---|---|
| **부재** | `auth` | `CREDENTIAL_SET_UNAVAILABLE` | `null` | `ich/redfish/dell` |
| **존재** (틀린 자격) | `auth` | `AUTH_PROBE_FAILED` | `false` | `ich/redfish/dell` |

- 사용자 문장은 두 경우 모두 4번 (`대상에 접속할 수 없습니다. 자격증명과 계정 권한을 확인하세요.`)
  → Portal 5문장 집합 불변.
- 구분은 `failure_code` 와 `errors[].detail` 이 한다:
  `Credential set 을 열 수 없습니다 (scope=ich/redfish/dell, outcome=credential_set_missing).`
- **`auth_success` 가 `null` vs `false` 로 갈린다** — 미시도와 명시적 거부의 구분이
  실제 실행에서 성립함을 확인.

### 3.4 Secret 미노출

- 위 3.3 실행의 envelope JSON 전문에서 vault 의 username/password 문자열 검색 → **0건**
- ansible 실행 로그(`-v` 기본) 에서도 password 문자열 → **0건**
- `vault_decrypt_check.py` 결과/출력에 canary 값 미노출 (테스트 9건으로 고정)

---

## 4. 사용자 제약 준수 확인

| 제약 | 확인 방법 | 결과 |
|---|---|---|
| accounts 배열 순서 불변 | 정렬 코드 grep 0건 + 런타임 순서 관측 | [PASS] |
| Generation 미사용 | resolver 시그니처에 축 부재 (테스트 고정) | [PASS] |
| 다른 Location/Vendor fallback 금지 | `fallback_profiles` 루프 삭제, 폴백 분기 0건 | [PASS] |
| Adapter 선택 로직 무변경 | `adapter_common.py` / `adapter_loader.py` / `adapters/` diff 0 | [PASS] |
| Redfish 5초 backoff 유지 | `try_one_account.yml:133` `sleep 5` 존재 | [PASS] |
| OS/ESXi backoff 미추가 | 4개 파일 `retries:`/`until:` 0건 | [PASS] |
| flat vault 미삭제 | `vault/*.yml` + `vault/<loc>/redfish/*.yml` 12개 존재 | [PASS] |
| runtime flat fallback 부재 | 신규/수정 코드에서 구 경로 참조 0건 | [PASS] |

---

## 5. 실장비 Pilot 필요 항목 (테스트 통과로 대체 불가)

| # | 항목 | 왜 필요한가 |
|---|---|---|
| P1 | Location 별 실제 vault 작성 + 복호화 검증 | 실제 계정 값은 운영 담당자만 안다. mock 은 평문 YAML 이었고 **ansible-vault 암호문 복호화 경로는 미검증** |
| P2 | OS Linux / Windows 실장비 1대씩 | `credential_scope == <loc>/os/<type>`, become 경로, WinRM 인증 |
| P3 | ESXi 실장비 1대 | `credential_scope == <loc>/esxi`, lockdown 환경 동작 |
| P4 | Redfish vendor 별 최소 1대 | 실제 BMC 의 Manufacturer 표기로 canonical 이 기대대로 나오는지 |
| P5 | Jenkins `built-in` 노드 SCM checkout 가부 | `Resolve Location` stage 성립 조건. 저장소 코드로 확인 불가 |
| P6 | 미등록 Location 빌드 → agent 대기 없이 실패 | Jenkins 런타임 동작 |
| P7 | Redfish reconcile (Account Write) 경로 | credential 경로 변경 후에도 진입 게이트가 그대로인지. **dry-run 과 실제 write 를 구분해 보고할 것** |
| P8 | Portal 소비자의 미지 `failure_code` 처리 | 외부 시스템. `CREDENTIAL_SET_UNAVAILABLE` 수신 시 동작 확인 |

**mock BMC 검증은 실장비 검증이 아니다.** 위 8건이 끝나기 전에는 flat vault 를 삭제하지 않는다.


---

## 6. Phase 7 전체 검증 — 14개 항목 (2026-08-12, commit `117c5190` 기준)

| # | 항목 | 결과 | 증거 |
|---|---|---|---|
| 1 | `ansible-playbook --syntax-check` × 3 | [PASS] | os/esxi/redfish `exit=0` (WSL) |
| 2 | 전체 pytest | [PASS] | **2638 passed** / 10 skipped / 7 xfailed |
| 3 | `validate_field_dictionary.py` | [PASS] | `10 checks, 8 passed, 0 failed` |
| 4 | `output_schema_drift_check.py` | [PASS] | `sections=11 fd_paths=175 fd_section_prefixes=18` |
| 5 | `verify_vendor_boundary.py` | [PASS] | vendor 하드코딩 0건 |
| 6 | `verify_harness_consistency.py` | [PASS] | 모든 참조 정합 |
| 7 | Credential Resolver 신규 테스트 | [PASS] | 7파일 **358 passed** |
| 8 | 기존 Gathering regression | [PASS] | regression 169 / integration(not live) 200 / e2e 587 |
| 9 | Secret · password 로그 노출 | [PASS] | 아래 6.1 |
| 10 | 다른 Location/Vendor runtime fallback 부재 | [PASS] | 아래 6.2 |
| 11 | accounts 후보 순서 보존 | [PASS] | 아래 6.3 |
| 12 | Redfish 5초 backoff 유지 | [PASS] | `try_one_account.yml:133` + `test_credential_probe_classification.py:85` 고정 |
| 13 | `CREDENTIAL_SET_UNAVAILABLE` Contract + 기존 code 회귀 | [PASS] | 아래 6.4 |
| 14 | `credential_scope` 3채널 반영 | [PASS] (**결함 1건 수정 후**) | 아래 6.5 |

### 6.0 Phase 7 에서 발견·수정한 결함

**항목 14 검증 중 OS 성공 경로 2곳의 `credential_scope` 누락을 발견했다.**
Redfish / ESXi 는 성공·실패 양쪽에 반영됐는데 `os-gather` 는 rescue 에만 들어가 있었다.
성공 경로에 없으면 "성공한 대상과 실패한 대상이 같은 자격 세트를 썼는가" 를 비교할 수 없어
원인 범위를 좁히지 못한다. `os-gather/site.yml:343`(linux) / `:629`(windows) 에 추가하고,
3채널 성공/실패 8곳을 `tests/e2e/test_credential_scope_exposure.py` 로 고정했다.
수정 후 전체 회귀를 다시 수행했다 (위 표는 재수행 결과다).

### 6.1 Secret 노출 — 정적 + 런타임

정적:
- vault 내용을 다루는 태스크의 `no_log` 누락 **0건** (11개 파일 AST 검사)
- 민감 변수를 `debug` 로 출력하는 태스크 **0건**
- 신규/수정 Python 5종에 평문 자격 하드코딩 **0건**

런타임 (`ANSIBLE_VERBOSITY=2`, mock BMC + 평문 vault 에 canary 값 주입):
- `CANARYUSER1/2`, `CANARYPASS1/2` — ansible 로그 **0건**, envelope **0건**
- 이때 자격은 실제로 로드·사용됐다 (`auth_success=false`, 즉 401 을 받을 만큼 전송됨)
  → "안 읽어서 안 샌 것" 이 아니라 **읽고도 안 샌 것**

### 6.2 교차 fallback 부재 (정적)

- 주석 제외 후 실행 코드의 구 flat vault 경로 참조 **0건**
- `fallback_profiles` production 코드 **0건** (주석 1건만 — 삭제 사유 기록)
- `include_vars` + `loop` 조합 **0건** (여러 vault 순회 구조 부재)
- 순수함수: (location, vendor) 9조합 → distinct 경로 9개, 반환값에 경로 list 필드 없음

### 6.3 후보 순서 보존

- `credential_common.py` / `credential_accounts.py` 에 정렬 코드 **0건**
- 3채널 `loop:` 이 정규화 결과를 그대로 소비
  (`try_credentials.yml:36` / `:30` / `collect_standard.yml:90`)
- recovery-first 포함 3케이스에서 입력 순서 == 출력 순서, 필터 == 순수함수

### 6.4 failure_code Contract

- 기존 7종 **전부 유지**, 삭제 0, 추가 `CREDENTIAL_SET_UNAVAILABLE` 1종
- `field_dictionary` enum == `REASON_BY_FAILURE_CODE` 키 집합 (양쪽 정본 일치)
- 기존 7종의 사용자 문장 **변경 0건**
- 신규 code → 4번 문장 재사용, `failure_reasons.yml` 문장 수 **6개 불변** (신규 문장 없음)
- Ansible YAML ↔ Python 상수 글자 동일
- baseline 10건 전부 `failure_code: null` → **영향 없음**

### 6.5 `credential_scope` 3채널 (8곳)

`os-gather:343, 449, 629, 713` / `esxi-gather:236, 310` / `redfish-gather:276, 445`
= 3채널 × 성공·실패 (OS 는 linux/windows 두 Play).
`field_dictionary` 등록: `type=string|null`, `channel=[esxi, os, redfish]`.
미결정 시 `''` 가 아니라 `null` 로 떨어지는 것까지 테스트로 고정.

### 6.6 런타임 시나리오 매트릭스 (mock BMC, 실장비 아님)

| 시나리오 | vendor | credential_scope | failure_code | auth_success |
|---|---|---|---|---|
| ServiceRoot 정상 + vault 부재 | dell | `ich/redfish/dell` | `CREDENTIAL_SET_UNAVAILABLE` | `null` |
| ServiceRoot 정상 + vault 존재, 자격 불일치 | dell | `ich/redfish/dell` | `AUTH_PROBE_FAILED` | `false` |
| ServiceRoot 정상 + vault 존재, **자격 일치** | dell | `ich/redfish/dell` | (수집 단계) | **`true`** |
| Manufacturer 미등록(Contoso) + 무인증 응답 | null | **`null`** (vault 미접근) | `null` (success) | `true` |
| TEST-NET 2대 (미도달) | null | `null` | `TCP_CONNECT_FAILED` | `null` |

3행이 **Location vault 의 자격으로 실제 인증이 통과함**을 보인다 (`first_auth=200`).
그 실행에서 수집이 0섹션인 것은 DMTF Contoso mockup 에 `Vendor='Dell'` 을 강제로 덮어
Dell OEM 경로(`ServiceRoot.Oem.Dell.ServiceTag`)와 데이터가 어긋나게 만든 **mock 의 인위적
조건** 때문이다 — mock 이 404 로 답한 경로는 0건이었고, 같은 recording 을 쓰는 기존
`tests/integration/test_dmtf_mockup_replay.py` 8건은 통과한다.
4행은 "정체 미상 장비는 빈 자격 1회 best-effort" 보존 분기가 vault 를 건드리지 않음을 보인다.

**위 표는 전부 mock 이다. 실장비 검증이 아니다** (§5 Pilot 8건 유효).
