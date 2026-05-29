# Server Exporter - 엔터프라이즈 서버 정보 수집 시스템

## 개요

엔터프라이즈급 서버 정보 수집 파이프라인이다. Jenkins-Ansible 기반의 **3-채널 통합 수집 시스템**으로 멀티벤더(Dell, HPE, Lenovo, Supermicro, Cisco) 하드웨어 및 OS 정보를 수집하고 표준화한다.

**특징:**
- **3중 채널**: OS-gather (Linux/Windows) + ESXi-gather + Redfish-gather (BMC/IPMI)
- **Fragment 모듈화**: 각 gather가 자신의 역할만 하고, 공통 정규화 파이프라인이 병합
- **Adapter 시스템**: 벤더/세대별 수집 방식을 YAML로 추상화 (코드 수정 불필요)
- **Vault 자동 로딩**: 호출자는 IP만 전달, 인증정보는 ansible vault에서 자동 로드
- **표준 JSON Output**: 3채널 공통 스키마 (status, sections, data, errors, meta, diagnosis)

**상태**: 프로덕션 준비 완료 (실장비 검증: Dell/HPE/Lenovo, Round 7-10 완료)

---

## 아키텍처

### 전체 흐름 (호출자 → Jenkins → Ansible → JSON 결과)

```
호출자 (HTTP POST)
  ├─ loc: "ich|chj|yi"
  ├─ target_type: "os|esxi|redfish"
  └─ inventory_json: [{"service_ip":"10.x.x.1"}]  (os/esxi)
                      [{"bmc_ip":"10.x.x.1"}]     (redfish)
                      [{"ip":"10.x.x.1"}]          (fallback)
         ↓
    Jenkins Job (Jenkinsfile v3, 4-Stage)
    ├─ [1 Validate] 입력값 검증
    ├─ [2 Gather] ansible-playbook 실행
    │   ├─→ os-gather/site.yml (Play1:포트감지 → Play2:Linux → Play3:Windows)
    │   ├─→ esxi-gather/site.yml (1-Play)
    │   └─→ redfish-gather/site.yml (1-Play)
    ├─ [3 Validate Schema] field_dictionary.yml 정합성 (FAIL 게이트)
    ├─ [4 E2E Regression] pytest baseline/fixture 회귀 검증 (FAIL 게이트)
    └─ [Post] json_only callback → JSON 출력
         ↓
    호출자 (console log 파싱 또는 artifact)
```

### Fragment 정규화

각 gather는 자신의 fragment만 생성하고, merge_fragment.yml이 누적 병합한다.
공통 builder(build_sections/status/errors/meta/correlation/output)가 최종 JSON을 조립한다.
각 gather는 자신의 역할만 담당하며, 새 섹션 추가 시 build_output.yml 전체 수정은 필요하지 않다. 필요한 경우 site.yml에는 include_tasks 한 줄만 추가하면 된다.

Fragment 변수 규칙, 네이밍 컨벤션, 실패 처리 패턴은 GUIDE_FOR_AI.md 참조.

### Adapter 시스템 (벤더 자동 감지)

```
adapter_loader (lookup plugin)
  ├─ adapters/<channel>/*.yml 스캔
  ├─ 각 adapter의 match 조건 평가
  │   (vendor AND model_patterns AND firmware_patterns AND ...)
  ├─ 점수 계산
  │   score = priority × 1000 + specificity × 10 + match_score
  ├─ 점수순 정렬
  └─ 최고 점수 adapter 반환 (또는 generic fallback)

예: Redfish Dell iDRAC 선택 과정
  ├─ dell_idrac9.yml (priority=100) vs
  ├─ dell_idrac8.yml (priority=50) vs
  ├─ dell_idrac.yml (priority=10) vs
  ├─ redfish_generic.yml (priority=0)
  └─ → 펌웨어 매칭 + 우선순위 기반 최종 선택
```

**새 벤더 추가 (3단계):**
1. `common/vars/vendor_aliases.yml`에 벤더 이름 매핑 추가
2. `adapters/redfish/{벤더}_*.yml` adapter YAML 생성 (match, capabilities, collect, normalize 경로)
3. (선택) `redfish-gather/tasks/vendors/{벤더}/` OEM 태스크 추가

