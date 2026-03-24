# GUIDE FOR AI — clovirone-portal

이 파일과 repo 코드를 함께 AI 에 업로드하면,
AI 가 이 repo 의 컨벤션에 맞게 새 gather 를 생성하거나 기존 gather 를 수정한다.

---

## 이 Repo 의 역할

포털에 등록되기 전 서버의 하드웨어/OS 정보를 수집한다.
포털 → Jenkins → Ansible → 표준 JSON → 포털 흐름으로 동작한다.

---

## 핵심 제약 (절대 변경 불가)

| 제약 | 값 |
|------|-----|
| 포털 입력 | `inventory_json = [{"ip":"10.x.x.1"}]` — ip 만 |
| 계정 관리 | vault 자동 로딩 (포털이 계정 전달 안 함) |
| OUTPUT 태스크명 | `name: OUTPUT` — callback plugin 캡처 기준 |
| schema_version | `"1"` 고정 |

---

## Fragment 기반 수집 철학

각 gather_*.yml / normalize_*.yml 은 전체 JSON 을 만들지 않는다.
자기 역할에 해당하는 fragment 만 생성하고, merge_fragment 를 호출한다.
공통 builder 가 fragment 들을 병합해 최종 JSON 을 만든다.

```
raw collect
→ normalize (gather별)
→ _data_fragment + _sections_*_fragment + _errors_fragment 생성
→ merge_fragment.yml 호출 (누적 병합)
→ build_sections / build_status / build_errors / build_output (공통)
→ schema_version 주입
→ OUTPUT
```

**새 수집 항목 추가 방법:**
1. 새 `gather_xxx.yml` 또는 `normalize_xxx.yml` 작성
2. 해당 fragment 변수 생성
3. `merge_fragment.yml` 호출
4. `site.yml` 에 `include_tasks` 한 줄 추가

`site.yml`, `build_output.yml` 전체를 수정할 필요가 없다.

---

## 전체 디렉터리 구조

```
clovirone-portal/
  common/
    tasks/normalize/
      init_fragments.yml       ← 누적 변수 초기화 (gather 시작 시 반드시 호출)
      merge_fragment.yml       ← fragment 누적 병합 엔진
      build_sections.yml       ← _all_sec_* → sections dict
      build_status.yml         ← sections 기반 status 계산
      build_errors.yml         ← _all_errors → 표준 errors
      build_output.yml         ← _out_* + _merged_data → _output
      build_failed_output.yml  ← 단일 호출 완전 실패 output
      build_empty_data.yml     ← 빈 data 뼈대 (_norm_empty_data)

  ansible.cfg                    ← 플러그인 경로, callback, forks 등 (프로젝트 필수)
  callback_plugins/json_only.py  ← stdout callback (ansible.cfg에서 단일 관리)

  os-gather/
    site.yml                   ← Play1:감지 Play2:Linux Play3:Windows
    inventory.sh
    tasks/
      linux/
        preflight.yml          ← Python 경로, 명령 존재 확인
        gather_system.yml      ← → system fragment
        gather_cpu.yml         ← → cpu fragment
        gather_memory.yml      ← → memory fragment (dmidecode)
        gather_storage.yml     ← → storage fragment (lsblk + mounts)
        gather_network.yml     ← → network fragment
        gather_users.yml       ← → users fragment (getent + lastlog 3단계)
      windows/
        gather_system / cpu / memory / storage / network / users
        (각각 → fragment → merge_fragment)
      normalize/
        build_output.yml       ← OS 전용 마무리 → common 호출

  esxi-gather/
    site.yml                   ← 1 Play
    tasks/
      collect_facts.yml        ← → _e_raw_facts
      collect_config.yml       ← → _e_raw_config
      collect_datastores.yml   ← → _e_raw_ds
      normalize_system.yml     ← → system/hardware/cpu/memory fragment
      normalize_network.yml    ← → network fragment
      normalize_storage.yml    ← → storage fragment

  redfish-gather/
    site.yml                   ← 1 Play (vendor adapter 포함)
    library/redfish_gather.py  ← 커스텀 모듈 (stdlib only, v4)
                                  detect_vendor() → (vendor, system_uri, manager_uri, chassis_uri, errors)
                                  gather_storage(): StorageControllers 인라인 + Controllers 서브링크 fallback
                                  gather_power(): chassis_uri 직접 수신 (ServiceRoot 중복 호출 제거)
                                  gather_system(): HostName 빈문자열→None, IndicatorLED→LocationIndicatorActive fallback,
                                                   MemorySummary Health→HealthRollup fallback, 누락 필드 경고 로깅
    tasks/
      detect_vendor.yml        ← → _rf_detected_vendor
      load_vault.yml           ← vault/redfish/{vendor}.yml
      collect_standard.yml     ← → _rf_raw_collect (표준 Redfish)
      normalize_standard.yml   ← → 표준 fragment (전 섹션)
      vendors/
        dell/
          collect_oem.yml      ← Dell OEM 수집 (placeholder)
          normalize_oem.yml    ← Dell OEM 정규화
        hpe / lenovo / supermicro / cisco (동일 구조)
```

