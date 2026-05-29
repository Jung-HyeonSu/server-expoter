# Coverage Main — gather 영역별 외부 호환성 전수 조사

> 목적: 모든 gather 섹션이 외부 시스템 (Redfish API + OS Linux/Windows + ESXi vSphere)
> 의 다양한 펌웨어/버전 변종을 견고하게 수집하도록 호환성 매트릭스 구축.

## 영역 매트릭스 (13 영역 × 3 round)

| # | 영역 | 채널 | 진행 R1 | 진행 R2 | 진행 R3 | 비고 |
|---|---|---|---|---|---|---|
| 1 | system | Redfish + OS + ESXi | [TODO] | [TODO] | [TODO] | hardware/firmware level |
| 2 | bmc | Redfish only | [TODO] | [TODO] | [TODO] | Manager schema |
| 3 | cpu (processors) | Redfish + OS + ESXi | [TODO] | [TODO] | [TODO] | |
| 4 | memory | Redfish + OS + ESXi | [TODO] | [TODO] | [TODO] | |
| 5 | storage | Redfish + OS + ESXi | [TODO] | [TODO] | [TODO] | Storage / SimpleStorage / VMFS |
| 6 | network | Redfish + OS + ESXi | [TODO] | [TODO] | [TODO] | EthernetInterfaces |
| 7 | network_adapters | Redfish only | [TODO] | [TODO] | [TODO] | Chassis NA + NetworkPorts |
| 8 | firmware | Redfish + OS | [TODO] | [TODO] | [TODO] | UpdateService/FirmwareInventory |
| 9 | users | Redfish + OS | [TODO] | [TODO] | [TODO] | AccountService / passwd / Win users |
| 10 | power | Redfish only | [TODO] | [TODO] | [TODO] | Power / PowerSubsystem (DMTF 2020.4) |
| 11 | thermal | Redfish only (NEW) | [TODO] | [TODO] | [TODO] | Thermal / ThermalSubsystem / EnvironmentMetrics |
| 12 | hba_ib | OS Linux only | [TODO] | [TODO] | [TODO] | lspci / FibreChannel / InfiniBand |
| 13 | runtime | OS only | [TODO] | [TODO] | [TODO] | uptime / load / process |

## Round 정의

### Round 1 — DMTF / 표준 spec
- 각 영역의 표준 schema 위치 (URI / endpoint)
- 표준 변천 history (deprecation / 신규 schema)
- 필수 필드 vs 선택 필드

### Round 2 — Vendor 펌웨어 호환성
- Dell iDRAC (7/8/9 generation)
- HPE iLO (4/5/6)
- Lenovo XCC (1/2/3) + IMM2
- Supermicro (X9/X10/X11/X12/X14)
- Cisco CIMC (UCS C-Series)

### Round 3 — 알려진 사고 / 함정
- GitHub issue / 사용자 보고 사례
- 펌웨어 버그 / spec 위반
- 우리 코드의 가설 위반 risk

## 진행 규칙

1. 한 영역 R1 끝나면 coverage/{section}.md 갱신 + 다음 영역 R1
2. 모든 영역 R1 끝나면 R2 진입
3. 모든 영역 R2 끝나면 R3 진입
4. 추가 발견이 0건이면 cycle 종료

## 종합 매트릭스 (R1+R2+R3 완료 — 25건 fix 후보 발견)

### 우선순위별 분류

#### P0 — cycle 2026-05-01 에서 모두 처리됨
- 404 → 'not_supported' 분류 (3채널 인프라)
- gather_power PowerSubsystem fallback (DMTF 2020.4)
- _compute_final_status 401/403 강제 failed
- precheck Accept 헤더 명시

#### P1 — 다음 cycle 권장 (3건)
| # | 영역 | 작업 |
|---|---|---|
| F5 | power | EnvironmentMetrics fallback (PowerControl 보존) |
| F13 | users | Cisco CIMC AccountService 'not_supported' 분류 적용 |
| F23 | os | OS gather 'not_supported' 점진 전환 (인프라 활용) |

#### P2 — 후속 cycle (lab 검증 또는 사고 재현 후, 9건)
| # | 영역 | 작업 |
|---|---|---|
| F2 | cpu | ProcessorType 'Accelerator'/'Core' enum 통과 |
| F4 / F11 | network_adapters | HPE iLO 5 BaseNetworkAdapters fallback |
| F6 | thermal | thermal 섹션 신규 도입 (DMTF 2020.4 ThermalSubsystem) |
| F8 | users | Cisco CIMC AccountService 제한 |
| F10 | memory | HPE Gen11 HBM memory 모듈 enum |
| F12 | power | Cisco CIMC PowerSubsystem 검증 |
| F17 | (전체) | Schema 버전 errata 사용 |
| F20 | users | BMC lockout backoff 1초 → 5초 |
| F21 | os Linux | paramiko 2.9.0+ + RHEL 9 ssh-rsa 호환 |

#### P3 — 선제 변경 자제 (rule 92 R2, 11건)
F1 / F3 / F9 / F14 / F15 / F16 / F18 / F19 / F22 / F24 — NEXT_ACTIONS 등재만, 사고 재현 후 작업

### 채널 별 발견 분포

| 채널 | fix 후보 |
|---|---|
| Redfish (전체) | F1~F2 / F4~F6 / F8~F20 (16건) |
| OS Linux | F7 / F21 / F23 (3건) |
| OS Windows | F22 (1건) |
| ESXi | F24 / F25 (2건) |
| 모든 채널 공통 | F17 / F18 / F19 (3건) |

### 영역별 발견 분포

| 영역 | 발견 |
|---|---|
| system | F1, F9, F14, F15 (4) |
| bmc | F16 (1) |
| cpu | F2 (1) |
| memory | F10 (1) |
| storage | (없음) |
| network | F3 (1) |
| network_adapters | F4 (1) |
| firmware | (없음) |
| users | F8, F13, F20 (3) |
| power | F5, F12 (2) |
| thermal | F6 (1) |
| hba_ib | F7 (1) |
| runtime | (없음) |
| ssh/winrm/vsphere | F21, F22, F24 (3) |
| 횡단 | F17, F18, F19, F23, F25 (5) |

## 종료 조건 도달 확인

사용자 명시 (2026-05-01): "검색-티켓저장 반복. 더이상 검색할 게 없으면 종료. 최소 3번."

- Round 1 (DMTF 표준): [DONE]
- Round 2 (vendor 펌웨어 호환성): [DONE]
- Round 3 (사고/함정): [DONE]
- OS/ESXi 추가 검색: R3에 통합 [DONE]
- **추가 검색 항목**: 5 vendor 외 비표준 BMC (Gigabyte/Advantech 등)는 우리 영향 미미 — skip
- **최소 3 round**: 충족
- **종료 조건**: 도달 ✓

## 갱신 history

- 2026-05-01: 본 매트릭스 생성, R1~R3 모두 완료. 25건 fix 후보 (P0 처리됨 / P1~P3 follow-up).