**site.yml 수정 불필요** — adapter_loader가 동적으로 감지한다.

---

## 기술 스택

> 아래는 검증 기준 Agent (10.100.64.154) 에서 2026-03-27 확인한 값이다.
> 최소 요구사항은 [REQUIREMENTS.md](REQUIREMENTS.md) 4절 참조.

| 카테고리 | 기술 | 검증 기준 버전 | 용도 |
|---------|------|--------------|------|
| **Orchestration** | ansible-core | 2.20.3 | 플레이북 실행 |
| | ansible (package) | 13.4.0 | core + bundled collections |
| **Language** | Python | 3.12.3 | 커스텀 모듈, 필터, 플러그인 (venv: `/opt/ansible-env/`) |
| **Runtime** | Java (OpenJDK) | 21.0.10 | Jenkins Agent 실행 |
| **Template** | Jinja2 | 3.1.6 | Ansible 템플릿 엔진 |
| **Protocol** | SSH, WinRM, Redfish API | — | 정보 수집 |
| **CI/CD** | Jenkins | — | 파이프라인 실행 (Java 21 필수) |
| **Secrets** | Ansible Vault | — | 인증 정보 관리 |
| **Utils** | Python stdlib | — | Redfish HTTP, XML, JSON (외부 라이브러리 없음) |

**Collections (프로젝트 사용 분):**
- `ansible.windows` 3.3.0 — Windows gather
- `community.vmware` 6.2.0 — ESXi gather
- `community.windows` 3.1.0 — Windows 보조 모듈
- `ansible.posix` 2.1.0, `community.general` 12.4.0, `ansible.utils` 6.0.1

**pip 패키지:**
- `pywinrm` 0.5.0 — Windows WinRM
- `pyvmomi` 9.0.0 — ESXi vSphere API
- `redis` 7.3.0 — Ansible fact caching
- `jmespath` 1.1.0 — json_query 필터
- `netaddr` 1.3.0 — ipaddr 필터
- `lxml` 6.0.2 — VMware XML 파싱
- Redfish는 **stdlib만 사용** (urllib, ssl, json)

---

## 파일 구조

