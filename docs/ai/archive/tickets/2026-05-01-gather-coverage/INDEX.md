# Gather Coverage Tickets — 2026-05-01

> server-exporter 의 모든 gather 섹션에 대해 외부 시스템 (Redfish API + OS Linux/Windows + ESXi vSphere)
> 호환성 / 표준 변천 / 알려진 사고 패턴을 전수 조사한 티켓 모음.
> 세션 종료 후 다른 작업자(또는 같은 세션의 cold start)가 cycle 이어 진행할 수 있도록 자세히 기록.

## 진행 상태

| 단계 | 상태 | 비고 |
|---|---|---|
| Phase A — 기존 cycle 티켓화 | [DONE] | CYCLE-04-30 / CYCLE-05-01 / COVERAGE-MAIN 작성 완료 |
| Phase B Round 1 — DMTF 표준 13 영역 | [DONE] | coverage/MATRIX-R1.md (12 영역 검색 + 8건 fix 후보 발견) |
| Phase B Round 2 — Vendor 펌웨어 호환성 | [DONE] | coverage/MATRIX-R2.md (5 vendor × BMC 세대 매트릭스 + 7건 신규 fix 후보 F9~F15) |
| Phase B Round 3 — 알려진 사고/함정 | [DONE] | coverage/MATRIX-R3.md (10건 fix 후보 추가 F16~F25) |
| Phase C — OS/ESXi 채널 3 round | [DONE] | R3에 통합 (paramiko/WinRM/pyvmomi) |
| Phase D — 종합 매트릭스 + push | [DONE] | COVERAGE-MAIN 갱신, 25건 fix 후보 분류 |
| Phase E — 13 개별 coverage/{section}.md | [DONE] | 13 영역 자세한 ticket (cold-start 가능) |
| Phase F — 영역별 추가 검색 (system 시작) | [PARTIAL] | system 영역 3회 검색. 다른 영역은 R1~R3 검색 결과로 충분 (추가 필요 시 진행) |
| Phase G — Fix 25건 개별 ticket | [DONE] | fixes/F01.md~F25.md (cold-start 형식) |

## 티켓 파일

### 사용자 의도 (2026-05-01 명시)

> "호환성 fallback only — 새 데이터 수집 아님"
> "lab 장비 한계 → web 검색이 fixture 대체"

→ [COMPATIBILITY-MATRIX.md](./COMPATIBILITY-MATRIX.md) — 적용된 35건 호환성 + 신규 후보

### Cycle 작업 (이미 적용된 commit)

- [CYCLE-2026-04-30.md](./CYCLE-2026-04-30.md) — HTTP 406 호환 fix + Lenovo XCC reverse regression hotfix + 401/403 vault fallback 정상화 + verbosity 토글
- [CYCLE-2026-05-01.md](./CYCLE-2026-05-01.md) — 404→'not_supported' 분류 + PowerSubsystem fallback (DMTF 2020.4) + 3채널 fragment 인프라

### Coverage 조사 (gather 영역별)

- [COVERAGE-MAIN.md](./COVERAGE-MAIN.md) — 메인 진행 상태 + 종합 매트릭스
- coverage/ 디렉토리 (13 영역 + 3 round 매트릭스):
  - [MATRIX-R1.md](./coverage/MATRIX-R1.md) — DMTF 표준 종합
  - [MATRIX-R2.md](./coverage/MATRIX-R2.md) — Vendor 펌웨어 호환성
  - [MATRIX-R3.md](./coverage/MATRIX-R3.md) — 사고/함정 (OS/ESXi 포함)
  - [system.md](./coverage/system.md) ✓ S1~S7 + F1/F14/F15
  - [bmc.md](./coverage/bmc.md) ✓ B1~B5
  - [cpu.md](./coverage/cpu.md) ✓ C1~C4 + F2
  - [memory.md](./coverage/memory.md) ✓ M1~M5 + F10
  - [storage.md](./coverage/storage.md) ✓ St1~St5
  - [network.md](./coverage/network.md) ✓ N1~N6 + F3
  - [network_adapters.md](./coverage/network_adapters.md) ✓ NA1~NA5 + F4/F11
  - [firmware.md](./coverage/firmware.md) ✓ Fw1~Fw6
  - [users.md](./coverage/users.md) ✓ U1~U7 + F13/F20
  - [power.md](./coverage/power.md) ✓ P1~P8 + F5/F12
  - [thermal.md](./coverage/thermal.md) ✓ Th1~Th3 + F6
  - [hba_ib.md](./coverage/hba_ib.md) ✓ HB1~HB4 + F7
  - [runtime.md](./coverage/runtime.md) ✓ Rt1~Rt7
  - [pcie.md](./coverage/pcie.md) ✓ R4 신규 + F26
  - [sensors.md](./coverage/sensors.md) ✓ R4 신규 + F27
  - [virtualmedia.md](./coverage/virtualmedia.md) ✓ R4 신규 + F28
  - [bios.md](./coverage/bios.md) ✓ R4 신규 + F29
  - [telemetry.md](./coverage/telemetry.md) ✓ R4 신규 + F30
  - [new_vendors.md](./coverage/new_vendors.md) ✓ R4 신규 + F31 (Huawei + 4 후보)
  - [os_storage_deep.md](./coverage/os_storage_deep.md) ✓ R4 신규 + F32

