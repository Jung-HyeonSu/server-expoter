# 외부 시스템 계약 무결성 (External Contract Integrity)

> server-exporter 내부 enum / 상수 / DTO / VO가 외부 시스템 (Redfish API path / IPMI sensor / SSH 명령 출력 / WinRM session / vSphere API)의 실제 지원 집합과 drift 차단.

## 적용 대상

- 외부 시스템 연동 변수 / 상수 / 매핑 — adapter YAML의 vendor list / firmware list, vendor_aliases.yml, redfish_gather.py의 endpoint 매핑
- 외부 시스템 연동 기능 디버깅

## 목표 규칙

### R1. 외부 계약 origin 주석 의무

외부 시스템 지원 집합 / 스키마 / URL 구조를 반영하는 내부 enum / 상수는 **origin 주석** 필수:

```yaml
# adapters/redfish/dell_idrac9.yml
# 이 adapter는 Dell iDRAC9 Redfish API 5.x / 6.x 펌웨어 기준.
# 원본 위치: Dell support.dell.com / Redfish API guide
# 마지막 동기화 확인: 2026-04-27 (hshwang)
# tested_against: ["5.10.x", "6.5.x"]
# oem_path: /redfish/v1/Dell/...
priority: 100
match:
  manufacturer: ["Dell Inc.", "Dell EMC"]
  model_patterns: ["PowerEdge R7*", "PowerEdge R6*"]
  ...
```

**Allowed**: 원본 접근 불가한 경우 "문의 채널" 또는 "담당자" 명시.

**Forbidden**: 외부 시스템 반영 enum / vendor list에 origin 주석 없이 신규 값 추가/삭제/리네임.

**재검토**: origin 자동 대조 CI job (Redfish probe로 실 펌웨어와 비교) 도입 시 주석 의무 완화.

### R1-A. lab 부재 vendor / 펌웨어 → web sources 의무 (cycle 2026-05-01 신설)

server-exporter lab 은 일부 vendor / 펌웨어 / 환경만 보유. 부재 영역 (Huawei iBMC / Inspur / NEC / iDRAC 7~8 / iLO 4~5 / XCC2~3 / Supermicro X9~X14 / InfiniBand / RHEL 10) 은 **web 검색 sources 명시 의무**:

- **Default**: lab 부재 vendor / 펌웨어 / 외부 계약 (Redfish path / IPMI sensor / vSphere API) 반영 시 다음 4종 sources 중 1개 이상 origin 주석:
  1. **vendor 공식 docs** — `developer.dell.com` / `pubs.lenovo.com` / `support.hpe.com` / `cisco.com/c/en/us/td/docs/...` / `supermicro.com/manuals` / `support.huawei.com`
  2. **DMTF Redfish 표준** — `redfish.dmtf.org/schemas/v1/...` / DSP-NNNN spec PDF
  3. **GitHub issue / 사용자 보고** — vendor 공식 repo 또는 community
  4. **사용자 사이트 실측** — `tests/evidence/<날짜>-<vendor>.md` (rule 70 R3)

- **주석 포맷**:
  ```yaml
  # adapters/redfish/huawei_ibmc.yml
  # source: https://support.huawei.com/.../iBMC_Redfish_API_v1.30.pdf (확인 2026-05-01)
  # source: https://redfish.dmtf.org/schemas/v1/Power.v1_8_0.json (PowerSubsystem 신schema 2020.4)
  # lab: 부재 — 사용자 결정 시 추가
  ```

- **Allowed**: 사이트 실측 fixture 가 capture 됐고 evidence 가 있다면 web sources 생략 가능 (사용자 실측 우선 — rule 25 R7-A-1)
- **Forbidden**:
  - lab 부재 영역에 web sources 0건으로 adapter / vendor list 변경
  - "추정 / likely" 만으로 외부 계약 반영 (rule 25 R7-B)
- **Why**: lab 한계가 server-exporter 의 본질적 제약 (사용자 인정 cycle 2026-05-01). web sources 가 lab fixture 대체. sources 0 건 시 다음 작업자가 검증 불가
- **재검토**: lab 보유 vendor 가 8 vendor 이상 도달 시 web sources 의무 완화

