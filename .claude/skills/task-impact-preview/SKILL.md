---
name: task-impact-preview
description: 코드 변경 작업 전에 영향 범위·의존성·리스크를 한 장으로 프리뷰한다 (rule 91 R1). 사용자가 "기능 추가해줘", "리팩토링", "고쳐줘", "수정해줘", "벤더 추가", "schema 변경" 등 비단순 코드 변경을 요청한 모든 경우 다른 skill 호출 전에 자동 호출. 신규 작업자가 영향 예상 못한 채 구현으로 직진하는 것을 차단. 사용자가 "그냥 진행해줘", "프리뷰 skip" 명시하면 건너뜀. - 기능 추가 / 수정 / 리팩토링 / 벤더 추가 / schema 변경 / Jenkinsfile cron / 의존성 변경. 매우 단순한 변경 (오타 1줄, 주석)은 skip.
---

# task-impact-preview

## 목적

server-exporter는 3-channel + multi-vendor + adapter + schema + Jenkins 등 cross-cutting 영향이 흔함. 5초 프리뷰로 100배 수정 비용 절감 (rule 91).

## 5 섹션 출력 (rule 91 R3)

```markdown
## task-impact-preview — <변경 요약>

### 1. 영향 모듈 (파일 경로 수준)
- {file 1}: 변경 내용
- {file 2}: 변경 내용

### 2. 영향 vendor
- 전 vendor agnostic / 또는
- 영향: Dell / HPE / ... (구체 list)

### 3. 함께 바뀔 것
- 테스트: tests/redfish-probe/ 아래 해당 테스트 / fixtures
- 문서: docs/X / .claude/ai-context/Y
- adapter: adapters/{channel}/{vendor}_*.yml
- schema: sections.yml + field_dictionary.yml + baseline_v1
- 외부 시스템 계약: Redfish path / IPMI / SSH / WinRM / vSphere (rule 96)

### 4. 리스크 top 3
- [HIGH] {위험}
- [MED] {위험}
- [LOW] {위험}

### 5. 진행 확인
- (A) 그대로 진행 → 다음 skill: implement-safe-change / write-quality-tdd
- (B) 옵션 비교 → compare-feature-options
- (C) 영향 브리핑 → write-impact-brief (HIGH 리스크)
- (D) 취소
```

## 자동 호출 조건 (rule 91 R1)

다음 키워드 감지 시 다른 skill 호출 전 본 skill 먼저:
- "추가해줘", "구현해줘", "만들어줘", "개발해줘"
- "리팩토링", "바꿔줘", "변경", "개선", "옮겨줘"
- "고쳐줘", "수정해줘"
- "벤더 추가", "schema 변경", "필드 추가", "섹션 추가"
- "마이그레이션", "Jenkinsfile cron"

## Skip 조건 (rule 91 R2)

- 사용자 명시 ("그냥 진행해줘" / "프리뷰 skip" / "간단하니까")
- 오타 1줄 / 주석만 / 변수명 1개
- 이미 plan-* skill로 계획 끝남

## 절차

1. **변경 요청 분석**: 사용자 메시지에서 동사 / 대상 추출
2. **실측 (`Grep` / `Glob` / `Read`)**:
   - 영향 파일 list
   - 변경 키워드가 있는 다른 위치
3. **영향 분류**:
   - 채널 (os / esxi / redfish)
   - vendor (agnostic 또는 specific)
   - schema (sections / field_dictionary / baseline / 무관)
   - 외부 시스템 (Redfish / vSphere / SSH / WinRM)
4. **리스크 평가** (FAILURE_PATTERNS.md 패턴 비교):
   - HIGH: 보호 경로 / vault / 벤더 경계 위반 / schema 3종 미동반
   - MED: 다중 vendor / Jenkinsfile cron / fragment 영역
   - LOW: 단일 vendor adapter / 문서 / fixture
5. **회귀 영역 자동 식별** (rule 91 R7):
   - 공통 fragment (common/tasks/normalize/)
   - adapter 추가/수정
   - Jenkinsfile cron
   - 출력 schema
   - vault
6. **출력 5 섹션**

## 후속 라우팅 (rule 91 R4)

| 리스크 | 다음 |
|---|---|
| LOW | implement-safe-change 직진 |
| MED + 2+ 옵션 | compare-feature-options |
| HIGH | write-impact-brief 에스컬레이트 + 사용자 승인 |
| Critical (벤더 경계 / schema / Jenkinsfile cron / vault) | 사용자 명시 승인 없이 구현 금지 |

## SUB 진입 시 재호출 (rule 91 R6)

- 에픽 첫 SUB 착수 전 1회
- 후속 SUB 착수마다 재실행
- Skip: SUB 범위가 에픽 preview에 이미 상세 열거된 그대로

## server-exporter 도메인 적용

- 모든 코드 변경에 진입점
- 출력 5 섹션은 server-exporter 어휘 (vendor / channel / schema / vault / Jenkinsfile)

## 적용 rule / 관련

- **rule 91** (task-impact-gate) 정본
- rule 92 (dependency-and-regression-gate) — 후속 회귀 검사
- rule 95 (production-code-critical-review) — 의심 패턴 12종
- rule 96 (external-contract-integrity) — 외부 계약 변경
- skill: `compare-feature-options`, `write-impact-brief`, `prepare-regression-check`, `validate-fragment-philosophy`, `vendor-change-impact`
- agent: `change-impact-analyst`
- catalog: `docs/ai/catalogs/FAILURE_PATTERNS.md`
