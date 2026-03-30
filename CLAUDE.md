# Server Exporter - 엔터프라이즈 서버 정보 수집 시스템

## 개요

엔터프라이즈급 서버 정보 수집 파이프라인이다. Jenkins-Ansible 기반의 **3-채널 통합 수집 시스템**으로 멀티벤더(Dell, HPE, Lenovo, Supermicro, Cisco) 하드웨어 및 OS 정보를 수집하고 표준화한다.

**특징:**
- **3중 채널**: OS-gather (Linux/Windows) + ESXi-gather + Redfish-gather (BMC/IPMI)
- **Fragment 모듈화**: 각 gather가 자신의 역할만 하고, 공통 정규화 파이프라인이 병합
- **Adapter 시스템**: 벤더/세대별 수집 방식을 YAML로 추상화 (코드 수정 불필요)
- **Vault 자동 로딩**: 포털은 IP만 전달, 인증정보는 ansible vault에서 자동 로드
- **표준 JSON Output**: 3채널 공통 스키마 (status, sections, data, errors, meta, diagnosis)

**상태**: 프로덕션 준비 완료 (실장비 검증: Dell/HPE/Lenovo, Round 7-10 완료)

---

## 아키텍처

### 전체 흐름 (포털 → Jenkins → Ansible → 포털)

```
포털 (HTTP POST)
  ├─ loc: "ich|chj|yi"
  ├─ target_type: "os|esxi|redfish"
  └─ inventory_json: [{"ip":"10.x.x.1"}]
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
    포털 (console log 파싱 또는 artifact)
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
       ├── library/redfish_gather.py (300줄, Redfish API 엔진)
       └── tasks/ + vendors/{dell,hpe,lenovo,supermicro,cisco}/

[2] 공통 로직 (Fragment 정규화)
   ├── common/library/
   │   └── precheck_bundle.py (4단계 진단: ping→port→protocol→auth)
   └── common/tasks/normalize/
       ├── init_fragments.yml (누적 변수 초기화)
       ├── merge_fragment.yml (Fragment 재귀 병합 엔진)
       ├── build_*.yml (10개: sections, status, errors, meta, correlation, output)
       └── supported_sections.yml, status_rules.yml

[3] Adapter 시스템 (25개 YAML)
   ├── adapters/redfish/ (14개: generic + dell×3 + hpe×4 + lenovo×2 + supermicro×3 + cisco)
   ├── adapters/os/ (7개: linux_*/windows_*)
   └── adapters/esxi/ (4개: generic + 6x/7x/8x)

[4] Schema & 데이터
   ├── schema/
   │   ├── sections.yml (10개: system, hardware, bmc, cpu, memory, storage, network, firmware, users, power)
   │   ├── field_dictionary.yml (18 Must + Nice + Skip)
   │   ├── baseline_v1/ (7개 벤더 baseline JSON)
   │   └── examples/ (success/partial/failed 예시)
   └── vault/ (linux.yml, windows.yml, esxi.yml, redfish/{vendor}.yml)

[5] Python 플러그인 (12개)
   ├── callback_plugins/json_only.py (stdout callback, OUTPUT 태스크만 JSON)
   ├── lookup_plugins/adapter_loader.py (adapter 동적 선택)
   ├── filter_plugins/diagnosis_mapper.py, field_mapper.py
   └── module_utils/adapter_common.py (점수 계산, 벤더 정규화)

[6] 테스트 (145개 Redfish fixture + 7개 baseline)
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
- [ ] Fragment 변수 생성 (`_data_fragment`, `_sections_<name>_supported_fragment`, `_errors_fragment`)
- [ ] `normalize_*.yml` 또는 `common/tasks/normalize/build_*.yml` 작성
- [ ] `merge_fragment.yml` 호출 확인 (각 gather 후)
- [ ] `common/vars/supported_sections.yml` 업데이트
- [ ] `schema/sections.yml` + `schema/fields/*.yml` 추가
- [ ] Baseline JSON 예시 추가 + 문서 업데이트

---

## 주의사항 & Best Practices

### Critical: Fragment 철학 지키기

**WRONG** - 다른 gather의 fragment 수정:
```yaml
- name: 다른 섹션의 fragment 수정 (금지!)
  set_fact:
    _sections_memory_collected_fragment: [...]
```

**CORRECT** - 자신의 fragment만:
```yaml
- name: 자신의 fragment 생성
  set_fact:
    _data_fragment:
      cpu: {...}
    _sections_cpu_collected_fragment: ['cpu']
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
| Adapter 수 | 7개 | 4개 | 14개 |
| 지원 섹션 | 6개 | 6개 | 9개 |
| Precheck | 포트 감지 | 4단계 | 4단계 |
| Graceful Degradation | O | O | O |
| 벤더 지원 | N/A | VMware | Dell, HPE, Lenovo, Supermicro, Cisco |
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

**프로젝트 상태: 핵심 수집 경로 검증 완료**
