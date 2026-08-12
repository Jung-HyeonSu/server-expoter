# Location 기반 Credential Resolver — 구현 검증 증거

- **일시**: 2026-08-12
- **대상 commit**: `70744c76` (feat: Location 기반 Credential Resolver 도입)
- **설계 정본**: `docs/ai/VAULT-CREDENTIAL-RESOLVER-DESIGN-2026-08-12.md`
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
| flat vault 미삭제 | `vault/*.yml` + `vault/redfish/*.yml` 12개 존재 | [PASS] |
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
