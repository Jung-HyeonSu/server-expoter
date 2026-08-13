---
name: prepare-regression-check
description: 변경된 코드 기반 회귀 테스트 대상 선정 + 테스트 계획. 사용자가 "어떤 테스트 돌려야 해?", "회귀 검사" 등 요청 시. - 코드 변경 후 / PR 머지 전 / Jenkins Stage 4 사전 점검
---

# prepare-regression-check

## 목적

server-exporter 회귀 테스트 대상을 자동 선정. 변경 경로 → 테스트 영역 매핑은 rule 91 R7 과 rule 92 R3 을 따른다.

## 절차

1. **변경 파일 list 추출**: `git diff --name-only`
2. **각 파일을 아래 영역 매핑과 매칭**:
   - `os-gather/**` → 회귀: pytest probe + Linux/Windows 실장비
   - `redfish-gather/**` → probe_redfish + 영향 vendor baseline
   - `common/library/**` → 4단계 진단 회귀 (모든 채널)
   - `schema/sections.yml` → schema validate + 영향 vendor baseline
   - `adapters/{channel}/{vendor}_*.yml` → score-adapter-match + 해당 vendor baseline
   - `Jenkinsfile*` → Jenkins 4-Stage dry-run
   - `vault/**` → rotate-vault 절차 + dry-run
3. **회귀 영역 자동 포함** (rule 91 R7 / rule 92 R9):
   - 공통 fragment / adapter / callback / Jenkinsfile cron / 출력 schema / vault
4. **테스트 명령 list 출력**

## 출력

```markdown
## 회귀 테스트 계획 — <변경 요약>

### 대상 영역
- redfish-gather/library/redfish_gather.py (수정)
- adapters/redfish/dell_idrac9.yml (수정)
- common/tasks/normalize/build_storage.yml (수정)

### 회귀 명령
1. `ansible-playbook --syntax-check redfish-gather/site.yml`
2. `pytest tests/redfish-probe/probe_redfish.py --vendor dell -v`
3. `pytest tests/regression/ -k dell -v` (영향 vendor 회귀)
4. `pytest tests/regression/ tests/e2e/ -v` (전 vendor — common 변경)
5. `python scripts/ai/hooks/output_schema_drift_check.py`
6. `python scripts/ai/verify_vendor_boundary.py`
7. `python scripts/ai/verify_harness_consistency.py`

### 실장비 검증 필요
- Dell iDRAC9 1대 이상 (Round X)

### 우선순위
- P0: 1 / 2 / 3 (직접 영향)
- P1: 4 / 5 (간접 영향)
- P2: 6 / 7 (정합성 검증)
```

## 적용 rule / 관련

- **rule 40** (qa-pytest-baseline) 정본
- rule 91 R7 / rule 92 R9 (자동 회귀 영역)
- rule: `91-task-impact-gate` R7, `92-dependency-and-regression-gate` R3
- skill: `vendor-change-impact`, `run-baseline-smoke`, `task-impact-preview`
- agent: `qa-regression-worker`
