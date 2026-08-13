# Vault / Credential 선택 구조 — 코드 전수 조사

> **작성일**: 2026-08-12
> **목적**: Location / Vendor / Generation 을 고려한 Vault·Credential Resolver 를 설계하기 위한 **코드 사실 자료**.
> 설계 제안·리팩터링·코드 수정은 하지 않았다.
> **기준**: 실제 코드. `README` / `docs/` 는 근거로 쓰지 않았고, 불일치는 15절에 따로 적었다.
> **라인 번호 기준**: HEAD `892be15f` + **워킹트리 미커밋 변경 포함 상태**.
> 인용한 파일 중 `common/library/precheck_bundle.py`, `os-gather/site.yml`, `esxi-gather/site.yml`,
> `redfish-gather/site.yml`, `redfish-gather/library/redfish_gather.py` **5개는 미커밋 수정본**이다.
> 라인 번호는 전부 **워킹트리 기준**으로 읽었다.
>
> **[WARN] 조사 도중 워킹트리가 계속 바뀌었다.** 이 세션이 아닌 다른 작업이 같은 저장소를 편집 중이며,
> 조사 시작 시점에 수정되지 않았던 `redfish-gather/library/redfish_gather.py`,
> `callback_plugins/json_only.py` 등이 조사 중 수정 상태로 바뀌었다. 그로 인해 일부 라인이 밀렸고,
> **밀린 인용은 전수 재확인해 교정했다**(16.3절). 그래도 읽는 시점에 다시 밀렸을 수 있으므로
> **함수명 / 태스크명 / 문자열로 재확인**할 것.
> **검증 방법**: 파일 직접 읽기 + 실제 production 코드 실행(`module_utils/adapter_common.py` 를
> import 해 adapter 점수 재현) + 관련 pytest 141건 실행. 추측한 곳은 "코드만으로 확인 불가"로 표시했다.

---

## 0. 핵심 결론

### 0.1. 한 줄 요약

현재 Credential 선택축은 **채널 1개 + (Redfish 한정) Vendor 1개**뿐이다.
**Location 축은 존재하지 않고, Generation 축도 존재하지 않는다.**

### 0.2. 결론 8가지

| # | 결론 | 근거 |
|---|---|---|
| 1 | `loc` 은 **Ansible 에 전달되지 않는다.** Jenkins agent label + Callback body 두 곳에서만 쓰인다 | `Jenkinsfile_portal:53,121,204,269` / Ansible 코드 내 `loc` 참조 0건 |
| 2 | Vault Master Password 는 **전 loc·전 채널 공통 1개**다. 분리 수단이 코드에 없다 | `credentialsId` 참조 3곳 전부 `server-gather-vault-password` |
| 3 | vault 파일은 **12개**, 전부 `$ANSIBLE_VAULT;1.1` = **vault_id 라벨 없음**(단일 키) | `vault/**` 헤더 실측 |
| 4 | Credential 후보 **순서 = vault YAML `accounts` 배열 순서**. `role` 값은 순서를 결정하지 **않는다** | `load_vault.yml:6-7`, `collect_standard.yml:61-69`, `try_credentials.yml:34-42` |
| 5 | Vault 선택에 Adapter 가 관여하는 채널은 **Redfish 뿐**이다. OS/ESXi adapter 의 `credentials.profile` 은 **읽는 코드가 없다**(dead) | 소비처가 `load_vault.yml:17-18` 단 2줄 |
| 6 | Redfish 31개 adapter → vault profile은 **9개(vendor 단위)**. **Generation 이 달라도 같은 vault** 를 연다 | 실행 결과 매핑표(9절) |
| 7 | 인증 전에 확보되는 식별정보는 **Redfish vendor** 와 **OS 포트 기반 os_type** 뿐이다. Model/Firmware 는 **HPE 만** 예외적으로 확보된다 | `_extract_probe_facts()` 가 `vendor=='hpe'` 에서만 값 반환 (`redfish_gather.py:1273-1291`) |
| 8 | `fallback_profiles` 는 42개 adapter 전부 `[]` → `load_vault.yml:49-60` 의 fallback 루프는 **production 에서 실행되지 않는다** | `grep` 결과 `fallback_profiles: []` × 42 |

### 0.3. 설계에 직접 영향을 주는 사실 3가지

1. **Location 축을 넣으려면 새 전달 경로가 필요하다.** 현재 `loc` 이 Ansible 에 닿는 경로가 0개이므로,
   기존 변수를 재활용하는 방식이 불가능하다 (1절).
2. **Generation 축을 Credential 에 넣으면 순환 의존이 생긴다.** Generation 을 아는 시점이
   OS/ESXi 는 **인증 후**, Redfish 는 **HPE 외 인증 후**이기 때문이다 (5~8절).
3. **Redfish 는 Generation adapter 선택이 인증 전에는 부정확하다.** 실제 코드를 실행해 확인했다 —
   Dell 무인증 probe 는 항상 `redfish_dell_idrac10`(최신)이 선택된다. 지금은 **모든 Dell adapter 가
   같은 vault profile 이라 결과에 영향이 없지만**, generation별 credential 을 도입하면 즉시 문제가 된다 (8.4절).

---

## 1. loc 전달 경로

### 1.1. 전수 grep 결과

Ansible 실행 경로(`os-gather`, `esxi-gather`, `redfish-gather`, `common`, `adapters`,
`lookup_plugins`, `filter_plugins`, `module_utils`, `callback_plugins`, `schema`, `ansible.cfg`)
전체에서 `loc` 을 단어 단위로 검색한 결과, **파라미터로서의 `loc` 참조는 0건**이다.

유일한 매칭 3건은 Redfish 부품 위치를 담는 **지역 변수**로, 이름만 같고 무관하다:

```python
# redfish-gather/library/redfish_gather.py:2671-2673
loc = _safe(adata, 'Location', 'PartLocation') or {}
service_label = _str(_safe(loc, 'ServiceLabel')).upper()
location_type = _str(_safe(loc, 'LocationType')).lower()
```

### 1.2. `loc` 사용처 전량 (Jenkins 안에서만)

| 위치 | 용도 |
|---|---|
| `Jenkinsfile_portal:53`, `:121`, `:204` | stage 별 `node { label "${params.loc}" }` — **Jenkins agent 선택** |
| `Jenkinsfile:30` | `agent { label "${params.loc}" }` — 파이프라인 전체 agent |
| `Jenkinsfile_portal:64-66`, `Jenkinsfile:80-81` | 공백 여부 검증 |
| `Jenkinsfile_portal:111`, `Jenkinsfile:123` | 로그 echo |
| `Jenkinsfile_portal:269` | **Callback body** `{"loc": "..."}` |

### 1.3. 질문별 답

| 질문 | 답 | 근거 |
|---|---|---|
| 1. Agent 선택 외 다른 용도 | Callback body 1곳뿐 | `Jenkinsfile_portal:269` |
| 2. Playbook 에 전달되는가 | **아니오**. `-e`/`--extra-vars` 자체가 0개 | `Jenkinsfile_portal:174`, `Jenkinsfile:174-180` |
| 3. inventory / hostvars 에 들어가는가 | **아니오**. hostvars 는 `{"ansible_host": ip}` 뿐 | `os-gather/inventory.sh:93` |
| 4. Vault 선택에 사용되는가 | **아니오** | `load_vault.yml` 전체에 `loc` 없음 |
| 5. Adapter 선택에 사용되는가 | **아니오**. facts 에 `loc` 키 없음 | `adapter_loader` 호출부 4곳 |
| 6. Gathering 로직에 영향 | **없음**. 단 agent 선택이 곧 **실행 위치(네트워크 경로)** 를 결정한다 | 위 |

### 1.4. 현재 Ansible 이 `loc` 을 참조할 방법이 있는가

**없다.** 세 경로 모두 막혀 있다.

| 후보 경로 | 상태 |
|---|---|
| extra-vars | `-e` 미사용 |
| 환경변수 | Gather stage env 4개(`REPO_ROOT`/`ANSIBLE_CONFIG`/`ANSIBLE_JSON_OUTPUT_FILE`/`ANSIBLE_VERBOSITY`)에 `loc` 없음 (`Jenkinsfile_portal:127-132`) |
| inventory | `inventory.sh` 가 IP 외 필드를 전부 버림 (`os-gather/inventory.sh:84-94`) |

