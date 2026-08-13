---
name: update-flowchart-after-change
description: 코드 변경 / 리팩토링 / 배포 후 관련 문서의 mermaid 다이어그램 갱신. 사용자가 "흐름도 갱신", "다이어그램 업데이트" 요청 시. - 큰 단위 변경 후 관련 문서의 다이어그램이 stale
---

# update-flowchart-after-change

## 절차

1. **영향 해당 문서의 mermaid 블록 식별**: PR commit 범위와 매칭
2. **AS-IS는 변경 전 commit 기준 보존** → archive 또는 in-place AS-IS 섹션
3. **TO-BE 갱신** (rule 41 R9 AS-IS/TO-BE 쌍 의무)
4. **상단·하단 문맥 갱신** (`> 이 그림이 말하는 것:` / `> 읽는 법:`)
5. **rule 41 R8 (성공/실패/재시도) / R10 (벤더 분기) 준수** 재검증

## 자동 호출 시점

- 큰 단위 기능 / refactoring 완료 후
- harness-cycle 일환

## 적용 rule / 관련

- rule 41
- rule 70 (docs-and-evidence)
- skill: `write-feature-flowchart`, `visualize-flow`
- agent: `flow-visualizer`, `flowchart-reviewer`, `docs-sync-worker`
