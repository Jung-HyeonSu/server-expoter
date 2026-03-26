# Server Exporter - 엔터프라이즈 서버 정보 수집 시스템

## 📋 개요

엔터프라이즈급 서버 정보 수집 파이프라인입니다. Jenkins-Ansible 기반의 **3-채널 통합 수집 시스템**으로 멀티벤더(Dell, HPE, Lenovo, Supermicro, Cisco) 하드웨어 및 OS 정보를 수집하고 표준화합니다.

**핵심 특징:**
- 🔄 **3중 채널**: OS-gather (Linux/Windows) + ESXi-gather + Redfish-gather (BMC/IPMI)
- 🧩 **Fragment 기반 모듈화**: 각 gather가 자신의 역할만 하고, 공통 정규화 파이프라인이 병합
- 📌 **Adapter 시스템**: 벤더/세대별 수집 방식을 YAML로 추상화 (코드 수정 X)
- 🔐 **Vault 자동 로딩**: 포털은 IP만 전달, 인증정보는 ansible vault에서 자동 로드
- 📊 **표준 JSON Output**: 3채널 공통 스키마 (status, sections, data, errors, meta, diagnosis)

**상태**: 🟢 **프로덕션 준비 완료** (실장비 검증: Dell/HPE/Lenovo, Round 7-10 완료)

---

## 🏗️ 아키텍처

### 전체 흐름 (포털 → Jenkins → Ansible → 포털)

```
포털 (HTTP POST)
  ├─ loc: "ich|chj|yi"
  ├─ target_type: "os|esxi|redfish"
  └─ inventory_json: [{"ip":"10.x.x.1"}]
         ↓
    Jenkins Job
    ├─ [Validate] 입력값 검증
    ├─ [Gather] ansible-playbook 실행
    │   ├─→ os-gather/site.yml (Play1:포트감지 → Play2:Linux → Play3:Windows)
    │   ├─→ esxi-gather/site.yml (1-Play)
    │   └─→ redfish-gather/site.yml (1-Play)
    └─ [Post] json_only callback → JSON 출력
         ↓
    포털 (console log 파싱 또는 artifact)
```

### Fragment 기반 정규화 (핵심 설계)

```
Raw 수집 (각 gather_*.yml)
  ↓
Fragment 생성
  ├─ _data_fragment
  ├─ _sections_supported_fragment
  ├─ _sections_collected_fragment
  ├─ _sections_failed_fragment
  └─ _errors_fragment
  ↓
merge_fragment.yml (누적 병합)
  ├─ _merged_data (재귀 dict 병합)
  ├─ _all_sec_supported (list 합산)
  ├─ _all_sec_collected
  ├─ _all_sec_failed
  └─ _all_errors
  ↓
공통 정규화 빌더 (common/tasks/normalize/)
  ├─ build_sections.yml → sections dict
  ├─ build_status.yml → status (success|partial|failed)
  ├─ build_errors.yml → errors[]
  ├─ build_meta.yml → meta (adapter_id, duration_ms)
  ├─ build_correlation.yml → correlation (serial_number, system_uuid)
  └─ build_output.yml → 최종 JSON + schema_version
```

**설계 철학:**
- 각 gather는 자신의 역할만 → **낮은 결합도**
- 새 섹션 추가 시 site.yml 수정 불필요 → **높은 확장성**
- Fragment 구조로 부분 실패 처리 → **우아한 오류 처리**

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

**site.yml 수정 불필요!** adapter_loader가 동적으로 감지.

---

## 📦 기술 스택

| 카테고리 | 기술 | 버전 | 용도 |
|---------|------|------|------|
| **Orchestration** | Ansible | 2.10+ | 플레이북 실행 |
| **Language** | Python | 3.8+ | 커스텀 모듈, 필터, 플러그인 |
| **Protocol** | SSH, WinRM, Redfish API | v4 | 정보 수집 |
| **CI/CD** | Jenkins | 2.x | 파이프라인 실행 |
| **Secrets** | Ansible Vault | - | 인증 정보 관리 |
| **Utils** | Python stdlib | - | HTTP, XML, JSON (외부 라이브러리 없음) |

