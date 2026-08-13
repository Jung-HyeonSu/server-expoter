---
name: debug-external-integrated-feature
description: 외부 시스템 (Redfish / IPMI / SSH / WinRM / vSphere) 연동 기능 버그 조사 시 systematic-debugging 진입 전 호출. 외부 계약을 사용자에게 먼저 질의하여 추측 턴 낭비 차단 (rule 96 R2). 사용자가 "Redfish 응답 이상", "vSphere 연결 실패", "외부 시스템 디버그" 등 요청 시. - 외부 시스템 연동 버그 / 응답 형식 불명 / 펌웨어 차이 의심
---

# debug-external-integrated-feature

## 목적

외부 시스템 응답에 의존하는 server-exporter 기능의 버그를 조사할 때 **외부 계약을 사용자에게 먼저 질의** (rule 96 R2). 코드만으로 추측 시 가설 확장 위험.

## 외부 시스템 list

| 시스템 | 채널 | 라이브러리 |
|---|---|---|
| Redfish API | redfish-gather | stdlib (urllib/ssl) |
| IPMI | (현재 미사용, 향후 fallback) | — |
| SSH | os-gather Linux | paramiko (Ansible 내부) |
| WinRM | os-gather Windows | pywinrm |
| vSphere | esxi-gather | pyvmomi + community.vmware |

## 질의 포맷 (rule 23 + rule 96 R2)

```
외부 계약 확인 필요 — <기능명>

- 연동 시스템: Redfish / vSphere / SSH / WinRM 중
- 확인 항목: 지원 endpoint / 응답 schema / 펌웨어 지원 / 인증 방식
- 왜: 내부 코드에 <enum/상수 경로>가 있지만 외부 원본 접근권 없음
- 결정 필요: 사용자 / BMC 운영자 / vCenter 운영자가 <구체 계약> 알려주시면 1턴에 해결 가능

예시:
"Dell iDRAC9 7.x 펌웨어에서 /redfish/v1/Systems/.../Storage/Volumes 응답 형식이
변경됐는지 확인 필요합니다. BMC 운영자께 다음 명령 실행 요청드립니다:
curl -k -u service_account:... https://10.x.x.1/redfish/v1/Systems/System.Embedded.1/Storage/Volumes"
```

## 절차

1. **사용자 / 외부 시스템 운영자에게 질의** (위 포맷)
2. **응답 받음** → 외부 계약 확정
3. **그 후에야** systematic-debugging 진입 (가설 검증 1턴)
4. **drift 발견 시** rule 96 R4 — 3 곳 기록:
   - docs/ai/catalogs/FAILURE_PATTERNS.md (`external-contract-drift`)
   - docs/ai/catalogs/CONVENTION_DRIFT.md (DRIFT-NNN)
   - 해당 enum/adapter origin 주석 갱신

## Forbidden

- 외부 계약 확인 없이 "내부 코드 분석만으로" 근본 원인 확정
- 외부 원본 접근 불가로 판단하여 가설 계속 확장 (2턴 이상)

## 자동 호출 시점

- 사용자가 "~ 실행 안 됨", "외부 시스템 연동 오류", "Redfish 500", "vSphere 응답 이상" 등 언급

## 적용 rule / 관련

- **rule 96** (external-contract-integrity) 정본
- rule 25 R7-B (Agent 추정 격상 금지)
- rule 95 R1 #11 (외부 계약 drift 의심)
- skill: `task-impact-preview`, `probe-redfish-vendor`, `debug-precheck-failure`
- agent: `integration-impact-reviewer`, `change-impact-analyst`
- catalog: `docs/ai/catalogs/EXTERNAL_CONTRACTS.md`
- reference: 외부 API 공식 문서
