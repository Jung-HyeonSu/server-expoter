# 11. 진단 4단계 — 어디서 막혔는지 한눈에 보기

## 왜 진단을 따로 하나

수집이 실패했을 때 사람들이 가장 먼저 묻는 건 "**왜 실패했어?**" 다. "그냥 안 됐어" 로는 조치가 불가능하다.

server-exporter 는 본 수집에 들어가기 전에 4단계 사전 진단을 돌려서, 실패 시 **어느 단계에서 막혔는지** 까지 같이 돌려준다.

세 가지 이점이 있다.

1. 운영자가 **즉시 어디를 손볼지** 안다 (방화벽? 비밀번호? 펌웨어?).
2. 의미 없는 timeout 이 누적되지 않는다 (port 막혔는데 인증 시도하지 않음).
3. 수집 결과 envelope 의 `diagnosis` 필드가 풍부해서 호출자가 자동 분기 가능.

---

## 1. 4단계 — 위에서 아래로 차례로

```
[ 단계 1 ]  reachable      ─→ 호스트 자체에 닿는가? (TCP 응답)
              │
              │ OK
              ▼
[ 단계 2 ]  port_open      ─→ 채널 별 포트가 열렸는가? (Redfish=443, SSH=22, WinRM=5986, vSphere=443)
              │
              │ OK
              ▼
[ 단계 3 ]  protocol       ─→ 응답 형식이 맞는가? (HTTPS handshake / SSH banner / Redfish JSON)
              │
              │ OK
              ▼
[ 단계 4 ]  auth_success   ─→ 자격증명이 통과하는가?
              │
              │ OK
              ▼
       ┌─────────────┐
       │  본 수집 시작  │
       └─────────────┘
```

> 실제로 단계 1+2 는 **TCP connect 한 번**으로 합쳐서 처리한다. ping ICMP 가 차단된 환경이 흔해서 TCP 응답 자체로 reachable 까지 동시 판정.
> 호스트는 살아있는데 서비스 포트가 닫혀있으면 `failure_stage="reachable"` 로 보고한다.

각 단계가 막히면 **그 다음 단계는 건너뛰고** `failure_stage` / `failure_reason` 을 envelope 에 담아 반환한다.

---

## 2. 진단 결과 — 정상이면 이렇게 생김

```json
"diagnosis": {
  "reachable":          true,
  "port_open":          true,
  "protocol_supported": true,
  "auth_success":       true,

  "failure_stage":      null,    // 막힌 단계 이름. 정상이면 null.
  "failure_reason":     null,    // 사람이 읽을 사유. 정상이면 null.

  "details": {                   // precheck / probe 단계에서 알아낸 부가 정보 (probe_facts 병합)
    "channel":           "redfish",
    "adapter_candidate": "redfish_dell_idrac9",
    "checked_ports":     [443],
    "selected_port":     443,
    "redfish_version":   "1.6.0",
    "product":           "Integrated Dell Remote Access Controller",
    "systems_uri":       "/redfish/v1/Systems"
  }
}
```

읽는 법: 4개 boolean 이 모두 `true` 이고 `failure_stage` 가 `null` 이면 정상.

---

## 3. 실패하면 이렇게 생김

### 예시 가) 포트가 막힘

```json
{
  "reachable":          true,
  "port_open":          false,    ← 여기서 false
  "protocol_supported": false,    ← 막혔으니 false 로 표기 (시도 안 함)
  "auth_success":       false,
  "failure_stage":      "reachable",
  "failure_reason":     "TCP 443 connection refused"
}
```

조치 방향: 방화벽 규칙 / BMC 서비스 기동 / 포트 번호 오설정 점검.

### 예시 나) 포트는 열렸는데 응답이 이상함

```json
{
  "reachable":          true,
  "port_open":          true,
  "protocol_supported": false,    ← 여기서 false
  "auth_success":       false,
  "failure_stage":      "protocol",
  "failure_reason":     "Redfish ServiceRoot (/redfish/v1/) 응답 없음"
}
```

조치 방향: TLS 버전 / cipher 호환성 / 펌웨어 버그 / 구형 BMC (Redfish 미지원) 가능성.

### 예시 다) 인증 실패

```json
{
  "reachable":          true,
  "port_open":          true,
  "protocol_supported": true,
  "auth_success":       false,    ← 여기서 false
  "failure_stage":      "auth",
  "failure_reason":     "401 Unauthorized"
}
```