**의존성:**
- `ansible.windows` (Windows support)
- `community.vmware` (ESXi support)
- Redfish는 **stdlib만 사용** (urllib, ssl, json)

---

## 📁 파일 구조 (핵심)

```
server-exporter/ (프로젝트 루트)

1️⃣ 수집 채널 (3개)
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

2️⃣ 공통 로직 (Fragment 정규화)
   ├── common/library/
   │   └── precheck_bundle.py (4단계 진단: ping→port→protocol→auth)
   └── common/tasks/normalize/
       ├── init_fragments.yml (누적 변수 초기화)
       ├── merge_fragment.yml (Fragment 재귀 병합 엔진)
       ├── build_*.yml (10개: sections, status, errors, meta, correlation, output)
       └── supported_sections.yml, status_rules.yml

3️⃣ Adapter 시스템 (13개 YAML)
   ├── adapters/redfish/ (9개: generic + dell/hpe/lenovo/supermicro/cisco)
   ├── adapters/os/ (7개: linux_*/windows_*)
   └── adapters/esxi/ (4개: generic + 6x/7x/8x)

4️⃣ Schema & 데이터
   ├── schema/
   │   ├── sections.yml (10개: system, hardware, bmc, cpu, memory, storage, network, firmware, users, power)
   │   ├── field_dictionary.yml (18 Must + Nice + Skip)
   │   ├── baseline_v1/ (7개 벤더 baseline JSON)
   │   └── examples/ (success/partial/failed 예시)
   └── vault/ (linux.yml, windows.yml, esxi.yml, redfish/{vendor}.yml)

5️⃣ Python 플러그인 (12개)
   ├── callback_plugins/json_only.py (stdout callback, OUTPUT 태스크만 JSON)
   ├── lookup_plugins/adapter_loader.py (adapter 동적 선택)
   ├── filter_plugins/diagnosis_mapper.py, field_mapper.py
   └── module_utils/adapter_common.py (점수 계산, 벤더 정규화)

6️⃣ 테스트 (145개 Redfish fixture + 7개 baseline)
   ├── tests/redfish-probe/ (probe_redfish.py, deep_probe_redfish.py)
   ├── tests/fixtures/ (실장비 JSON 응답)
   ├── tests/evidence/ (Round 7-10 조건부 검토)
   └── tests/scripts/ (conditional_review.py, os_esxi_verify.sh)

7️⃣ 문서 (23개: 루트 4 + docs/ 19)
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
       ├── 15_variable-naming       — 변수 네이밍 사전
       ├── 16_os-esxi-mapping       — OS/ESXi 필드 매핑
       ├── 17_jenkins-pipeline      — Jenkins 파이프라인 런타임
       ├── 18_ansible-project-config — Ansible 프로젝트 설정
       └── 19_decision-log          — 의사결정 로그
```

---

## 🔌 ECC 활용 전략

### Python 부분 (100% ECC 지원)

**redfish_gather.py 개선:**
```bash
# TDD: 테스트 먼저 작성
/tdd "Redfish API 타임아웃 처리"

# 코드 품질 검사
/python-review

# 보안 취약점 검사
/security-review
```

**precheck_bundle.py 개선:**
```bash
/tdd "4단계 진단 중 protocol 단계 개선"
/python-review
```

### Ansible 플레이북 설계 (계획 수립)

