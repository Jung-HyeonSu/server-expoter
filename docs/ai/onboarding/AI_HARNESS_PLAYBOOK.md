# server-exporter AI Harness Playbook (Onboarding)

> 신규 작업자 / AI 진입 가이드. 사람용 — rule 23 R5 (5W1H + 사람 친화 어휘).

## 무엇 (What)

server-exporter는 엔터프라이즈급 멀티벤더 서버 정보 수집 파이프라인 (Ansible + Python + Jenkins, 3-channel × 5 vendor). 본 하네스는 AI 협업 시 도메인 규칙 / 영향 분석 / 회귀 / 보안을 일관 적용하기 위한 인프라.

## 왜 (Why)

- Fragment 철학 / 벤더 경계 / 출력 schema 정합 같은 도메인 규칙을 **AI가 자동 적용**
- 새 vendor 추가 / schema 변경 / Jenkinsfile cron 같은 작업에 **사전 영향 미리보기**
- 사고 / 의심 패턴을 **append-only 카탈로그로 누적 학습**
- 자기개선 루프로 **시간이 갈수록 정확도 향상**

## 어디서 (Where) — 5분 진입

### 신규 사용자

1. `CLAUDE.md` (Tier 0 정본) — 5분 읽기
2. rule 22 (fragment-philosophy) — 가장 중요한 도메인 규칙
3. `REQUIREMENTS.md` — 벤더 / 펌웨어 검증 기준
4. `docs/develop/01-gather-structure.md` — 3-channel 흐름

### 신규 AI 세션

1. session_start hook이 자동 출력 (브랜치 / 측정 대상 / 구조 issue)
2. 사용자 첫 메시지에서 **역할 자동 추론** (`docs/ai/policy/SESSION_ROUTING_POLICY.md`)
3. 코드 변경 요청 시 **task-impact-preview 자동 호출** (rule 91 R1)

## 누가 (Who)

| 역할 | 책임 |
|---|---|
| gather | 3-channel gather (os/esxi/redfish) |
| output-schema | sections / field_dictionary / baseline / callback |
| infra | Jenkinsfile / Agent / Vault / Redis |
| qa | pytest / probe / 실장비 검증 |
| po | 요구사항 / 벤더 추가 결정 |
| tpm | Round 진행률 / 릴리즈 / docs/ai 갱신 |

각 role README: `.claude/role/<role>/README.md`.

## 어떻게 (How) — 일반 작업 플로우

### 새 기능 추가

1. `analyze-new-requirement` (선택)
2. **`task-impact-preview` 자동** (rule 91)
3. 리스크별 라우팅 (`docs/ai/policy/DYNAMIC_ROUTING_RULES.md`)
4. 구현 (skill / agent 위임)
5. 회귀 (`prepare-regression-check` → `run-baseline-smoke`)
6. PR (`pr-review-playbook`)
7. 머지 (rule 93 R5 squash)

### 새 vendor 추가

1. PO 결정 (rule 50 R2)
2. `probe-redfish-vendor` (펌웨어 프로파일)
3. `add-new-vendor` skill (9 단계)
4. `update-vendor-baseline` (실장비 검증 후)
5. PR + 리뷰

### 사고 발생

1. 즉시 affected commit revert 검토 (`rollback-advisor`)
2. `FAILURE_PATTERNS.md` append (즉시)
3. `investigate-ci-failure` (Jenkins 실패면)
4. rule / skill 보강 cycle

## 절대 금지사항 8 (CLAUDE.md "절대 금지사항" 정본)

1. 비밀값 하드코딩
2. 보호 경로 자율 수정
3. 벤더 경계 위반 (gather 코드에 vendor 이름)
4. Fragment 침범 (다른 gather의 fragment 변수 수정)
5. 외부 라이브러리 추가 (redfish library는 stdlib only)
6. 문서 갱신 누락
7. bypassPermissions
8. 전역 설정 자율 수정

## 자주 사용하는 명령

```bash
# 세션 시작 (자동)
python scripts/ai/hooks/session_start.py

# Fragment 검증
# (skill: validate-fragment-philosophy)

# Adapter 점수 디버그
# (skill: score-adapter-match)

# Vendor 경계 검증
python scripts/ai/verify_vendor_boundary.py

# 하네스 일관성
python scripts/ai/verify_harness_consistency.py

# 측정 대상 재 snapshot
# (skill: measure-reality-snapshot)

# 회귀 빠르게
# pytest tests/redfish-probe/test_baseline.py --vendor dell -v

# git hooks 설치
bash scripts/ai/hooks/install-git-hooks.sh
```

## 어디서 도움 받기

| 질문 | 보세요 |
|---|---|
| 무엇을 어떻게 하지? | `.claude/commands/usage-guide.md` |
| 코드 리뷰 절차 | `.claude/commands/review-guide.md` |
| Jenkins cron 변경 | `.claude/commands/scheduler-guide.md` |
| 하네스 cycle 실행 | `.claude/commands/harness-cycle.md` 또는 `/harness-cycle` |
| 새 벤더 추가 | skill `add-new-vendor` |
| 외부 시스템 reference | `docs/ai/references/` |
| 사고 패턴 | `docs/ai/catalogs/FAILURE_PATTERNS.md` |
| 결정 기록 | `docs/ai/decisions/` |

## 정본 reference

- `CLAUDE.md` (Tier 0)
- rule 22 (fragment-philosophy) (Fragment 철학)
- `REQUIREMENTS.md`
- `docs/01_jenkins-setup ~ 19_decision-log` (운영 정본)
- `docs/ai/CURRENT_STATE.md` (현재 상태)
- `docs/ai/NEXT_ACTIONS.md` (다음 작업)
