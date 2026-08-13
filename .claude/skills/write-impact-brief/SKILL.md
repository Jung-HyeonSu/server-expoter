---
name: write-impact-brief
description: 한 장 영향 브리핑. 사용자 의사결정용. HIGH 리스크 변경 전. 사용자가 "이거 바꾸면 어떻게 돼?", "진행해도 돼?" 등 요청 시. - HIGH 리스크 변경 전 / 사용자 명시 승인 필요한 변경 (보호 경로 / vault / schema 3종 / Jenkinsfile cron / 새 vendor)
---

# write-impact-brief

## 출력 (한 장)

```markdown
# 영향 브리핑 — <변경 요약>

## 무엇 (What)
{2 줄 요약}

## 왜 (Why)
{현재 문제 / 필요}

## 어떻게 (How)
{접근 방법 high-level}

## 영향 (Impact)
| 영역 | 영향 | 회귀 |
|---|---|---|
| 채널 | os/esxi/redfish | ... |
| vendor | Dell+HPE | baseline 회귀 |
| schema | 3종 동반 갱신 | Stage 3+4 |
| 외부 시스템 | Redfish path 변경 | rule 96 origin 주석 |

## 위험 top 3
1. [HIGH] {위험}
2. [MED] {위험}
3. [LOW] {위험}

## 롤백 계획
- {커밋 revert / vault 복원 / Jenkinsfile 되돌리기}

## 결정 필요
- (A) 진행 / (B) 조정 / (C) 취소

## 결정 주체
- **{개발자/PO/아키텍트 님}**의 결정
```

## 적용 rule / 관련

- rule 23 (communication-style) R1 (4 요소 포맷)
- rule 91 R4 (HIGH 리스크 에스컬레이트)
- rule 92 (dependency-and-regression)
- skill: `task-impact-preview`, `analyze-new-requirement`, `compare-feature-options`
- agent: `change-impact-analyst`
