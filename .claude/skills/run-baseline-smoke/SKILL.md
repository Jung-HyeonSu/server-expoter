---
name: run-baseline-smoke
description: vendor fixture 기반 빠른 baseline 회귀. 실장비 없이 mock fixture로 핵심 회귀 점검. 사용자가 "빠른 회귀", "smoke test", "baseline smoke" 등 요청 시 또는 PR 머지 직전. - PR 직전 빠른 점검 / common 변경 후 / 실장비 없는 환경 / Jenkins Stage 4 dry-run
---

# run-baseline-smoke

## 목적

server-exporter baseline 회귀를 빠르게 (실장비 없이 fixture만) 실행. vendor 별 fixture 단위 smoke.

## 절차

```bash
# 영향 vendor만 (변경 영역 따라)
pytest tests/regression/ -k dell -v

# 전수
pytest tests/regression/ -v

# 빠른 mode (fixture만, 실장비 skip)
pytest tests/regression/ tests/e2e/ -m "not live" -v

# schema 검증 동반
python scripts/ai/hooks/output_schema_drift_check.py
```

## 입력

- 영향 vendor list (vendor-change-impact 결과)
- 또는 전수

## 출력

```markdown
## Baseline Smoke 결과

| Vendor | Fixture | Result | 시간 |
|---|---|---|---|
| dell_idrac9 | dell_idrac9_baseline.json | PASS | 2.3s |
| hpe_ilo5 | hpe_ilo5_baseline.json | PASS | 1.8s |
| lenovo_xcc | lenovo_xcc_baseline.json | FAIL | — |
| supermicro_x12 | (fixture 없음) | SKIP | — |
| cisco_cimc | cisco_cimc_baseline.json | PASS | 1.5s |

### FAIL: lenovo_xcc
- 차이: storage.volumes 배열 길이 (예상 3, 실제 2)
- 원인 추정: 최근 schema 변경의 영향
- 다음 단계: prepare-regression-check + 수동 분석
```

## 자동 호출 시점

- PR 머지 직전 (rule 24 R1 정적 검증 일환)
- common / schema 변경 후 (rule 91 R7 자동 회귀 영역)
- Jenkins Stage 4 (E2E Regression) dry-run

## 적용 rule / 관련

- **rule 40** (qa-pytest-baseline)
- rule 24 (completion-gate) — 정적 검증 일부
- skill: `prepare-regression-check`, `update-vendor-baseline`, `vendor-change-impact`
- agent: `qa-regression-worker`, `baseline-validation-worker`
- 정본: `docs/reference/live-validation.md`