> **참고**: Jenkins 는 빌드 파라미터를 셸 환경변수로 노출하므로 `lookup('env','loc')` 이 이론적으로
> 값을 볼 가능성은 있으나, **그렇게 하는 코드는 없고** Jenkins 파이프라인 `sh` step 의 파라미터
> 자동 export 여부는 이 저장소 코드만으로 확인 불가다. `inventory.sh:45` 가 `inventory_json`
> 소문자 환경변수를 폴백으로 읽는 것은 "Jenkins 파라미터명 그대로 내보내짐" 을 전제한 코드이므로
> 같은 메커니즘이 `loc` 에도 적용될 개연성은 있으나 **코드로 확정 불가**다.

---

## 2. Vault Master Password

### 2.1. Credential ID 참조 위치 (전수)

저장소 전체에서 `credentialsId` 를 참조하는 **비문서 위치는 3곳뿐**이며 전부 동일 ID다.

| 파일:라인 | 타입 |
|---|---|
| `Jenkinsfile:159` | `string(credentialsId: 'server-gather-vault-password', variable: 'VAULT_PASSWORD')` |
| `Jenkinsfile_portal:160` | 동일 |
| `Jenkinsfile_portal_test:161` | 동일 |

### 2.2. loc / 채널별 분리 여부

| 질문 | 답 |
|---|---|
| 모든 loc 가 같은 Master Password 인가 | **그렇다.** `withCredentials` 가 `params.loc` 을 참조하지 않는다 |
| os / esxi / redfish 가 같은 Master Password 인가 | **그렇다.** credential 주입은 target_type 분기 **이전**에 stage 레벨에서 1회 (`Jenkinsfile_portal:158-176`) |

### 2.3. Vault Password 공급 경로 전수

| 경로 | 상태 |
|---|---|
| `--vault-password-file` CLI | **유일한 production 경로** (`Jenkinsfile_portal:174`, `Jenkinsfile:179`) |
| `ansible.cfg` `vault_password_file` | **주석 처리 = 비활성** (`ansible.cfg:57`) |
| `vault_id` / `vault_identity_list` | 저장소 전체 **0건** |
| `ANSIBLE_VAULT_PASSWORD_FILE` 환경변수 | production 코드 **0건** |
| `jenkins/jobs/redfish-account-provision-verify/config.xml:99-102` | `.vault_pass` 파일을 `${VAULT_PASSWORD}` 로 생성. **단 이 XML 에 credential 바인딩이 없다** — `<buildWrappers/>`(`:133`)가 비어 있어 변수 출처가 이 저장소 코드로는 확인 불가 |
| `scripts/ai/**` 다수 | 운영 보조 스크립트. gather production path 아님 |

### 2.4. vault_id 미사용 근거 (파일 헤더 실측)

12개 vault 파일 전부 헤더가 `$ANSIBLE_VAULT;1.1;AES256` 이다.
Ansible vault 포맷상 **1.1 은 vault_id 라벨이 없는 형식**이고, 라벨이 있으면 `1.2;AES256;<label>` 이 된다.
→ **단일 마스터 키 운영이 파일 포맷 수준에서 확정**된다.

### 2.5. loc별 Master Password 분리 시 영향 받는 코드 위치

> 변경을 구현하지 않았다. **수정이 필요해지는 지점 목록**이다.

| # | 위치 | 이유 |
|---|---|---|
| 1 | `Jenkinsfile_portal:158-163` / `Jenkinsfile:157-162` | credential ID 가 상수. loc별 선택 로직이 없음 |
| 2 | `Jenkinsfile_portal_test:161` | 동일 구조 |
| 3 | `Jenkinsfile_portal:164-175` / `Jenkinsfile:163-183` | 임시파일 1개 전제. 다중 키면 `--vault-id` 로 형태가 바뀜 |
| 4 | `vault/**` 12개 파일 | 현재 단일 키로 암호화됨. 키 분리 시 재암호화 대상 |
| 5 | `ansible.cfg:57` | 비활성 주석. `vault_identity_list` 도입 시 여기 |
| 6 | `jenkins/jobs/.../config.xml:99-102` | 별도 freestyle job. 바인딩 부재 상태라 함께 정리 필요 |
| 7 | `tests/unit/test_vault_dynamic_loading_m_c3.py:54` | `ansible.cfg` 에 fact_caching 없음을 고정. vault 설정 추가 시 확인 필요 |

**영향 없는 곳**: `load_vault.yml`, os/esxi `vars_files` — 이들은 복호화된 결과만 보므로 키 개수와 무관하다.

---

## 3. Vault 파일 구조

### 3.1. 전체 목록 (12개 + 평문 1개)

| 경로 | 암호화 | git 추적 |
|---|---|---|
| `vault/linux.yml` | `$ANSIBLE_VAULT;1.1;AES256` | O |
| `vault/windows.yml` | 동일 | O |
| `vault/esxi.yml` | 동일 | O |
| `vault/redfish/{cisco,dell,fujitsu,hpe,huawei,inspur,lenovo,quanta,supermicro}.yml` | 동일 (9개) | O |
| `vault/.lab-credentials.yml` | **평문** | **X** (gitignored) |

### 3.2. 채널 → vault → schema → 소비 코드

> vault 내용은 복호화하지 않았다. **키 이름은 그것을 읽는 코드**와 **평문으로 남아 있는 vault 생성
> 스크립트의 구조 정의**에서 확정했다. 실제 값은 확인하지도 출력하지도 않았다.

#### OS Linux

```
os-gather (PLAY 2)
→ vault/linux.yml                       (vars_files 정적 로딩)
→ accounts: [{username, password, label, role}]  + ansible_become_password
→ os-gather/site.yml:241 `accounts` → _os_accounts → try_credentials.yml
```

| 항목 | 값 | 근거 |
|---|---|---|
| 로딩 | `vars_files` (play 시작 시 1회) | `os-gather/site.yml:217-220` |
| 소비 변수명 | 최상위 `accounts` | `os-gather/site.yml:241` |
| 후보 스키마 | `{username, password, label, role}` | `try_one_credential.yml:23-25,77-79` |
| 추가 키 | `ansible_become_password` | `os-gather/site.yml:227` |
| legacy 구조 | **없음** (accounts 전용) | `site.yml` 에 `ansible_user` 직접 참조 없음 |

#### OS Windows

```
os-gather (PLAY 3)
→ vault/windows.yml                     (vars_files 정적 로딩)
→ accounts: [{username, password, label, role}]
→ os-gather/site.yml:488 `accounts` → _os_accounts → try_credentials.yml
```

`vault/windows.yml` 의 구조는 평문으로 남아 있는 생성 스크립트에 정의돼 있다
(`scripts/ai/reorder_windows_vault_admin_primary.py:19-31`): `accounts` 3개
(label `lab_win_administrator`/`windows_legacy`/`windows_infraops`, role `primary`/`secondary`/`secondary`)
+ backward-compat `ansible_user`/`ansible_password`.

#### ESXi

```
esxi-gather
→ vault/esxi.yml                        (vars_files 정적 로딩)
→ accounts: [{username, password, label, role}]
→ esxi-gather/site.yml:69 `accounts` → _e_accounts → try_credentials.yml
```

| 항목 | 근거 |
|---|---|
| 로딩 | `esxi-gather/site.yml:27-30` |
| 소비 | `esxi-gather/site.yml:69`, `:80` |
| 승격 시 세팅 | `ansible_user`/`ansible_password`/`_e_user`/`_e_pass` | `esxi/try_one_credential.yml:41-44` |

#### Redfish (vendor별 9개)

```
redfish-gather
→ adapter.credentials.profile (vendor 단위)
→ vault/redfish/{profile}.yml           (include_vars 동적 로딩)
→ accounts: [{username, password, label, role}]  (legacy: ansible_user/ansible_password)
→ _rf_accounts → collect_standard.yml → try_one_account.yml
```

정규화 코드 (`load_vault.yml:64-81`)가 읽는 키는 정확히 둘이다:

```jinja
{{ (_rf_vault_data).accounts | default([])                      # 신 스키마 우선
   if (...accounts) | length > 0
   else ( [{ 'username': ...ansible_user, 'password': ...ansible_password,
             'label': 'legacy_single', 'role': 'primary' }]      # legacy 단일 자격
          if (...ansible_user) != '' else [] ) }}
```

**label 허용 집합**은 테스트가 정본으로 고정하고 있다
(`tests/unit/test_adapter_vault_label_consistency.py:32-68`):

| vendor | 허용 label |
|---|---|
| dell | `dell_fallback_1`, `dell_fallback_2`, `dell_current`, `lab_dell_root` |
| hpe | `hpe_fallback`, `hpe_current`, `hpe_factory` |
| lenovo | `lenovo_fallback`, `lenovo_current`, `lenovo_factory` |
| cisco | `cisco_current`, `cisco_factory` |
| supermicro / huawei / inspur / fujitsu / quanta | `{vendor}_factory` |

