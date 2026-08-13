---
name: scheduler-change-playbook
description: Jenkins cron / scheduler 변경 절차 (rule 80 + 92 R5). 사용자가 "스케줄러 바꿔줘", "Jenkins cron 변경", "배치 시간 조정" 등 요청 시. - Jenkinsfile* cron 표현식 변경 / triggers 블록 변경
---

# scheduler-change-playbook

## 절차 (rule 80 R2)

### Step 1: 영향 분석

- task-impact-preview 호출
- 어느 Jenkinsfile / 어느 호출자 / 어느 loc 영향
- 변경 시간대 운영 환경 충돌 (배포 / 정기 점검)

### Step 2: 사용자 명시 승인

cron 표현식 변경은 rule 92 R5와 동일 정신 — **사용자 명시 승인 필수**:

- WHY: 왜 변경
- WHAT: cron 식 before → after
- IMPACT: Jenkins 빌드 빈도 / agent 부하 / 호출자 시간 윈도우
- 결정 필요: 진행 / 조정 / 취소

`pre_commit_jenkinsfile_guard.py`가 advisory 검출.

### Step 3: 변경 + 4-Stage 검증

- 변경 commit
- Jenkins dry-run (가능 시): 4-Stage 통과
- 영향 vendor baseline 회귀 (Stage 4)

### Step 4: 단계적 적용

- 운영 배포 시간대 외 (rule 80)
- 일부 loc 먼저 (단일 loc 운영이면 적용 안 함)
- callback URL 무결성 확인 (rule 31)

### Step 5: 모니터링

- 첫 cron 실행 결과
- Jenkins 빌드 시간 / 성공률 baseline 대비

## 적용 rule / 관련

- **rule 80** (ci-jenkins-policy) 정본
- rule 92 R5 (사용자 확인)
- rule 91 (task-impact-preview)
- skill: `task-impact-preview`, `investigate-ci-failure`
- agent: `refactor-worker`, `jenkinsfile-engineer`
- script: `scripts/ai/hooks/pre_commit_jenkinsfile_guard.py`
- 정본: `docs/operate/04-pipeline-runtime.md`
- command: `/scheduler-guide`