### R1-C. lab 부재 vendor / 펌웨어 → NEXT_ACTIONS 자동 등록 (cycle 2026-05-06-post 학습 형식화)

lab 부재 vendor / 펌웨어 추가 시 후속 작업 자동 추적 의무 (rule 50 R2 단계 10 과 연동):

- **Default**: 다음 trigger 발생 시 `docs/ai/NEXT_ACTIONS.md` 의 "lab 도입 후 별도 cycle 권장" 절에 항목 추가
  - 새 adapter YAML 추가 + lab 부재 명시 (`# lab: 부재` origin 주석)
  - baseline JSON SKIP (실장비 검증 보류)
  - vault SKIP 사용자 명시 승인 (placeholder 만)
  - 사이트 실측 fixture 부재 (`capture-site-fixture` skill 미호출)
- **NEXT_ACTIONS 등재 항목 4종**:
  1. **사이트 fixture 캡처** — capture-site-fixture skill 적용 (Round 검증 후 회귀 회피)
  2. **baseline 추가** — 실장비 검증 후 schema/baseline_v1/{vendor}_baseline.json (rule 13 R4)
  3. **lab 도입 후 cycle** — 별도 round (`{vendor} lab 검증`)
  4. **vault 결정** — 사용자 명시 승인 시점 (rule 27 R6 / `docs/operate/05-vault.md`)
- **Allowed**: lab 부재 vendor 가 NEXT_ACTIONS 에 이미 등재된 경우 중복 등재 skip
- **Forbidden**:
  - lab 부재 vendor 추가 + NEXT_ACTIONS 등재 누락 (다음 작업자 / 다음 cycle 진입 시 추적 불가)
  - "추후 처리" 만 명시하고 구체 항목 list 누락
- **Why**: cycle 2026-05-01 4 신규 vendor + cycle 2026-05-06 Superdome Flex — lab 부재 영역이 본질적 제약. 후속 작업이 NEXT_ACTIONS 에 자동 등재되어야 다음 cycle 진입 시 우선 순위 식별 가능. 등재 누락 시 lab 도입 cycle 가 작업자 기억에만 의존
- **재검토**: lab 도입 자동 감지 + NEXT_ACTIONS 자동 갱신 hook 도입 시 advisory → blocking 격상

### R1-B. envelope 13 필드 / 새 키 추가 자제 (cycle 2026-05-01 신설)

cycle 2026-05-01 학습 — 사용자 의도 두 번 강조 후에야 정확히 이해. `diagnosis.details.detail` 신규 키 추가 → revert. 본 R1-B 는 호환성 fallback 와 새 데이터/섹션/키 추가를 **명시 분리**:

- **Default**: 호환성 fix (사용자 사이트 사고 → fallback) 시 envelope 13 필드 / `data.<section>.<field>` 추가/삭제/리네임 **금지**. 기존 path 유지 + 새 환경 fallback path **추가만** (Additive only)
- **Allowed**: 새 데이터 / 새 섹션 / 새 vendor 는 **별도 cycle** (호환성 cycle 외) — schema 변경 사용자 명시 승인 (rule 92 R5)
- **Forbidden**:
  - 호환성 cycle 에서 envelope 신규 키 추가 (예: `diagnosis.details.detail`, `data.power.thermal_score`)
  - "더 풍부한 정보 제공" 명목의 schema 확장 (호환성 영역 외)
  - 호출자 시스템 파싱 변경 유발하는 모든 변경
- **검증**: `scripts/ai/hooks/envelope_change_check.py` (신규 cycle 2026-05-01) — PreToolUse 또는 post-edit 시 envelope shape 변경 검출 → 호환성 cycle 외 영역으로 분류 advisory
- **Why**: 호출자 시스템 (Jenkins downstream / 모니터링 시스템) 은 envelope shape 가정으로 파싱. 신 키 추가는 파싱 변경 유발. 호환성 fix 와 schema 확장은 의도 분리 필요
- **재검토**: envelope schema 정본 자동 검증 100% 도달 시 본 R1-B 자동화로 위임

### R2. 외부 연동 기능 디버깅 시 외부 계약 질의 우선