```
server-exporter/ (프로젝트 루트)

[1] 수집 채널 (3개)
   ├── os-gather/
   │   ├── site.yml (3-Play: 포트감지→Linux→Windows)
   │   └── tasks/linux/ (6개) + windows/ (6개) → gather_*.yml
   ├── esxi-gather/
   │   ├── site.yml (1-Play)
   │   └── tasks/ → collect_facts/config/datastores + normalize_*
   └── redfish-gather/
       ├── site.yml (1-Play: precheck→detect→adapter→collect→normalize)
       ├── library/redfish_gather.py (약 3,812줄, Redfish API 엔진 — Storage+Volumes 수집, 2026-05-29 재실측)
       └── tasks/ + vendors/{dell,hpe,lenovo,supermicro,cisco}/

[2] 공통 로직 (Fragment 정규화)
   ├── common/library/
   │   └── precheck_bundle.py (4단계 진단: ping→port→protocol→auth)
   └── common/tasks/normalize/
       ├── init_fragments.yml (누적 변수 초기화)
       ├── merge_fragment.yml (Fragment 재귀 병합 엔진)
       ├── build_*.yml (10개: sections, status, errors, meta, correlation, output)
       └── supported_sections.yml, status_rules.yml

[3] Adapter 시스템 (42개 YAML + adapters/registry.yml — cycle 2026-05-11 실측)
   ├── adapters/redfish/ (31개: generic + dell×4 + hpe×7 + lenovo×4 + supermicro×8 + cisco×3
   │                       + huawei×1 + inspur×1 + fujitsu×1 + quanta×1)
   │   ※ cisco 3 = bmc + cimc + ucs_xseries (cycle 2026-05-01 ucs_xseries 신설 — cisco 그룹 내)
   │   - cycle 2026-05-01 신 generation 7개: dell_idrac10 (F41) + hpe_ilo7 (F47) + lenovo_xcc3 (F55)
   │     + supermicro_x12/x13/x14 (F61) + cisco_ucs_xseries (F69)
   │   - cycle 2026-05-06 M-E2: hpe_superdome_flex (priority=95, lab 부재 web sources 14건)
   │   - cycle 2026-05-07 M-B1~B4: supermicro x9 + x10 + ars + bmc 보강 (4 adapter — 6 generation)
   │   - cycle 2026-05-11 hpe-csus-add: hpe_csus_3200 (priority=96, Compute Scale-up Server 3200, lab 부재 web sources 7건)
   │   - cycle 2026-05-12 csus-rmc-multi-node: CSUS/Superdome RMC 멀티노드 수집 구현 — **lab 부재 (mock/web sources, 실장비 미검증)**
   │     (전 Partition/Manager/Chassis 수집, data.multi_node Additive 컨테이너, lab 도입 후 실 baseline 교체 의무, ADR-2026-05-12)
   │   - cycle 2026-05-01 신규 vendor 4개 (vault SKIP, 사용자 명시 승인): F44 huawei_ibmc /
   │     F45 inspur_isbmc / F46 fujitsu_irmc / F47 quanta_qct_bmc
   ├── adapters/os/ (7개: linux_*/windows_*)
   └── adapters/esxi/ (4개: generic + 6x/7x/8x)

[4] Schema & 데이터
   ├── schema/
   │   ├── sections.yml (10개: system, hardware, bmc, cpu, memory, storage, network, firmware, users, power)
   │   ├── field_dictionary.yml (39 Must + 38 Nice + 6 Skip = 83 entries — 2026-05-29 재실측, 16 section prefixes)
   │   ├── baseline_v1/ (9 baseline JSON: redfish 5 [cisco/dell/hpe/lenovo 실측 4 + hpe_csus_3200 **MOCK**] + esxi/ubuntu/windows + rhel810_raw_fallback)
   │   └── examples/ (success/partial/failed 예시)
   └── vault/ (linux.yml, windows.yml, esxi.yml, redfish/{vendor}.yml)

[5] Python 플러그인 (12개)
   ├── callback_plugins/json_only.py (stdout callback, OUTPUT 태스크만 JSON)
   ├── lookup_plugins/adapter_loader.py (adapter 동적 선택)
   ├── filter_plugins/diagnosis_mapper.py, field_mapper.py
   └── module_utils/adapter_common.py (점수 계산, 벤더 정규화)

[6] 테스트 (tests/fixtures 353개 + 9 baseline + test_*.py 42파일/375 함수 — 2026-05-29 재실측)
   ├── tests/redfish-probe/ (probe_redfish.py, deep_probe_redfish.py)
   ├── tests/fixtures/ (실장비 JSON 응답)
   ├── tests/evidence/ (Round 7-10 조건부 검토)
   └── tests/scripts/ (conditional_review.py, os_esxi_verify.sh)

[7] 문서 (23개: 루트 4 + docs/ 19)
   ├── README.md, GUIDE_FOR_AI.md, REQUIREMENTS.md
   └── docs/
       ├── 01_jenkins-setup        — Jenkins 설치·플러그인·자격증명·RBAC
       ├── 02_redis-install         — Redis 설치·설정
       ├── 03_agent-setup           — Agent 노드 구성 (VM·방화벽·패키지·노드등록)
       ├── 04_job-registration      — Jenkins Job 등록·네이밍
       ├── 05_inventory-json-spec   — inventory_json 입력 스펙
       ├── 06_gather-structure      — 3-채널 Gather 구조
       ├── 07_normalize-flow        — Fragment 정규화 흐름
       ├── 08_failure-handling      — block/rescue/always 실패 처리
       ├── 09_output-examples       — 표준 JSON 출력 예시
       ├── 10_adapter-system        — Adapter 시스템 (matrix 포함)
       ├── 11_precheck-module       — Precheck 모듈 (4단계 진단)
       ├── 12_diagnosis-output      — Diagnosis 출력 구조
       ├── 13_redfish-live-validation — 3대 실장비 검증
       ├── 14_add-new-gather        — 새 Gather 추가 가이드
       ├── 16_os-esxi-mapping       — OS/ESXi 필드 매핑
       ├── 17_jenkins-pipeline      — Jenkins 파이프라인 런타임
       ├── 18_ansible-project-config — Ansible 프로젝트 설정
       └── 19_decision-log          — 의사결정 로그
```

