---
name: pr-review-playbook
description: PR 생성 전 server-exporter 최종 체크리스트. Jenkins 4-Stage 통과 / 4축 리뷰 / 회귀 / docs 갱신 검증. 사용자가 "PR 올리기 전에 확인해줘", "PR 준비됐어?", "체크리스트" 등 요청 시. - PR push 직전 / 머지 직전 최종 검증
---

# pr-review-playbook

## 목적

server-exporter PR을 origin/main에 머지하기 전 체크리스트 일괄 실행. 머지 후 사고를 사전 차단.

## 체크리스트

### 1. 정적 검증 (rule 24 R1)
- [ ] `ansible-playbook --syntax-check` (3-channel)
- [ ] `pytest tests/` (변경 영역)
- [ ] `python -c "import ast; ..."` (Python 파일)
- [ ] `yamllint` (편집한 YAML)

### 2. 4축 리뷰 (rule 22/12/60/95)
- [ ] Structure (Fragment 철학 / 경계 / adapter score)
- [ ] Quality (의심 패턴 12종)
- [ ] Security (vault / cert verify / log redaction)
- [ ] Vendor Boundary (verify_vendor_boundary.py)

### 3. 회귀 검증 (rule 40 / rule 91 R7)
- [ ] 영향 vendor baseline 회귀 통과 (run-baseline-smoke 또는 Stage 4)
- [ ] 공통 fragment 변경 시 3-channel 모두 회귀
- [ ] schema 변경 시 3종 동반 + 영향 vendor baseline

### 4. 문서 갱신 (rule 70)
- [ ] docs/ai/CURRENT_STATE.md
- [ ] 영향 `docs/` 문서
- [ ] 영향 ADR (docs/ai/decisions/, 결정 있을 시)
- [ ] tests/evidence/ (Round 검증 시)

### 5. Jenkins 4-Stage dry-run
- [ ] Stage 1 Validate (입력 형식)
- [ ] Stage 2 Gather (ansible-playbook)
- [ ] Stage 3 Validate Schema
- [ ] Stage 4 E2E Regression
- [ ] callback URL 무결성 (rule 31)

### 6. Commit 메시지 (rule 90)
- [ ] type prefix (feat / fix / refactor / docs / test / chore / harness / hotfix)
- [ ] 50자 이내
- [ ] 금지어 단독 사용 안 함
- [ ] 본문 3줄 이내

### 7. 외부 계약 (rule 96)
- [ ] adapter metadata origin 주석
- [ ] schema 변경 시 호출자 호환성

### 8. 보안 (운영 권장 — cycle-011: rule 60 정책 해제)
- [ ] vault encrypt 유지 (cycle-012 8 vault encrypt 채택)
- [ ] BMC password log 출력 없음
- [ ] HTTPS verify 정책 의도 명시

## 출력

```markdown
## PR 준비 체크리스트 — feature/huawei-vendor

### 정적 검증: PASS
### 4축 리뷰: WARN (Quality 1건 — int cast)
### 회귀: PASS (Huawei baseline 신규 + 기존 5 vendor 무영향)
### 문서: PASS (CURRENT_STATE / `docs/reference/live-validation.md` / 19 / ai-context/vendors/huawei.md 갱신)
### Jenkins dry-run: PASS
### Commit 메시지: PASS
### 외부 계약: PASS (adapter metadata origin 주석 존재)
### 보안: PASS

### 권고
- Quality WARN 1건은 다음 정리 PR (advisory)
- PR 머지 가능 (rule 24 6 체크리스트 통과)
```

## 자동 호출 시점

- 사용자 "PR 준비" 요청 시
- finishing-a-development-branch skill 일환

## 적용 rule / 관련

- **rule 24** (completion-gate) — 6 체크리스트
- rule 22 / 12 / 60 / 95 (4축)
- rule 40 / 70 / 80 / 90 / 91 / 92 / 96
- skill: `review-existing-code`, `run-baseline-smoke`, `verify-adapter-boundary`, `validate-fragment-philosophy`, `verify-json-output`, `update-evidence-docs`
- agent: `code-reviewer`, `qa-regression-worker`, `release-manager`