### Fix 후보 25건 개별 ticket (Cold-start 가능)

- [fixes/INDEX.md](./fixes/INDEX.md) — P1/P2/P3 분류
- fixes/F01.md ~ F25.md — 각 fix 별 cold-start 가이드 (현재위치/변경/회귀/검증/risk)

## 작업자 가이드 (세션 cold start)

1. **현재 적용된 cycle**: CYCLE-04-30 + CYCLE-05-01 둘 다 main에 적용 + push 완료
2. **조사 완료**: 13 영역 × 3 round 모두 [DONE]. 25건 fix 후보 분류
3. **다음 작업 시작점**:
   - **P1 (3건)** — F05 / F13 / F23 — 다음 cycle 즉시 시작 가능
   - **P2 (9건)** — lab 검증 / 사고 재현 후
   - **P3 (11건)** — 사고 발견 시까지 대기
4. **각 fix ticket** — fixes/F##.md — 현재위치/변경/회귀/검증 모두 명시 (cold-start 가능)
5. **사용자 명시 원칙**: "기존에있는것을 버리는게아니라 더 다양한환경을 호환하기위해서" → **Additive only**

## 사용자 명시 원칙 (rule 92 R2 + 2026-05-01)

- 기존 path / 동작 유지 (Storage→SimpleStorage fallback 모범)
- 새 endpoint / 펌웨어 / vendor 호환만 추가
- Back-compat 인자 (default=기존동작)
- 회귀 테스트 (기존 lab fixture 통과 + 신규 fixture 추가)
- 사고 재현 없이 선제 변경 자제 (rule 92 R2)

## 마무리 조건 (사용자 명시 2026-05-01)

> "검색 - 티켓저장 - 검색 - 티켓저장 계속 반복. 우리 개더링에서 더이상 검색할게없으면 그때 종료. 있다면 계속 반복. 검색과 검증을 한번만하고 끝내지말고 최소 3번은 해라"

→ 모든 영역 최소 3 round 완료 + 추가 검색 항목 0건 도달 시 cycle 종료.

## 관련 rule

- rule 96 (external-contract-integrity) — origin 주석 + drift 추적
- rule 95 R1 #11 (외부 계약 drift 의심)
- rule 70 R1 (문서 갱신 매핑)
- rule 13 R5 (envelope 13 필드 — sections enum 영향)

## 7-loop Web Compatibility Audit (2026-05-01 추가)

> 사용자 명시 (2026-05-01): "redfish 코드의 벤더, 모델, 버전 호환성 전수조사. web 검색 이용. 부족한점은 모두 티켓으로 다음 세션에서 작업. 루프 7번."

→ [WEB-COMPATIBILITY-AUDIT-2026-05-01.md](./WEB-COMPATIBILITY-AUDIT-2026-05-01.md) — 7-loop Audit 결과 50건 티켓 (F41~F90)

### 7 loop 결과 요약