---

## ECC 활용

| 작업 | 명령어 | 비고 |
|------|--------|------|
| 새 기능 계획 | `/plan "기능명"` | 구현 전 아키텍처·단계 계획 |
| TDD | `/tdd "기능명"` | Python 부분: 테스트 먼저 |
| Python 리뷰 | `/python-review` | redfish_gather.py, precheck_bundle.py 등 |
| 일반 리뷰 | `/code-review` | Ansible YAML 포함 |
| 보안 검사 | `/security-review` | 커밋 전 점검 |

새 벤더/gather 추가 상세 절차는 docs/14_add-new-gather.md 참조.

### Fragment 추가 체크리스트

- [ ] `gather_*.yml` 또는 `collect_*.yml` 작성 (raw 수집)
- [ ] Fragment 변수 생성 (5 공통 변수: `_data_fragment`, `_sections_supported_fragment`, `_sections_collected_fragment`, `_sections_failed_fragment`, `_errors_fragment` — 변수 이름은 모든 gather가 동일, 값으로 자기 섹션을 채움)
- [ ] `normalize_*.yml` 또는 `common/tasks/normalize/build_*.yml` 작성
- [ ] `merge_fragment.yml` 호출 확인 (각 gather 후)
- [ ] `common/vars/supported_sections.yml` 업데이트
- [ ] `schema/sections.yml` + `schema/fields/*.yml` 추가
- [ ] Baseline JSON 예시 추가 + 문서 업데이트

---

## 주의사항 & Best Practices

### Critical: Fragment 철학 지키기

**WRONG** - 누적 변수를 직접 수정:
```yaml
- name: 누적 변수 직접 수정 (금지! merge_fragment.yml 영역)
  set_fact:
    _collected_data: "{{ _collected_data | combine(...) }}"
```

**WRONG** - 다른 gather의 섹션을 자기 fragment에 포함:
```yaml
- name: cpu gather에서 memory도 추가 (금지!)
  set_fact:
    _sections_collected_fragment: ['cpu', 'memory']  # memory는 다른 gather 영역
```

**CORRECT** - 자신의 fragment만 (5 공통 변수):
```yaml
- name: 자신의 fragment 생성
  set_fact:
    _data_fragment:
      cpu: {...}
    _sections_supported_fragment: ['cpu']
    _sections_collected_fragment: ['cpu']
    _sections_failed_fragment: []
```

### High: Adapter 점수 계산

```
score = priority × 1000 + specificity × 10 + match_score
```

**점수 최적화:**
- 범용 (generic) → priority=0
- 기본 벤더 → priority=10
- 세대별 → priority=50-100
- 구체적 모델 → match.model_patterns + 높은 specificity

### Medium: Vault 2단계 로딩

**Redfish 특화:**
```yaml
# 1단계: 무인증으로 벤더 감지
- redfish_gather:
    ip: "{{ target_ip }}"
    # 계정 없음 (ServiceRoot 무인증)
  register: _rf_probe

# 2단계: 벤더에 맞는 vault 로딩
- include_vars:
    file: "vault/redfish/{{ _rf_detected_vendor }}.yml"
    name: _rf_vault

# 3단계: 인증으로 재수집
- redfish_gather:
    ip: "{{ target_ip }}"
    username: "{{ _rf_vault.username }}"
    password: "{{ _rf_vault.password }}"
```

### Medium: Linux 2-Tier Gather (Python 감지 + Raw Fallback)

Linux OS gather는 `preflight.yml`에서 Python 버전을 감지하여 `_l_python_mode`를 설정한다.

