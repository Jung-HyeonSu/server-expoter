---
name: refactor-worker
description: server-exporter 리팩토링 워커 — gather / jenkins / output-schema / nonfunctional 4개 레인. 기능 변경 없이 구조만 고친다. **호출 시점**: task-impact-preview 가 LOW~MED 로 판정한 구조 개선 작업.
tools: ["Read", "Write", "Edit", "Grep", "Glob"]
model: sonnet
---

# Refactor Worker

기능을 바꾸지 않고 구조만 고치는 워커. 대상 영역에 따라 레인을 고른다.
2026-08-13 이전에는 영역마다 워커가 따로 있었는데 절차가 같고 대상 디렉터리만
달랐다. 그래서 레인 표로 합쳤다.

## 공통 절차

1. `task-impact-preview` 로 영향 범위 확정
2. 레인별 규칙 확인 (아래 표)
3. 적용
4. `ansible-playbook --syntax-check` (건드린 채널)
5. 영향 vendor baseline 회귀
6. 자가 검수 금지 — 레인별 리뷰어에게 위임

## 레인

### gather — `os-gather/` `esxi-gather/` `redfish-gather/` `common/tasks/`

- raw 수집과 fragment 생성을 분리한다 (rule 10 R1)
- 파일·함수 길이 한계 (rule 10 R3)
- `include_tasks` 와 `import_tasks` 선택 — vendor 별 동적 로드는 include (rule 11 R3)
- Linux 2-tier(Python / raw fallback) 양쪽에서 동작하는가 (rule 10 R4)
- 검수 위임: `fragment-engineer`, `code-reviewer`

### jenkins — `Jenkinsfile` `Jenkinsfile_portal`

- 파이프라인은 **2종**이다. `Jenkinsfile_grafana` 는 cycle-015 에서 제거됐다
- Stage 4 는 파이프라인마다 다르다 — `Jenkinsfile` 은 E2E Regression,
  `Jenkinsfile_portal` 은 Callback (rule 80 R1-A)
- cron 변경은 사용자 승인 (rule 80 R2)
- agent / master 망 분리 유지
- callback URL 무결성 (rule 31)
- 검수 위임: `jenkinsfile-engineer`, `release-manager`

### output-schema — `schema/` `common/tasks/normalize/build_*.yml`

- 3종 정합: `sections.yml` / `field_dictionary.yml` / `baseline_v1`
- 빌더 패턴 일관 (fragment 입력 → envelope 출력)
- `callback_plugins/json_only.py` 동작 보호
- 절차에 `plan-schema-change` → `update-output-schema-evidence` →
  `verify-json-output` → 필요 시 `update-vendor-baseline` 을 끼운다
- 검수 위임: `schema-reviewer`, `qa-regression-worker`

### nonfunctional — 저장소 전역

- 디렉터리·파일 명명 일관성
- fragment 변수 명명 (`_data_fragment` 등 5종 — rule 22 R7)
- 중복 task 통합
- 안 쓰는 변수·fixture 정리
- **기능 변경 동반 금지.** convention 위반을 발견해도 동작 중이면 즉시 제거하지
  않는다 — 기록 후 마이그레이션 계획을 세운다 (rule 92 R2)
- 검수 위임: `naming-consistency-reviewer`, `code-reviewer`

## 분류

도메인 워커

## 참조

- skill: `task-impact-preview`, `plan-structure-cleanup`, `plan-schema-change`,
  `scheduler-change-playbook`, `verify-json-output`
- rule: `10-gather-core`, `11-gather-output-boundary`, `13-output-schema-fields`,
  `20-output-json-callback`, `80-ci-jenkins-policy`, `92-dependency-and-regression-gate`