---

## Fragment 변수 규칙

### 생성 변수 (각 gather/normalize task 가 set_fact 해야 하는 것)

```yaml
_data_fragment:               {}   # data 기여분 (없으면 {})
_sections_supported_fragment: []   # 이 task 가 지원하는 섹션
_sections_collected_fragment: []   # 수집 성공한 섹션
_sections_failed_fragment:    []   # 수집 실패한 섹션
_errors_fragment:             []   # errors
```

### 누적 변수 (merge_fragment.yml 이 관리)

```
_merged_data       ← data 재귀 병합 결과
_all_sec_supported ← 지원 섹션 누적
_all_sec_collected ← 수집 성공 누적
_all_sec_failed    ← 수집 실패 누적
_all_errors        ← errors 누적
```

### 공통 builder 입력 변수

```
_out_target_type, _out_collection_method, _out_ip, _out_vendor
→ build_output.yml 호출 전 set_fact
```

### 실패 전용 변수

```
_fail_sec_supported   ← 이 gather 가 지원하는 섹션 목록
_fail_error_section   ← 에러 섹션명
_fail_error_message   ← 에러 메시지
→ build_failed_output.yml 호출 전 set_fact
```

---

## 변수 네이밍 컨벤션

```
_{채널}_{단계}_{의미}

채널: rf(Redfish) e(ESXi) l(Linux) w(Windows)
단계: raw(수집 직후) d(raw 하위 추출) norm(정규화) ok(bool)

예:
  _e_raw_facts          ESXi vmware_host_facts 직접 반환값
  _e_raw_config         ESXi vmware_host_config_info 직접 반환값
  _rf_raw_collect       Redfish 모듈 직접 반환값
  _rf_d_system          raw 에서 추출한 system 데이터
  _rf_norm_interfaces   Redfish 정규화된 인터페이스 목록
  _e_norm_interfaces    ESXi 정규화된 인터페이스
  _l_norm_filesystems   Linux 정규화된 파일시스템
  _l_norm_interfaces    Linux 정규화된 인터페이스
  _l_norm_users_list    Linux 정규화된 사용자 목록
  _w_norm_filesystems   Windows 정규화된 파일시스템
  _w_norm_interfaces    Windows 정규화된 인터페이스
  _w_norm_users_list    Windows 정규화된 사용자 목록
  _e_facts_ok           ESXi facts 수집 성공 여부
  _rf_vendor            최종 확정 벤더 (null 허용)
  _output               최종 OUTPUT 변수 — 이름 변경 금지
```

---

## 표준 JSON 스키마

### 최상위 구조

```json
{
  "schema_version": "1",
  "target_type":       "os | esxi | redfish",
  "collection_method": "agent | vsphere_api | redfish_api",
  "ip":       "10.x.x.1",
  "hostname": "10.x.x.1",
  "vendor":   "dell | hpe | lenovo | supermicro | cisco | null",
  "status":   "success | partial | failed",
  "sections": {
    "system":   "success | failed | not_supported",
    "hardware": "...", "bmc": "...", "cpu": "...", "memory": "...",
    "storage":  "...", "network": "...", "firmware": "...", "users": "..."
  },
  "errors": [{"section":"...","message":"...","detail":null}],
  "data": { ... }
}
```

### sections 판정 규칙