| 모드 | 조건 | 수집 방식 |
|------|------|----------|
| `python_ok` | Python 3.9+ | 기존 Python 경로 (setup/shell/command/getent) |
| `python_missing` / `python_incompatible` | Python 미설치 또는 3.8 이하 | raw-only 경로 |
| `raw_forced` | `SE_FORCE_LINUX_RAW_FALLBACK=true` | raw-only (개발/검증 전용) |

**raw fallback 원칙:**
- remote 실행은 `raw` 모듈만 사용, controller-side `set_fact`/Jinja2 파싱은 허용
- 6개 섹션 모두 수집 가능, JSON 스키마 호환성 100% 유지
- `diagnosis.details`에 `gather_mode`, `python_version` 추가
- SELinux: `getenforce` 출력을 `enabled`/`disabled`로 정규화 (Round 2에서 수정)
- Memory: raw 경로는 dmidecode 기반으로 `physical_installed`를 반환 (Python 경로의 `os_visible`보다 정밀)
- 검증 완료: RHEL 8.10 (py3.6→auto raw), RHEL 9.2, 9.6, Rocky 9.6, Ubuntu 24.04, 5대 31필드 전수 검증
- 복잡 토폴로지 실증 완료 (bridge+VLAN+container NIC+policy routing, Round 4)

### Low: OEM 확장 (선택)

OEM이 없으면:
```yaml
collect:
  strategy: standard_only
```

OEM이 있으면:
```yaml
collect:
  strategy: standard+oem
  oem_tasks: redfish-gather/tasks/vendors/{vendor}/collect_oem.yml
```

---

## Git 워크플로우

### Commit 메시지 포맷

```
<type>: <description>

<optional body>

Examples:
  feat: Add thermal information collection
  fix: Fragment merge null value handling
  refactor: Simplify adapter scoring algorithm
  docs: Update field dictionary
  test: Add Dell R760 thermal fixture
```

### Branch 전략 (권장)

```bash
main
├─ feature/new-vendor-huawei
│   └─ adapters/redfish/huawei_*.yml
│   └─ redfish-gather/tasks/vendors/huawei/
├─ bugfix/fragment-merge
│   └─ common/tasks/normalize/merge_fragment.yml
└─ docs/add-thermal-section
    └─ schema/sections.yml
    └─ docs/thermal-section.md
```

---

## 3-채널 지원 현황

| 기능 | OS (Linux/Windows) | ESXi | Redfish |
|------|-------------------|------|---------|
| 구현 완료 | O | O | O |
| Adapter 수 | 7개 | 4개 | 31개 (2026-05-29 재실측) |
| 지원 섹션 | 6개 | 6개 | 9개 |
| Precheck | 포트 감지 | 4단계 | 4단계 |
| Graceful Degradation | O | O | O |
| 벤더 지원 | N/A | VMware | Dell, HPE, Lenovo, Supermicro, Cisco + (lab 부재) Huawei, Inspur, Fujitsu, Quanta |
| 실장비 검증 | O | O (문서) | O (3대: Dell/HPE/Lenovo) |

---

## 트러블슈팅

### Q1: Fragment 병합이 제대로 되지 않음
**원인:** merge_fragment.yml을 호출하지 않음
**해결:**
```yaml
# gather_*.yml 후에 반드시 호출
- include_tasks: "{{ playbook_dir }}/common/tasks/normalize/merge_fragment.yml"
```

### Q2: Adapter가 선택되지 않음
**원인:** match 조건이 맞지 않음
**해결:**
```bash
# -vvv로 adapter_loader lookup 디버그 출력 확인
ansible-playbook redfish-gather/site.yml \
  -i redfish-gather/inventory.sh \
  -e "target_ip=10.x.x.1" -vvv 2>&1 | grep -i "adapter"
```

### Q3: Vault 로딩 실패
**원인:** 벤더명이 정규화되지 않음
**해결:**
```yaml
# vendor_aliases.yml 확인
cat common/vars/vendor_aliases.yml | grep "{{ detected_vendor }}"
```

---

## 주요 문서

