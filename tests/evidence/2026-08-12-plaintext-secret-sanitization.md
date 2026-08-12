# Repository 평문 Secret 전수 조사 및 정리

- 일자: 2026-08-12
- 기준 Commit: `26394474`
- 범위: **현재 HEAD 의 tracked content 만.** Git history 는 재작성하지 않았다 (사용자 지시 §13).
- **이 문서에는 자격증명 평문이 없다.** 모든 값은 sha256 앞 8자리로만 지칭한다.

---

## 1. 조사 방법

1. 운영 Vault 49개를 복호화해 살아 있는 자격증명 문자열을 확보 (15종).
2. 직전 감사가 digest 로 지목한 **과거 세대** 값을 해당 문서 라인에서 복원 (4종).
3. 두 집합을 합쳐 `git ls-files` 기준 **tracked 17,982개 파일 전수**를 부분문자열 검사.

digest 는 원문을 복원할 수 없으므로 이 문서와 게이트 코드에 남아도 자격증명이 아니다.

---

## 2. 자명성 분류 — 무엇을 Secret 으로 볼 것인가

발견된 15종 중 5종은 **벤더가 매뉴얼에 공개한 공장 기본값이자 사전 단어**였다.

| 분류 | 종수 | 파일 수 (최대) | 처리 |
|---|---:|---:|---|
| 공개 기본값 / 사전 단어 (`admin`, `password`, `ADMIN`, Dell 공장값, Huawei 공장값) | 5 | 627 / 433 / 13 / 11 / 3 | **정리 대상 아님** |
| 실제 자격증명 (non-trivial) | 10 | 373 / 17 / 14 / 8 / 8 / 7 / 7 / 3 / 3 / 2 | **전량 제거** |

공개 기본값을 정리 대상에 넣지 않은 이유: 문자열이 `admin` / `password` 같은 평범한
단어라 산문·코드·주석 어디에나 등장한다. 이를 누출로 취급하면 627개 파일을 건드리면서도
얻는 보안 이득이 0 이고, 게이트는 오탐으로 무력해진다. 해당 값은 이미
`docs/21_vault-operations.md` 의 벤더 기본값 표에 **공개 문서로** 존재한다.

---

## 3. 정리 전 / 후

### 정리 전 (실 자격증명 10종)

| secret_type | digest8 | file_count | location_category | runtime_required | sanitized |
|---|---|---:|---|---|---|
| vault master (= git Location 의 OS/ESXi/Dell recovery, Redis fact-cache 와 동일 값) | `428829ae` | 373 | `tests/reference/os` 269, `tests/evidence` 61, `tests/reference/agent` 20, `docs/ai` 12, 테스트 코드 7, `scripts` 3, root 1 | **아니오** | 예 |
| 표준 계정 gen1 (= 일부 Location 의 HPE/Lenovo recovery) | `9892c533` | 17 | `docs/ai` 8, `tests/evidence` 4, 테스트 코드 3, `schema` 2 | 아니오 | 예 |
| git HPE/Lenovo recovery | `2b3b6862` | 14 | `docs/ai` 6, `tests/evidence` 5, 테스트 코드 2, `scripts` 1 | 아니오 | 예 |
| Cisco recovery (전 Location) | `9477272a` | 8 | `docs/ai` 4, `tests/evidence` 2, `scripts` 1, 테스트 코드 1 | 아니오 | 예 |
| 표준 계정 gen2 (회전됨) | `9b87f708` | 8 | `docs/ai` 4, `schema` 2, `tests/evidence` 1, 테스트 코드 1 | 아니오 | 예 |
| ich/yi Dell recovery | `f28b309b` | 7 | `docs/ai` 3, 테스트 코드 2, `tests/evidence` 2 | 아니오 | 예 |
| 과거 자격 (회전됨) | `37a1db6b` | 7 | `docs/ai` 3, 테스트 코드 2, `tests/evidence` 2 | 아니오 | 예 |
| 표준 계정 gen3 (직전 세대) | `a109e369` | 3 | `docs/ai` 3 | 아니오 | 예 |
| 과거 Dell recovery | `1d8fe022` | 3 | `docs/ai` 2, `tests/evidence` 1 | 아니오 | 예 |
| chj/ich/yi OS 계정 | `f3e3f831` | 2 | `docs/ai` 2 | 아니오 | 예 |

