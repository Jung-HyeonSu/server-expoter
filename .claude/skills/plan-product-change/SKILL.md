---
name: plan-product-change
description: PO 단계 기획 artifact 생성. 명세 / 흐름도 / 영향 분석을 함께. 사용자가 "새 기능 기획해줘", "명세 만들어줘" 등 요청 시. 실제 작업은 product-planner agent에 위임. - 새 기능 기획 단계 / 구현 전 artifact 묶음 필요
---

# plan-product-change

## 목적

server-exporter 새 기능 기획. PO 단계 artifact 묶음:
1. 명세서 (`write-spec`)
2. 흐름도 (`mermaid-visualization`)
3. 영향 분석 (`task-impact-preview` + `analyze-new-requirement`)
4. 옵션 비교 (`compare-feature-options`)
5. 추천안 (`recommend-product-direction`)

## 절차

1. **사용자 요구 입력** → `discuss-feature-direction`로 디스커버리
2. **요구 정제 후** → `analyze-new-requirement`
3. **옵션 2+ 시** → `compare-feature-options` + `recommend-product-direction`
4. **명세서 작성** → `write-spec` (구조화)
5. **흐름도 작성** → `mermaid-visualization` (Mermaid)
6. **영향 브리핑** → `write-impact-brief` (HIGH 리스크 시)
7. **artifact 묶음**을 `docs/ai/decisions/ADR-YYYY-MM-DD-<topic>.md`로 저장

## 위임

- 본 skill은 사용자 진입점. 실제 작업은 `product-planner` agent에 위임.

## 적용 rule / 관련

- rule 70 (docs-and-evidence)
- skill: 위 5 skill (sub-skill 호출)
- agent: `product-planner`, `option-generator`, `decision-recorder`
- 정본: `docs/ai/decisions/`