| 문서 | 용도 |
|------|------|
| **README.md** | 프로젝트 정체성, 3-채널 개요 |
| **GUIDE_FOR_AI.md** | Fragment 철학, 새 gather 템플릿 |
| **REQUIREMENTS.md** | 벤더/버전별 최소 요구사항 |
| **docs/06_gather-structure.md** | 전체 구조 |
| **docs/07_normalize-flow.md** | Fragment 정규화 흐름 |
| **docs/10_adapter-system.md** | Adapter 상세 설명 |
| **docs/13_redfish-live-validation.md** | 3대 실장비 검증 결과 |
| **docs/17_jenkins-pipeline.md** | Jenkins 파이프라인 런타임 |
| **docs/18_ansible-project-config.md** | Ansible 프로젝트 설정 |
| **docs/19_decision-log.md** | 설계 의사결정 기록 |

---

## 알려진 제한사항

- ESXi 수집은 community.vmware 컬렉션 의존 (프로덕션 Agent에 설치 필요, 03_agent-setup.md 3절 참조)
- OEM vendor task는 placeholder 상태 (향후 운영 요구 시 확장)

> 해결 완료된 항목(B1/B3/B5/B6/C1)은 docs/19_decision-log.md 참조.

---

## AI 하네스 운영 (Tier 0)

> 본 절은 2026-04-27 추가. clovirone 풀스펙 하네스를 server-exporter 도메인으로 1:1 포팅한 결과.

### 세션 시작 프로세스

**원칙**: 자동 추론 먼저, 질문은 최소한.

#### Step 1: 자동 감지

`git branch --show-current`로 브랜치명을 읽고:

```
server-exporter — 운영 기준선 (브랜치: main)
```

또는 작업 브랜치면:
```
server-exporter — 기능 작업 (huawei-vendor) (브랜치: feature/huawei-vendor)
```

#### Step 2: 작업 요청에서 역할 자동 추론

| 키워드/패턴 | 추론 역할 |
|---|---|
| Ansible / playbook / gather / 채널 / Fragment | gather |
| schema / sections / field_dictionary / baseline / callback / output | output-schema |
| Jenkins / cron / agent / vault / Redis / 인프라 | infra |
| pytest / probe / fixture / 회귀 / Round | qa |
| 요구사항 / 기획 / 명세 | po |
| 일정 / 릴리즈 / 진행률 | tpm |

#### Step 3: 컨텍스트 로드

- `.claude/role/{역할}/README.md`
- 거기 명시된 ai-context 문서들
- 정본: `GUIDE_FOR_AI.md` / `REQUIREMENTS.md` / `docs/01~19`

#### Step 4: 코드 변경 요청 → task-impact-preview 먼저

- 단순 오타 외의 코드 변경 시 **반드시** `task-impact-preview` 먼저 (rule 91 R1)
- 사용자가 "그냥 진행해줘" / "프리뷰 skip" 명시하면 건너뜀
- 5 섹션 출력 (영향 모듈 / 영향 vendor / 함께 바뀔 것 / 리스크 top 3 / 진행 확인)

#### Step 5: AI 커뮤니케이션 원칙

- 일상어 + WHY + WHAT + IMPACT + 결정 주체 명시 (rule 23)
- 승인 요청 4요소 (무엇 / 왜 / 영향 / 결정 필요)
- 완료 보고 6 체크리스트 (rule 24)

#### Step 6: 자율 판단 원칙

**R1. 자율 진행** (묻지 말고 바로):
- 사용자가 "모두 진행", "계속" 명시
- 이미 승인받은 범위 내 세부 선택
- 검증 (ansible-playbook --syntax-check / pytest / verify_*)
- 문서 갱신, commit, **push (main 포함 — 2026-05-01 사용자 명시, rule 93 R1+R4)**

**R2. 명시 승인 필요**:
1. 보호 경로 변경 (vault / Jenkinsfile / schema/baseline_v1)
2. **force push** (`--force` / `-f` / `--force-with-lease`) — rule 93 R1
3. 의존성 추가/삭제 (requirements 변경)
4. schema 버전 결정 (rule 92 R5)
5. cron 변경 (rule 80)
6. 새 Vendor 추가 (rule 50)
7. branch 간 merge / cherry-pick (rule 93 R2)

