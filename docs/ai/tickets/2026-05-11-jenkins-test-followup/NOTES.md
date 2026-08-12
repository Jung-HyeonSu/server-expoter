# 운영 영역 노트 (AI 작업 외)

직전 세션 (2026-05-11) Jenkins 개더링 테스트 중 발견된 호스트 측 이슈. **AI 환경에서 진단/수정 불가** — 운영 담당자 인계.

## Cisco 10.100.15.1

| 항목 | 값 |
|---|---|
| TCP/443 | OK (`http_code=503, time=1.5s`) |
| Redfish API | **HTTP 503 Service Unavailable** |
| 인증 | 시도 불가 (503 응답으로 인증 단계 진입 불가) |
| 사용자 제공 자격증명 | admin / __REDACTED__ (검증 못 함) |

**증상 해석**: BMC TCP 포트 응답하지만 Redfish 서비스가 down 또는 busy 상태. BMC 재부팅 또는 Redfish 서비스 재시작 필요 가능.

**vault 자체 정상** — 같은 `vault/redfish/cisco.yml` 로 10.100.15.2 정상 수집됨 (build #133 cisco_ucs_xseries SUCCESS).

## Cisco 10.100.15.3

| 항목 | 값 |
|---|---|
| ICMP / TCP/443 | **Connection timeout (3초)** |
| HTTP | 응답 0 |

**증상 해석**: BMC 자체 도달 불가. 가능 원인:
- BMC 전원 down
- 네트워크 경로 차단 (방화벽 / VLAN)
- BMC NIC 비활성

## 후속 액션 (운영 담당자)

| 호스트 | 점검 항목 |
|---|---|
| 10.100.15.1 | BMC console 접속 → Redfish 서비스 상태 → 필요시 재시작 |
| 10.100.15.3 | BMC 전원 + 네트워크 경로 (ping 가능 여부) |

해당 호스트 복구 후 Jenkins `hshwang-gather` 빌드 (target_type=redfish, bmc_ip=대상 IP) 로 검증.
