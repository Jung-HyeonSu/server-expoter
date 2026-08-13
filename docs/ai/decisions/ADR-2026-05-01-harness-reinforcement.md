# ADR-2026-05-01: Harness Reinforcement (B1~B8 + D + E 일괄)

- 일자: 2026-05-01
- 상태: Accepted
- 사용자: hshwang1994
- 트리거: rule 70 R8 — 본문 의미 변경 (rule 25 R7-A-1 신설 / rule 96 R1-A + R1-B 신설) + 표면 카운트 증가 (agents 57→59 / skills 43→48 / hooks 18→21)

## 컨텍스트 (Why)

cycle 2026-05-01 종료 시점, 사용자 명시 "하네스 보강 작업 모두 수행해라 남겨두지말고 모두" 와 "하네스 전체 점검 하네스 작업을 마무리해라 전부해라". 본 cycle 종료 ticket 아카이브(정리됨) 의 B1~B8 부족 + D 신규 후보 + E 권한 완화 모두 일괄 적용.

### 2주간 학습 (HARNESS-RETROSPECTIVE A 절)

| 학습 | 출처 |
|---|---|
| 사용자 실측 > spec | cycle 2026-04-30 Lenovo XCC reverse regression |
| 호환성 ≠ 새 데이터 (Additive only) | cycle 2026-05-01 사용자 두 번 강조 후 정확히 이해 |
| lab 한계 → web sources 의무 | cycle 2026-05-01 |
| 404 = 미지원 vs 5xx = fail 분리 | cycle 2026-05-01 |
| 3채널 fragment 인프라 = 호환성 표준 | OS/ESXi 점진 전환 가능 |

### 발견된 부족 (B1~B8)

자세히는 retrospective 참조. 핵심:
- B1 lab 한계 / B2 reverse regression / B3 신 JSON 키 자제 / B4 ticket cold-start /
- B5 fallback 패턴 추상화 / B6 origin 주석 / B7 사이트 fixture / B8 cross-channel 일관성

## 결정 (What)

### 1. rule 본문 강화 (3건)

| Rule | 신설 | 의미 |
|---|---|---|
| `25-parallel-agents` | R7-A-1 | 사용자 실측 > spec |
| `96-external-contract-integrity` | R1-A | lab 부재 → web sources 의무 (4종 sources) |
| `96-external-contract-integrity` | R1-B | envelope 13 필드 / 새 키 추가 자제 (Additive only) |

### 2. 신규 hook (3건)

| Hook | 검출 대상 | 모드 |
|---|---|---|
| `envelope_change_check.py` | envelope 13 필드 / data.* 신규 키 | advisory |
| `adapter_origin_check.py` | adapter YAML origin 주석 부재 | advisory |
| `cross_channel_consistency_check.py` | diagnosis.details list / capacity 단위 혼재 / status 'unknown' | advisory |

3종 모두 self-test 모드 PASS.

### 3. 신규 skill (5건)

| Skill | 진입점 |
|---|---|
| `cross-review-workflow` | `/cross-review-workflow` (디렉터리 형식 변환) |
| `write-cold-start-ticket` | 새 cycle ticket 디렉터리 cold-start 형식 생성 |
| `capture-site-fixture` | 사이트 사고 fixture sanitize + commit |
| `web-evidence-fetch` | vendor docs / DMTF / GitHub web 검색 + ticket 흡수 |
| `lab-inventory-update` | lab 보유/부재 자동 측정 + LAB-INVENTORY 갱신 |

### 4. 신규 agent (2건 + 기존 1건)

| Agent | model | 역할 |
|---|---|---|
| `web-evidence-collector` | opus | web sources 자동 수집 |
| `lab-tracker` | opus | lab 보유/부재 자동 추적 |
| `compatibility-detective` | (기존) | 사이트 사고 호환성 영역 자동 탐지 |

### 5. 코드 헬퍼 (1건)

`redfish_gather.py:567` — `_endpoint_with_fallback(bmc_ip, primary_path, fallback_path, ...)` 헬퍼 추가. Storage→SimpleStorage / Power→PowerSubsystem / 향후 ThermalSubsystem 같은 DMTF 변천 호환 패턴 추상화. 기존 코드 영향 없음 (Additive).

### 6. 권한 정책 (E절 — cycle-011 부터 존재)

- `.claude/policy/agent-permissions.yaml` 유지 (cycle-011 + 본 cycle 보강)
- `ADR-2026-05-01-harness-full-permissions.md` 유지

## 결과 (Impact)

### 표면 카운트

| 항목 | 시작 | 종료 |
|---|---|---|
| agents | 57 | 59 (+2) |
| skills | 43 | 48 (+5) |
| hooks | 18 | 21 (+3) |
| rules | 28 | 28 (본문 R7-A-1 / R1-A / R1-B 신설) |
| policies | 10 | 10 |
| decisions (ADR) | N | N+1 (본 ADR) |

### 검증

- `verify_harness_consistency.py` PASS (rules 28 / skills 48 / agents 59 / policies 10)
- `verify_vendor_boundary.py` PASS (vendor 하드코딩 0건)
- `output_schema_drift_check.py` PASS (sections=10 / fd_paths=65)
- `check_project_map_drift.py --update` 적용 후 drift 0
- `commit_msg_check.py --self-test` PASS (5/5)
- 3 신규 hook self-test PASS
- `pytest tests/unit/` PASS (76/76)
- `python -m ast` (`redfish_gather.py`) PASS

### 호환성 영향

- envelope 13 필드 변경 0건 (Additive only)
- 기존 vendor / 펌웨어 영향 0건
- 호출자 시스템 (Jenkins downstream) 영향 0건

### 차단 영역 유지 (rule 70 R8 governance)

- main 강제 push 금지 (rule 93 R1)
- schema 버전 변경 사용자 명시 승인 (rule 92 R5)
- 새 vendor 추가 사용자 명시 승인 (rule 50 R2)

## 대안 비교 (Considered)

### 대안 A: 점진 적용 (cycle 별 1~2건)
- **장점**: 영향 작음 / 검증 용이
- **단점**: 사용자 명시 "남겨두지말고 모두" 거부

### 대안 B: 일괄 적용 (본 ADR)  ✓ 채택
- **장점**: 사용자 의도 일치 / 검증 인프라 + 워크플로우 + 권한 한 묶음 commit
- **단점**: commit diff 크기. cycle 단위 추적은 본 ADR + retrospective + cycle-017.md 로 보존

### 대안 C: Tier 분류 후 일부만 (Tier 1 자동 / Tier 2 사용자 승인 / Tier 3 보류)
- **장점**: rule 70 R8 governance 강화
- **단점**: 사용자가 "묻지마라 전부해라" 명시 → Tier 분류 자체 불필요

## 갱신 history

- 2026-05-01: 본 ADR 신규. cycle 2026-05-01 하네스 보강 종료 시점.

## 관련

- HARNESS-RETROSPECTIVE.md (G절 적용 결과)
- cycle 로그(정리됨) (cycle 보고서)
- ADR-2026-05-01-harness-full-permissions.md (권한 정책)
- ADR-2026-04-28-rule12-oem-namespace-exception.md (rule 70 R8 첫 적용 사례)