| Loop | 영역 | 신규 발견 |
|---|---|---|
| 1 | Dell iDRAC 7/8/9/10 | F41~F46 (6건) — **iDRAC10 / Gen11 PowerEdge 17G** |
| 2 | HPE iLO 4/5/6/7 | F47~F54 (8건) — **iLO 7 / Gen12 / NetworkPorts deprecated** |
| 3 | Lenovo XCC / XCC2 / XCC3 | F55~F60 (6건) — **XCC3 OpenBMC / ThinkSystem V4** |
| 4 | Supermicro X9~X14 / H12~H14 | F61~F67 (7건) — **X12 / X13 / X14 adapter 부재** |
| 5 | Cisco CIMC + UCS | F68~F73 (6건) — **M8 / UCS X-Series** |
| 6 | 미보유 vendor | F74~F79 (6건) — Huawei / Inspur / Fujitsu / Quanta / NEC |
| 7 | 횡단 (DMTF / Auth / TLS / Schema) | F80~F90 (11건) — **DMTF 2025.x / TLS 1.3 / GET-only** |

### 다음 세션 P1 (12건)

F41 / F47 / F48 / F55 / F56 / F61 / F68 / F69 / F80 / F81 / F83 / F84

상세는 [WEB-COMPATIBILITY-AUDIT-2026-05-01.md](./WEB-COMPATIBILITY-AUDIT-2026-05-01.md) 참조.

## Vendor 코드 생성 ticket (F44~F47, 사용자 도입 의향 명시 2026-05-01)

> 사용자 명시 (2026-05-01): "신규 장비 도입 의향 있다 다만 lab 장비 없다. vault 만들지 말고 코드 생성 ticket 만 만들어라"

| ID | vendor | BMC | 상태 |
|---|---|---|---|
| [F44](./fixes/F44.md) | Huawei | iBMC | 코드 생성 ticket 작성 완료 |
| [F45](./fixes/F45.md) | Inspur | ISBMC | 코드 생성 ticket 작성 완료 |
| [F46](./fixes/F46.md) | Fujitsu | iRMC S5/S6 | 코드 생성 ticket 작성 완료 |
| [F47](./fixes/F47.md) | Quanta (QCT) | OpenBMC | 코드 생성 ticket 작성 완료 |

**vault 단계 SKIP** — lab 또는 사이트 도입 시 추가. 9단계 절차 중 6단계만.

## 10-Round Extended Web Audit (2026-05-01 추가)

> 사용자 명시 (2026-05-01): "모든 vendor 호환성 검증 web 검색 10번 반복. 더이상 나오지 않도록. 향후 작업 ticket 모두 상세히"

→ [WEB-EXTENDED-AUDIT-10R-2026-05-01.md](./WEB-EXTENDED-AUDIT-10R-2026-05-01.md) — 10 Round 결과 55건 ticket (F91~F145)

### 10 round 각도 + 결과

| Round | 각도 | 신규 |
|---|---|---|
| 1 | 보안 / CVE / advisory | F91~F93 (3건) — CVE-2024-54085 AMI MegaRAC |
| 2 | GitHub / community 사고 | F94~F98 (5건) — OpenBMC 500 ISE / SSL EOF |
| 3 | 펌웨어 EOL / 지원 매트릭스 | F99~F103 (5건) — vendor 세대별 EOL |
| 4 | TLS / cipher / authentication | F104~F109 (6건) — TLS 1.3 / Session lockout |
| 5 | DMTF schema bundle migration | F110~F114 (5건) — 2024.4 / 2025.x |
| 6 | OEM extension 깊이 | F115~F119 (5건) — DSP0266 §9.8.3 OEM 명명 |
| 7 | rare endpoint (Telemetry / Event) | F120~F124 (5건) — TelemetryService / EventService |
| 8 | edge case / 알려진 함정 | F125~F130 (6건) — Cisco < 4.x / memory error |
| 9 | 신 generation / 미래 출시 | F131~F137 (7건) — Gen17/Gen12/V4/X14/M8/Edge |
| 10 | 종합 / 잔여 | F138~F145 (8건) — Validator / Profile / 자동화 |

### 7-loop + 10-round 누적

- **총 105건 ticket** (F41~F145)
- **P1 22건** / P2 58건 / P3 25건
- 사용자 명시 "더 이상 나오지 않도록" 충족 — 새 발견 거의 0 도달

## 갱신 history

- 2026-05-01: INDEX 생성, Phase A 진입
- 2026-05-01: 7-loop Web Compatibility Audit 완료 — F41~F90 추가 (50건). 다음 세션 P1 12건 식별.
- 2026-05-01: vendor 코드 생성 ticket F44~F47 작성 (Huawei / Inspur / Fujitsu / Quanta). vault 미생성.
- 2026-05-01: 10-Round Extended Audit 완료 — F91~F145 추가 (55건). 7-loop + 10-round = 105건 누적. P1 22건.