| 조건 | 값 |
|------|-----|
| `_all_sec_supported` 에 없음 | `not_supported` |
| supported + `_all_sec_failed` 에 있음 | `failed` |
| supported + `_all_sec_collected` 에 있음 | `success` |
| supported 이지만 neither | `failed` |

### status 판정 규칙

| 조건 | status |
|------|--------|
| supported 섹션 모두 success | `success` |
| success + failed 혼재 | `partial` |
| success 가 하나도 없음 | `failed` |

### gather 타입별 섹션 지원 현황

| 섹션 | os | esxi | redfish |
|------|-----|------|---------|
| system | ✅ | ✅ VMware | ✅ |
| hardware | ❌ | ✅ | ✅ |
| bmc | ❌ | ❌ | ✅ |
| cpu | ✅ | ✅ | ✅ |
| memory | ✅ | ✅ | ✅ |
| storage | ✅ | ✅ datastores | ✅ physical |
| network | ✅ | ✅ vmkernel | ✅ server_nic |
| users | ✅ | ❌ | ❌ |
| firmware | ❌ | ❌ | ✅ |
| power | ❌ | ❌ | ✅ |

### memory.total_basis

| 값 | 의미 |
|----|------|
| `physical_installed` | dmidecode / Win32_Physical / Redfish DIMM |
| `os_visible` | OS 인식 메모리 fallback |
| `hypervisor_visible` | ESXi 하이퍼바이저 인식 |

### network.interfaces[].kind

| 값 | 의미 |
|----|------|
| `os_nic` | Linux/Windows OS NIC |
| `vmkernel` | ESXi VMkernel |
| `server_nic` | Redfish 서버 물리 NIC |

---

## Null / 빈값 정책

| 케이스 | 값 |
|-------|-----|
| 단일 값 누락 | `null` |
| 배열 없음 | `[]` |
| 섹션 not_supported | `null` |
| 빈 문자열 | **사용 금지** |
| vendor 불명 | `null` (문자열 `"unknown"` 금지) |

---

## 실패 처리 패턴

```yaml
block:
  - include_tasks: common/tasks/normalize/init_fragments.yml
  - include_tasks: tasks/gather_*.yml  # 각자 fragment 생성
  - include_tasks: tasks/normalize_*.yml
  - include_tasks: common/tasks/normalize/build_sections.yml
  - include_tasks: common/tasks/normalize/build_status.yml
  - include_tasks: common/tasks/normalize/build_errors.yml
  - set_fact: _out_target_type/method/ip/vendor
  - include_tasks: common/tasks/normalize/build_output.yml
  - set_fact: _output="{{ _output | combine({'schema_version':'1'}) }}"

rescue:
  - set_fact:
      _out_target_type: "..."
      _out_collection_method: "..."
      _out_ip: "{{ _ip }}"
      _out_vendor: null
      _fail_sec_supported: [...]
      _fail_error_section: "gather_name"
      _fail_error_message: "{{ ansible_failed_result.msg | default('수집 예외') }}"
  - include_tasks: common/tasks/normalize/build_failed_output.yml
  - set_fact: _output="{{ _output | combine({'schema_version':'1'}) }}"

always:
  - name: OUTPUT
    debug: msg="{{ _output | to_json }}"
```

---

## Adapter 시스템 (Phase 2 추가)

벤더/세대/OS 확장 시 YAML 파일 추가만으로 지원 가능합니다.
자세한 내용은 `docs/18_adapter-system.md` 참조.

```
adapters/
  redfish/                     # 벤더별/세대별 adapter YAML (13개)
    redfish_generic.yml        # fallback (priority: 0)
    redfish_dell_idrac.yml     # Dell 기본 (priority: 10)
    redfish_dell_idrac9.yml    # iDRAC 9 (priority: 100)
    redfish_hpe_ilo.yml        # HPE 기본 (priority: 10)
    redfish_hpe_ilo5.yml       # iLO 5 (priority: 100)
    redfish_hpe_ilo6.yml       # iLO 6 Gen11 (priority: 100)
    redfish_lenovo_xcc.yml     # Lenovo XCC (priority: 100)
    ...
  os/                          # OS 배포판별 adapter
  esxi/                        # ESXi 버전별 adapter

module_utils/adapter_common.py   # 벤더 정규화, match, score 계산
lookup_plugins/adapter_loader.py # Ansible lookup (adapter 스캔+선택)
common/vars/vendor_aliases.yml   # 벤더명 정규화 매핑
```

