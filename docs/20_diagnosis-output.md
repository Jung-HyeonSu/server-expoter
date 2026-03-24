# 20. 진단 출력 (diagnosis / meta / correlation)

## 개요

리팩토링을 통해 output JSON에 3개 신규 필드가 추가되었습니다.
기존 필드는 변경 없이 유지됩니다 (하위 호환).

## 신규 필드

### diagnosis

수집 실패 원인을 단계별로 보여줍니다.

```json
{
  "diagnosis": {
    "reachable": true,
    "port_open": true,
    "protocol_supported": false,
    "auth_success": false,
    "failure_stage": "protocol",
    "failure_reason": "Redfish ServiceRoot (/redfish/v1/) 응답 없음 — iDRAC 7 등 구 세대 추정",
    "probe_facts": {},
    "checked_ports": [443]
  }
}
```

**failure_stage 값:**
- `reachable` — 호스트 도달 불가 또는 서비스 포트 미응답
- `protocol` — 프로토콜 미지원 (Redfish ServiceRoot 응답 없음 등)
- `auth` — 인증 실패
- `null` — 모든 단계 통과 (정상)

> Stage 1(reachable)과 2(port_open)는 TCP 포트 연결로 통합 처리된다.
> 호스트가 살아있지만 서비스 포트가 닫힌 경우에도 `failure_stage="reachable"` 로 보고된다.

### meta

수집 메타데이터입니다.

```json
{
  "meta": {
    "started_at": "2026-03-18T10:00:00Z",
    "finished_at": "2026-03-18T10:00:18Z",
    "duration_ms": 18420,
    "adapter_id": "redfish_dell_idrac9",
    "adapter_version": "1.0.0",
    "ansible_version": "2.19.1"
  }
}
```

### correlation

다중 채널 결과를 연결하기 위한 키입니다.
같은 물리 장비에 대해 redfish/os/esxi 결과를 매칭할 때 사용합니다.

```json
{
  "correlation": {
    "serial_number": "ABC1234XYZ",
    "system_uuid": "550e8400-e29b-41d4-a716-446655440000",
    "bmc_ip": "10.0.0.10",
    "host_ip": "10.0.1.10"
  }
}
```

## 하위 호환

- 3개 필드 모두 `| default(none)` 처리되어 있어 기존 플레이북과 호환
- 기존 필드 (`target_type`, `status`, `sections`, `errors`, `data`) 변경 없음
- `schema_version`은 여전히 `"1"` 유지

## 관련 파일

| 파일 | 역할 |
|------|------|
| `common/tasks/normalize/build_output.yml` | diagnosis/meta/correlation 포함 |
| `common/tasks/normalize/build_failed_output.yml` | 실패 시에도 동일 필드 포함 |
| `common/tasks/normalize/build_meta.yml` | meta 딕셔너리 생성 |
| `common/tasks/normalize/build_correlation.yml` | correlation 딕셔너리 생성 |
| `common/tasks/normalize/init_fragments.yml` | _started_at 타임스탬프 초기화 |
