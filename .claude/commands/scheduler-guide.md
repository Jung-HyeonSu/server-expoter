---
description: server-exporter Jenkinsfile cron / scheduler 변경 절차 가이드.
argument-hint: "[Jenkinsfile name]"
---

# /scheduler-guide

server-exporter Jenkins cron / scheduler 변경 안전 절차 (rule 80 + 92 R5).

## 대상

- `Jenkinsfile` — 메인 (3-channel 통합)
- `Jenkinsfile_portal` — Portal 호출

## 변경 절차

### Step 1: 영향 분석

- `task-impact-preview` skill 호출
- 해당 Jenkinsfile이 어느 호출자 / 어느 loc / 어느 채널을 처리하는지 명시
- 변경 시간대가 운영 환경 영향 (배포 / 정기 점검) 충돌 여부

### Step 2: 사용자 승인

cron 표현식 변경은 **사용자 명시 승인** 필수 (rule 92 R5와 동일 정신):
- WHY: 왜 변경하는가
- WHAT: 변경 내용 (cron 식 before → after)
- IMPACT: 영향 범위 (Jenkins 빌드 빈도 / agent 부하 / 호출자 시간 윈도우)
- 결정 필요: 진행 / 조정 / 취소

`pre_commit_jenkinsfile_guard.py`가 advisory로 cron 변경 감지.

### Step 3: 변경 + 4-Stage 검증

- 변경 commit
- Jenkins dry-run (가능 시): 4-Stage (Validate / Gather / Validate Schema / E2E Regression) 통과
- 영향 vendor baseline 회귀 (Stage 4)

### Step 4: 단계적 적용

- 운영 배포 시간대 외 (rule 80)
- 일부 loc만 먼저 (ich → chj → yi 순) — 단일 loc 운영이면 단일 적용
- callback URL 무결성 (rule 31) 확인

### Step 5: 모니터링

- 첫 cron 실행 결과 모니터링
- Jenkins 빌드 시간 / 성공률 baseline 대비 비교

## 자동 검사

- `pre_commit_jenkinsfile_guard.py` — cron 변경 감지 (advisory)
- `post_commit_measurement_trigger.py` — Jenkinsfile 변경 시 docs/ai/catalogs/JENKINS_PIPELINES.md 갱신 권고

## 관련

- skill: `scheduler-change-playbook`, `task-impact-preview`, `investigate-ci-failure`
- agent: `jenkins-refactor-worker`, `jenkinsfile-engineer`, `release-manager`, `deploy-orchestrator`
- rule: 80, 92 R5
- 정본: `docs/operate/04-pipeline-runtime.md`