조치 방향: 비밀번호 회전 / 계정 잠김 / 권한 부족 / vault 자격증명 stale.

---

## 4. 채널별 차이

| 채널 | 포트 | protocol 단계에서 보는 것 | auth 단계에서 쓰는 것 |
|---|:---:|---|---|
| Redfish | 443 | `GET /redfish/v1/` (ServiceRoot) | Basic Auth |
| OS (Linux) | 22 | SSH banner | SSH 로그인 |
| OS (Windows) | 5986 (또는 5985) | WinRM HTTPS handshake | NTLM |
| ESXi | 443 | `GET /sdk` (vSphere SOAP entry) | vSphere API |

각 채널이 자기 프로토콜에 맞춰 단계 3·4 를 수행한다. 단계 1·2 는 동일 (TCP connect).

---

## 5. 사용법 (Ansible task 안에서)

```yaml
- name: precheck 실행
  ansible.builtin.include_tasks:
    file: "{{ lookup('env','REPO_ROOT') }}/common/tasks/precheck/run_precheck.yml"
  vars:
    _precheck_host:    "{{ _rf_ip }}"
    _precheck_channel: "redfish"     # redfish / os / esxi
    _precheck_timeout: 30            # protocol/auth 공통 (port 제외). 개별: _precheck_timeout_{port,protocol,auth}
```

호출 후 두 변수가 채워진다.

| 변수 | 타입 | 의미 |
|---|---|---|
| `_precheck_ok` | bool | 4단계 모두 통과했는가 |
| `_diagnosis` | dict | 위 2~3절 모양의 진단 결과 |

각 channel 의 site.yml 은 이 결과를 보고 다음 단계 진입 여부를 결정한다.

---

## 6. 코드 위치

| 파일 | 역할 |
|---|---|
| `common/library/precheck_bundle.py` | Ansible 커스텀 모듈 본체 (Controller 에서 실행, stdlib 만 사용) |
| `common/tasks/precheck/run_precheck.yml` | precheck 호출 task |
| `filter_plugins/diagnosis_mapper.py` | precheck 결과를 envelope `diagnosis` 형태로 변환 |

---

## 7. 자주 헷갈리는 점

**Q. ping (ICMP) 은 막혔는데 port 는 응답한다. 진행해도 되나?**
된다. 보안 정책상 ICMP 가 차단된 환경이 흔해서 단계 1·2 는 TCP connect 로 합쳐서 본다. ping 실패는 차단 사유가 아니다.

**Q. `auth_success: true` 인데 본 수집이 실패한다. precheck 가 잘못된 거 아닌가?**
precheck 는 ServiceRoot 한 개만 검증한다. 실제 수집 endpoint 별로 권한이 다를 수 있다 (예: AccountService 만 admin 권한 필요). 본 수집 실패는 envelope `errors[]` 에서 어느 섹션이 실패인지 확인.

**Q. `protocol_supported: false` 인데 BMC 가 살아있다고 자신한다.**
구형 IPMI 전용 BMC 거나, Redfish 는 지원하지만 `/redfish/v1/` 가 비표준 path 인 케이스. probe 로 raw 응답을 직접 받아서 확인.

**Q. precheck 가 너무 느리다.**
단계별 기본 timeout 은 port=3초 / protocol=15초 / auth=8초 (합 최대 ~26초). 죽은 호스트는 port(3초)에서 빠르게 걸러진다. protocol/auth 단계를 줄이려면 `_precheck_timeout` 을 5~10초로 낮추면 된다(port 는 영향 없음). 단, 응답 느린 BMC 에서 false negative 발생 위험. 단계별 개별 조정은 `_precheck_timeout_port` / `_precheck_timeout_protocol` / `_precheck_timeout_auth`.

---

## 8. 더 보고 싶을 때

| 보고 싶은 것 | 파일 |
|---|---|
| 진단 결과가 envelope 의 어디에 들어가나 | `docs/12_diagnosis-output.md` |
| 실패 시 호출자가 어떻게 분기하나 | `docs/08_failure-handling.md` / `docs/20_json-schema-fields.md` 의 `diagnosis` 절 |
| precheck 모듈 본체 | `common/library/precheck_bundle.py` |