**새 벤더 추가:**
```bash
# Step 1: 아키텍처 계획
/plan "Huawei Redfish 벤더 지원 추가"
# → 파일 구조, 단계별 구현, 테스트 계획 받음

# Step 2: Python 부분 (새 정규화 로직이 있으면)
/tdd "Huawei OEM 필드 정규화"
/python-review

# Step 3: Ansible YAML은 /plan 결과 참고해서 직접 작성
cat > adapters/redfish/huawei.yml << 'EOF'
adapter_id: huawei_redfish
channel: redfish
priority: 100
match:
  vendor: [huawei]
  firmware_patterns: ["BMC.*"]
capabilities:
  sections_supported: [...]
collect:
  strategy: standard+oem
  oem_tasks: redfish-gather/tasks/vendors/huawei/collect_oem.yml
normalize:
  oem_tasks: redfish-gather/tasks/vendors/huawei/normalize_oem.yml
EOF

# Step 4: OEM 태스크 작성
mkdir -p redfish-gather/tasks/vendors/huawei
cat > redfish-gather/tasks/vendors/huawei/collect_oem.yml << 'EOF'
---
- name: Huawei OEM 확장 수집
  ...
EOF
```

### 버그 수정 (TDD)

**Fragment 병합 엣지 케이스:**
```bash
# 1. 실패 테스트 작성
/tdd "Fragment 병합 - null값 처리"

# 2. 버그 수정
vim common/tasks/normalize/merge_fragment.yml

# 3. 코드 리뷰
/python-review

# 4. 커밋
git add .
git commit -m "fix: Fragment 병합 시 null값 재귀 처리"
```

### 통합 테스트

```bash
# 로컬 테스트 (실장비 아님)
ansible-playbook redfish-gather/site.yml \
  -i tests/inventory/local/ \
  -e "target_ip=10.x.x.1" \
  -e "target_type=redfish"

# Fixture 검증
python tests/redfish-probe/validate_fields.py \
  --fixture tests/fixtures/redfish/dell_r760/ \
  --schema schema/field_dictionary.yml
```

---

## 🔄 개발 워크플로우

### Daily Development

```bash
# 1. 프로젝트 진입
cd server-exporter/

# 2. 새 기능 계획
/plan "새 섹션 추가: Thermal 정보"

# 3. Python 부분 (TDD)
/tdd "Thermal 정보 파싱 로직"

# 4. Ansible YAML 작성 (gather + normalize)
vi redfish-gather/tasks/collect_thermal.yml
vi common/tasks/normalize/build_thermal.yml

# 5. Fragment 추가
vi common/tasks/normalize/init_fragments.yml
# → thermal: 섹션명 추가
# → _sections_thermal_fragment 초기화

# 6. Schema 업데이트
vi schema/sections.yml
# → thermal 섹션 추가
vi schema/fields/redfish.yml
# → thermal 필드 정의

# 7. 통합 테스트
ansible-playbook redfish-gather/site.yml -i tests/inventory/

# 8. 코드 리뷰
/python-review
/code-review

# 9. 커밋
git add .
git commit -m "feat: Thermal 정보 수집 추가

- redfish-gather: collect_thermal.yml 추가
- common: build_thermal.yml 추가
- schema: thermal 섹션 정의
- tests: thermal fixture 추가 (Dell R760)"
```

### Fragment 추가 체크리스트

- [ ] `gather_*.yml` 또는 `collect_*.yml` 작성 (raw 수집)
- [ ] Fragment 변수 생성
  - `_data_fragment`
  - `_sections_<name>_supported_fragment`
  - `_sections_<name>_collected_fragment` (선택)
  - `_errors_fragment` (실패 시)
- [ ] `normalize_*.yml` 또는 `common/tasks/normalize/build_*.yml` 작성
- [ ] `merge_fragment.yml` 호출 확인 (각 gather 후)
- [ ] `common/vars/supported_sections.yml` 업데이트
- [ ] `schema/sections.yml` + `schema/fields/*.yml` 추가
- [ ] Baseline JSON 예시 추가 (tests/fixtures 또는 examples)
- [ ] 문서 업데이트 (`docs/09_output-examples.md`)

---

## ⚠️ 주의사항 & Best Practices

### 🔴 Critical: Fragment 철학 지키기

