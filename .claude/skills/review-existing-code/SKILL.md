---
name: review-existing-code
description: 기존 server-exporter 코드를 4축 (구조 / 품질 / 보안 / 벤더 경계)으로 리뷰. PR 제출 전, 의심 영역 점검, 신규 작업자 온보딩 시. 사용자가 "코드 리뷰해줘", "이 파일 봐줘", "리뷰" 등 요청 시. - 코드 리뷰 일반 / PR 머지 전 / 4축 점검 (rule 22 fragment + rule 12 boundary + CLAUDE.md §12 security + rule 95 quality)
---

# review-existing-code

## 목적

server-exporter 코드를 4 축 매트릭스로 리뷰 (`.claude/policy/review-matrix.yaml` 정본). PR 제출 전 또는 의심 발견 시 호출.

## 4 축

### Structure
- Fragment 철학 준수 (rule 22): 각 gather 자기 fragment만, merge_fragment 호출
- gather ↔ output 경계 (rule 11)
- adapter 점수 일관성 (rule 12 R2)
- 파일 500줄 / 함수 50줄 (rule 10 R3)

### Quality (의심 패턴 12종, rule 95 R1)
- Ansible default(omit) 누락
- set_fact 재정의로 fragment 침범
- Jinja2 정규식 dead code
- adapter score 동률 처리
- `is none` / `is undefined` / `length == 0` 혼동
- 빈 callback message
- `int()` cast 미방어
- single-vendor 분기 silent
- adapter_loader self-reference
- mutable/immutable 혼동
- 외부 시스템 계약 drift (rule 96)

### Security (CLAUDE.md §12)
- vault 변수 평문 누설
- BMC password log 출력
- Vault 2단계 로딩 절차 (Redfish)
- HTTPS verify 정책 명시
- callback message에 stacktrace 노출

### Vendor Boundary (rule 12)
- common / 3-channel 코드에 vendor 이름 하드코딩 0건
- 벤더 분기는 adapter YAML 또는 OEM tasks에만
- vendor_aliases.yml 정규화 메타 사용

## 입력

- 대상 파일 / PR 번호 / 디렉터리

## 출력 (`.claude/templates/REVIEW_SUMMARY.template.md` 형식)

```markdown
## 4축 리뷰 결과 — <대상>

| 축 | 결과 | 발견 |
|---|---|---|
| Structure | PASS | — |
| Quality | WARN | int cast 미방어 1건 |
| Security | PASS | — |
| Vendor Boundary | FAIL | redfish-gather/library/ 안에 "Dell" 하드코딩 |

### 심각도별 list
- [CRIT] Vendor Boundary: redfish-gather/library/redfish_gather.py:152 "Dell" 하드코딩
- [WARN] Quality: redfish-gather/tasks/collect_storage.yml:88 int(capacity) 미방어

### 권고
1. CRIT 즉시 수정 PR
2. WARN은 다음 정리 PR (CONVENTION_DRIFT.md 기록)

### 회귀 검토 필요
- 영향 vendor: Dell (변경 시 baseline 회귀)
```

## 절차

1. **대상 파일 Read** (or 변경 diff)
2. **rule 95 R1 12 패턴 grep**: 의심 영역 list
3. **rule 22 R1-R9 검증**: validate-fragment-philosophy skill 호출 (gather/normalize 영역)
4. **rule 12 R1 grep**: `verify_vendor_boundary.py` 결과 통합
5. **보안 grep** (CLAUDE.md §12): vault 누설 / cert verify / callback redaction
6. **각 발견을 4 축으로 분류 + 심각도 (CRIT / WARN / Info)**
7. **회귀 영역 자동 식별** (rule 91 R7)
8. **REVIEW_SUMMARY 출력**

## server-exporter 도메인 적용

- 영향 채널: 리뷰 대상에 따라
- 영향 vendor: 위반 발견 시 영향 vendor 명시

## 자가 검수 금지 (rule 25 R7)

본인이 작성한 코드를 본인이 리뷰/승인하지 말 것. 별도 reviewer agent 호출.

## 적용 rule / 관련

- **rule 22** (fragment), **rule 12** (vendor boundary), **rule 95** (quality) — cycle-011: rule 60 해제
- policy: `.claude/policy/review-matrix.yaml`
- skill: `validate-fragment-philosophy`, `verify-adapter-boundary`, `verify-json-output`
- agent: `code-reviewer`, `adapter-boundary-reviewer`, `vendor-boundary-guardian`, `output-schema-reviewer`, `naming-consistency-reviewer`, `integration-impact-reviewer` (cycle-011: security-reviewer 제거)
- template: `.claude/templates/REVIEW_SUMMARY.template.md`
- command: `/review-guide`
