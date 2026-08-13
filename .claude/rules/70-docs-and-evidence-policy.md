# 문서 및 증거 정책

## 규칙 표기 구조

본 rule의 각 항목은 **Default / Allowed / Forbidden + Why + 재검토 조건** 3단 구조.

## 적용 대상

- `docs/ai/**`
- `.claude/**` (규칙/정책 문서)
- `tests/evidence/**`
- 정본 문서: `CLAUDE.md`, `REQUIREMENTS.md`, `README.md`, `docs/` 문서

## 현재 관찰된 현실

- server-exporter는 내부 프로젝트. 규제 감사 대상 아님
- 감사 증명용 이력은 git log + cycle log에 보존
- AI가 자주 생성하는 문서 (cycle 보고서 / V-number 증가 / 1회성 review) 누적 시 catalog stale 위험
- PROJECT_MAP fingerprint로 구조 변경 자동 감지

## 목표 규칙

### R1. 변경 종류 → 갱신 대상 매핑

- **Default**: 다음 매핑에 따라 갱신
  | 변경 종류 | 갱신 대상 |
  |---|---|
  | 기능 추가/수정 | `docs/ai/CURRENT_STATE.md` |
  | 테스트 수행 | `docs/ai/catalogs/TEST_HISTORY.md` + `tests/evidence/` |
  | 구조/모듈 변경 | `docs/ai/catalogs/PROJECT_MAP.md` + fingerprint 갱신 |
  | 컨벤션 위반 발견 | `docs/ai/catalogs/CONVENTION_DRIFT.md` |
  | 보안 이슈 발견 | `docs/ai/policy/SECURITY_POLICY.md` |
  | 다음 작업 식별 | `docs/ai/NEXT_ACTIONS.md` |
  | 실패·반복 실수 | `docs/ai/catalogs/FAILURE_PATTERNS.md` (append-only) |
  | Round 검증 | `tests/evidence/<날짜>-<vendor>.md` + `docs/reference/decision-log.md` |
  | 외부 시스템 계약 변경 | `docs/ai/catalogs/EXTERNAL_CONTRACTS.md` |
  | 벤더 어댑터 추가 | `docs/ai/catalogs/VENDOR_ADAPTERS.md` + `.claude/ai-context/vendors/` |
- **Allowed**: 영향 없는 항목은 skip 가능. 단 "X 영향 없음" 명시
- **Forbidden**: 코드 변경 + 매핑된 문서 갱신 누락
- **Why**: 다음 세션이 진실성 있는 reference로 사용. 갱신 누락 시 stale catalog로 잘못된 판단
- **재검토**: 자동 doc-sync hook 도입 시

### R2. PROJECT_MAP fingerprint 갱신

- **Default**: 구조 변경 시 `python scripts/ai/check_project_map_drift.py --update`
- **Allowed**: 세션 시작 hook이 자동 drift 체크 — 사용자가 인지하면 명시적 update
- **Forbidden**: 디렉터리 추가/삭제 후 fingerprint 미갱신
- **Why**: stale fingerprint → 매 세션 drift 경고 noise. 진짜 drift 발견 어려움
- **재검토**: 자동 fingerprint 갱신 hook 도입 시

### R3. 문서 작성 원칙

- **Default**:
  - 한국어 기본 (영어 기술 용어 병기 가능 — `redfish_gather.py`, `iDRAC`)
  - 실제 결과만 기록 (추정은 "추정" 명시)
  - 절대 날짜 (YYYY-MM-DD)
  - 실무자 문서처럼 (마케팅 문구 금지)
- **Allowed**: AI 전용 문서 (`.claude/rules/`, `.claude/skills/`, `.claude/agents/`)는 컨텍스트 효율 위해 간결
- **Forbidden**:
  - 상대 날짜 ("어제", "지난주")
  - 추정을 사실처럼 (rule 25 R7-B 정신)
  - 마케팅 표현 ("강력한", "혁신적인", "최첨단")
- **Why**: AI가 catalog를 reference로 사용 시 진실성 + 시간 경과 후 해석 가능성 보장
- **재검토**: 자동 문체 검사 도구 도입 시

### R4. 정본 문서 보호

- **Default**: 정본은 실제 변경이 있을 때만 수정
  - `CLAUDE.md`, `REQUIREMENTS.md`, `README.md`
  - `docs/` 문서
  - `.claude/{rules,policy,skills,agents,ai-context,templates}/`
- **Allowed**: 사용자 명시 승인 후 정본 수정
- **Forbidden**:
  - 설명 다듬기 용도의 수정 (cycle 작업 중 "더 나아 보이게" 같은 의도)
  - 본문 cycle 번호 태그 박기 (cycle 진행 흔적은 `harness/cycle-*-log.md`에)
- **Why**: 정본은 cycle 영향 받지 않는 안정 reference. 자주 변경 시 git blame 노이즈 + 의미 변동 위험
- **재검토**: 정본 변경 자동 검출 hook 도입 시

### R5. 문서 보존 판정 (근본 질문)

- **Default**: 문서 작성/유지 결정 시 "**다음 기능 개발 / 리팩토링 / 리뷰 / 디버깅 작업에서 AI가 이 문서를 참조하면 실제 도움이 되는가?**"
  - YES → 남긴다 (active 위치)
  - NO → 남기지 않는다 (삭제 또는 archive)