**새 벤더 추가:**
1. `common/vars/vendor_aliases.yml`에 매핑 추가
2. `adapters/redfish/{벤더}.yml` 생성
3. (선택) `tasks/vendors/{벤더}/` 에 OEM 태스크 추가
4. **site.yml 수정 불필요**

## Pre-check 진단 (Phase 1 추가)

수집 전 4단계 연결 진단: ping → port → protocol → auth.
자세한 내용은 `docs/19_precheck-module.md` 참조.

```
common/library/precheck_bundle.py        # 커스텀 모듈
common/tasks/precheck/run_precheck.yml   # 호출 태스크
filter_plugins/diagnosis_mapper.py       # 결과 변환 필터
```

## 실장비 검증 기반 참고 문서 (2026-03-18)

| 문서 | 내용 |
|------|------|
| `docs/21_redfish-live-validation.md` | 3대 실장비(Dell/HPE/Lenovo) Redfish API 직접 검증 결과 |
| `docs/22_adapter-matrix.md` | 13개 adapter 비교표 + 실장비 매칭 결과 |
| `docs/23_decision-log.md` | 설계 의사결정 로그 |
| `docs/24_refactor-checklist.md` | 리팩토링 체크리스트 (P0 완료, P1 일부 완료, P2 보류) |
| `docs/25_ansible-runtime-requirements.md` | Ansible 실행환경 요구사항 |
| `docs/26_jenkins-runtime-requirements.md` | Jenkins 런타임 요구사항 |
| `tests/fixtures/redfish/` | 실장비 Redfish 응답 145개 JSON fixture |

## Redfish Safe Common 5 필드 (확정)

모든 지원 벤더(dell, hpe, lenovo, supermicro, cisco)에서 일관되게 수집 가능한 필드:

| 필드 | 위치 | 타입 | 설명 |
|------|------|------|------|
| `health` | `hardware` | string\|null | 시스템 Health — OK/Warning/Critical |
| `power_state` | `hardware` | string\|null | 전원 상태 — On/Off/PoweringOn/PoweringOff |
| `serial` | `physical_disks[]` | string\|null | 디스크 시리얼 번호 |
| `failure_predicted` | `physical_disks[]` | boolean\|null | SMART 기반 고장 예측 |
| `predicted_life_percent` | `physical_disks[]` | integer\|null | 예상 수명 (0-100) |

**디스크 필터 정책**:
- CapacityBytes == 0 → 드라이브 skip (FlexFlash, Empty Bay)
- Name에 "empty" 포함 → 드라이브 skip
- HPE PredictedMediaLifeLeftPercent float → int() 변환

**Conditional 필드 (보류)**: 아래 필드는 벤더 간 일관성 미확보로 스키마 반영 보류.
- PowerConsumedWatts, PowerCapacityWatts, PowerMetrics.*
- Proc.MaxSpeedMHz, System.SKU, PSU.Health, NIC.LinkStatus

**필드 설명 사전**: 각 필드의 상세 의미, null 해석, 채널 간 차이 →
`schema/field_dictionary.yml` 참조. 포털에서 필드명 기반 help_ko/help_en lookup으로 사용.

## Output JSON 신규 필드 (Phase 3 추가)

기존 필드 변경 없이 3개 필드 추가. `docs/20_diagnosis-output.md` 참조.
- `diagnosis` — 실패 원인 진단 (failure_stage, failure_reason)
- `meta` — 수집 메타데이터 (adapter_id, duration_ms)
- `correlation` — 다중 채널 결과 연결 키 (serial_number, system_uuid)

## Redfish vendor adapter 구조

```
redfish-gather/tasks/vendors/{dell|hpe|lenovo|supermicro|cisco}/
  collect_oem.yml    ← OEM 전용 추가 수집 → fragment 생성 → merge_fragment
  normalize_oem.yml  ← OEM 수집 결과 정규화

원칙:
  - 표준 스키마 섹션 내 하위 필드로 확장 우선
  - 예: hardware.oem_dell, hardware.oem_hpe
  - 새 최상위 섹션은 완전히 새로운 개념일 때만 추가
  - 항상 fragment 방식 유지
```

