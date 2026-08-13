# Production 코드 비판적 검증 (Critical Review)

> TDD 추가 / 코드 리뷰 / 리팩토링 작업 전에 production 코드도 버그 후보로 간주.

## 적용 대상

- `**/*.py`, `**/*.yml`, `**/*.yaml` (production 코드 전반)
- AI가 대상 파일을 한 줄이라도 읽거나 인용하는 모든 TDD/리뷰/리팩토링 작업

## 목표 규칙

### R1. TDD/리뷰 작성 전 production 자동 스캔

대상 코드의 모든 함수/태스크를 읽은 뒤 **의심 패턴 12종** 자동 스캔:

1. **Ansible default(omit) 누락** — vendor-specific 변수가 없을 때 정의되지 않은 변수 참조
2. **set_fact 재정의로 인한 fragment 침범** — 다른 gather의 fragment 변수를 set_fact (rule 22)
3. **Jinja2 정규식 dead code** — `{{ x | regex_search('...') }}` 후 dead branch
4. **Adapter score 동률 처리** — 같은 점수의 adapter 둘 이상 시 정렬 결과 불확정
5. **`is none` vs `is undefined` vs `length == 0` 혼동** — Ansible 변수 상태 분기 잘못
6. **빈 callback message** — error 발생했는데 errors[]에 message 없이 빈 dict
7. **`int()` cast 미방어** — Redfish 응답의 string→int 변환 시 ValueError 미처리
8. **Single-vendor 분기 silent** — 한 vendor만 처리하고 다른 vendor 응답 silent skip
9. **adapter_loader self-reference** — adapter가 다른 adapter를 include하는데 순환
10. **mutable/immutable 혼동** — Ansible vars dict의 deep copy 누락 (set_fact가 reference 공유)
11. **외부 시스템 계약 drift** (rule 96 연동) — adapter YAML의 vendor 목록 ↔ 실제 BMC 펌웨어 지원 집합 drift. 스캔 방식: adapter의 vendor / firmware 메타가 실 펌웨어와 일치하는지 origin 주석 확인 의무 (불가 시 사용자 질의)
12. **`regex_search` / `regex_findall` / `regex_replace` + `when` 절 None 가드 누락** — Ansible Jinja2 `regex_*` 가 미매치 시 None 반환 → strict mode conditional fail (`Conditional result (False) was derived from value of type 'NoneType'`). 가드: `(var | regex_search('p')) is not none` / `| length > 0` / `| default(false) | bool`. 가드는 regex_* 호출 **뒤** 에 와야 함 — `| default('')` 가 regex_search **앞** 에 있으면 INPUT 만 가드 (출력은 여전히 None, 5d6cf72c 사고 사례). 자동 검출 hook: `scripts/ai/hooks/pre_commit_regex_search_conditional_check.py` (advisory — cycle 2026-05-11 도입).

### R2. 개발자 답변도 검증 대상

- **Default**: 개발자 답변 ("의도된 로직", "수정 완료", "그 파일 없음")을 수용하기 전에 실제 코드 / 파일 시스템 / commit log 교차 확인
- **검증 절차**:
  - "수정 완료" → `git show <commit>` diff 확인 + 관련 테스트 pass
  - "의도된 로직" → 코드에 `# TODO`, `# 추후`, `# placeholder` 같은 임시 구현 주석 검사
  - "그 파일 없음" → `find` / `git ls-files`로 실제 존재 확인 (브랜치 간 차이)
- **Forbidden**: 답변만 수용하고 검증 없이 다음 단계

### R3. 의심 발견 시 드러내기 의무

- **Default**: R1·R2 스캔 중 의심 발견 시 반드시 **회귀 테스트 1건 이상 추가** + `FAILURE_PATTERNS.md` entry
- **Forbidden**:
  - 의심 발견 후 "경미하다" 판단으로 무시
  - 현재 동작에 맞춰 assertion 작성 (버그 고정)
  - AI 독단으로 "의도된 동작" 분류

### R4. Cross-branch 검증 (단일 main)

- **Default**: feature/* 브랜치 작업 시 `origin/main`과 대상 파일 diff 확인
- **도구**: `python scripts/ai/check_gap_against_main.py`
- **Forbidden**: main에서 변경/삭제된 것을 모른 채 작업
- **자동 트리거**:
  - 세션 시작 (session_start hook)
  - merge / pull / rebase 직후 (post_merge_gap_check hook)
  - branch 전환 직후 (수동 호출)

### R5. 스캔 결과 요약 의무

- **Default**: 대상 코드 읽을 때 답변에 의심 스캔 결과 1줄 요약 포함. 발견 없어도 "R1 12 패턴 스캔 — clean" 명시

## 금지 패턴

- production 코드 미확인 후 TDD 작성 — R1
- 개발자 답변 수용하고 실제 확인 skip — R2
- 의심 발견 후 현재 동작에 맞춰 assertion — R3
- main 갭 모르고 작업 — R4
- 스캔 결과 보고 안 함 — R5

## 리뷰 포인트

- [ ] PR에 의심 패턴 스캔 결과 기록
- [ ] 회귀 테스트 추가 (의심 발견 시)
- [ ] 개발자 답변 기반 수정에 commit hash + diff 확인
- [ ] Cross-branch 갭 체크 결과

## 관련

- rule: `91-task-impact-gate`, `92-dependency-and-regression-gate`, `96-external-contract-integrity`, `25-parallel-agents` (R7-B)
- skill: `write-quality-tdd`, `debug-external-integrated-feature`, `task-impact-preview`
- script: `scripts/ai/check_gap_against_main.py`
- catalog: `docs/ai/catalogs/FAILURE_PATTERNS.md`