### 3.3. primary / recovery 개념의 코드상 표현

| 개념 | 표현 | 코드에서의 실제 효과 |
|---|---|---|
| `role: primary` | vault entry 필드 | ① `account_service` 의 **복구 대상** 지정 (`account_service.yml:31`) ② **401 거부 판정 대상** (`collect_standard.yml:85`) |
| `role: recovery` | vault entry 필드 | reconcile **진입 자격** 판정 (`site.yml:152`) |
| `role: secondary` | windows vault 에 존재 | 코드가 특별 취급하지 않음. `!= 'primary'` 이므로 `fallback_used=true` 로만 집계 |
| **순서 결정** | **하지 않음** | 순서는 배열 순서 (4절) |

---

## 4. 채널별 Credential 선택

> 4채널 공통: 후보 배열을 **위에서부터** 순회하고, 성공 시 이후 후보를 skip 한다.
> `role` 은 순서에 관여하지 않는다.

### 4.1. OS Linux

```
입력        : inventory IP (hostvars = ansible_host 뿐)
→ Precheck  : precheck_bundle(channel='os', probe_protocol=true)
              포트 [5986,5985,22] 순차 + 프로토콜 확인       precheck_bundle.py:100-104,1122-1136
→ 대상 식별 : 열린 포트로 os_type 판정 (22 → linux)          precheck_bundle.py:1161-1167
              add_host → group _os_linux, connection=ssh      os-gather/site.yml:103-117
→ Vault 선택: 없음 — vault/linux.yml 이 play vars_files 로 고정  os-gather/site.yml:217-220
→ 후보 생성 : _os_accounts = accounts (vault 배열 그대로)      os-gather/site.yml:241
→ 시도      : set_fact(ansible_user/password/become_pass)
              → meta: reset_connection
              → raw "echo __auth_ok__"                        try_one_credential.yml:21-46
→ 성공 판정 : rc == 0 AND '__auth_ok__' in stdout             try_one_credential.yml:59-64
→ 실패 시   : 다음 후보 (backoff 없음)                         try_credentials.yml:34-42
→ 전부 실패 : _os_auth_ok=false → fail → rescue               os-gather/site.yml:243-250
```

### 4.2. OS Windows

```
입력        : 동일
→ Precheck  : 동일 (포트 5986/5985 에서 WS-Man Identify 확인)
→ 대상 식별 : 5985/5986 → windows, winrm_scheme 결정          precheck_bundle.py:1161-1167
              add_host → group _os_windows, connection=winrm  os-gather/site.yml:119-135
→ Vault 선택: 없음 — vault/windows.yml 고정                    os-gather/site.yml:469-472
→ 후보 생성 : _os_accounts = accounts                          os-gather/site.yml:488
→ 시도      : set_fact → reset_connection → win_ping          try_one_credential.yml:48-54
→ 성공 판정 : _os_probe_windows.ping == 'pong'                 try_one_credential.yml:66-68
→ 실패 시   : 다음 후보 (backoff 없음)
→ 전부 실패 : fail → rescue                                    os-gather/site.yml:490-497
```

### 4.3. ESXi

```
입력        : 동일
→ Precheck  : precheck_bundle(channel='esxi') — /sdk SOAP     precheck_bundle.py:999-1014
→ 대상 식별 : 없음 (vendor/version 을 이 단계 결과로 쓰지 않음)
→ Vault 선택: 없음 — vault/esxi.yml 고정                        esxi-gather/site.yml:27-30
→ 후보 생성 : _e_accounts = accounts                            esxi-gather/site.yml:69
→ 시도      : vmware_host_facts(schema: summary)                esxi/try_one_credential.yml:19-27
→ 성공 판정 : is not failed AND ansible_facts is defined        esxi/try_one_credential.yml:35
              (후자는 Round 17 #2 수정 — 없으면 첫 후보가 무조건 승격)
→ 실패 시   : 다음 후보 (backoff 없음)
→ 전부 실패 : fail → rescue                                     esxi-gather/site.yml:71-80
```

### 4.4. Redfish

```
입력        : inventory bmc_ip
→ Precheck  : precheck_bundle(channel='redfish') — ServiceRoot 구조 확인  site.yml:46-52
→ 대상 식별 : detect_vendor.yml — 무인증 redfish_gather probe   detect_vendor.yml:12-22
              → _rf_detected_vendor (alias 정규화)               detect_vendor.yml:24-48
              → _rf_probe_facts {vendor, firmware, model}        detect_vendor.yml:58-76
→ Adapter   : adapter_loader(channel='redfish', facts=_rf_probe_facts)   site.yml:68-75
→ Vault 선택: adapter.credentials.profile → vault/redfish/{profile}.yml  load_vault.yml:17,29-36
→ 후보 생성 : _rf_accounts (accounts 배열 / legacy 1개)          load_vault.yml:64-81
→ 시도      : redfish_gather(username,password)                  try_one_account.yml:21-34
→ 성공 판정 : is not failed AND status != 'failed'               try_one_account.yml:38-40
→ 실패 시   : 관측 누적 → **sleep 5 backoff** → 다음 후보        try_one_account.yml:54-65,109-113
→ 전부 실패 : _rf_collect_ok=false → 실패 메시지                  site.yml:133
→ 추가 경로 : recovery 로 성공 + primary 가 401 거부됨 →
              account_service.yml (공통계정 복구)                site.yml:149-158
```

### 4.5. `role` 이 실행 순서를 결정하는가 — **아니다**

| 확인 | 결과 |
|---|---|
| 순회 대상 | `loop: "{{ _rf_accounts }}"` / `loop: "{{ _os_accounts }}"` — **배열 원본 순서** |
| 정렬 코드 | `sort` / `selectattr` 기반 재정렬 **0건** (grep 결과 `selectattr('role')` 2건은 모두 필터링 용도) |
| 명시 주석 | "별도 role-based 정렬 없음 — vault YAML 파일의 accounts list 순서가 곧 multi-account fallback 시도 순서" (`load_vault.yml:6-7`) |
| 관례 | list[0] = primary, list[1...] = recovery — **관례일 뿐 코드 강제 아님** (`load_vault.yml:7`) |

`role` 의 실제 효과는 4가지뿐이다:
1. `account_service` 복구 대상 선정 (`account_service.yml:31`)
2. primary 401 거부 판정 (`collect_standard.yml:81-87`)
3. reconcile 진입 조건 (`site.yml:151-154`)
4. `fallback_used` 메타 집계 (`collect_standard.yml:106-108`, `try_credentials.yml:50-52`)

---

## 5. 인증 전 확보 가능한 Facts

> 판정 기준: **현재 코드 실행 순서에서 첫 Credential 시도 이전에 실제로 변수에 담기는가.**
> 이론적 가능성은 반영하지 않았다.

### 5.1. 표

범례: `[OK]` 인증 없이 확보됨 / `[AUTH]` 인증 후에만 / `[NONE]` 현재 코드가 확인하지 않음

| 정보 | OS Linux | OS Windows | ESXi | Redfish |
|---|---|---|---|---|
| IP | `[OK]` inventory | `[OK]` inventory | `[OK]` inventory | `[OK]` inventory |
| Protocol | `[OK]` SSH ident | `[OK]` WS-Man Identify | `[OK]` vim25 SOAP | `[OK]` ServiceRoot |
| OS Type | `[OK]` 포트 22 | `[OK]` 포트 5985/5986 | `[NONE]` | — |
| Vendor | `[NONE]` | `[NONE]` | `[NONE]` | **`[OK]`** ServiceRoot |
| Model | `[AUTH]` | `[AUTH]` | `[AUTH]` | **HPE만 `[OK]`**, 그 외 `[AUTH]` |
| Firmware | `[NONE]` | `[NONE]` | `[NONE]` | **HPE만 `[OK]`**, 그 외 `[AUTH]` |
| Version | `[NONE]` | `[AUTH]` `ansible_kernel` | `[OK]`**로 확보되나 미사용** | `[AUTH]` |
| Generation | `[NONE]` | `[AUTH]` (version 유래) | `[OK]`로 확보되나 미사용 | HPE만 `[OK]`(manager_type) |
| Distribution | `[AUTH]` preflight | — | — | — |
| 기타 | `[OK]` 포트/실패종류 | `[OK]` winrm_scheme | `[OK]` apiType/productLineId (미사용) | `[OK]` first_system_uri |

### 5.2. 근거

