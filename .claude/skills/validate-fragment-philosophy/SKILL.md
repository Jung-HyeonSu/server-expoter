---
name: validate-fragment-philosophy
description: server-exporter 핵심 규칙인 Fragment 철학 (rule 22) 위반을 검증한다. 각 gather가 자기 fragment만 만드는지, 다른 gather의 fragment를 침범하지 않는지, merge_fragment.yml 호출이 누락되지 않았는지 자동 검사. 사용자가 "fragment 침범 검사", "rule 22 검증", "이 PR이 다른 gather 영역 건드려?" 등 요청 시 또는 gather 코드 변경 후 자동 호출. - gather/normalize 코드 변경 후 / 새 gather 추가 / fragment 의심 패턴 발견 시
---

# validate-fragment-philosophy

## 목적

server-exporter의 가장 중요한 규칙(rule 22)을 자동 검증. Fragment 철학 위반은 회귀/누락/오염 동시 발생 → 사고 1순위 원인.

## 검사 항목 (rule 22 R1-R9)

1. **자기 fragment만**: 각 gather에서 set_fact가 5 공통 변수만 생성하고, 값으로 자기 섹션만 채우는가
   - 검사 대상: `_data_fragment`, `_sections_supported_fragment`, `_sections_collected_fragment`, `_sections_failed_fragment`, `_errors_fragment`
   - 위반 패턴 A: 변수 이름에 섹션명 추가 (예: `_sections_cpu_collected_fragment`)
   - 위반 패턴 B: 다른 gather가 만들어야 할 섹션을 자기 fragment list에 포함 (예: cpu gather에서 `_sections_collected_fragment: ['cpu', 'memory']`)
2. **누적 변수 침범 금지**: gather에서 `_collected_data`, `_supported_sections`, `_collected_sections`, `_failed_sections`, `_collected_errors` 직접 수정
3. **merge_fragment.yml 호출**: 각 gather 후 호출 존재
4. **fragment prefix `_`**: 모든 fragment 변수가 `_` prefix
5. **fragment 변수 타입**:
   - `_data_fragment` = dict (key=섹션 이름)
   - `_sections_{supported,collected,failed}_fragment` = list of strings
   - `_errors_fragment` = list of dicts
6. **vendor 하드코딩 없음** (rule 12 연동)
7. **builder 침범 없음**: gather에서 envelope 필드 (status / data / meta) 직접 set_fact 안 함

## 입력

- 검사 대상: `os-gather/`, `esxi-gather/`, `redfish-gather/`, `common/tasks/normalize/` 안의 변경된 파일
- 또는 전체 (rule 22 자동 점검)

## 출력

```markdown
## Fragment 철학 검증 결과

### Clean (검사 9 항목 통과)
또는

### 위반 N건

| # | 위반 | 파일 | 라인 | 심각도 |
|---|---|---|---|---|
| 1 | 다른 섹션 fragment 침범 | os-gather/tasks/linux/gather_memory.yml | 42 | CRITICAL |

### 권고
- {위반 1}: {수정 방향}
```

## 절차

1. **변경 파일 탐색**: `git diff --name-only HEAD~1..HEAD` 또는 staged
2. **gather 디렉터리 필터**: os/esxi/redfish-gather + common/tasks/normalize
3. **set_fact 패턴 grep**:
   - 변수 이름 분기 검출: `_sections_{section}_(supported|collected|failed)_fragment` 같은 비공통 변수
   - `_collected_data` / `_supported_sections` / `_collected_sections` / `_failed_sections` / `_collected_errors` (누적 변수 침범)
   - `status:` / `data:` / `meta:` 등 envelope 필드 직접 (builder 침범)
   - 자기 영역 외 섹션을 list에 포함하는 set_fact (의미 분석 필요 — 수동 보강)
4. **merge_fragment.yml 호출 확인**: 각 gather playbook의 마지막 task가 호출하는지
5. **타입 검증**: set_fact 본문이 dict / list 타입 정합
6. **vendor 하드코딩 검출**: `verify_vendor_boundary.py` 결과 통합
7. **결과 보고서 출력**

## server-exporter 도메인 적용

- 영향 채널: 모든 gather (os / esxi / redfish)
- 영향 vendor: agnostic
- 영향 schema: 간접 (fragment 침범 → 출력 envelope 오염)

## 실패 / 오탐 처리

- common/tasks/normalize/ 안의 builder는 누적 변수 set_fact 가능 (정상)
- gather가 같은 섹션의 fragment 여러 번 set_fact (병합)는 정상
- 한계: 동적 변수명 (예: `_data_fragment | combine(...)`) 일부 패턴 검출 어려움 — 수동 리뷰 보강

## 적용 rule / 관련

- **rule 22** (fragment-philosophy) — 본 skill의 정본 규칙
- rule 11 (gather-output-boundary) — builder 경계
- rule 12 (adapter-vendor-boundary) — vendor 하드코딩 (verify_vendor_boundary.py)
- skill: `task-impact-preview` (변경 영향 미리보기 시 본 skill 호출)
- agent: `fragment-engineer` (Fragment 철학 보호 전문)
- 정본 reference: `.claude/rules/22-fragment-philosophy.md`

## 자동 호출 시점

- gather/normalize 파일 편집 후 (`post_edit_hint.py`가 권고)
- PR 리뷰 시 (rule 22 R9 self-test)
- task-impact-preview의 회귀 영역 자동 식별 (rule 91 R7)
