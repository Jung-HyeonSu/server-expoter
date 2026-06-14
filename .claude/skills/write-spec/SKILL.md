---
name: write-spec
description: 구조화된 server-exporter 기능 명세서 작성. 사용자가 "명세서 써줘", "스펙 정리" 등 요청 시. - 구조화된 spec 필요 / PR 본문 / 문서화
---

# write-spec

## 출력 (구조)

```markdown
# Spec — <기능명>

## 1. 목적 / 동기 (Why)
{1-3 줄}

## 2. 입력 / 호출 contract
- 호출자: {Jenkins / Portal / Grafana 등}
- 입력 형식: {target_type / loc / inventory_json}
- callback URL contract

## 3. 출력 / Envelope
- status / sections / data / errors / meta / diagnosis 6 필드
- 영향 섹션 list (11 sections 중)
- field_dictionary Must/Nice/Skip

## 4. 영향 영역
- 채널 (os / esxi / redfish)
- 영향 vendor (전수 / 일부)
- adapter (신규 / 변경)
- vault (신규 / 회전)
- Jenkinsfile (변경 / 추가)

## 5. 설계 / 아키텍처
- Fragment 흐름 (어떤 gather가 어느 fragment 만드는가)
- Adapter score 계산
- Vault 2단계 시퀀스 (Redfish 시)
- 4단계 Precheck 적용

## 6. 테스트
- 단위 / 통합 / 회귀 / 실장비 (Round)

## 7. 회귀 / 비호환 위험
- 기존 vendor baseline 영향
- 외부 시스템 계약 변경 (rule 96)

## 8. 보안
- vault 처리
- BMC 자격증명 흐름

## 9. 일정 / SUB 분할
- SUB-1 / SUB-2 / ...

## 10. 결정 / 대안
- 채택 안 + 기각 안 위치 (rule 23 R3 결정 주체 명시)
```

## 적용 rule / 관련

- rule 23 R5 (육하원칙 — 사람 대상)
- rule 70 (docs-and-evidence)
- skill: `analyze-new-requirement`, `plan-feature-change`, `write-feature-flowchart`
- agent: `spec-writer`, `product-planner`
- template: `.claude/templates/REQUIREMENT_ANALYSIS.template.md` 일부 활용
