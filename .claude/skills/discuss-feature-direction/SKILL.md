---
name: discuss-feature-direction
description: 모호한 요구사항을 사용자와 대화로 좁혀 기능 방향 결정. discovery 루프 진입점. 사용자가 "어떻게 만들지 같이 생각해줘", "방향이 애매해" 등 요청 시. - 요구가 모호 / 여러 해석 가능 / 바로 구현 불가
---

# discuss-feature-direction

## 목적

server-exporter의 모호한 요구를 디스커버리 대화로 정제. PO / 아키텍트와 함께 의도 / 제약 / 트레이드오프 좁히기.

## 디스커버리 질문 패턴

1. **사용자 flow**: 호출자가 어떤 시점에 어떤 결과를 받기를 원하는가?
2. **벤더 / 채널 범위**: 모든 vendor / 모든 채널 / 일부?
3. **외부 시스템 의존**: Redfish? IPMI? vSphere? SSH? WinRM?
4. **Schema 영향**: 출력 envelope 변경 필요? 새 섹션? 새 필드?
5. **Vault / 인증 영향**: 새 자격증명? Vault 2단계 변경?
6. **Jenkins 영향**: 4-Stage 변경? cron 변경?
7. **회귀 부담**: baseline 전수 vs 일부?
8. **운영 환경**: 전 loc? 일부 loc? (등록된 loc 은 `common/vars/locations.yml`)

## 절차

1. 사용자 요구 paraphrase (서로 같은 의미인지 확인)
2. 위 8 질문 중 답이 부족한 것 1~2개씩 (rule 23 R1 4요소 포맷)
3. 답이 모이면 → `analyze-new-requirement` 또는 `compare-feature-options`로 라우팅

## 적용 rule / 관련

- rule 23 (communication-style)
- skill: `analyze-new-requirement`, `compare-feature-options`
- agent: `discovery-facilitator`, `product-planner`
