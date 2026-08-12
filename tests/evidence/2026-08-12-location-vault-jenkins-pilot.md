# Evidence — Location Vault 실환경 Jenkins Pilot (2026-08-12)

> 대상: 실제 Jenkins (`clovirone-server-gather-vault-pilot`) + 실제 encrypted Ansible Vault + 실장비.
> 기준 commit: `d09ff344` (구현 `92bfdc1d` + Location Vault 48개 + `git` Location).
> 이 문서는 **자동 테스트 결과가 아니다.** 전부 실 빌드 로그에서 뽑은 값이다.
> Secret 값은 이 문서 어디에도 없다 — 경로 / label / role / 개수만 다룬다.

## 0. 한눈에

| # | 성공 조건 | 결과 |
|---|---|---|
| P1 | 신규 encrypted Location Vault 48개 구성/검증 | [PASS] |
| P2 | `ich` Location Resolve | [PASS] |
| P3 | `chj` Location Resolve | [PASS] |
| P4 | `yi` Location Resolve | [PASS] |
| P5 | `git` Location Resolve | [PASS] |
| P6 | Invalid Location 사전 차단 | [PASS] |
| P7 | Linux 실장비 | [PASS] (2대 / 2 Location) |
| P8 | Windows 실장비 | [PASS] (대상 IP 정정 후) |
| P9 | ESXi 실장비 | [PASS] |
| P10 | Redfish Dell | [PASS] (수집) — 단 P16 참조 |
| P11 | Redfish HPE | **[HOLD]** — BMC 미응답 (환경) |
| P12 | credential_scope 정확성 | [PASS] (13 envelope 전수) |
| P13 | 실제 encrypted Vault 복호화 | [PASS] |
| P14 | Secret 비노출 | [PASS] |
| P15 | runtime cross-location / vendor / flat fallback 없음 | [PASS] (음성 대조군 포함) |
| P16 | Redfish 실제 Account Write 0건 | **[FAIL] — 1건 발생** (§7) |

추가 검증: Redfish Lenovo [PASS] (2 Location), Redfish Cisco [PASS].

## 1. 사용한 Jenkins Job