`runtime_required` 가 전부 **아니오** 인 근거: 운영 경로는 자격증명을 오직
**암호화된 `vault/**`** 에서만 읽는다. Vault master 는 Jenkins credential 로 주입돼
`.vault_pass` 로 쓰이고 그 파일은 `.gitignore` 되어 있다. `redfish-gather/`, `os-gather/`,
`esxi-gather/`, `common/`, `callback_plugins/`, `filter_plugins/`, `lookup_plugins/`,
`adapters/`, `ansible.cfg`, `Jenkinsfile*` 어디에도 위 literal 이 없다.

### 정리 후

```
digest 검사 (tracked 17,982건)                          → 평문 자격증명 0건
literal 검사 (운영 자격 11종 × tracked 17,982건)         → 평문 자격증명 0건
```

회전되어 원문을 복원할 수 없는 4종(`1d8fe022`, `37a1db6b`, `9b87f708`, `a109e369`)은
**저장소에서 더 이상 복원되지 않는다** — 그 자체가 제거의 증거다.

**신규 표준 비밀번호(`6292d395`)는 정리 전에도 후에도 tracked file 0건**이다.

---

## 4. 처리 방식별 내역

### 4.1 문서 / 증거 / 참조 덤프 (379 파일)

`__REDACTED__`(저장소 기존 관례) 로 치환.

| 위치 | 파일 수 | 성격 |
|---|---:|---|
| `tests/reference/os` | 269 | `echo <PW> \| sudo -S ...` 형태로 캡처된 raw 명령 출력 |
| `tests/evidence` | 66 | 과거 검증 기록 |
| `docs/ai` | 21 | CURRENT_STATE / ADR / catalog / ticket |
| `tests/reference/agent` | 20 | Jenkins agent `ansible.cfg` 덤프 (`fact_caching_connection` 4번째 필드) |
| `schema/output_examples` | 2 | 어느 계정으로 인증했는지 적은 주석 |
| `.gitignore` | 1 | 주석 안의 값 |

이 파일들을 읽는 **테스트는 없다** — `tests/integration/account_replay.py` 와
`test_account_reconcile_replay.py` 가 읽는 것은 `tests/reference/redfish/**` 이고,
그쪽에는 실 자격증명이 없었다. 치환 후 integration 243건 전량 통과로 확인했다.

### 4.2 테스트 코드 (8 파일) — 가드 자체가 누출 지점이었다

누출 방지 테스트들이 **검사 대상인 진짜 비밀번호를 소스에 그대로 적어** 두고 있었다.

```python
SECRET_VALUE_PATTERNS = tuple(re.compile(p) for p in (
    r"<실제 비밀번호 5개>",          # ← 가드 파일이 곧 누출 지점
    r"password\s*[=:]\s*...",
))
```

두 가지로 나눠 고쳤다.

- **입력으로 쓰이던 값** (`_try_redfish_auth(..., <실비밀번호>, ...)`,
  `account_service_provision(target_password=<실비밀번호>)`) → 합성 canary
  (`zzz-canary-*-zzz`). 테스트 의미는 동일하다 — "넣은 자격증명이 출력에 새지 않는가".
  오히려 **입력과 검사 대상이 같은 값**이 되어 더 정확해졌다.
- **needle 로만 쓰이던 값** → `tests/secret_guard.py` 의 **digest 대조**로 대체.
  `find_known_secrets(text)` 가 알려진 자격증명의 sha256 앞 8자리와 대조하므로 평문을
  저장하지 않고도 종전과 동일하게 "이 값이 나왔는가" 를 판정한다. 실패 메시지에도
  digest 만 찍힌다.

대상: `test_envelope_failure_modes.py`, `test_failure_code_contract.py`,
`test_failure_reason_case_matrix.py`, `test_account_service_unsupported_f13.py`,
`test_os_candidate_search.py`, `test_os_precheck_integration.py`,
`test_precheck_detail_propagation.py`, `test_precheck_probe_os.py`.

### 4.3 보조 스크립트 (4 파일) — 환경변수 전환