**Redfish vendor `[OK]`** — 무인증 ServiceRoot 로 확보되며 3단 fallback 이 있다:
`_detect_vendor_from_service_root()` (`redfish_gather.py:1173`) → Chassis/Managers/Systems
`Manufacturer` (`:1202-1222`, 무인증 시 401 로 대개 실패) → **401 `WWW-Authenticate: realm`**
(`:1224-1231` → `_probe_realm_hint()`, 무인증 동작).

**Redfish model/firmware 가 HPE 만 `[OK]`** — 결정적 근거:

```python
# redfish-gather/library/redfish_gather.py:1272-1291
    facts = {}
    if vendor == 'hpe':                        # nosec rule12-r1
        product = _safe(root, 'Product')       # → model_hint
        ...ManagerFirmwareVersion              # → firmware_hint
        ...ManagerType                         # → manager_type
    return facts                               # ← HPE 아니면 항상 {}
```

같은 파일 주석(`:1257-1262`)이 이유를 밝힌다 — Dell 등은 ServiceRoot `Product` 가 **BMC 제품명**
("Integrated Dell Remote Access Controller")이라 서버 모델이 아니고, 무분별 추출 시 model_patterns
미매치로 모든 vendor adapter 가 실격되어 generic 으로 떨어진다.

`detect_vendor.yml:58-76` 은 `data.system.model` / `data.bmc.firmware_version` 을 1순위로 쓰는데,
무인증 probe 에서는 이 두 경로가 401 로 비어 있어 결국 `probe_facts` hint 만 남는다.

**ESXi version 이 "확보되나 미사용"** — 5.3절 참조.

### 5.3. ESXi: 확보되지만 버려지는 정보

precheck 의 `/sdk` 프로브는 무인증으로 4개 값을 파싱한다:

```python
# common/library/precheck_bundle.py:990-996
return True, {
    "evidence": "service_content",
    "api_type": api_type,           # about.apiType
    "api_version": api_version,     # about.apiVersion
    "product_line_id": _vim_text(about, "productLineId"),
    "version": _vim_text(about, "version"),
}, "ServiceContent 확인"
```

이 값은 `result["probe_facts"].update(facts)` (`:1385`) 로 실려 나가지만, 소비처는 단 하나다:

```python
# filter_plugins/diagnosis_mapper.py:62-65
probe_facts = precheck_result.get("probe_facts", {})
if isinstance(probe_facts, dict) and probe_facts:
    details.update(probe_facts)      # → diagnosis.details 로만
```

**adapter 선택이나 credential 선택에 쓰는 코드는 없다** (grep 전수 확인).

---

## 6. OS 세대 판별 시점

### 6.1. Linux

| 정보 | 시점 | 근거 |
|---|---|---|
| distribution (NAME) | **인증 후** — `raw` 로 `/etc/os-release` 읽음 | `preflight.yml:38`, `:70` |
| distribution **version** | **수집하지 않음** | preflight 는 `OS_NAME` 만 파싱 (`:38`) |
| kernel | **수집하지 않음** (preflight 단계에서) | 위 |
| RHEL 계열 여부 | **인증 후** — `_l_distro_name` 을 adapter `distribution_patterns` 로 판정 | `adapters/os/linux_rhel.yml:15` |
| RHEL 7/8/9 세대 구분 | **하지 않는다** | OS adapter 4개 중 version_patterns 를 가진 것 0개 |

Linux adapter 는 계열만 나눈다:

```
linux_rhel.yml:15    distribution_patterns: ["Red Hat","RHEL","CentOS","Rocky","AlmaLinux","Oracle"]
linux_ubuntu.yml:15  distribution_patterns: ["Ubuntu","Debian"]
linux_suse.yml:15    distribution_patterns: ["SUSE","SLES","openSUSE"]
linux_generic.yml:15 os_type: linux                       (패턴 없음)
```

**preflight 가 수집하는 유일한 버전 정보는 Python 버전**(`_l_python_version`, `:56`)이며,
이는 raw fallback 분기(`_l_python_mode`, `:57-65`)에만 쓰이고 adapter/credential 과 무관하다.

### 6.2. Windows

| 정보 | 시점 | 근거 |
|---|---|---|
| Windows version / kernel | **인증 후** — `ansible.builtin.setup` | `os-gather/site.yml:501-506` |
| 2016/2019/2022/2025 구분 | **인증 후**, 그리고 **2019/2022 만** adapter 존재 | `adapters/os/windows_2019.yml:15`, `windows_2022.yml:15` |

```
windows_2019.yml:15  version_patterns: ["2019", "10\\.0\\.17763"]
windows_2022.yml:15  version_patterns: ["2022", "10\\.0\\.20348"]
windows_generic.yml  (패턴 없음)
```

**2016 / 2025 전용 adapter 는 존재하지 않는다** — generic 으로 떨어진다.

### 6.3. Credential 과 Adapter 의 선후 — **Credential 이 먼저다**

| 채널 | 순서 | 근거 |
|---|---|---|
| Linux | try_credentials(`:237`) → preflight(`:254`) → init_fragments(`:257`) → **adapter(`:262`)** | `os-gather/site.yml` |
| Windows | try_credentials(`:484`) → setup(`:501`) → init_fragments(`:508`) → **adapter(`:513`)** | 동일 |

adapter 선택을 뒤로 미룬 것은 의도된 수정이다 — `os-gather/site.yml:265-267` 주석:
adapter 선택 시점에 `ansible_distribution` 이 미정의이고 형식도 `RedHat`(공백 없음)이라
패턴이 불일치해 **전 Linux 가 rhel 로 오선택**되던 버그(2026-06-22 fix) 때문이다.

---

## 7. ESXi 세대 판별 시점

### 7.1. 인증 전 `/sdk` probe 에서 얻는 것

| 필드 | 출처 | 확보 여부 |
|---|---|---|
| `apiType` | `about.apiType` | 확보 (성공 판정의 필수 조건, `precheck_bundle.py:984-986`) |
| `apiVersion` | `about.apiVersion` | 확보 (필수 조건, `:987-989`) |
| `productLineId` | `about.productLineId` | 확보 (없으면 None) |
| `version` | `about.version` | 확보 (없으면 None) |

**실제 값**은 코드에 하드코딩돼 있지 않다 — 대상 장비 응답에 따라 달라지므로 **코드만으로 확인 불가**다.
성공 경로 2번째(`:966-971`)인 vim25 SOAP Fault 인정 경로에서는 `{"evidence":"vim25_fault","fault":...}`
만 담겨 **버전 정보가 아예 없다.**

### 7.2. 이 값으로 ESXi 7/8 을 구분하도록 구현돼 있는가 — **아니다**

`probe_facts` 의 소비처는 `diagnosis.details` 하나뿐이다(5.3절). 세대 구분에 쓰는 코드가 없다.

### 7.3. Adapter 가 쓰는 Version 값의 출처

```yaml
# esxi-gather/site.yml:111-117
_selected_adapter: >-
  {{ lookup('adapter_loader', channel='esxi',
             facts={'version': _e_raw_facts.ansible_distribution_version | default('')},
             repo_root=...) }}
```

`_e_raw_facts` 는 **인증 후** `collect facts`(`esxi-gather/site.yml:82-83`)의 결과다.
즉 adapter 용 version 은 **precheck probe 가 아니라 인증된 vSphere API** 에서 온다.