---

## 새 gather 추가 방법

### 1. 파일 준비

```bash
GATHER=ipmi
mkdir -p ${GATHER}-gather/tasks
cp os-gather/inventory.sh ${GATHER}-gather/inventory.sh
touch vault/${GATHER}.yml
# callback_plugins 복사 불필요 — ansible.cfg가 중앙 ./callback_plugins/ 참조
```

### 2. 필수 태스크 패턴

```yaml
# tasks/collect_standard.yml
- name: "collect raw data"
  your_module:
    host: "{{ _ip }}"
    username: "{{ ansible_user }}"
    password: "{{ ansible_password }}"
  register: _raw_collect
  failed_when: false
  no_log: true

- name: "set collect status"
  set_fact:
    _collect_ok: "{{ _raw_collect is not failed }}"

# tasks/normalize.yml — fragment 방식
- name: "normalize | build fragment"
  set_fact:
    _data_fragment:
      hardware:
        vendor: "{{ _raw_collect.data.vendor | default(none) }}"
    _sections_supported_fragment: ['hardware','cpu','memory']
    _sections_collected_fragment: >-
      {{ ['hardware','cpu','memory'] if _collect_ok | bool else [] }}
    _sections_failed_fragment: >-
      {{ [] if _collect_ok | bool else ['hardware','cpu','memory'] }}
    _errors_fragment: []

- include_tasks:
    file: "{{ lookup('env','REPO_ROOT') }}/common/tasks/normalize/merge_fragment.yml"
```

### 3. site.yml 템플릿

```yaml
- name: "{gather}-gather"
  hosts: all
  gather_facts: no
  connection: local
  vars_files:
    - "{{ lookup('env','REPO_ROOT') }}/vault/{gather}.yml"
  vars:
    _ip: "{{ ansible_host | default(inventory_hostname) }}"
  tasks:
    - name: "{gather} | gather"
      block:
        - include_tasks: file="{{ REPO_ROOT }}/common/tasks/normalize/init_fragments.yml"
        - include_tasks: tasks/collect_standard.yml
        - include_tasks: tasks/normalize.yml
        - include_tasks: file="{{ REPO_ROOT }}/common/tasks/normalize/build_sections.yml"
        - include_tasks: file="{{ REPO_ROOT }}/common/tasks/normalize/build_status.yml"
        - include_tasks: file="{{ REPO_ROOT }}/common/tasks/normalize/build_errors.yml"
        - set_fact:
            _out_target_type: "{gather}"
            _out_collection_method: "{gather}_api"
            _out_ip: "{{ _ip }}"
            _out_vendor: null
        - include_tasks: file="{{ REPO_ROOT }}/common/tasks/normalize/build_output.yml"
        - set_fact: _output="{{ _output | combine({'schema_version':'1'}) }}"
      rescue:
        - set_fact:
            _out_target_type: "{gather}"
            _out_collection_method: "{gather}_api"
            _out_ip: "{{ _ip }}"
            _out_vendor: null
            _fail_sec_supported: ['hardware','cpu','memory']
            _fail_error_section: "{gather}_gather"
            _fail_error_message: "{{ ansible_failed_result.msg | default('수집 예외') }}"
        - include_tasks: file="{{ REPO_ROOT }}/common/tasks/normalize/build_failed_output.yml"
        - set_fact: _output="{{ _output | combine({'schema_version':'1'}) }}"
      always:
        - name: OUTPUT
          debug: msg="{{ _output | to_json }}"
```

### 4. AI 요청 예시

```
이 repo 코드와 GUIDE_FOR_AI.md 를 참고해서 ipmi-gather 를 새로 만들어줘.

조건:
- inventory_json = [{"ip":"10.x.x.1"}] 형식
- vault/ipmi.yml 에서 계정 로딩
- ipmitool 기반 수집 (tasks/collect_standard.yml)
- 지원 섹션: hardware, cpu, memory, power
- 미지원 섹션: system, bmc, storage, network, firmware, users
- fragment 방식 + common builder 사용
- block/rescue/always + build_failed_output
- schema_version: "1" 포함
```