❌ **WRONG** - 다른 gather의 fragment 수정:
```yaml
- name: 다른 섹션의 fragment 수정 (금지!)
  set_fact:
    _sections_memory_collected_fragment: [...]
```

✅ **CORRECT** - 자신의 fragment만:
```yaml
- name: 자신의 fragment 생성
  set_fact:
    _data_fragment:
      cpu: {...}
    _sections_cpu_collected_fragment: ['cpu']
```

### 🟡 High: Adapter 점수 계산

```
score = priority × 1000 + specificity × 10 + match_score
```

**점수 최적화:**
- 범용 (generic) → priority=0
- 기본 벤더 → priority=10
- 세대별 → priority=50-100
- 구체적 모델 → match.model_patterns + 높은 specificity

### 🟢 Medium: Vault 2단계 로딩

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

### 🔵 Low: OEM 확장 (선택)

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

## 🚀 Git 워크플로우

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

## 📊 3-채널 지원 현황

| 기능 | OS (Linux/Windows) | ESXi | Redfish |
|------|-------------------|------|---------|
| 구현 완료 | ✅ | ✅ | ✅ |
| Adapter 수 | 7개 | 4개 | 9개 |
| 지원 섹션 | 6개 | 6개 | 9개 |
| Precheck | ✅ 포트 감지 | ✅ 4단계 | ✅ 4단계 |
| Graceful Degradation | ✅ | ✅ | ✅ |
| 벤더 지원 | N/A | VMware | Dell, HPE, Lenovo, Supermicro, Cisco |
| 실장비 검증 | ✅ | ✅ (문서) | ✅ (3대: Dell/HPE/Lenovo) |

---

## 🛠️ 트러블슈팅

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
# Adapter 점수 계산 디버깅
ansible-debug-adapter:
  vars:
    debug_adapter: true
  tasks:
    - debug: var=_adapter_candidates
```

### Q3: Vault 로딩 실패
**원인:** 벤더명이 정규화되지 않음
**해결:**
```yaml
# vendor_aliases.yml 확인
cat common/vars/vendor_aliases.yml | grep "{{ detected_vendor }}"
```

---

## 📚 주요 문서

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

## 🎯 ECC 명령어 빠른 참조

```bash
# 계획 수립 (새 기능 추가)
/plan "새 벤더/섹션 추가"

# TDD (테스트 먼저)
/tdd "기능명"

# 코드 리뷰 (구현 후)
/python-review
/code-review

# 보안 검사
/security-review

# 문서 생성
/docs "주제"

# E2E 테스트
/e2e "시나리오"
```

---

## 📞 문의 & 개선

**기여 방식:**
1. 새 기능은 /plan으로 계획 수립
2. Python은 /tdd로 테스트부터
3. Ansible은 /code-review 후 병합
4. 문서는 /docs로 자동화

**해결된 제한사항 (Round 14):**
- ~~ESXi precheck이 block/rescue 내부~~ → precheck guard 추가로 조기 중단 구현 완료 (B3)
- ~~OEM 확장 경로 상수 참조~~ → 조사 결과 adapter config 기반 동적 로딩 이미 구현 완료 (C1)
- ~~Diagnosis 필드가 부분 적용~~ → OS(Linux/Windows) + ESXi 전채널 diagnosis 생성 완료 (B1)
- ESXi/Redfish host resolution bug → delegate_to: localhost 환경 대응 완료 (B5/B6)

**현재 알려진 제한사항:**
- ESXi 수집은 community.vmware 컬렉션 의존 (프로덕션 Agent에 설치 필요, 03_agent-setup.md §3 참조)
- OEM vendor task는 placeholder 상태 (Standard Redfish로 95%+ 커버, 향후 운영 요구 시 확장)

---

**프로젝트 성숙도: 🟢 프로덕션 준비 완료**

최종 커밋: `5321646` (2026-03-24) - Windows 정규화 + Round 7-10 evidence
