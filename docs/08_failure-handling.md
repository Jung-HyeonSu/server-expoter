# 08. 실패해도 같은 모양의 JSON 을 돌려준다

## 핵심 약속

수집이 어떻게 실패하든 — 네트워크가 막혀도, 인증이 거부돼도, 대상 서버에서 명령이 죽어도 — **호출자는 항상 같은 모양의 JSON envelope** 를 받는다.

빈 응답이 가는 일은 없다. Ansible 의 raw 에러 메시지가 그대로 흘러나가는 일도 없다.

이 약속이 깨지면 호출자 코드가 매번 "응답이 JSON 인지", "필드가 있는지" 부터 확인해야 해서 신뢰가 무너진다.

---

## 1. 어떻게 약속을 지키나 — block / rescue / always

각 채널의 site.yml 은 다음 구조로 감싸져 있다.

```yaml
block:
  # ── 정상 경로 ──
  - include_tasks: common/init_fragments.yml      # 빈 보고서 준비
  - include_tasks: tasks/collect_*.yml            # 수집 (fragment 생성)
  - include_tasks: tasks/normalize_*.yml          # 정규화 (fragment 생성)
  - include_tasks: common/build_sections.yml
  - include_tasks: common/build_status.yml
  - include_tasks: common/build_errors.yml
  - include_tasks: common/build_meta.yml
  - include_tasks: common/build_correlation.yml
  - include_tasks: common/build_output.yml
  - set_fact: _output="{{ _output | combine({'schema_version':'1'}) }}"

rescue:
  # ── block 안에서 예외 발생 시 ──
  - set_fact:
      _fail_sec_supported: [ ... ]                # 이 gather 가 원래 다룰 섹션
      _fail_error_section: "<gather 이름>"
      _fail_error_message: "{{ ansible_failed_result.msg | default('수집 예외') }}"
  - include_tasks: common/build_failed_output.yml # status=failed envelope 생성
  - set_fact: _output="{{ _output | combine({'schema_version':'1'}) }}"

always:
  # ── 무슨 일이 있어도 마지막에 실행 ──
  - name: "OUTPUT: <channel>"
    debug:
      msg: "{{ _output | to_json }}"
```

핵심은 `always` 블록의 OUTPUT 태스크다. block 이 끝까지 갔든, rescue 로 빠졌든 **반드시 한 번** 실행된다. callback plugin (`json_only.py`) 이 이 태스크의 msg 만 stdout 으로 흘려보낸다.

---

## 2. 실패 유형별 처리

### (가) 연결 / 인증 실패 (unreachable)

Ansible 의 `block / rescue` 는 unreachable 예외를 자동으로 잡지 못한다. 그래서 각 gather 가 자기 수집 성공 여부를 `_*_ok` 변수로 체크하고, 실패 시 `fail` 모듈로 일부러 예외를 일으켜 rescue 로 보낸다.

```yaml
- name: facts 수집 실패 시 rescue 로 진입
  ansible.builtin.fail:
    msg: "ESXi facts 수집 실패 — 연결 또는 인증 문제"
  when: not (_e_facts_ok | bool)
```

### (나) 부분 수집 실패 (partial)

일부 섹션만 못 가져오는 케이스. `failed_when: false` 로 감싸서 실패해도 진행한 뒤, normalize 단계에서 fragment 의 `_sections_failed_fragment` 에 기록한다.

```yaml
_sections_failed_fragment: >-
  {{ [] if _e_ds_ok | bool else ['storage'] }}
```

merge → build_sections → build_status 가 자동으로 `partial` 을 계산한다 (`docs/07`).

### (다) 예외 발생 → rescue

block 안에서 처리 못 한 예외가 터지면 rescue 가 받는다. 이때 `build_failed_output.yml` 한 번 호출로 envelope 13 필드를 모두 채운 failed 응답을 만든다.

```yaml
rescue:
  - set_fact:
      _fail_sec_supported: ['system','hardware','cpu','memory','storage','network']
      _fail_error_section: "esxi_gather"
      _fail_error_message: "{{ ansible_failed_result.msg | default('ESXi 수집 예외') }}"
  - include_tasks: common/build_failed_output.yml
  # → status=failed, 모든 supported 섹션이 failed, empty data 가 자동 생성됨
```

---

## 3. `status` 가 정해지는 4가지 시나리오

자세한 사례는 `docs/20_json-schema-fields.md` 4절. 한 줄 정리:

| 어떤 상황 | `status` |
|---|---|
| 모든 지원 섹션 수집 성공 | `success` |
| 일부 섹션은 성공, 일부는 실패 | `partial` |
| 한 섹션도 못 건짐 | `failed` |
| rescue 로 빠짐 (예외 발생) | `failed` |

`build_status.yml` 이 자동 계산한다.

---

## 4. failed 응답 — 실제 모양

ESXi 채널이 인증 실패로 rescue 진입한 케이스.

```json
{
  "schema_version":   "1",
  "target_type":      "esxi",
  "collection_method":"vsphere_api",
  "ip":               "10.x.x.10",
  "hostname":         "10.x.x.10",
  "vendor":           null,

  "status":           "failed",
  "sections": {
    "system":   "failed",  "hardware": "failed",
    "bmc":      "not_supported",
    "cpu":      "failed",  "memory":   "failed",
    "storage":  "failed",  "network":  "failed",
    "firmware": "not_supported",
    "users":    "not_supported",
    "power":    "not_supported"
  },

  "diagnosis": { "auth_success": false, "failure_stage": "auth", ... },
  "meta":        { "duration_ms": 2400, "adapter_id": "esxi_generic" },
  "correlation": { "host_ip": "10.x.x.10" },

  "errors": [
    { "section": "esxi_gather",
      "message": "vmware_host_facts 수집 실패",
      "detail":  null }
  ],

  "data": {
    "system":   null, "hardware": null, "bmc": null,
    "cpu":      null, "memory":   null,
    "storage":  { "filesystems": [], "physical_disks": [], "datastores": [], "controllers": [] },
    "network":  { "dns_servers": [], "default_gateways": [], "interfaces": [] },
    "users":    [],
    "firmware": [],
    "power":    null
  }
}
```

failed 케이스라도 envelope 13 필드를 모두 갖춘다. `data.*` 는 빈 값이지만 키 자체는 존재한다 — 호출자가 `response["data"]["cpu"]` 로 접근해도 KeyError 가 안 난다.

---

## 5. 호출자가 어떻게 분기해야 하나

```python
# 좋은 분기 패턴
status = response["status"]

if status == "failed":
    # 수집 자체 실패 — data 무시, 원인 파악
    stage = response["diagnosis"]["failure_stage"]
    notify_ops(f"수집 실패 ({stage}): {response['errors']}")

elif status == "partial":
    # 일부 섹션만 사용
    for sec, sec_status in response["sections"].items():
        if sec_status == "success":
            process(sec, response["data"][sec])

else:  # status == "success"
    # 모든 지원 섹션 사용 — 단, errors[] 가 비어있지 않으면 장비 자체에 문제 있음
    process_all(response["data"])
    if response["errors"]:
        log_hardware_warnings(response["errors"])
```

핵심:
- **`status` 로 분기.** `errors` 만 보고 분기하면 success 케이스에도 알람 발생.
- **`data` 는 필드 키가 항상 존재.** null 또는 빈 컬렉션 처리만 하면 됨.

---

## 6. 자주 헷갈리는 점

**Q. `status: success` 인데 `errors[]` 가 비어있지 않다. 버그인가?**
정상이다. **수집은 성공했는데** 도중에 본 비정상 신호 (PSU fault / SMART warning 등) 가 errors[] 에 기록된다. 알람을 errors 로만 띄우면 정상 케이스에도 시끄러워진다.

**Q. `status: failed` 인데 일부 섹션이 `success` 다.**
이론적으로는 안 일어나야 하는데, 만약 발생하면 회귀 버그다. `schema/baseline_v1` 회귀가 잡는다.

**Q. envelope 의 `data.*` 가 모두 null 인데 status 는 success?**
모든 섹션이 `not_supported` 인 케이스 (빈 inventory 같은 극단). 거의 안 일어나지만 envelope 일관성을 위해 허용된다.

---

## 7. 더 보고 싶을 때

| 보고 싶은 것 | 파일 |
|---|---|
| envelope 13 필드 사전 | `docs/20_json-schema-fields.md` |
| success / partial / failed / not_supported 4가지 응답 예시 | `docs/09_output-examples.md` |
| precheck 4단계 결과 해석 | `docs/11_precheck-module.md` |
| diagnosis / meta / correlation 상세 | `docs/12_diagnosis-output.md` |
| Fragment 누적 과정 | `docs/07_normalize-flow.md` |
