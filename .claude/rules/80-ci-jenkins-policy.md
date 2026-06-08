# CI / Jenkins 정책

## 적용 대상
- `Jenkinsfile`, `Jenkinsfile_portal`
- `ansible.cfg`
- Jenkins Job 등록 (docs/04)
- callback URL endpoint 구성

## 현재 관찰된 현실

- Jenkins multi-pipeline 2종 (`Jenkinsfile` / `Jenkinsfile_portal`) — cycle-015에서 `Jenkinsfile_grafana` 제거 (사용자 명시 결정 — Grafana 적재 미사용)
- 외부 CI 시스템 미사용 (Jenkins 단독)
- 4-Stage: Validate / Gather / Validate Schema / **(pipeline별 Stage 4)** — 아래 R1-A 참조
- agent-master 망 분리: Ingest / Callback은 master, gather는 agent

## 목표 규칙

### R1. 4-Stage 의무

모든 Jenkinsfile은 4-Stage 통과 후 callback POST:

| Stage | 책임 | FAIL 게이트 |
|---|---|---|
| 1. Validate | 입력값 (loc / target_type / inventory_json) 형식 검증 | YES |
| 2. Gather | ansible-playbook 실행 (해당 채널 site.yml) | YES |
| 3. Validate Schema | field_dictionary 정합 (`output_schema_drift_check`) | YES |
| 4. (pipeline별, 아래 R1-A 참조) | YES |
| Post | json_only callback → JSON 출력 | NO (advisory) |

### R1-A. Stage 4 (pipeline별 차이)

| Pipeline | Stage 4 | 책임 |
|---|---|---|
| `Jenkinsfile` | E2E Regression | pytest baseline 회귀 (영향 vendor) + 오프라인 회귀 하네스 (`tests/integration/ -m "not live"` — HPE iLO 에뮬레이터 + DMTF 표준 mockup, 2026-06-08 — 별도 invocation) |
| `Jenkinsfile_portal` | Callback | 호출자 통보 (master 실행, rule 31 무결성) |

> **cycle-015**: `Jenkinsfile_grafana` 제거됨 (사용자 명시 결정).

상세: `docs/ai/catalogs/JENKINS_PIPELINES.md`.

### R2. cron 변경 사용자 승인

- **Default**: cron 표현식 변경은 사용자 명시 승인 (rule 92 R5와 동일 정신)
- **Forbidden**: AI가 임의로 cron 변경 (운영 영향 큼)

`pre_commit_jenkinsfile_guard.py`가 advisory.

### R3. agent-master 망 분리

- Callback 단계 → master (`Jenkinsfile_portal`)
- gather (ansible-playbook) → agent 실행

### R4. 빌드 실패 분석

- **Default**: 실패 시 `investigate-ci-failure` skill로 console log 분석
- **재시도**: 실패가 일시적 (네트워크 / 외부 시스템 timeout)이면 재시도. 코드/설정 문제면 fix 후 재실행

### R5. 단계적 적용

- 운영 배포 시간대 외
- 일부 loc만 먼저 (현재 단일 loc 운영이면 적용 안 함)
- callback URL 무결성 (rule 31)

### R6. 모니터링

- 첫 cron 실행 결과 모니터링
- Jenkins 빌드 시간 / 성공률 baseline 대비

## 금지 패턴

- 4-Stage 일부 skip — R1
- AI 임의 cron 변경 — R2
- agent에서 Ingest / Callback 실행 — R3
- 빌드 실패 후 분석 없이 재시도 반복 — R4

## 리뷰 포인트

- [ ] Jenkinsfile 변경이 4-Stage 유지
- [ ] cron 변경 사용자 승인
- [ ] agent-master 망 분리 준수

## 관련

- rule: `31-integration-callback`, `92-dependency-and-regression-gate`
- skill: `scheduler-change-playbook`, `investigate-ci-failure`
- agent: `jenkins-refactor-worker`, `jenkinsfile-engineer`, `ci-failure-investigator`
- 정본: `docs/01_jenkins-setup.md`, `docs/04_job-registration.md`, `docs/17_jenkins-pipeline.md`
