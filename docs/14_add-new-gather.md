# 14. 새 Gather 추가 방법

## 절차

### 1. 파일 생성

```bash
GATHER=ipmi
mkdir -p ${GATHER}-gather/tasks
cp os-gather/inventory.sh ${GATHER}-gather/inventory.sh
echo -e "---\nansible_user: CHANGE_ME\nansible_password: CHANGE_ME" > vault/${GATHER}.yml
# callback_plugins 복사 불필요 — ansible.cfg가 프로젝트 루트의 단일 사본을 참조
```

### 2. tasks/collect_standard.yml 작성 (수집)

```yaml
- name: "{gather} | collect raw data"
  your_module:
    host: "{{ _ip }}"
    username: "{{ ansible_user }}"
    password: "{{ ansible_password }}"
  register: _raw_collect
  failed_when: false
  no_log: true

- name: "{gather} | set collect status"
  set_fact:
    _collect_ok: "{{ _raw_collect is not failed }}"
```

### 3. tasks/normalize.yml 작성 (fragment 방식)

```yaml
- name: "{gather} | normalize | build fragment"
  set_fact:
    _data_fragment:
      hardware:
        vendor: "{{ _raw_collect.data.vendor | default(none) }}"
        model:  "{{ _raw_collect.data.model  | default(none) }}"
      cpu:
        sockets:         "{{ _raw_collect.data.sockets | default(none) }}"
        logical_threads: "{{ _raw_collect.data.threads | default(none) }}"
        model:           null
        cores_physical:  null
        architecture:    null
      memory:
        total_mb:     "{{ _raw_collect.data.mem_mb | default(none) }}"
        total_basis:  "physical_installed"
        installed_mb: "{{ _raw_collect.data.mem_mb | default(none) }}"
        visible_mb:   null
        free_mb:      null
        slots:        []
    _sections_supported_fragment: ['hardware','cpu','memory']
    _sections_collected_fragment: >-
      {{ ['hardware','cpu','memory'] if _collect_ok | bool else [] }}
    _sections_failed_fragment: >-
      {{ [] if _collect_ok | bool else ['hardware','cpu','memory'] }}
    _errors_fragment: []
  no_log: true

- include_tasks:
    file: "{{ lookup('env','REPO_ROOT') }}/common/tasks/normalize/merge_fragment.yml"
```

### 4. site.yml 작성

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
        - include_tasks:
            file: "{{ lookup('env','REPO_ROOT') }}/common/tasks/normalize/init_fragments.yml"
        - include_tasks: tasks/collect_standard.yml
        - include_tasks: tasks/normalize.yml
        - include_tasks:
            file: "{{ lookup('env','REPO_ROOT') }}/common/tasks/normalize/build_sections.yml"
        - include_tasks:
            file: "{{ lookup('env','REPO_ROOT') }}/common/tasks/normalize/build_status.yml"
        - include_tasks:
            file: "{{ lookup('env','REPO_ROOT') }}/common/tasks/normalize/build_errors.yml"
        - set_fact:
            _out_target_type:       "{gather}"
            _out_collection_method: "{gather}_api"
            _out_ip:                "{{ _ip }}"
            _out_vendor:            null
          no_log: true
        - include_tasks:
            file: "{{ lookup('env','REPO_ROOT') }}/common/tasks/normalize/build_output.yml"
        - set_fact:
            _output: "{{ _output | combine({'schema_version': '1'}) }}"
          no_log: true

      rescue:
        - set_fact:
            _out_target_type:       "{gather}"
            _out_collection_method: "{gather}_api"
            _out_ip:                "{{ _ip }}"
            _out_vendor:            null
            _fail_sec_supported:    ['hardware','cpu','memory']
            _fail_error_section:    "{gather}_gather"
            _fail_error_message:    "{{ ansible_failed_result.msg | default('수집 예외') }}"
          no_log: true
        - include_tasks:
            file: "{{ lookup('env','REPO_ROOT') }}/common/tasks/normalize/build_failed_output.yml"
        - set_fact:
            _output: "{{ _output | combine({'schema_version': '1'}) }}"
          no_log: true

      always:
        - name: OUTPUT
          debug: msg="{{ _output | to_json }}"
```

---

## 체크리스트

- [ ] `{gather}-gather/inventory.sh` — ip 만 처리
- [ ] `vault/{gather}.yml` — 계정 placeholder
- [ ] `tasks/collect_standard.yml` — `_raw_collect`, `_collect_ok`
- [ ] `tasks/normalize.yml` — fragment 생성 + `merge_fragment` 호출
- [ ] `site.yml` — `init_fragments` → collect → normalize → build_* → `schema_version` 주입
- [ ] `OUTPUT` 태스크 — `name: OUTPUT` 유지 (절대 변경 금지)
- [ ] `GUIDE_FOR_AI.md` — 섹션 지원 현황 표 업데이트

---

## 새 섹션 추가 (기존 gather 확장)

기존 gather 에 완전히 새로운 데이터가 필요할 때:

```yaml
# 새 tasks/gather_sensors.yml 추가 예시
- name: "linux | sensors | collect"
  shell: ...
  register: _raw_sensors

- name: "linux | sensors | build fragment"
  set_fact:
    _data_fragment:
      sensors:                         # 새 섹션 추가
        temperatures:
          - {name: CPU1, value_c: 48}
    _sections_supported_fragment: ['sensors']
    _sections_collected_fragment: ['sensors']
    _sections_failed_fragment:    []
    _errors_fragment:             []

- include_tasks: "{{ REPO_ROOT }}/common/tasks/normalize/merge_fragment.yml"
```

그 다음 `site.yml` 에 `include_tasks: tasks/linux/gather_sensors.yml` 한 줄 추가.
`build_sections.yml` 이 자동으로 `sensors: success` 를 생성한다.
