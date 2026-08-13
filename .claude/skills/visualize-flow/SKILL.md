---
name: visualize-flow
description: 시스템 흐름을 Mermaid / sequence diagram으로 시각화. 사용자가 "흐름도", "시퀀스 다이어그램", "다이어그램 그려줘" 등 요청 시. - 일반 시각화 (write-feature-flowchart 보다 가벼움)
---

# visualize-flow

## 사용 패턴 (rule 41 R1 목적별)

- **분기 / 흐름**: flowchart
- **시간축 (callback / Vault 2단계)**: sequenceDiagram
- **상태 (precheck 단계 / gather lifecycle)**: stateDiagram-v2
- **데이터 (sections × fields × baseline)**: erDiagram
- **벤더 매트릭스**: sankey
- **후보안**: quadrantChart
- **Round 진행**: timeline / gantt

## server-exporter sequence 예시

```mermaid
sequenceDiagram
  actor Caller as 호출자
  participant J as Jenkins
  participant A as Agent
  participant R as Redfish BMC

  Caller->>J: POST /trigger (target_ip, vendor=auto)
  J->>A: ansible-playbook redfish-gather/site.yml
  A->>R: GET /redfish/v1/ (무인증)
  R-->>A: ServiceRoot (Manufacturer=Dell)
  Note over A: vendor 결정 → vault 로드
  A->>A: include_vars vault/<loc>/redfish/dell.yml
  A->>R: GET /redfish/v1/Systems (Basic Auth)
  R-->>A: System info
  A->>A: build_*.yml → JSON envelope
  A-->>J: stdout (json_only callback)
  J->>Caller: POST callback_url (envelope)
```

## 적용 rule / 관련

- rule 41 (mermaid-visualization)
- skill: `write-feature-flowchart`, `update-flowchart-after-change`
- agent: `flow-visualizer`, `flowchart-reviewer`