`:105-108` 주석이 이유를 남겼다 — 종전엔 collect 전에 `facts={}` 로 선택해 version 이 비어
`version_patterns`(`^6.`/`^7.`/`^8.`)가 죽고 priority 만으로 **`esxi_8x` 가 항상 선택**되던 버그(Round 17 #9).

### 7.4. Credential 이 Adapter 보다 먼저인가 — **그렇다**

```
esxi-gather/site.yml
  :43-45   init_fragments
  :48-54   precheck
  :66-69   try_credentials      ← Credential
  :82-83   collect facts
  :111-117 select adapter       ← Adapter
```

### 7.5. 세대별 Credential 을 도입할 경우의 순환 의존

현재 코드 구조에서 사실관계는 다음과 같다:

- adapter 용 version 은 **인증 후** facts 에서 온다 (`site.yml:115`).
- 따라서 "adapter 로 세대 판정 → 세대별 credential 선택" 은 **인증이 이미 끝나야 성립** → 순환.
- 다만 **인증 없이 얻는 version 경로가 이미 존재한다** (`precheck_bundle.py:990-996`).
  이 값을 credential 선택에 쓰면 순환은 발생하지 않는다. **단 현재 그렇게 하는 코드는 없다.**
- 예외: vim25 Fault 경로로 프로토콜을 통과한 호스트는 version 이 없다(`:970`) → 이 경우는
  인증 전 세대 판정 불가.

---

## 8. Redfish Vendor / Generation 판별

### 8.1. 실제 코드 순서

```
site.yml:41-43   init_fragments
site.yml:46-52   precheck (ServiceRoot 구조 확인 — 자격증명 미전달)
site.yml:54-61   abort if precheck failed
site.yml:64-65   detect_vendor.yml   ┐ 무인증 redfish_gather probe
                                     │  → _rf_detected_vendor
                                     └  → _rf_probe_facts{vendor,firmware,model}
site.yml:68-75   select adapter (adapter_loader, facts=_rf_probe_facts)
site.yml:86-89   extract manager_layout
site.yml:92-93   load_vault.yml  (adapter.credentials.profile → vault)
site.yml:96-97   collect_standard.yml  ← 첫 인증 시도
```

질문에 제시된 순서(`Precheck → ServiceRoot → Vendor → Model/Firmware → Adapter → Credential Profile
→ Vault → Credential Attempt`)와 **일치한다.** 단 "Model/Firmware Detection" 이 독립 단계가 아니라
Vendor Detection 과 **같은 probe 호출 1회 안에서** 파생된다는 점이 다르다.

### 8.2~8.3. 인증 전 확보 가능성

| 정보 | 확보 | 근거 |
|---|---|---|
| **Vendor** | **가능** | ServiceRoot + Manufacturer fallback + realm hint (`redfish_gather.py:1173,1202-1231`) |
| **Model** | **HPE 만 가능** | `_extract_probe_facts` 가 `vendor=='hpe'` 에서만 `model_hint` (`:1220-1223`) |
| **Firmware** | **HPE 만 가능** | 동일, `firmware_hint`/`manager_type` (`:1284-1290`) |

### 8.4. 세대를 Credential 이전에 구분할 정보가 존재하는가

**HPE 만 존재한다.** `manager_type` 이 "iLO 6" 같은 세대 문자열을 준다(`:1288-1290`).
Dell 15G/16G, Lenovo XCC2/3 등은 **인증 전 판별 근거가 없다.**

이것을 실제 production 코드를 실행해 확인했다
(`module_utils/adapter_common.py` 의 `adapter_matches`/`adapter_score` 를 그대로 import,
`adapters/redfish/*.yml` 31개 전량 대상):

| 시나리오 (facts) | 선택된 adapter | score | profile |
|---|---|---|---|
| Dell 무인증 probe `{vendor:'Dell Inc.', firmware:'', model:''}` | **`redfish_dell_idrac10`** | 120520 | `dell` |
| Dell 인증 후 `{firmware:'7.00.00', model:'PowerEdge R750'}` | `redfish_dell_idrac9` | 100345 | `dell` |
| Supermicro 무인증 | `redfish_supermicro_x14` | 110320 | `supermicro` |
| Lenovo 무인증 | `redfish_lenovo_xcc3` | 120520 | `lenovo` |
| HPE 무인증 `{firmware:'iLO 6', model:'ProLiant DL380 Gen11'}` | `redfish_hpe_ilo6` | 100345 | `hpe` |

원인은 빈 facts 를 **실격이 아니라 보너스 제외**로 처리하기 때문이다:

```python
# module_utils/adapter_common.py:290-299
firmware_patterns = match.get("firmware_patterns", [])
if firmware_patterns:
    if pattern_match_any(firmware_patterns, facts.get("firmware", "")):
        score += 25
    elif not facts.get("firmware", ""):
        pass                    # ← 빈 값: 실격 아님, 보너스만 없음
    else:
        return -9999
```

결과적으로 무인증 시점에는 **priority 가 가장 높은(=최신 세대) adapter 가 항상 이긴다.**

> **현재는 무해하다** — Dell 4개 adapter 가 모두 `profile: "dell"` 이라 vault 선택 결과가 같기 때문이다.
> generation별 credential 을 도입하면 이 성질이 곧바로 오선택으로 이어진다.

### 8.5. `credentials.profile` 의 역할

정확히 **vault 파일명 조각 1개**다. 다른 역할은 없다.

```yaml
# redfish-gather/tasks/load_vault.yml:17, 29-36
_rf_vault_profile: "{{ _selected_adapter.credentials.profile | default('') }}"
...
- ansible.builtin.include_vars:
    file: "{{ lookup('env','REPO_ROOT') }}/vault/redfish/{{ _rf_vault_profile }}.yml"
    name: _rf_vault_data
  when: _rf_vault_profile != ''
```

### 8.6. Adapter ↔ Credential 결합도

결합 지점은 **2줄**뿐이다 (`load_vault.yml:17-18`). 그 외 credential 로직은 adapter 를 참조하지 않는다.
따라서 결합도는 **낮지만 단일점**이다 — 이 2줄이 Redfish vault 선택의 전부다.

### 8.7. `fallback_profiles` 의 실제 동작

```yaml
# load_vault.yml:49-60
- name: "redfish | load_vault | try fallback profiles"
  ansible.builtin.include_vars:
    file: ".../vault/redfish/{{ item }}.yml"
  loop: "{{ _rf_vault_fallbacks }}"
  when:
    - _rf_vault_data is not defined or _rf_vault_data | default({}) == {}
    - _rf_vault_fallbacks | length > 0
```

**production 에서 실행되지 않는다.** 42개 adapter 전부 `fallback_profiles: []` 이기 때문이다
(`grep -rh "fallback_profiles" adapters/` → `fallback_profiles: []` × 42).
→ **dead path** (문법상 존재, 실행 조건 미성립).

### 8.8. generic adapter 의 vault 처리

```yaml
# adapters/redfish/redfish_generic.yml:36-40
credentials:
  profile: ""
  fallback_profiles: []
  recovery_accounts: []
```

`profile == ''` 이면:
1. 경고 출력 (`load_vault.yml:21-26`) — "빈 자격증명으로 수집을 시도합니다"
2. `include_vars` 가 `when: _rf_vault_profile != ''` 로 **skip** (`:36`)
3. `_rf_accounts` = `[]` (`:64-81`)
4. `collect_standard.yml:37-57` 의 **빈 자격 1회 시도** 경로로 진입 (`username: ""`, `password: ""`)

즉 generic adapter 가 선택되면 **인증 없이 1회만 수집을 시도**하고 후보 순회는 하지 않는다.

---

## 9. Adapter–Credential 결합

### 9.1. 실제 존재하는 필드 (42개 adapter 전수)

```yaml
credentials:
  profile: "<str>"              # 42/42 존재
  fallback_profiles: []         # 42/42 존재, 42/42 가 빈 배열
  recovery_accounts:            # redfish 31개만 존재
    - { vault_label: <str>, role: recovery }
```

### 9.2. 질문별 답

**1. Adapter 가 Credential Profile 을 직접 결정하는 채널** → **Redfish 뿐이다.**

**2. OS / ESXi adapter 에도 credential 설정이 있는가** → **선언은 있으나 읽는 코드가 없다.**

| adapter | 선언된 profile | 대응 vault 파일 |
|---|---|---|
| `adapters/os/linux_*.yml` (4개) | `os_linux` | `vault/os_linux.yml` — **존재하지 않음** |
| `adapters/os/windows_*.yml` (3개) | `os_windows` | `vault/os_windows.yml` — **존재하지 않음** |
| `adapters/esxi/esxi_*.yml` (4개) | `esxi_default` | `vault/esxi_default.yml` — **존재하지 않음** |

OS/ESXi 는 vault 를 `vars_files` 로 고정 로딩하므로 이 필드가 쓰이지 않는다.
→ **선언만 있는 dead 필드**이며, 파일명이 실제 vault(`linux.yml`/`windows.yml`/`esxi.yml`)와도 다르다.

**3. Redfish 만 있는가** → 선언은 전 채널에 있고, **동작하는 것은 Redfish 뿐**이다.

**4. `credentials` 를 adapter 에서 제거한다고 가정할 때 영향받는 코드 위치**

> 변경 제안이 아니라 **의존 위치 목록**이다.

| # | 위치 | 의존 내용 |
|---|---|---|
| 1 | `redfish-gather/tasks/load_vault.yml:17` | `credentials.profile` — **유일한 production 소비처** |
| 2 | `redfish-gather/tasks/load_vault.yml:18` | `credentials.fallback_profiles` |
| 3 | `adapters/**/*.yml` 42개 | 필드 선언 |
| 4 | `tests/unit/test_adapter_vault_label_consistency.py:132,146,165,179` | `recovery_accounts` 존재·label·role 을 **테스트가 강제** |
| 5 | `tests/unit/test_vault_dynamic_loading_m_c3.py:137` | `test_m_c3_vault_profile_from_adapter` — adapter→profile 경로 고정 |

**`recovery_accounts` 는 production 코드가 전혀 읽지 않는다.** 참조처는 위 4번 테스트뿐이다
(grep 전수: `adapters/`, `docs/`, 그리고 해당 테스트 파일 외 0건).
→ **테스트로만 강제되는 미사용 필드.**

`graceful_degradation`(42개 adapter 선언)도 production 소비처가 없다 —
`common/vars/status_rules.yml:64-65` 에 같은 키가 있으나 이 파일 자체가 별도 정본이다.

---

## 10. Inventory Metadata 전달

질문의 JSON 을 그대로 넣었을 때 각 필드의 운명이다.

| 필드 | Jenkins | inventory.sh | hostvars | 결론 |
|---|---|---|---|---|
| `service_ip` | 검증에 사용 (`Jenkinsfile_portal:88-95`) | os/esxi 1순위 키 (`inventory.sh:86`) | `ansible_host` 값이 됨 | **전달됨** |
| `bmc_ip` | 검증에 사용 (redfish) | redfish 1순위 키 (`redfish-gather/inventory.sh:88`) | `ansible_host` 값이 됨 | **전달됨** |
| `ip` | fallback 검증 | fallback 키 | `ansible_host` 값이 됨 | **전달됨** |
| `vendor` | **메인 `Jenkinsfile:115-120` 만** WARNING 출력. `Jenkinsfile_portal` 은 아예 안 봄 | 읽지 않음 | 없음 | **버려짐** |
| `generation` | 안 봄 | 읽지 않음 | 없음 | **버려짐** |
| `os_type` | 안 봄 | 읽지 않음 | 없음 | **버려짐** |
| `model` | 안 봄 | 읽지 않음 | 없음 | **버려짐** |
| `site` | 안 봄 | 읽지 않음 | 없음 | **버려짐** |
| `loc` (JSON 안의) | 안 봄 (파라미터 `loc` 과 별개) | 읽지 않음 | 없음 | **버려짐** |

근거 — 루프가 IP 키만 읽고 나머지 키를 순회하지 않는다:

```python
# os-gather/inventory.sh:84-94
for idx, host in enumerate(payload):
    ip = (host.get("service_ip") or host.get("ip") or "").strip()
    ...
    hostvars[ip] = {"ansible_host": ip}     # ← 다른 키는 어디에도 담기지 않음
    host_keys.append(ip)
```

### 10.1. Portal 이 향후 `generation` hint 를 보내면

**현재 코드로는 Ansible 까지 전달되지 않는다.** `inventory.sh` 가 dict 에서 IP 키 하나만 꺼내
새 dict 를 만들기 때문에, 추가 필드는 파싱 단계에서 소멸한다. Jenkins Validate 도 `generation` 을
보지 않는다. 전달하려면 `inventory.sh` 의 `hostvars[ip]` 구성부(`:93`) 수정이 필요하다.

---

## 11. Credential Retry / Lockout

### 11.1. 채널 비교표

| 항목 | OS Linux | OS Windows | ESXi | Redfish |
|---|---|---|---|---|
| 최대 후보 개수 제한 | **없음** | 없음 | 없음 | 없음 |
| 후보 순서 | vault 배열 순 | 동일 | 동일 | 동일 |
| 성공 후 중단 | `when: not _os_auth_ok` (`try_credentials.yml:42`) + block-level `when`(`try_one_credential.yml:17`) | 동일 | `esxi/try_credentials.yml` + block `when:12` | `collect_standard.yml:69` + block `when:18` |
| 실패 후 sleep/backoff | **없음** | **없음** | **없음** | **`sleep 5`** (`try_one_account.yml:109-113`) |
| 후보당 시도 횟수 | 1 (`raw` 1회) | 1 (`win_ping` 1회) | 1 (`vmware_host_facts` 1회) | 1 (`redfish_gather` 1회) |
| `retries:` / `until:` | 없음 | 없음 | 없음 | 없음 |
| timeout | 연결 기본값 (`ansible.cfg:31` timeout=60) + ssh args ConnectTimeout=15 (`site.yml:110-112`) | winrm operation 60 / read 70 (`site.yml:129-130`) | 모듈 기본 | `_rf_timeout: 30` (`site.yml:34`) |
| 같은 username + 다른 password | **지원** (후보마다 독립 set_fact) | 지원 | 지원 | 지원 (F49 대응으로 password 별도 보존, `try_one_account.yml:86`) |
| HTTP 401 과 timeout 구분 | **안 함** | 안 함 | 안 함 | **함** — `auth_evidence.first_auth_status` 정수 비교 (`try_one_account.yml:54-65`, `collect_standard.yml:81-87`) |
| Connection 실패도 다음 후보로 | **넘어감** (`ignore_unreachable: true`, `:45`,`:53`) | 넘어감 | 넘어감 (`failed_when: false`) | 넘어감 (`failed_when: false`) |
| 무한 retry 가능성 | 없음 (유한 loop) | 없음 | 없음 | 없음 |

### 11.2. Account Lockout 방지 로직

**Redfish 에만 존재한다.** 근거 주석이 vendor 정책까지 남겼다:

```yaml
# redfish-gather/tasks/try_one_account.yml:102-108
# F20 (cycle 2026-05-01): BMC lockout 회피 backoff 1초 → 5초.
# source: Dell iDRAC IPMI Lockout Policy (5회 fail / 5분), HPE iLO Account
# Lockout (3회 fail), Lenovo XCC Login Lockout (5회 fail) — vendor docs.
# multi-account vault (5 자격) × 5초 = 25초/host 추가
```

**OS / ESXi 에는 backoff 가 없다.** 후보 개수만큼 즉시 연속 시도한다.

### 11.3. 테스트로 고정된 동작

`tests/e2e/test_credential_probe_classification.py:69-85` 가 시도 횟수를 잠근다:

```python
assert os_text.count("ansible.builtin.raw:") == 1
assert os_text.count("ansible.windows.win_ping:") == 1
assert "retries:" not in os_text and "until:" not in os_text
...
assert "sleep 5" in rf_text, "lockout backoff 를 제거하면 안 된다"
```

`tests/unit/test_account_reconcile_entry_gate.py` 29개 테스트가 reconcile 진입 조건
(401 정수 비교, 403 제외, dryrun 기본값, role 기반 식별 등)을 고정한다.
관련 141건 전부 통과함을 확인했다 (`pytest tests/unit/test_vault_dynamic_loading_m_c3.py
tests/unit/test_account_reconcile_entry_gate.py tests/unit/test_adapter_vault_label_consistency.py -q`
→ `141 passed`).

### 11.4. Primary 실패 → Recovery 진입 조건

```yaml
# redfish-gather/site.yml:151-154
_rf_account_reconcile_allowed: >-
  {{ (((_rf_used_account | default({})).role | default('primary')) == 'recovery')
     and (_rf_collect_ok | default(false) | bool)
     and (_rf_primary_auth_rejected | default(false) | bool) }}
```

`_rf_primary_auth_rejected` 는 **role=primary 후보의 첫 인증 응답이 정수 401** 일 때만 true 다
(`collect_standard.yml:81-87`). 403 / timeout / TLS / 5xx 는 전부 제외된다.

쓰기 모드는 이 값이 성립할 때만 켜진다 (`account_service.yml:50-53`):

```jinja
_rf_account_service_dryrun_effective:
  {{ (_rf_account_service_dryrun | bool) if (_rf_account_service_dryrun is defined)
     else (not (_rf_account_reconcile_allowed | default(false) | bool)) }}
```

**OS / ESXi 에는 recovery/reconcile 개념 자체가 없다.**

### 11.5. "세대별 Credential 후보 전량 순차 시도" 로 확대할 경우 영향받는 기존 로직

> 사실 기준 목록이며 권고가 아니다.

| # | 로직 | 영향 |
|---|---|---|
| 1 | `try_one_account.yml:109-113` sleep 5 | 후보 수 N → 실패 시 5N 초. 세대별 확장은 N 증가에 선형 비례 |
| 2 | vendor lockout 임계 (주석 `:103-104`: iLO 3회 / iDRAC·XCC 5회) | 후보 수가 임계를 넘으면 **계정 잠금** |
| 3 | `collect_standard.yml:103` `attempted_count` | `_rf_accounts \| length` = **후보 총수**이지 실제 시도 수가 아님. 후보가 늘면 의미가 더 벌어짐 |
| 4 | `collect_standard.yml:81-87` primary 401 판정 | role=primary 후보가 여러 개가 되면 "하나라도 401" 로 판정됨 |
| 5 | `account_service.yml:31` `selectattr('role','eq','primary') \| first` | primary 가 복수면 **첫 번째만** 대상이 됨 |
| 6 | `tests/e2e/test_credential_probe_classification.py:69-85` | 시도 횟수·backoff 를 잠그고 있어 구조 변경 시 재작성 필요 |
| 7 | `os/esxi try_credentials.yml` | backoff 가 없어 후보 증가가 곧 연속 인증 시도 증가 |
| 8 | `Jenkinsfile_portal:126` Gather timeout 60분 | 후보×호스트 증가 시 총 소요 증가 |

---

## 12. Location–Agent 결합

### 12.1. `loc` 은 사실상 Jenkins Agent Label 인가 — **그렇다**

```groovy
// Jenkinsfile_portal:51-56 (Validate), :119-124 (Gather), :202-207 (Validate Schema)
agent { node { label "${params.loc}"; customWorkspace "..." } }
// Jenkinsfile:30
agent { label "${params.loc}" }
```

파라미터 값이 **가공 없이** label 로 들어간다.

### 12.2. 질문별 답

| # | 질문 | 답 | 근거 |
|---|---|---|---|
| 1 | `ich/chj/yi` 가 코드에 whitelist 로 존재 | **아니오** | `loc` 검증은 공백 여부만 (`Jenkinsfile_portal:64-66`) |
| 2 | description 에만 존재 | **그렇다** | `Jenkinsfile_portal:9` `'Agent 로케이션 (ich \| chj \| yi)'`, `Jenkinsfile:12` 주석 |
| 3 | 새 loc 추가 시 코드 수정 위치 | **저장소 코드 수정 불필요** — Jenkins 에 해당 label agent 만 추가하면 됨. 단 description 문자열(`Jenkinsfile_portal:9`, `Jenkinsfile:12,37`)은 stale 해짐 | 위 |
| 4 | 잘못된 loc 시 동작 | **Validate 에서 실패하지 않는다.** 비어있지만 않으면 통과하고, 그 label 을 가진 agent 가 없으면 **Jenkins 가 executor 를 무한 대기**한다 (파이프라인 `timeout` 120분에 걸림, `:43`) | `:64-66`, `:43` |
| 5 | loc ↔ agent label 분리 계층 존재 | **없다.** 매핑 테이블·변환 함수·설정 파일이 저장소에 0건 | 전수 grep |

> 4번의 "무한 대기 후 timeout" 은 Jenkins 런타임 동작이다. 이 저장소 코드는 label 을 그대로
> 넘기는 것까지만 보장하며, 그 이후 스케줄러 거동은 **코드만으로 확인 불가**다.

---

## 13. 전체 흐름도

> 4채널 비교용. `[PRE]` = 인증 전 확보, `[AUTH]` = 인증 후 확보.

### 13.1. 공통 진입 (모든 채널)

```
Jenkins loc ──────────────► agent label 선택 (Ansible 에 전달 안 됨) ─────► [소멸]
                            └► Callback body "loc"
Jenkins target_type ──────► playbook / inventory.sh 파일 경로 선택 ──────► [소멸]
Jenkins inventory_json ───► env INVENTORY_JSON ──► inventory.sh
                                                    └► IP 만 추출, 나머지 필드 폐기
                                                       hostvars = {ansible_host: IP}
vault master password ────► --vault-password-file (전 loc·전 채널 공통 1개)
```

### 13.2. OS Linux

```
Inventory(IP)
   │
   ├─[PRE]─ Precheck: TCP 5986→5985→22 + 프로토콜 확인
   │         └► detected_os = 'linux'  (포트 22)
   │
   ├──────── add_host → _os_linux (connection=ssh, port=22)
   │
   ├──────── Vault: vault/linux.yml   ← vars_files 고정 (adapter 무관, loc 무관)
   │         └► accounts[] (배열 순서 = 시도 순서)
   │
   ├──────── Credential 시도: set_fact → reset_connection → raw echo
   │         └► 성공 판정: rc==0 AND '__auth_ok__' in stdout
   │            실패 → 다음 후보 (backoff 없음)
   │
   ├─[AUTH]─ preflight: /etc/os-release NAME → _l_distro_name   (버전 없음)
   │
   ├─[AUTH]─ Adapter: facts={os_type:'linux', distribution:_l_distro_name}
   │         └► 계열만 구분 (RHEL/Ubuntu/SUSE/generic) — 세대 구분 없음
   │
   └──────── Gather
```

### 13.3. OS Windows

```
Inventory(IP)
   │
   ├─[PRE]─ Precheck: WS-Man Identify → detected_os='windows', winrm_scheme
   ├──────── add_host → _os_windows (connection=winrm)
   ├──────── Vault: vault/windows.yml  ← vars_files 고정
   ├──────── Credential 시도: win_ping → ping=='pong'   (backoff 없음)
   ├─[AUTH]─ setup(hardware,network) → ansible_kernel
   ├─[AUTH]─ Adapter: facts={os_type:'windows', version:ansible_kernel}
   │         └► 2019 / 2022 / generic  (2016·2025 adapter 부재)
   └──────── Gather
```

### 13.4. ESXi

```
Inventory(IP)
   │
   ├─[PRE]─ Precheck: /sdk vim25 RetrieveServiceContent
   │         └► apiType / apiVersion / productLineId / version 확보
   │            └► diagnosis.details 로만 흘러가고 **선택에 미사용**
   │
   ├──────── Vault: vault/esxi.yml   ← vars_files 고정
   ├──────── Credential 시도: vmware_host_facts(summary)
   │         └► 성공 판정: not failed AND ansible_facts is defined  (backoff 없음)
   │
   ├─[AUTH]─ collect facts → _e_raw_facts.ansible_distribution_version
   ├─[AUTH]─ Adapter: facts={version: <인증 후 버전>}  → esxi_6x/7x/8x/generic
   └──────── Gather
```

### 13.5. Redfish (유일하게 Adapter → Vault 결합)

```
Inventory(bmc_ip)
   │
   ├─[PRE]─ Precheck: ServiceRoot 구조 확인 (자격증명 미전달, auth stage skip)
   │
   ├─[PRE]─ detect_vendor: 무인증 redfish_gather probe
   │         ├► vendor        : ServiceRoot → Manufacturer fallback → realm hint
   │         ├► model_hint    : **HPE 만**
   │         └► firmware_hint : **HPE 만**
   │
   ├──────── Adapter: adapter_loader(facts={vendor,model,firmware})
   │         └► 빈 model/firmware 는 실격이 아니라 보너스 제외
   │            → 비-HPE 는 최신 세대 adapter 가 선택됨 (실행 확인)
   │
   ├──────── Vault: adapter.credentials.profile → vault/redfish/{vendor}.yml
   │         └► 31 adapter → 9 profile (**vendor 단위, 세대 무관**)
   │            fallback_profiles 는 전부 [] → dead
   │            generic(profile='') → vault 미로딩 → 빈 자격 1회 시도
   │
   ├──────── Credential 시도: redfish_gather(username,password)
   │         ├► 성공 → promote (password 별도 보존)
   │         └► 실패 → auth_evidence 누적 → **sleep 5** → 다음 후보
   │
   ├──────── [조건부] recovery 성공 + primary 401 → account_service (쓰기)
   └──────── Gather
```

---

## 14. 설계 전에 반드시 결정해야 하는 사항

> 코드 조사만으로는 답이 나오지 않고, **정책 결정이 있어야 설계가 가능한** 질문만 적었다.
> 해결책은 제시하지 않는다.

### 14.1. Location 축

1. Location 별로 **Vault Master Key** 까지 분리해야 하는가, 아니면 마스터 키는 1개로 두고
   **vault 파일만** location 별로 나누는가?
   (현재는 둘 다 단일. 전자는 `Jenkinsfile*` credential 바인딩과 vault 재암호화가 함께 걸린다 — 2.5절)
2. Location 이 **Credential 값에 실제로 영향을 주는가**, 아니면 네트워크 도달 경로(agent)만
   다른 것인가? (현재 코드는 후자를 전제한다 — 1절)
3. `loc` 을 Ansible 로 전달해야 한다면 어느 경로인가 — extra-vars / 환경변수 / inventory hostvars?
   (현재 세 경로 모두 미사용 — 1.4절)
4. `ich/chj/yi` 외 값이 들어올 수 있는가? whitelist 를 코드에 둘 것인가?
   (현재 whitelist 없음, 잘못된 값은 agent 대기로 빠짐 — 12절)

### 14.2. Generation 축

5. **OS 세대별 계정이 실제로 다른가?** (RHEL 7/8/9, Windows 2016/2019/2022/2025)
   현재 세대 정보는 **인증 후에만** 확보되므로, 다르다면 순환 의존을 어떻게 끊을지 결정이 필요하다 (6절).
6. **Redfish 세대별 계정이 실제로 다른가?** (Dell 15G/16G, HPE Gen10/11/12, Lenovo XCC2/3)
   HPE 외에는 인증 전 세대 판별 근거가 없다 (8.4절).
7. **ESXi 세대별 계정이 다른가?** 다르다면 인증 전 확보되는 `/sdk` 의 `version`/`apiVersion` 을
   선택 근거로 승격할 것인가? (현재는 확보만 하고 버린다 — 5.3·7절)
8. 세대 판별이 불가능한 호스트(비-HPE Redfish, vim25 Fault 로만 통과한 ESXi)에서
   **어떤 credential 집합을 쓸 것인가** — 전 세대 후보 순차 시도인가, 기본 집합인가?

### 14.3. 후보 수 / 잠금

9. 세대·Location 축을 추가하면 후보 수가 곱셈으로 늘어난다.
   **vendor lockout 임계**(iLO 3회 / iDRAC·XCC 5회 — `try_one_account.yml:103-104`) 대비
   **후보 수 상한**을 둘 것인가? (현재 상한 없음 — 11.1절)
10. OS/ESXi 에도 backoff 를 넣을 것인가? (현재 Redfish 에만 있음 — 11.2절)
11. `role: primary` 가 복수가 될 수 있는가?
    현재 `account_service.yml:31` 은 `first` 만 취하고, `collect_standard.yml:81-87` 은
    "하나라도 401" 로 판정한다 (11.5절 #4·#5).

### 14.4. Adapter 결합

12. Credential 선택을 **Adapter 에서 분리**할 것인가, 유지할 것인가?
    현재 결합점은 `load_vault.yml:17-18` 2줄뿐이지만, Redfish vault 선택의 전부다 (8.6절).
13. OS/ESXi adapter 의 dead `credentials.profile`(`os_linux`/`os_windows`/`esxi_default`)을
    **실제 동작시킬 것인가, 제거할 것인가?** 현재 대응 vault 파일조차 없다 (9.2절).
14. 테스트만 강제하는 `recovery_accounts` 를 **production 에서 쓸 것인가, 정리할 것인가?** (9.2절 #4)

### 14.5. Inventory 계약

15. Portal 이 `generation` / `model` / `site` 같은 hint 를 보낼 것인가?
    보낸다면 `inventory.sh` 의 hostvars 구성(`:93`)을 열어 **호출자 hint 를 신뢰**할 것인가,
    아니면 **자체 탐지만 신뢰**할 것인가? (현재는 전부 폐기 — 10절)

---

## 15. 코드 / 문서 불일치

> 이번 조사에서 **코드와 대조해 확인된 것만** 적었다. 수정하지 않았다.

| # | 위치 | 문서 서술 | 실제 코드 |
|---|---|---|---|
| 1 | `CLAUDE.md` §3 / `.claude/rules/20-output-json-callback.md` R1 | envelope 예시에 `"meta": { "loc": "...", ... }` | `build_meta.yml:17-25` 에 **`loc` 필드 없음**. `schema/` 에도 `loc` 0건 |
| 2 | `docs/operate/04-pipeline-runtime.md:103-106` | credential `vault-pass` (Secret **file**), "미등록" | 실제 `server-gather-vault-password` (Secret **text**), 3곳에서 사용 중 |
| 3 | `docs/operate/08-ansible-config.md:79` | `withCredentials([file(credentialsId: 'vault-pass', ...)])` | 실제는 `string(credentialsId: 'server-gather-vault-password', ...)` |
| 4 | `docs/operate/05-vault.md` §4.1 | `ansible.cfg` 에 `vault_password_file` 이 있어야 함 | `ansible.cfg:57` **주석 처리 = 비활성** |
| 5 | `docs/operate/05-vault.md` §5.2 | `vault_redfish_password` 키를 갱신하라 | **이 키를 읽는 코드가 저장소에 없다.** `load_vault.yml:66-79` 는 `accounts` 와 legacy `ansible_user`/`ansible_password` 만 읽음 |
| 6 | `docs/ai/PRE-GATHER-PIPELINE-TRACE-2026-08-11.md` §9.4 (본인 선행 문서) | "Jenkins credential id 가 **세 곳**에서 일치 — `Jenkinsfile:159`, `Jenkinsfile_portal:160`, `jenkins/jobs/.../config.xml:22`" | `config.xml:22` 는 **설명 텍스트**이지 `credentialsId` 바인딩이 아니다. 실제 세 번째 코드 위치는 **`Jenkinsfile_portal_test:161`**. 또한 그 job 은 `<buildWrappers/>`(`:133`)가 비어 credential 바인딩이 **없다** |
| 7 | `lookup_plugins/adapter_loader.py:13` (주석) | 사용 예시로 `facts=_precheck_result.probe_facts` | 실제 호출부 4곳 중 precheck 의 `probe_facts` 를 넘기는 곳은 **0곳**. redfish 는 `_rf_probe_facts`(detect_vendor 산출물), os/esxi 는 자체 dict |
| 8 | `adapters/os/*.yml`, `adapters/esxi/*.yml` `credentials.profile` | `os_linux` / `os_windows` / `esxi_default` | 대응 vault 파일이 **존재하지 않고**, 읽는 코드도 없다 |
| 9 | `redfish-gather/tasks/load_vault.yml:7` (주석) | "list[0] = role=primary (provision target = infraops)" | `infraops` 문자열을 코드가 강제하지 않는다. vault 내용은 미확인 — **코드만으로 확인 불가** |

---

## 16. 조사 방법 및 한계

### 16.1. 검증한 것

- 인용한 모든 `파일:라인` 을 직접 읽어 확인
- **production 코드 실행 검증**: `module_utils/adapter_common.py` 의 `adapter_matches`/`adapter_score`
  를 import 해 `adapters/redfish/*.yml` 31개 전량에 대해 무인증/인증 시나리오 점수를 재현 (8.4절)
- **테스트 실행**: 관련 unit 141건 통과 확인
- dead path 판정은 **실행 조건 실측**으로 확인 (`fallback_profiles: []` × 42, `recovery_accounts`
  production 참조 0건)

### 16.2. 확인하지 못한 것 (추측하지 않음)

| 항목 | 이유 |
|---|---|
| vault 파일 **내부 실제 값** (username / password / 실제 role 배열 순서) | 복호화하지 않았다. 키 이름·구조만 코드와 생성 스크립트에서 확정 |
| ESXi `apiVersion` / `productLineId` 의 **실제 값** | 대상 장비 응답에 의존. 코드에 하드코딩 없음 |
| Jenkins 가 빌드 파라미터를 `sh` step 환경변수로 export 하는지 | Jenkins 런타임 거동. 저장소 코드로 확인 불가 |
| 잘못된 `loc` 입력 시 Jenkins 스케줄러의 정확한 거동 | 동일 |
| `jenkins/jobs/redfish-account-provision-verify` 의 `${VAULT_PASSWORD}` 출처 | XML 에 바인딩이 없어 저장소 코드로 확인 불가 |

### 16.3. 라인 번호 주의

`common/library/precheck_bundle.py`, `os-gather/site.yml`, `esxi-gather/site.yml`,
`redfish-gather/site.yml`, `redfish-gather/library/redfish_gather.py` 5개는 **미커밋 워킹트리 상태**를 읽었다.

**조사 도중 다른 작업이 같은 저장소를 편집해 라인이 밀린 사례가 실제로 발생했다.**
아래는 발견 즉시 재확인해 교정한 내역이다.

| 인용 | 최초 읽은 라인 | 교정 후 (현재) |
|---|---|---|
| `redfish_gather.py` `loc` 지역변수 | 2615-2617 | **2671-2673** |
| `precheck_bundle.py` `_detect_os_from_port` | 1141-1147 | **1161-1167** |
| `os-gather/site.yml` Linux `vars_files` | 211-214 | **217-220** |
| `esxi-gather/site.yml` select adapter | 112-116 | **111-117** |

교정 후 본 문서의 모든 인용을 다시 대조했다. 그럼에도 읽는 시점에 또 밀릴 수 있으므로
재확인 시 **태스크명 / 함수명 / 문자열**로 찾을 것.