**R3. "완료" 직전 체크**: rule 24 6체크 모두 PASS여야 완료 선언.

### 절대 금지사항

1. **비밀값 하드코딩 금지** — vault/{linux,windows,esxi}.yml + vault/redfish/{vendor}.yml만 사용. 평문 commit 금지.
2. **보호 경로 자율 수정 금지** — `.git/, vault/**, schema/baseline_v1/**, Jenkinsfile*`. 상세: `.claude/policy/protected-paths.yaml`
3. **벤더 경계 위반 금지** — `common/`, `os-gather/`, `esxi-gather/`, `redfish-gather/` (단 `tasks/vendors/` 제외) 코드에 vendor 이름 (Dell/HPE/...) 하드코딩 금지. 분기는 adapter YAML 또는 OEM tasks 안에만 (rule 12).
4. **Fragment 침범 금지** — 각 gather는 자기 fragment만 만든다. 다른 gather의 fragment 변수 / 누적 변수 직접 수정 금지 (rule 22).
5. **외부 라이브러리 추가 금지 (redfish library)** — `redfish-gather/library/redfish_gather.py`는 stdlib만 (urllib / ssl / json) (rule 10).
6. **문서 갱신 누락 금지** — 코드 변경 시 관련 증거 문서 갱신 필수 (rule 70).
7. **bypassPermissions 금지** — settings.json `disableBypassPermissionsMode: "disable"`로 강제. CLI 플래그 우회 금지.
8. **전역 설정 자율 수정 금지** — `~/.claude/settings.json` 수정 안 함. 팀 정책은 `.claude/settings.json` (이미 commit됨).

### 하네스 자기개선 루프

server-exporter는 두 개 루프 분리:

| 루프 | Orchestrator | 대상 | 금지 |
|---|---|---|---|
| 제품 루프 | `wave-coordinator` | os-gather / esxi-gather / redfish-gather / common / adapters / schema / tests | 하네스 파일 수정 |
| 하네스 루프 | `harness-evolution-coordinator` | .claude/, docs/ai/, scripts/ai/ | 제품 코드 수정 |

#### 6단계 파이프라인

```
observer (관측+1차해석) → architect → reviewer → governor → updater → verifier
```

- 자유방임 자기수정 금지 — 교차검증 + 승인
- control plane 완화 자동 금지 — 권한/보호/경계 변경은 사람만 승인

#### 변경 등급 (Tier)

| Tier | 예시 | 승인 |
|---|---|---|
| 1 (자동허용) | docs 초안, stale 정정, 보고서 | reviewer APPROVE 후 진행 |
| 2 (승인필요) | rules / agents / skills 변경 | governor 심사 |
| 3 (절대금지) | settings 권한 완화, 보호 경로 제거 | 사용자 에스컬레이션만 |

### 컨텍스트 자동 로드 매핑

작업 파일에 따라 아래 ai-context 자동 적용:

```
os-gather/, esxi-gather/, redfish-gather/, common/library/   → ai-context/gather/convention.md
schema/, common/tasks/normalize/, callback_plugins/          → ai-context/output-schema/convention.md
Jenkinsfile*, ansible.cfg, scripts/                          → ai-context/infra/convention.md
tests/                                                       → role/qa/README.md
adapters/{vendor}_*.yml, redfish-gather/tasks/vendors/{v}/   → ai-context/vendors/{vendor}.md
외부 시스템 (Redfish/IPMI/SSH/WinRM/vSphere) 응답 처리        → ai-context/external/integration.md
```

### 하네스 구조

```
.claude/
├── rules/        # 29 상시 규칙
├── skills/       # 호출형 작업 플레이북 (Plan 2 예정)
├── agents/       # 서브에이전트 정의 (Plan 2 예정)
├── role/         # 6 역할 README (gather / output-schema / infra / qa / po / tpm)
├── ai-context/   # 도메인별 컨벤션
├── policy/       # 10 YAML
├── templates/    # 10 문서 템플릿
├── commands/     # 5 사용 가이드
└── settings.json # 16 hooks 등록 + 보호 경로 deny

docs/ai/          # AI 협업 메타 (Plan 3 예정)
scripts/ai/       # 자동화 스크립트 (Python 27, OS 중립)
```

