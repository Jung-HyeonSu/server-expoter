---
name: measure-reality-snapshot
description: rule 28 R1 카탈로그 13종 측정 대상을 TTL / 무효화 trigger 기반으로 재측정 또는 캐시 사용 판정. 사용자가 "실측해줘", "최신 정보 맞아?" 요청 시 또는 장기 세션 중간 동기화. - 코드 작업 시작 전 / 측정 대상 stale 의심 / 사용자 명시 요청
---

# measure-reality-snapshot

## 목적

server-exporter rule 28 R1의 11 측정 대상을 캐시 vs 재측정 자동 판정. 컨텍스트 / 시간 vs 정확도 균형.

## 11 측정 대상 (정본: `.claude/policy/measurement-targets.yaml`)

| # | 대상 | TTL | trigger | 명령 |
|---|---|---|---|---|
| 1 | 출력 schema | 14d | sections.yml/field_dictionary 수정 | output_schema_drift_check.py |
| 2 | PROJECT_MAP | 7d | 디렉터리 추가/삭제 | check_project_map_drift.py |
| 3 | 벤더 어댑터 매트릭스 | 14d | adapters/*.yml 수정 | grep + summarize |
| 4 | callback URL endpoint | 7d | Jenkinsfile 수정 | grep callback_url |
| 5 | Jenkinsfile cron | 14d | cron 표현식 변경 | grep cron Jenkinsfile* |
| 6 | 하네스 표면 카운트 | 1d | .claude/ 추가/삭제 | pre_commit_harness_drift.py |
| 7 | 벤더 baseline | 30d | baseline JSON 수정 | ls schema/baseline_v1/ |
| 8 | Fragment 토폴로지 | 14d | gather/normalize 수정 | grep fragment 변수 |
| 9 | 브랜치 갭 | 세션 | merge/pull/rebase | check_gap_against_main.py |
| 10 | 벤더 경계 위반 | 커밋마다 | 커밋 | verify_vendor_boundary.py |
| 11 | 외부 시스템 계약 | 90d | 펌웨어 업그레이드 | probe-redfish-vendor skill |

## 절차 (rule 28 R2)

```
Step 1  저장 위치에서 캐시 조회
Step 2  TTL / trigger 확인
Step 3  만료/무효화 → 재측정 + 갱신 + "재측정 수행" 명시
Step 4  유효 → 캐시 사용 + "last measured: YYYY-MM-DD" 명시
```

## 출력

```markdown
## 측정 대상 13종 상태

| # | 대상 | last measured | TTL | 상태 |
|---|---|---|---|---|
| 1 | 출력 schema | 2026-04-25 (2일 전) | 14d | 캐시 사용 |
| 2 | PROJECT_MAP | 2026-04-27 (오늘) | 7d | 캐시 사용 |
| 3 | 벤더 어댑터 매트릭스 | (없음) | 14d | **재측정 필요** |
| ... |

### 재측정 수행
- #3 벤더 어댑터 매트릭스 → docs/ai/catalogs/VENDOR_ADAPTERS.md 갱신 (커밋 X)
```

## 적용 rule / 관련

- **rule 28** (empirical-verification-lifecycle) 정본
- policy: `.claude/policy/measurement-targets.yaml`
- skill: `update-evidence-docs`
- catalogs: `docs/ai/catalogs/PROJECT_MAP.md`, `VENDOR_ADAPTERS.md`, `SCHEMA_FIELDS.md`, `EXTERNAL_CONTRACTS.md`, `JENKINS_PIPELINES.md`
