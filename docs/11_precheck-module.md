# 11. Pre-check 모듈 (precheck_bundle)

## 개요

`precheck_bundle.py`는 수집 대상 호스트에 대해 **4단계 연결 진단**을 수행하는 Ansible 커스텀 모듈입니다.

수집 실패 시 "왜 실패했는지"를 운영자가 즉시 파악할 수 있도록 단계별 결과를 제공합니다.

## 진단 단계

```
1+2. reachable + port_open — TCP connect로 채널별 포트 응답 확인 (443, 22, 5986 등)
     → 성공 시 reachable=true, port_open=true 동시 설정
     → 실패 시 failure_stage="reachable"
 3.  protocol_supported — 프로토콜 핸드셰이크 (/redfish/v1/, SSH banner, /sdk 등)
 4.  auth_success — 인증 성공 여부 (선택적, 채널에 따라 스킵)
```

> Stage 1(reachable)과 2(port_open)는 TCP 포트 연결로 통합 처리됩니다.
> 호스트가 살아있지만 서비스 포트가 닫힌 경우 `failure_stage="reachable"`로 보고됩니다.

각 단계 실패 시 후속 단계는 건너뛰고 `failure_stage`와 `failure_reason`을 반환합니다.

## 사용법

```yaml
- name: "run precheck"
  ansible.builtin.include_tasks:
    file: "{{ lookup('env','REPO_ROOT') }}/common/tasks/precheck/run_precheck.yml"
  vars:
    _precheck_host: "{{ _rf_ip }}"
    _precheck_channel: "redfish"    # redfish / os / esxi
    _precheck_timeout: 30
```

## 출력 변수

| 변수 | 타입 | 설명 |
|------|------|------|
| `_precheck_ok` | bool | 모든 단계 통과 여부 |
| `_diagnosis` | dict | 진단 결과 딕셔너리 |

### `_diagnosis` 구조

```json
{
  "reachable": true,
  "port_open": true,
  "protocol_supported": true,
  "auth_success": true,
  "failure_stage": null,
  "failure_reason": null,
  "probe_facts": {
    "vendor": "Dell Inc.",
    "firmware": "iDRAC 9 v4.40.00.00"
  },
  "checked_ports": [443]
}
```

### 실패 예시

```json
{
  "reachable": true,
  "port_open": true,
  "protocol_supported": false,
  "auth_success": false,
  "failure_stage": "protocol",
  "failure_reason": "Redfish ServiceRoot (/redfish/v1/) 응답 없음",
  "probe_facts": {},
  "checked_ports": [443]
}
```

## 채널별 진단 방식

| 채널 | 포트 | 프로토콜 확인 | 인증 확인 |
|------|------|---------------|-----------|
| redfish | 443 | GET /redfish/v1/ | Basic Auth |
| os (Linux) | 22 | SSH banner | SSH 로그인 |
| os (Windows) | 5986/5985 | WinRM HTTPS/HTTP | NTLM |
| esxi | 443 | GET /sdk | vSphere API |

## 핵심 파일

| 파일 | 역할 |
|------|------|
| `common/library/precheck_bundle.py` | 커스텀 모듈 (controller에서 실행) |
| `common/tasks/precheck/run_precheck.yml` | precheck 호출 태스크 |
| `filter_plugins/diagnosis_mapper.py` | 결과 → diagnosis 변환 필터 |