- **Allowed (남김)**:
  | 유형 | 예시 |
  |---|---|
  | 현재 유효한 규칙 | `.claude/rules/*.md`, `.claude/policy/*.yaml` |
  | 결정의 reasoning | `docs/ai/decisions/ADR-*.md` |
  | 실행 패턴 사례 | `docs/ai/impact/*.md`, `handoff/*.md` |
  | 현재 상태 스냅샷 | `CURRENT_STATE.md`, `PROJECT_MAP.md` |
  | 알려진 이슈 | `CONVENTION_DRIFT.md`, `FAILURE_PATTERNS.md` |
  | 외부 계약 노트 | `EXTERNAL_CONTRACTS.md` |
  | Round 검증 결과 | `tests/evidence/` |
  | 실측 매트릭스 | `VENDOR_ADAPTERS.md`, `JENKINS_PIPELINES.md` |
- **Forbidden (남기지 않음)**:
  - V1/V2/V3 parallel 버전 (in-place 갱신 원칙)
  - 본문에 cycle 번호 태그 (cycle 로그에)
  - 1회성 audit/review (정책 흡수된 것)
- **Why**: server-exporter는 내부 프로젝트 + 감사 비대상. 감사 이력은 git log/cycle log에 보존. catalog 비대화는 catalog stale 가속
- **재검토**: 외부 감사 요건 도입 시

### R6. Archive 진입 기준

- **Default (archive)**: 다음 유형은 `docs/ai/archive/`로 이동
  | 유형 | 예시 |
  |---|---|
  | 구조·정책 전환의 결정 이력 | `INITIAL_STATE_*.md` |
  | 완결된 cycle 로그 (최신 N개 제외) | `cycle-001.md` ~ |
  | Deprecated active 문서 과거본 | `FOO_V1.md` (V2가 active 일 때) |
- **Default (물리 삭제)**: 다음은 git log에 맡기고 삭제
  | 유형 | 예시 |
  |---|---|
  | 1회성 빌드/배포 로그 | `BUILD_VERIFICATION_LOG.md` |
  | 1회성 cleanup 보고서 | `ARTIFACT_CLEANUP_*.md` |
  | PR description 복제본 | (PR에 이미 있음) |
- **판정 3 질문**:
  1. "왜 지금 이 모습인지"를 설명하나? → archive
  2. git log / cycle log에 이미 있나? → 삭제
  3. 6개월 내 "이 파일 어디?" 물을 사람? → archive
- **Forbidden**: 1회성 review를 같은 cycle에서 archive 안 옮김 (catalog 누적 가속)
- **Why**: archive는 역사 근거. 삭제는 git log에 맡김. 둘 다 active catalog 비대화 차단
- **재검토**: archive 자동 분류 도구 도입 시

### R7. cycle 자문 의무

- **Default**: 매 cycle 종료 시 "이번 cycle에서 추가한 문서 중 '감사 증명용 이력'인 것은? → archive 또는 삭제"
- **Allowed**: 의심스러우면 archive (안전한 쪽)
- **Forbidden**: 자문 skip 후 active catalog 누적
- **Why**: 매 cycle 자문이 가장 효과적인 catalog stale 차단
- **재검토**: cycle 종료 자동 archive hook 도입 시

### R8. ADR 의무 trigger (governance trace)

- **Default**: 다음 3 trigger 중 하나라도 해당 시 `docs/ai/decisions/ADR-YYYY-MM-DD-<주제>.md` 작성 의무
  1. **rule 본문 의미 변경** — Default / Allowed / Forbidden 절 추가·삭제·변경 (오타·표현 다듬기 제외). 예: rule 12 R1 Allowed 절 추가 (DRIFT-006)
  2. **표면 카운트 변경** — `.claude/policy/surface-counts.yaml`의 rules / skills / agents / policies 카운트 증감
  3. **보호 경로 정책 변경** — `.claude/policy/protected-paths.yaml` 추가·삭제·완화
- **Allowed**: 위 3 trigger 외의 결정은 rule 본문 + `CONVENTION_DRIFT.md` 만으로 trace
- **Forbidden**:
  - 3 trigger 발생 + ADR 작성 누락
  - ADR 없이 표면 카운트 + rule 본문 동시 변경
- **ADR 필수 4 섹션**: 컨텍스트(Why) / 결정(What) / 결과(Impact) / 대안 비교(Considered)
- **Why**: governance 결정은 미래 작업자가 "왜 이 정책인지" 추적 가능해야 함. 작은 결정은 rule 본문에 흡수, 큰 결정은 ADR로 reasoning 분리. 모든 결정 ADR 의무화는 overhead 과대 (06-A 거절 사유)
- **재검토**: ADR 작성 자동화 도구 도입 시 trigger 확대 검토

## 금지 패턴

- 코드 변경 후 문서 갱신 누락 — R1
- PROJECT_MAP fingerprint 미갱신 — R2
- 상대 날짜 / 추정 사실화 — R3
- 정본 설명 다듬기 — R4
- V-number 증가 / 본문 cycle 태그 — R5
- 1회성 review를 active catalog에 누적 — R5/R6
- cycle 자문 skip — R7
- 3 trigger 발생 + ADR 누락 — R8

## 리뷰 포인트

- [ ] 코드 변경 PR이 CURRENT_STATE 갱신 포함
- [ ] 테스트 결과 TEST_HISTORY 기록
- [ ] PROJECT_MAP fingerprint 갱신 (구조 변경 시)
- [ ] 절대 날짜 (YYYY-MM-DD)
- [ ] cycle 종료 시 자문
- [ ] R8 trigger 해당 시 ADR 작성

## 관련

- rule: `24-completion-gate` R3, `28-empirical-verification-lifecycle`
- skill: `update-evidence-docs`, `measure-reality-snapshot`
- templates: `.claude/templates/CURRENT_STATE.template.md` 등
