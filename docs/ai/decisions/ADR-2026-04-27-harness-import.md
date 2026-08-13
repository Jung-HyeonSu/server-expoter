# ADR-2026-04-27 — clovirone-base 풀스펙 하네스 도입

## 상태

**Accepted** (2026-04-27)

## 컨텍스트 (Why)

server-exporter는 Ansible/Python/Jenkins 기반 멀티벤더 서버 수집 파이프라인으로 프로덕션 준비 상태(Round 7-10 완료). 하지만 AI 협업 시:

- Fragment 철학 / 벤더 경계 / 출력 schema 정합 같은 도메인 규칙이 rule 22 (fragment-philosophy)에 분산
- 새 vendor 추가 / schema 변경 / Jenkinsfile cron 같은 작업의 영향 분석이 ad-hoc
- 작업 영역 침범 (다른 gather fragment 수정) / 회귀 누락 / 외부 계약 drift 사고 가능성

clovirone-base는 같은 ecosystem (Java/Spring/Vue/MyBatis) 도메인에서 정교한 self-improvement 하네스 운영. 그 패턴을 server-exporter 도메인 어휘로 1:1 포팅하면 검증된 게이트와 자기개선 루프를 즉시 도입 가능.

## 결정 (What)

clovirone-base/.claude/를 server-exporter 도메인으로 풀스펙 포팅.

| 결정 | 선택 |
|---|---|
| 야심 규모 | 풀스펙 포팅 (1:1 구조 보존) |
| customer-plugin slot | vendor만 (Dell/HPE/Lenovo/Supermicro/Cisco) |
| branch 정책 | main + feature/* 단순 (3계층 도입 안 함) |
| role 분류 | 6 (gather/output-schema/infra/qa/po/tpm) |
| 기존 문서 | 무수정 (CLAUDE.md만 Tier 0 보강) |
| 자기개선 루프 7 agents | 유지 |
| docs/ai/ 운영 메타 | 신규 (clovirone과 동일 패턴) |

## 결과 (Impact)

신규 약 220 파일. 기존 server-exporter 코드/문서 무수정.

| 카테고리 | 카운트 |
|---|---|
| settings.json + hooks | 28 + 1 |
| supporting scripts | 8 |
| rules | 29 |
| skills | 43 |
| agents | 51 |
| policies | 10 |
| roles | 6 |
| ai-context | 12 |
| templates | 10 |
| commands | 5 |
| references | 7 |
| docs/ai/ 운영 메타 | ~25 |

핵심 게이트:
- rule 22 (Fragment 철학) — server-exporter 핵심
- rule 12 (Adapter 경계) — vendor 하드코딩 차단
- rule 91 (task-impact-preview) — 변경 영향 자동 미리보기
- rule 24 (completion-gate) — 완료 6 체크
- rule 95 (production-critical) — 의심 패턴 11종
- rule 96 (external-contract) — Redfish/IPMI/SSH/WinRM/vSphere drift 차단

## 대안 (기각)

### 안 B. 핵심 추출 (Right-sized)
- 검증된 핵심 게이트만 살리고 운영 부담 줄이기
- 약 15~20 rules / 15~20 skills / 10~15 agents 규모
- 기각 사유: 사용자가 "전체를 다 뒤집어야할거야"라고 명시 + 풀스펙 포팅 지시. 사용 패턴 누적 후 keep/drop 재결정 가능.

### 안 C. 미니멀 부트스트랩
- 5~7 rules / 3~5 skills / 2~3 agents부터 시작
- 기각 사유: server-exporter가 이미 프로덕션 단계 — 작은 부트스트랩은 발전 속도 지연.

## 검증 결과 (Plan 1+2 종료 시점)

- `verify_harness_consistency.py`: PASS (참조 위반 0 / 잔재 어휘 0)
- `session_start.py`: 정상 (브랜치 main 인지)
- `commit_msg_check.py --self-test`: 6/6 PASS
- 모든 Python ast.parse PASS
- 기존 코드 회귀 영향 없음 (도메인 코드 무수정)

## 후속 (Plan 3 + 운영)

- docs/ai/ 운영 메타 문서 (catalogs / decisions / policy / workflows / harness / handoff / impact / incoming-review / roadmap / onboarding)
- 자기개선 루프 dry-run + 정기 cycle 도입
- 새 vendor 추가 시 add-new-vendor skill 검증

## 관련

- 설계서: 하네스 이식 계획(정리됨)
- 실행 계획: 하네스 이식 계획(정리됨)
- 정본: `CLAUDE.md` (Tier 0 보강)
- commits: ef5335b → b152898 → d87af96 → 31526c3 → ee82f1b → 031b32e → 63eaceb → 183a79e → 2b3268f → 145a0b1

## 결정 주체

- **제안자 (AI)**: 풀스펙 포팅 추천 + 4 핵심 결정에 대해 brainstorming skill로 사용자 합의
- **승인자**: hshwang1994 (2026-04-27 대화 승인)