| 항목 | 값 |
|---|---|
| Job | `clovirone-server-gather-vault-pilot` (신규) |
| 생성 방식 | 운영 Job `clovirone-server-gather` 의 `config.xml` 복제 후 description / `loc` 설명만 수정 |
| 왜 별도 Job | 운영 Job 의 빌드 이력·파라미터를 오염시키지 않기 위해. 파이프라인 정의·SCM·credential 은 **운영과 동일** |
| Pipeline | `Jenkinsfile_portal` (`*/main`, SCM 정의 그대로) |
| commit/ref | `d09ff344` |
| Vault credential | `server-gather-vault-password` (운영과 동일 Jenkins Credential) |
| callbackUrl | `http://127.0.0.1:1` — 즉시 거부되는 주소. **모든 빌드가 UNSTABLE 인 이유가 이것이다** (Callback stage 3회 재시도 후 `unstable`, rule 31 R2 의 graceful 동작). 운영 Job 최근 빌드(#185~#189)도 같은 이유로 UNSTABLE 이므로 이 상태가 기준선이다 |

임시로 만든 `se-vault-pilot-tmp` (§6, §7 용) 는 검증 후 **삭제했다** (`/api/json` → 404 확인).
임시 브랜치 `pilot/temp-verification` 도 양쪽 remote 에서 삭제했다.

## 2. Location Vault 48개 (P1)

`vault/{linux,windows,esxi}.yml` + `vault/redfish/<vendor>.yml` 9개 = flat 12개를
**복호화하지 않고 암호문 파일 그대로** 4 Location 에 복사했다.

```
vault/<loc>/os/linux.yml      vault/<loc>/os/windows.yml
vault/<loc>/esxi.yml          vault/<loc>/redfish/<vendor>.yml × 9
loc ∈ {ich, chj, yi, git}     → 12 × 4 = 48
```

| 검증 항목 | 방법 | 결과 |
|---|---|---|
| 1. 파일 존재 | `find` | 48/48 |
| 2. `$ANSIBLE_VAULT` 헤더 | 선두 22바이트 비교 | 48/48 |
| 3. 원본과 SHA256 동일 | working copy 바이트 해시 | 48/48 |
| 3'. **git index blob 동일** | `git ls-files -s` 의 blob SHA 대조 | 48/48 — Jenkins 가 실제로 받는 내용 기준 |
| 4. 마스터 키로 복호화 | `vault_decrypt_check.py --password-file` | 60/60 (flat 12 + 신규 48) |
| 5. YAML schema | 같은 도구 | 전량 dict / `accounts` 존재 |
| 6. `accounts[]` 구조 | `username/password/label/role` 필수 + role enum | 전량 통과, `role=primary` 후보 전량 존재 |
| 7. Secret 비노출 | 도구가 값 대신 개수·label·role 만 출력 | `tests/unit/test_vault_check_no_secret_output.py` 가 고정 |

> 4번의 "Jenkins 가 쓰는 마스터 키" 는 로컬 `.vault_pass` 로 검증했고, **Jenkins credential
> 자체로의 복호화는 §5 의 실 빌드가 증명한다** (인증 성공 = 복호화 성공).

### 2.1 검증 중 고친 도구 오탐

`vault_decrypt_check.py` 가 9 vendor 전부를 `[FAIL] 허용 label 밖` 으로 표시했다.
허용 label 정본(`test_adapter_vault_label_consistency.py`)은 adapter
`credentials.recovery_accounts[].vault_label` — 즉 **recovery 후보의 label 집합**인데,
도구가 `primary` label 까지 같은 집합으로 재고 있었다. vault 문제가 아니라 도구 버그였다.
recovery 후보에만 적용하도록 고치고 회귀 2건을 추가했다
(`test_recovery_label_outside_allowed_set_is_a_problem`,
`test_primary_label_outside_recovery_set_is_not_a_problem`).

## 3. Jenkins Runner 상태 (§8)

```
Built-In Node       online  exec=1000  labels=[built-in]
jenkins-agent-ops   online  exec=1000  labels=[chj, git, ich, jenkins-agent-ops,
                                               linux, os, redfish, windows, yi]
```

> **중요 — 물리 Runner 는 1대다.** `ich/chj/yi/git` 4개 label 이 **같은 노드**
> `jenkins-agent-ops` 에 붙어 있다. 따라서 이번 Pilot 이 증명한 것은
> **Location → label → 노드 배정 경로가 동작한다**는 것이고,
> **Location 별 물리 Runner 분리 / 망 분리는 증명하지 않았다.**
> 4 Location 의 네트워크 도달 범위가 현재 동일하다는 뜻이기도 하다.

| 확인 항목 | 결과 | 근거 |
|---|---|---|
| online / executor | [OK] | 위 API 출력 |
| workspace 생성 | [OK] | 각 빌드 `Running in /home/…/jenkins-agent/<job>-<n>` |
| Git checkout | [OK] | 14개 빌드 전부 `git init` + checkout 성공 |
| Repository 접근 | [OK] | `https://github.com/hshwang1994/server-expoter` (운영 Job 과 동일 URL, `server-exporter` 로 redirect) |
| Python 실행 | [OK] | `/opt/ansible-env` venv, gather 성공 |
| Ansible 실행 | [OK] | 13개 envelope 생성 |
| 현재 commit checkout | [OK] | `d09ff344` — 미등록 Location 오류 메시지에 `git` 이 포함된 것으로 확인 |
| **built-in 노드 SCM checkout** | [OK] | `Resolve Location` stage 가 `readYaml common/vars/locations.yml` 성공 → 설계 §12 **1안 성립** (2안 불필요) |

## 4. Location Resolve (P2~P6)

| loc | agent label | 근거 빌드 |
|---|---|---|
| ich | ich | #2, #5 |
| chj | chj | #9, #11, #7 |
| yi | yi | #4, #6, #12 |
| git | git | #3, #8, #10 |
| `invalid-location` | — | #1 |

빌드 #1 (`loc=invalid-location`):

```
[Pipeline] { (Resolve Location)
Running on Jenkins in /var/lib/jenkins/workspace/clovirone-server-gather-vault-pilot
ERROR: [Resolve Location] 등록되지 않은 Location: 'invalid-location'
       — 허용: [chj, git, ich, yi]. 새 Location 은 common/vars/locations.yml 에 등록하세요.
Stage "Validate" skipped due to earlier failure(s)
Stage "Gather" skipped …  Stage "Validate Schema" skipped …  Stage "Callback" skipped …
Finished: FAILURE
```

**18초 만에 FAILURE.** built-in 노드에서만 돌았고 `invalid-location` label agent 를 기다리는
상태로 들어가지 않았다. 허용 목록에 `git` 이 보이는 것이 registry 반영의 증거다.

## 5. 실장비 결과 (P7~P13)

`credential_scope` 는 전부 envelope 의 `diagnosis.details.credential_scope` 실측값이다.

| 빌드 | Location | 대상 | target_type | vendor | credential_scope | status | auth | sections | 사용 후보 |
|---|---|---|---|---|---|---|---|---|---|
| #2 | ich | 10.100.64.96 | os | dell | `ich/os/linux` | success | true | 6 | `linux_fallback` (secondary, 2번째) |
| #8 | git | 10.100.64.161 | os | vmware | `git/os/linux` | success | true | 6 | `linux_fallback` |
| #9 | chj | 10.100.64.135 | os | vmware | `chj/os/linux` | success | true | 6 | `linux_fallback` |
| #11 | chj | 10.100.64.120 | os | vmware | `chj/os/windows` | success | true | 7 | `windows_fallback` |
| #4 | yi | 10.100.64.1 | esxi | cisco | `yi/esxi` | success | true | 6 | `esxi_fallback` |
| #3 | git | 10.100.15.34 | redfish | dell | `git/redfish/dell` | success | true | 9 | `lab_dell_root` (recovery, 5번째) |
| #7 | chj | 10.50.11.232 | redfish | lenovo | `chj/redfish/lenovo` | success | true | 9 | `common_infraops` (primary) |
| #10 | git | 10.50.11.232 | redfish | lenovo | `git/redfish/lenovo` | success | true | 9 | `common_infraops` (primary) |
| #6 | yi | 10.100.15.2 | redfish | cisco | `yi/redfish/cisco` | success | true | 9 | `common_infraops` (primary) |
| #5 | ich | 10.50.11.231 | redfish | — | `null` | failed | null | 0 | — (TCP 실패) |
| #12 | yi | 10.50.11.231 | redfish | — | `null` | failed | null | 0 | — (TCP 실패) |

### 5.1 이 표에서 확인되는 것

- **P13 실제 복호화**: `auth=true` 는 encrypted vault 를 Jenkins credential 로 풀어
  얻은 실제 비밀번호로 장비 인증에 성공했다는 뜻이다. mock 이나 평문 YAML 이 아니다.
- **P12 scope 정확성**: OS 는 감지된 OS 로 `os/linux` ↔ `os/windows` 가 갈리고(#9 vs #11,
  같은 `chj`), ESXi 는 축이 location 하나뿐이라 `yi/esxi`, Redfish 는 canonical vendor 로
  `…/redfish/<vendor>` 가 된다.
- **같은 장비 / 다른 Location → 다른 vault 경로**: #7(`chj/redfish/lenovo`) 와
  #10(`git/redfish/lenovo`) 은 **동일 BMC 10.50.11.232** 다. 경로가 장비가 아니라
  Location 을 따라간다는 직접 증거다.
- **Generation 이 선택축이 아님**: #2 는 Ubuntu 24.04(Py 3.12.3), #8/#9 는 RHEL 계열
  (Py 3.9.21) 인데 scope 는 OS 버전과 무관하게 `<loc>/os/linux` 다. Redfish 도
  `redfish_dell_idrac10` / Lenovo XCC / Cisco CIMC 로 세대가 다르지만 scope 는 vendor 까지만이다.
- **Adapter `credentials.profile` 비의존**: #3 의 adapter 는 `redfish_dell_idrac10` 인데
  scope 는 adapter id 가 아니라 canonical vendor `dell` 로 결정됐다.
- **`fallback_used: true` 의 의미**: 같은 vault 파일 **안**의 `accounts[]` 다음 후보로
  넘어간 것이다 (배열 순서 = 시도 순서). 다른 Location / 다른 vendor vault 로 넘어간 것이
  아니다 — §6 이 이를 별도로 증명한다.
- **실패도 정상 형태**: #5/#12 는 `failure_stage=reachable`, `TCP_CONNECT_FAILED`,
  `auth_success=null`, `credential_scope=null`. vendor 를 모르니 경로를 **추측하지 않는다.**

### 5.2 대상 목록 정정 (환경 — 코드 무관)

| IP | catalog 기록 | 실측 (2026-08-12) |
|---|---|---|
| 10.100.64.135 | Windows Server 2022 | **RHEL 계열 Linux** `auto-install-test02.gooddi.lab`, Py 3.9.21 → Windows 대상 아님 |
| 10.100.64.120 | cycle-015 에서 "사내 부재" 로 제거 | **살아 있다.** Windows 수집 성공 (7 sections). 2026-06-22 evidence 와 일치 |
| 10.50.11.231 | HPE ProLiant DL380 Gen11 / iLO6 | **443 timeout** — ich / yi 두 Location 에서 각각 실패. 같은 대역의 10.50.11.232(Lenovo) 는 정상이므로 **경로 문제가 아니라 이 BMC 자체가 미응답** |

## 6. runtime fallback 부재 (P15)

정적 확인만으로는 "경로가 하나뿐" 을 증명할 수 없어 **음성 대조군**을 만들었다.

임시 브랜치에 `pilotnovault` Location 을 등록하되 `vault/pilotnovault/` 는 **만들지 않았다.**
flat `vault/linux.yml` 은 workspace 에 그대로 존재하는 상태다.

```
[Resolve Location] pilotnovault -> agent label 'ich'
ip=10.100.64.161  target_type=os
credential_scope = "pilotnovault/os/linux"
status           = failed
failure_stage    = auth
failure_code     = CREDENTIAL_SET_UNAVAILABLE
auth_success     = null
errors[0].message = 대상에 접속할 수 없습니다. 자격증명과 계정 권한을 확인하세요.
errors[0].detail  = [task: linux | abort if credential set unavailable]
                    Credential set 을 열 수 없습니다
                    (scope=pilotnovault/os/linux, outcome=credential_set_missing). …
```

- flat `vault/linux.yml` 이 **바로 옆에 있는데도 쓰지 않았다** → flat fallback 부재 확인
- `ich/chj/yi/git` 어느 vault 로도 넘어가지 않았다 → cross-location fallback 부재 확인
- `auth_success=null` (false 아님) → **미시도**와 `AUTH_PROBE_FAILED` 구분 유지
- 사용자 메시지는 기존 5문장 중 4번을 재사용, 기술 근거는 `detail` 로 분리 (CLAUDE.md §10)

같은 대상(10.100.64.161)이 `git` Location 에서는 정상 수집됐다(#8). 즉 장비 문제가 아니라
**Credential set 이 없는 Location 이라서** 실패한 것이다.

## 7. Redfish Account Write — **P16 위반 1건** (§13 지시 미준수)

### 무슨 일이 있었나

빌드 #3 (`git` / Dell 10.100.15.34) 에서 **실제 Account Write 가 1회 수행됐다.**

```
account_service = {
  attempted: true, method: "patch_existing", action: "password_sync",
  account_existed: true, slot_uri: "/redfish/v1/AccountService/Accounts/3",
  dryrun: false, verification: "failed", recovered: false, vendor: "dell"
}
errors[0].detail = 기존 계정의 비밀번호를 맞춘 뒤 인증 확인에 실패했습니다. …
                   HTTP 401: Unauthorized; slot=3; delete_recreate=disabled
```

경로 (`redfish_gather.py:4876-4950`): primary `common_infraops` 인증 → 구조화된 401 →
recovery `lab_dell_root` 인증 성공 → **reconcile gate 성립** → `_rf_account_service_dryrun`
미지정 시 유효 dryrun = `not _rf_account_reconcile_allowed` = **false** →
`PATCH /redfish/v1/AccountService/Accounts/3` 전송
(body: `Password / Enabled / Locked / RoleId`) → PATCH 2xx → 새 자격으로 `GET /Systems`
재인증 **401** → `verification: failed` → delete/recreate 는 기본 비활성이라 중단.

### 왜 막지 못했나 (내 판단 오류)

지시 §13 은 "코드가 지원하는 dry-run 변수를 **실제 코드에서 확인해서 적용**" 이었다.
나는 Redfish 빌드를 **먼저 돌리고 나서** 변수(`_rf_account_service_dryrun`)를 확인했다.
순서를 반대로 했어야 했다. 환경 문제가 아니라 내 절차 실수다.

### 장비에 남은 영향 (실측)

이후 dry-run 강제 빌드로 같은 장비를 다시 관측했다:

```
dryrun: true, action: "password_sync", account_existed: true,
slot_uri: "/redfish/v1/AccountService/Accounts/3", verification: "skipped",
auth: primary 실패 → lab_dell_root(recovery) 로 인증 (write 이전과 동일)
```

- 계정 슬롯 3 은 **그대로 존재**하고 삭제·재생성되지 않았다 (delete/recreate 비활성 유지)
- primary 인증은 write **전에도 후에도 401** 이고, recovery 는 전후 모두 성공한다
  → 관측 가능한 인증 동작이 write 전후로 **동일**하다
- 즉 PATCH 는 HTTP 로는 수락(2xx)됐지만 vault 의 비밀번호가 실효 적용되지는 않았다.
  코드 주석(`redfish_gather.py:5100` 부근)이 지목하는 Dell Security Strengthen Policy 정황과 일치한다

**단정하지 않는 것**: iDRAC 내부에 어떤 상태 변화(감사 로그, 비밀번호 이력, 정책 카운터)가
남았는지는 BMC 를 직접 열어보지 않고는 알 수 없다. 여기서 말할 수 있는 것은
"인증 동작이 전후 동일하다" 까지다.

### 이번 Pilot 전체의 write 집계

| 실행 | write |
|---|---|
| 빌드 #3 (Dell, main 파이프라인) | **1건 (실제 PATCH)** |
| 임시 job 빌드 #1 (Dell, dryrun 강제) | 0건 (`verification: skipped`) |
| Lenovo #7 / #10, Cisco #6 | 0건 — primary 인증 성공이라 reconcile gate 자체가 성립 안 함 (`account_service` 없음) |
| 나머지 OS / ESXi 빌드 | 해당 없음 |

**총 실제 Account Write = 1건.** 나머지 13개 빌드는 0건.

### 재발 방지 (적용 안 함 — 사용자 결정 필요)

`Jenkinsfile_portal` 에 `-e _rf_account_service_dryrun=true` 를 넣으면 막을 수 있지만,
그것은 **운영 동작을 바꾸는 변경**이라 이번 Pilot 범위에서 반영하지 않았다.
검증용으로는 임시 브랜치 + 임시 job 으로만 썼고 둘 다 삭제했다.
운영에서 reconcile write 를 끌지 여부는 사용자 결정 사항으로 NEXT_ACTIONS 에 올렸다.

## 8. Secret 비노출 (P14)

Jenkins 콘솔 로그 **14개 전량**을, vault 60개를 복호화해 얻은 실제 값으로 대조했다.

| 검사 대상 | 개수 | 로그 내 출현 |
|---|---|---|
| vault 비밀번호 (accounts + legacy + become) | 16종 | **0** (토큰 경계 일치) |
| Vault 마스터 비밀번호 | 1 | **0** |
| Jenkins 계정 비밀번호 | 1 | **0** |
| envelope(13개) 내부 Secret | — | **0** |

부분 문자열로는 161건이 걸렸으나 42개 문맥을 전수 확인한 결과 **전부 오탐**이었다:
`cloviradmin` / `/home/cloviradmin` / `Administrators` / NIC 팀 필드 `admin_mode` 안의
`admin`, `"action":"password_sync"` 안의 `password`. 실제 값이 값으로 등장한 사례는 0건이다.

`withCredentials` 로 주입된 `VAULT_PASSWORD` 는 임시파일(`mktemp` + `chmod 600` + `trap rm`)
로만 전달되고 `set +x` 라 명령줄도 echo 되지 않는다.

> 이 검사에 쓴 스크립트와 콘솔 원문은 세션 scratchpad 에만 있고 저장소에 커밋하지 않았다.

## 9. 이번 Pilot 이 증명한 것 / 아직 아닌 것 (§16)

증명됨:
Location Resolver / Jenkins Runner 라우팅 / `-e se_location` 전달 / Location 별 Vault 경로 /
실제 ansible-vault 복호화 / 인증 / 수집 / `credential_scope` / Vendor 라우팅 /
Secret 비노출 / runtime fallback 부재.

**아직 증명되지 않음:**

- **Location 마다 실제 Credential 값이 서로 다른 운영 상태** — 이번엔 4 Location 이
  동일 내용을 가리켰다. 값이 갈린 뒤 별도 검증이 필요하다.
- **Location 별 물리 Runner 분리** — label 4개가 한 노드에 붙어 있다 (§3).
- **HPE Redfish** — 장비 미응답 (P11 HOLD).
- **Location 별 마스터 키 분리** — 이번 범위 밖 (설계 §11 의 B안).

## 10. 실패 원인 분류 (§18)

| 사건 | 분류 |
|---|---|
| HPE 10.50.11.231 TCP 443 timeout | **대상 장비 문제** (같은 대역 Lenovo 정상 → Network / Runner 문제 아님) |
| 10.100.64.135 가 Windows 가 아님 | **환경 변경 + catalog stale** (코드 무관) |
| Dell primary 인증 401 | **Credential 값 문제** — vault 의 `common_infraops` 비밀번호가 장비 실제 값과 불일치 (Location 변경 이전부터 존재한 drift) |
| Dell Account Write 1건 | **절차 문제(나)** — dry-run 변수를 적용하기 전에 실행 |
| 전 빌드 UNSTABLE | **의도된 환경 설정** — callbackUrl 이 수신처 없는 주소 |
| `vault_decrypt_check.py` 오탐 9건 | **도구 버그** — 수정 + 회귀 고정 |

Credential Resolver 문제 0건 / Vault 복호화 문제 0건 / Jenkins Runner 문제 0건 /
Gathering 코드 문제 0건.

## 11. flat vault 삭제 가능 여부 (§18-18)

**아직 아니다.** 근거:

1. P11(HPE) 미검증 — Redfish 9 vendor 중 HPE 경로가 실장비로 확인되지 않았다
2. 4 Location 이 아직 **같은 내용**이라, 값 분리 시점에 flat 를 참조 자료로 쓸 여지가 남아 있다
3. Dell primary credential drift 가 미해결이라 vault 값 정정이 필요할 수 있다

flat 12개는 그대로 두었다.

## 12. 관련

- 설계: `docs/ai/VAULT-CREDENTIAL-RESOLVER-DESIGN-2026-08-12.md`
- 구현 검증: `tests/evidence/2026-08-12-location-credential-resolver.md`
- 운영 절차: `docs/21_vault-operations.md` §3
- 후속: `docs/ai/NEXT_ACTIONS.md` §E / §F
