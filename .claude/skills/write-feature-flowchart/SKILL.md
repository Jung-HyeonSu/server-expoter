---
name: write-feature-flowchart
description: 신규 / 변경 기능의 Mermaid 플로우차트 작성. rule 41 + rule 23 ASCII 태그 준수. 사용자가 "기능 흐름도", "플로우차트 그려줘" 등 요청 시. 큰 단위 기능에 의무. - 큰 단위 기능 추가/변경 시 관련 문서의 다이어그램 갱신 필요
---

# write-feature-flowchart

## 출력

관련 문서 안에 AS-IS / TO-BE 쌍으로 넣는 Mermaid 다이어그램.

### 필수 항목 (rule 41)

- `flowchart TD` 또는 목적별 (sequenceDiagram / stateDiagram / quadrantChart)
- 색상 팔레트:
  - OK / 신규: `#dfd` / `#3c3`
  - NG / 실패: `#fdd` / `#c33`
  - 외부 시스템 (Redfish/IPMI/SSH/WinRM/vSphere): `#def` / `#39c`
  - 분기: `#ffd` / `#c93`
- `color:#000, stroke-width:2px` 모든 style/classDef
- 노드 ID 의미 기반 (START_GATHER / CHECK_AUTH / SAVE_BASELINE / FAIL_PRECHECK)
- 30 노드 / 6 단계 이내 (초과 시 subgraph)
- 성공 / 실패 / 재시도 모두 표시
- 상단 `> 이 그림이 말하는 것: <한 문장>`
- 하단 `> 읽는 법: 방향 / 색 / 핵심 분기`
- 범례 (3색+ 사용 시)
- AS-IS / TO-BE 쌍 (변경 시)

### server-exporter 도메인 예시

- 호출자 → Jenkins 4-Stage → 3-channel ansible-playbook → adapter 자동 감지 → callback 출력
- Precheck (TCP 도달 → 프로토콜 → 인증 (ICMP 미사용)) → graceful degradation
- Vault 2단계 로딩 (Redfish)
- vendor 분기는 subgraph (profile-dell / profile-hpe / ...)

## 자동 호출 시점

- 큰 단위 기능 (새 vendor / 새 섹션 / 새 채널 / Jenkinsfile 추가) PR
- `plan-product-change` 일환

## 적용 rule / 관련

- **rule 41** (mermaid-visualization) 정본
- rule 23 R8 (ASCII 태그)
- skill: `visualize-flow`, `update-flowchart-after-change`
- agent: `feature-flowchart-designer`, `flowchart-reviewer`, `flow-visualizer`