### 핵심 컨벤션 요약

- **Fragment 철학** (rule 22): 각 gather 자기 fragment만, merge_fragment.yml이 누적
- **Adapter 점수**: `priority × 1000 + specificity × 10 + match_score`
- **Vault 2단계 로딩** (Redfish): 무인증 detect → vendor vault 로드 → 인증 수집
- **Linux 2-tier**: Python 3.9+ ok / raw fallback 자동 분기
- **JSON envelope**: 13 필드 고정 (정본 = `common/tasks/normalize/build_output.yml` / rule 13 R5)
  - 분석 6 카테고리: status / sections / data / errors / meta / diagnosis
  - 라우팅·식별 5: target_type / collection_method / ip / hostname / vendor
  - 추적 2: correlation / schema_version
  - 실패 fallback (always block) 도 13 필드 모두 emit + diagnosis.details는 dict 형태 유지
- **4단계 Precheck**: ping → port → protocol → auth
- **Jenkins 4-Stage**: Validate → Gather → Validate Schema → **(pipeline별)** Stage 4 (`Jenkinsfile`=E2E Regression / `Jenkinsfile_portal`=Callback). cycle-015에서 `Jenkinsfile_grafana` 제거
- **벤더 추가 3단계**: vendor_aliases.yml + adapter YAML + (선택) OEM tasks (site.yml 수정 불필요)

### 갭 리포트 해석 주의

- `session_start` hook이 origin/main 갭 출력
- ahead = 내 브랜치 앞선 commit 수
- behind = origin/main이 앞선 commit 수
- behind > 0이면 `pull-and-analyze-main` skill 또는 `git diff HEAD..origin/main`으로 분석

---

**프로젝트 상태: production-audit (2026-04-29) — 4 agent 전수조사 + HIGH 30+건 일괄 fix 완료**

production-audit 결과 (2026-04-29):
- **4 agent 병렬 전수조사** — Redfish (1504-line library + 16 adapter) / OS-ESXi-common / Schema-callback-cross-channel JSON / Tests-baselines-pipelines
- **공통 정합 정합성 fix**: skeleton drift 동기화 (3 normalize 파일) / diagnosis.details shape 통일 (dict) / field_dictionary top-level 8 entries 추가
- **Cross-channel JSON 일관성**: ESXi vendor `vendor_aliases.yml` 정규화 + `auth_success: true` set / cisco_baseline `users: []` / Windows storage `media_type` SSD/HDD enum 정규화
- **Linux gather 보강**: LANG=C / VLAN underscore / FS allow-list / df '-' parse defense
- **Windows gather 보강**: runtime swap namespace pattern / network InterfaceIndex grouping
- **Redfish 보강**: account_service 복구 creds 버그 / cross-channel typing (int/bool cast) / vendor map merge / Power.PowerControl 비-dict 방어
- **ESXi 보강**: DNS 추출 dict-level drill-in / netmask 비트 카운팅 (/22, /26, /28)
- **Common 보강**: precheck IPv6 듀얼스택 / diagnosis_mapper None 가드
- **Jenkins 보강**: per-stage timeout / E2E mandatory / archive / Jenkinsfile_portal Stage 3 hard gate / Callback unstable not error (rule 31 R2)
- **Secrets 정리**: tests/scripts + scripts/ai 13곳 'Goodmit0802!' 환경변수화
- 검증: **pytest 699/699 PASS** + harness consistency + vendor boundary + field_dictionary (83 entries) + PROJECT_MAP fingerprint 갱신

이전 cycle-016 (2026-04-29):
- 사용자 요구사항 11/11 검증 + 실 Jenkins 빌드 5회 (#39 ~ #45) + summary grouping 완성
- 9 파일 namespace pattern (Jinja2 loop scoping fix)
- 9 inline `{# ... #}` Jinja2 코멘트 제거
