---
name: vendor-change-impact
description: 코드 변경이 server-exporter 의 vendor (정본 `common/vars/vendor_aliases.yml`) 에 미치는 영향 분석. 사용자가 "Lenovo에 영향?", "이 변경 다른 vendor도 영향 있어?", "벤더별 영향" 등 요청 시. - common 또는 3-channel 코드 변경 / adapter 변경 / schema 변경 후 영향 vendor 식별 필요
---

# vendor-change-impact

## 목적

common / 3-channel 코드 변경이 어느 vendor adapter / vendor baseline에 영향을 주는지 분석. PR 머지 전 회귀 검사 대상 결정.

## 입력

- 변경 파일 list 또는 PR 번호

## 출력

```markdown
## Vendor 영향 — <변경 요약>

### 영향 매트릭스

| Vendor | 영향 | 회귀 필요 | 근거 |
|---|---|---|---|
| Dell | YES | baseline 회귀 | adapter dell_idrac9.yml 경유 변경 |
| HPE | YES (간접) | baseline 회귀 | common/library/precheck_bundle.py 변경 |
| Lenovo | YES (간접) | baseline 회귀 | 동일 |
| Supermicro | YES (간접) | baseline 회귀 | 동일 |
| Cisco | NO | (skip) | 변경 영역 미경유 |

### 회귀 우선순위
1. Dell (직접 변경)
2. HPE / Lenovo / Supermicro (간접)
3. Cisco는 skip 가능

### 권고
- pytest tests/regression/ -k dell 우선 실행
- 다른 vendor는 fixture 기반 회귀 (실장비 필요 없음)
```

## 절차

1. **변경 파일 분류**:
   - vendor-specific (`adapters/{channel}/{vendor}_*.yml`, 라이브러리 `_extract_oem_*`) → 해당 vendor만
   - common (`common/library/`, `common/tasks/normalize/`) → 모든 vendor 간접
   - schema (`schema/sections.yml`, `schema/field_dictionary.yml`) → Must 필드면 모든 vendor, Nice면 일부
2. **각 vendor 영향 평가**:
   - 직접: adapter 또는 OEM tasks 변경
   - 간접: common 또는 schema 변경
   - 무관: 변경 영역 미경유
3. **회귀 우선순위 산정**:
   - 직접 영향 > 간접 영향
   - 실장비 가용 vendor 먼저 (Round 검증)
4. **보고 + prepare-regression-check skill 후속**

## server-exporter 도메인 적용

- 영향 채널: 3-channel 모두 또는 일부
- 영향 vendor: 분석 결과
- 영향 schema: 변경 파일에 따라

## 적용 rule / 관련

- **rule 12** (adapter-vendor-boundary)
- rule 50 (vendor-adapter-policy)
- rule 91 R7 (회귀 검사 자동 식별)
- skill: `task-impact-preview`, `prepare-regression-check`, `verify-adapter-boundary`
- agent: `vendor-boundary-guardian`, `adapter-boundary-reviewer`, `change-impact-analyst`
- policy: `.claude/policy/vendor-boundary-map.yaml`
