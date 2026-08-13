# 리뷰 요약 (Review Summary)

> `review-existing-code` skill 출력 4축 매트릭스.

## 대상

- 파일/PR: {경로 또는 PR #}
- 변경 라인: +N / -M
- 영향 채널: {os / esxi / redfish / common / 다중}
- 영향 vendor: {agnostic / specific}

## 4축 결과

### Structure
- 결과: {PASS / WARN / FAIL}
- Findings:
  - [Critical/High/Med/Low] {item}

### Quality (의심 패턴 12종)
- 결과: {PASS / WARN / FAIL}
- Findings:
  - {item}

### Security (vault / BMC auth / log redaction)
- 결과: {PASS / WARN / FAIL}
- Findings:
  - {item}

### Vendor Boundary (rule 12)
- 결과: {PASS / WARN / FAIL}
- Findings:
  - {item}

## 총평

{1-3 줄 종합 의견 + merge 권고}

## 후속 작업

- [ ] {item}