- **Default**: 외부 시스템 연동 enum / 상수가 관여하는 버그 조사 시 **사용자에게 외부 계약 먼저 질의**. 코드만으로 추론 시작 금지
- **질의 포맷** (rule 23 WHY+WHAT+IMPACT):
  ```
  외부 계약 확인 필요 — <기능명>
  - 연동 시스템: Redfish / IPMI / vSphere / ...
  - 확인 항목: 지원 endpoint / 응답 schema / 펌웨어 지원
  - 왜: 내부 코드에 <enum/상수 경로> 있지만 외부 원본 접근권 없음
  - 결정 필요: 사용자 / 담당 개발자가 <구체 계약> 알려주시면 코드 가설 검증 1턴에 가능
  ```
- **Allowed**: 외부 계약이 `docs/ai/catalogs/EXTERNAL_CONTRACTS.md` 또는 명시 주석에 이미 기록 있으면 질의 생략
- **Forbidden**:
  - 외부 계약 확인 없이 "내부 코드 분석만으로" 근본 원인 확정
  - 외부 원본 접근 불가로 판단하여 가설 계속 확장 (2턴 이상 연쇄 추측)

### R3. 외부 연동 enum 값 변경 시 영향 범위

외부 연동 enum (예: target_type, vendor list, sections list) 값 변경 시 **쓰임 모든 경로** 자동 탐색:

- 해당 enum을 참조하는 모든 Python / Ansible YAML 파일
- adapter 매칭 metadata (vendor / firmware / model_patterns)
- vault path (`vault/<loc>/redfish/<vendor>.yml`)
- 화면이 없으므로 i18n / message 영향 없음
- baseline_v1/{vendor}_baseline.json
- vendor 별 OEM 추출 분기 (`redfish-gather/library/redfish_gather.py` 의 `_extract_oem_*`)

**Forbidden**: 외부 연동 enum 값 변경 시 위 탐색 skip.

### R4. 외부 계약 drift 발견 시 기록

외부 계약 ↔ 내부 enum drift 발견 시 **3 곳에 즉시 기록**:

1. `docs/ai/catalogs/FAILURE_PATTERNS.md` — `external-contract-drift` / `external-contract-unverified` append-only
2. `docs/ai/catalogs/CONVENTION_DRIFT.md` — drift 번호 (DRIFT-XXX)
3. 해당 enum / 상수 / adapter 파일 — origin 주석에 `# DRIFT 발견 YYYY-MM-DD: <요약>` 추가

**Forbidden**: drift 발견 후 "다음 PR에서 고치면 됨"으로 기록 skip.

### R5. 재검토 (rule 자체)

- 6개월간 external-contract drift 사고 0건 → R1 주석 의무를 "리팩토링 시 append" 수준 완화
- `EXTERNAL_CONTRACTS.md` 카탈로그 완결되면 R2 질의 빈도 감소

## 금지 패턴

- adapter / vendor enum에 origin 주석 없이 추가 — R1
- 외부 연동 디버깅 시 외부 계약 질의 skip — R2
- enum 값 변경 + 영향 탐색 skip — R3
- drift 발견 + 기록 skip — R4

## 리뷰 포인트

- [ ] adapter YAML에 origin 주석 (vendor / firmware / tested_against / oem_path)
- [ ] 외부 연동 디버그 PR에 외부 계약 질의 흔적
- [ ] enum 값 변경 PR에 쓰임 탐색 결과
- [ ] drift 발견 시 3 곳 기록

## 관련

- rule: `23-communication-style` (WHY+WHAT+IMPACT), `91-task-impact-gate` R3 (외부 시스템 항목), `92-dependency-and-regression-gate` R6 (코드 우선 — 외부 시스템 예외), `95-production-code-critical-review` R1 #11, `25-parallel-agents` R7-B (Agent 추정 격상 금지)
- skill: `debug-external-integrated-feature`, `task-impact-preview`, `write-quality-tdd`
- catalog: `docs/ai/catalogs/EXTERNAL_CONTRACTS.md` (신설), `FAILURE_PATTERNS.md`, `CONVENTION_DRIFT.md`
