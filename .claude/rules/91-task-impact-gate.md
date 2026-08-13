# task-impact-preview 자동 호출 게이트

## 적용 대상
- 저장소 전체 (`**`) — 코드 변경 요청 모두

## 목표 규칙

### R1. 자동 호출 의무

다음 키워드가 사용자 프롬프트에 포함되면 **다른 skill 호출 전에** `task-impact-preview` 먼저 실행:

- "추가해줘", "구현해줘", "만들어줘", "개발해줘"
- "리팩토링", "바꿔줘", "변경", "개선", "옮겨줘"
- "고쳐줘", "수정해줘" (단순 오타 제외)
- "마이그레이션", "스키마 변경", "필드 추가"
- "벤더 추가"

**Forbidden**: 위 트리거 감지 시 `task-impact-preview` 없이 구현 skill 직진.

### R2. Skip 조건

다음만 skip:
- 사용자 명시 ("그냥 진행해줘" / "프리뷰 skip" / "바로 해줘" / "간단하니까")
- 오타 1줄, 주석만 수정, 변수명 1개 변경
- 이미 `plan-feature-change` 등 계획 단계를 끝내고 구현에 들어간 경우

**Forbidden**: AI 자체 판단으로 "안전해 보여서" skip.

### R3. 프리뷰 5 섹션

`task-impact-preview` 출력 필수 5 섹션:

1. **영향 모듈** (파일 경로 수준)
2. **영향 vendor** (Dell / HPE / Lenovo / Supermicro / Cisco / agnostic)
3. **함께 바뀔 것** (테스트 / 문서 / adapter / **외부 시스템 계약: Redfish path / IPMI / SSH / WinRM / vSphere**)
4. **리스크 top 3** (HIGH / MED / LOW)
5. **진행 확인** (사용자 선택지)

**Forbidden**: 5 섹션 중 누락. "영향 모듈을 특정할 수 없음" 답변 허용 안 함 — Read/Grep/Glob/Bash로 실측.

### R4. 프리뷰 후속 라우팅

| 리스크 | 다음 단계 |
|---|---|
| LOW | 바로 구현 진행 |
| MED + 선택지 2+ | `compare-feature-options` 먼저 |
| HIGH | `write-impact-brief` 에스컬레이트 + 사용자 승인 대기 |
| Critical (벤더 경계 / schema 변경 / Jenkinsfile cron / vault) | 사용자 명시 승인 없이 구현 진입 금지 |

### R5. 실패·누락 기록

- preview가 실 발생 사고를 예측 못한 경우 → `docs/ai/catalogs/FAILURE_PATTERNS.md` 즉시 append (`scope-miss` 또는 `ai-hallucination`)

### R6. 하위 SUB 진입 시 재실행

- 에픽 → 첫 SUB 착수 전: 1회 실행
- 후속 SUB 착수마다 재실행
- Skip: SUB 범위가 에픽 preview에 이미 상세 열거된 그대로

### R7. 회귀 검사 자동 식별

변경 범위에 다음 영역 포함 시 회귀 검사 자동 브리핑:
- 공통 fragment 영역 (common/tasks/normalize/)
- adapter 추가/수정
- Jenkinsfile cron 변경
- 출력 schema 변경 (sections / field_dictionary)
- vault 변경

## 금지 패턴

- preview 누락 후 구현 직진 — R1
- AI 임의 skip — R2
- preview 5 섹션 불완전 — R3
- HIGH 리스크 무시한 채 구현 — R4
- 사고 후 FAILURE_PATTERNS append 누락 — R5

## 리뷰 포인트

- [ ] PR 최초 요청 세션에 task-impact-preview 실행
- [ ] 5 섹션 모두 포함
- [ ] HIGH 리스크 사용자 승인 흔적
- [ ] 사고 후 FAILURE_PATTERNS append

## 관련

- skill: `task-impact-preview`, `compare-feature-options`, `write-impact-brief`
- rule: `92-dependency-and-regression-gate`, `95-production-code-critical-review`, `96-external-contract-integrity`
- catalog: `docs/ai/catalogs/FAILURE_PATTERNS.md`
- 정본: `CLAUDE.md` §13
