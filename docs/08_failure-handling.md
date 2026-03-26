# 08. 실패 처리 원칙

## 원칙

어떤 상황에서도 `OUTPUT` 태스크가 반드시 실행되어야 한다.
포털은 항상 `schema_version: "1"` 이 포함된 JSON 을 받아야 한다.

---

## 구조

```yaml
block:
  - include_tasks: common/init_fragments.yml    ← 반드시 첫 번째
  - include_tasks: tasks/collect_*.yml          ← 수집 (fragment 생성)
  - include_tasks: tasks/normalize_*.yml        ← 정규화 (fragment 생성)
  - include_tasks: common/build_sections.yml
  - include_tasks: common/build_status.yml
  - include_tasks: common/build_errors.yml
  - set_fact: _out_target_type / method / ip / vendor
  - include_tasks: common/build_meta.yml
  - include_tasks: common/build_correlation.yml
  - include_tasks: common/build_output.yml
  - set_fact: _output="{{ _output | combine({'schema_version':'1'}) }}"

rescue:
  - set_fact:
      _out_target_type:    "..."
      _out_collection_method: "..."
      _out_ip:             "{{ _ip }}"
      _out_vendor:         null
      _fail_sec_supported: [...]   ← 이 gather 가 지원하는 섹션
      _fail_error_section: "gather_name"
      _fail_error_message: "{{ ansible_failed_result.msg | default('수집 예외') }}"
  - include_tasks: common/build_failed_output.yml
  - set_fact: _output="{{ _output | combine({'schema_version':'1'}) }}"

always:
  - name: OUTPUT           ← 항상 실행
    debug: msg="{{ _output | to_json }}"
```

---

## status 판정 (build_status.yml 자동 계산)

| 조건 | status |
|------|--------|
| supported 섹션 모두 success | `success` |
| success + failed 혼재 | `partial` |
| success 가 하나도 없음 | `failed` |
| rescue 진입 | `failed` (build_failed_output.yml) |

---

## 실패 유형별 처리

### 연결/인증 실패 (unreachable)

Ansible `block/rescue` 는 unreachable 을 잡지 못한다.
각 gather 는 수집 성공 여부를 `_*_ok` 변수로 체크하고,
핵심 수집 실패 시 `ansible.builtin.fail` 로 rescue 로 진입시킨다.

```yaml
- name: "abort if facts failed"
  ansible.builtin.fail:
    msg: "수집 실패 — 연결 또는 인증 문제"
  when: not (_e_facts_ok | bool)
```

### 부분 수집 실패 (partial)

`failed_when: false` 로 감싼 태스크는 실패해도 계속 진행한다.
각 normalize 태스크는 `_*_ok` 변수 기반으로 fragment 의
`_sections_failed_fragment` 를 설정한다.

```yaml
_sections_failed_fragment: >-
  {{ [] if _e_ds_ok | bool else ['storage'] }}
```

`merge_fragment` → `build_sections` → `build_status` 가
자동으로 `partial` 을 계산한다.

### rescue 진입 시 — build_failed_output.yml 단일 호출

```yaml
rescue:
  - set_fact:
      _fail_sec_supported: ['system','hardware','cpu','memory','storage','network']
      _fail_error_section: "esxi_gather"
      _fail_error_message: "{{ ansible_failed_result.msg | default('ESXi 수집 예외') }}"
      # + _out_target_type / method / ip / vendor
  - include_tasks: common/build_failed_output.yml
  # → status=failed, 모든 supported=failed, empty data 자동 생성
```

---

## failed 출력 예시

```json
{
  "schema_version": "1",
  "target_type": "esxi",
  "collection_method": "vsphere_api",
  "ip": "10.x.x.10",
  "hostname": "10.x.x.10",
  "vendor": null,
  "status": "failed",
  "sections": {
    "system":   "failed",  "hardware": "failed",
    "bmc":      "not_supported",
    "cpu":      "failed",  "memory":   "failed",
    "storage":  "failed",  "network":  "failed",
    "firmware": "not_supported",
    "users":    "not_supported"
  },
  "errors": [
    {"section":"esxi_gather","message":"vmware_host_facts 수집 실패","detail":null}
  ],
  "data": {
    "system":null,"hardware":null,"bmc":null,"cpu":null,"memory":null,
    "storage":{"filesystems":[],"physical_disks":[],"datastores":[],"controllers":[]},
    "network":{"dns_servers":[],"default_gateways":[],"interfaces":[]},
    "users":[],"firmware":[],"power":null
  }
}
```
