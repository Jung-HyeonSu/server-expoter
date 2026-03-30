# GUIDE FOR AI — server-exporter

이 파일과 repo 코드를 함께 AI 에 업로드하면,
AI 가 이 repo 의 컨벤션에 맞게 새 gather 를 생성하거나 기존 gather 를 수정한다.

---

## 이 Repo 의 역할

포털에 등록되기 전 서버의 하드웨어/OS 정보를 수집한다.
포털 → Jenkins → Ansible → 표준 JSON → 포털 흐름으로 동작한다.

---

## 제약 (변경 불가)

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
raw collect → normalize → fragment 생성 → merge_fragment.yml → build_* (공통) → OUTPUT
```

**새 수집 항목 추가 방법:**
1. 새 `gather_xxx.yml` 또는 `normalize_xxx.yml` 작성
2. 해당 fragment 변수 생성
3. `merge_fragment.yml` 호출
4. `site.yml` 에 `include_tasks` 한 줄 추가

`site.yml`, `build_output.yml` 전체를 수정할 필요가 없다.

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
  _rf_raw_collect       Redfish 모듈 직접 반환값
  _rf_d_system          raw 에서 추출한 system 데이터
  _rf_norm_interfaces   Redfish 정규화된 인터페이스 목록
  _l_norm_filesystems   Linux 정규화된 파일시스템
  _w_norm_users_list    Windows 정규화된 사용자 목록
  _e_facts_ok           ESXi facts 수집 성공 여부
  _rf_vendor            최종 확정 벤더 (null 허용)
  _output               최종 OUTPUT 변수 — 이름 변경 금지
```

### 채널별 변수 사전

#### OS 수집 변수

| 변수 | 설명 |
|------|------|
| `_l_python` | Linux Python 실행 경로 (preflight) |
| `_l_has_lsblk`, `_l_has_dmi`, `_l_has_last` | 명령 존재 여부 (preflight) |
| `_l_fb` | Linux raw fallback 파싱 결과 |

#### ESXi 수집 변수

| 변수 | 설명 |
|------|------|
| `_e_raw_facts` | vmware_host_facts 직접 반환값 |
| `_e_raw_config` | vmware_host_config_info 직접 반환값 |
| `_e_raw_ds` | vmware_datastore_info 직접 반환값 |
| `_e_facts_ok` | facts 수집 성공 여부 |
| `_e_config_ok` | config 수집 성공 여부 |
| `_e_ds_ok` | datastore 수집 성공 여부 |
| `_e_default_gw` | ESXi 기본 게이트웨이 |
| `_e_dns_servers` | ESXi DNS 서버 목록 |
| `_e_norm_interfaces` | 정규화된 인터페이스 |
| `_e_norm_datastores` | 정규화된 데이터스토어 |

#### Redfish 수집 변수

| 변수 | 설명 |
|------|------|
| `_rf_detected_vendor` | 1차 감지 벤더 ('unknown' 가능) |
| `_rf_vault_profile` | 실제 로딩된 vault 프로파일 |
| `_rf_raw_collect` | redfish_gather 모듈 전체 반환값 |
| `_rf_collect_ok` | 수집 성공 여부 |
| `_rf_vendor` | 최종 확정 벤더 (null 허용, "unknown" 금지) |
| `_rf_d_system` | 모듈 반환값에서 추출한 system raw |
| `_rf_d_bmc` | bmc raw |
| `_rf_d_procs` | processors raw |
| `_rf_d_memory` | memory raw |
| `_rf_d_storage` | storage raw |
| `_rf_d_network` | network raw |
| `_rf_norm_interfaces` | 정규화된 인터페이스 |
| `_rf_norm_gateways` | 집계된 default_gateways |
| `_rf_norm_controllers` | 정규화된 controllers |
| `_rf_norm_physical_disks` | controllers.drives 에서 추출 |

#### 최종 변수

| 변수 | 설명 |
|------|------|
| `_output` | 최종 표준 JSON — **이름 변경 절대 금지** |

---

## Null / 빈값 정책 및 금지 패턴

| 케이스 | 값 |
|-------|-----|
| 단일 값 누락 | `null` |
| 배열 없음 | `[]` |
| 섹션 not_supported | `null` |
| 빈 문자열 | **사용 금지** |
| vendor 불명 | `null` (문자열 `"unknown"` 금지) |

**추가 금지 패턴:**
- `_f`, `_d` 등 너무 짧은 변수명 금지 — 채널+단계+의미를 포함해야 한다
- `_raw` prefix 없이 모듈 반환값을 직접 저장하지 않는다

---

## 실패 처리 패턴 (block/rescue/always)

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

## 새 gather 추가 — site.yml 템플릿

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

---

## 참조 문서

| 주제 | 문서 |
|------|------|
| 스키마 / sections / status 규칙 | `docs/09_output-examples.md` |
| 아키텍처 / 정규화 흐름 | `docs/06_gather-structure.md`, `docs/07_normalize-flow.md` |
| Adapter 시스템 | `docs/10_adapter-system.md` |
| Pre-check 진단 | `docs/11_precheck-module.md` |
| 필드 매핑 | `docs/16_os-esxi-mapping.md` |
| Field Dictionary | `schema/field_dictionary.yml` |