| 파일 | 종전 | 변경 |
|---|---|---|
| `scripts/ai/bug_tracker/agent_ops.py` | `os.environ.get("SE_AGENT_PASS", <실비밀번호>)` | 평문 기본값 제거 + 미설정 시 명확히 실패 |
| `scripts/ai/bug_tracker/inventory_lab_linux.ini` | `ansible_password=<실비밀번호>` | `lookup('env','SE_LAB_SSH_PASS')` |
| `scripts/ai/bug_tracker/capture_raw_linux.yml` | `echo <실비밀번호> \| sudo -S` (9곳) | `echo {{ ansible_become_password }} \| sudo -S` |
| `scripts/ai/add_lab_recovery_to_all_vaults.py` | recovery 자격 표 평문 | `SE_LAB_RECOVERY_PASS` 환경변수 + DEPRECATED 표기 (대상 경로 `vault/redfish/*.yml` 는 flat vault 제거(`adc99570`)로 이미 부재) |

---

## 5. 재발 방지

- **`tests/secret_guard.py`** — digest + 길이 표, 합성 canary, 구조 패턴(일반 자격증명 형태).
  회귀 16건(`tests/unit/test_secret_guard.py`)이 "표에 평문이 없을 것", "공개 기본값을
  넣지 말 것", "실패 메시지에 평문이 찍히지 않을 것" 까지 고정한다.
- **`scripts/ai/verify_no_plaintext_secret.py`** — Secret Leak Gate.
  - 기본: 변경 파일만 digest 검사 (vault 비밀번호 불필요 → pre-commit / CI 어디서나)
  - `--all`: tracked 전수 digest 검사
  - `--vault-password-file`: 운영 Vault 를 복호화해 살아 있는 자격증명으로 전수 literal 검사

---

## 6. 남은 것 — 이번 cycle 에서 하지 않은 것

### 6.1 Git history (사용자 지시 §13 — 자동 재작성 금지)

위 10종 전부가 **과거 commit 의 파일 내용과 commit 메시지**에 남아 있다. 직전 감사가
약 13개 commit 의 메시지에 값이 그대로 있음을 확인했다. history 재작성은 하지 않았다.

### 6.2 Rotation 판단 (사용자 지시 §12 — 평문 제거와 rotation 분리)

| digest8 | 현재 유효한가 | rotation 필요성 | 영향 범위 |
|---|---|---|---|
| `428829ae` | **예** — vault master 이자 git Location 의 OS/ESXi/Dell recovery | **최우선.** 단일 값이 vault 마스터 + 다수 운영 계정을 겸한다 | Jenkins credential, git Location 전 채널, Redis fact-cache |
| `9892c533` | **예** — chj/ich/yi 의 HPE·Lenovo recovery | 높음 | 해당 Location Redfish recovery |
| `2b3b6862` | **예** — git HPE/Lenovo recovery | 높음 | git Redfish recovery |
| `9477272a` | **예** — 전 Location Cisco recovery | 높음 | Cisco recovery |
| `f28b309b` | **예** — ich/yi Dell recovery | 중간 | 해당 Location |
| `f3e3f831` | **예** — chj/ich/yi OS 계정 | 중간 | 해당 Location OS 채널 |
| `9b87f708` / `a109e369` / `1d8fe022` / `37a1db6b` | 아니오 (회전됨) | 불필요 | — |

**판단**: 평문 제거만으로는 history 노출이 남으므로, 위 "현재 유효" 6종은 rotation
대상이다. 특히 `428829ae` 는 vault master 를 겸하고 있어 우선순위가 가장 높다.
rotation 실행은 운영 결정이며 이번 cycle 범위 밖이다 (`docs/ai/NEXT_ACTIONS.md` 등재).

### 6.3 untracked 잔여물 (tracked 정리 범위 밖)

`.vault_pass`, `vault/.lab-credentials.yml`, `tests/reference/local/*`,
`__pycache__/*.pyc` 등 untracked 파일에도 값이 남아 있다. `.gitignore` 대상이라 저장소에
올라가지 않지만, **작업 머신 로컬에는 존재**한다. 정리는 운영자 몫으로 남긴다.
