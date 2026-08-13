---
name: <skill-name>
description: {WHAT: skill이 무엇을 하는가}. 사용자가 "{trigger phrase}", "{trigger phrase}" 등 {situation}을 요청할 때 사용. - {언제 사용 / 언제 skip}
---

# Skill: <skill-name>

## 목적

{이 skill을 호출하면 AI가 무엇을 해주는가? 1-2 문장}

## 입력

- {input 1}: {예시}
- {input 2}: {예시}

## 출력

```markdown
## {결과 섹션}
- 항목 1
- 항목 2
```

## 절차

1. {step 1}
2. {step 2}
3. {step 3}

## server-exporter 도메인 적용

- 영향 채널: {os-gather / esxi-gather / redfish-gather / common / 다중}
- 영향 vendor: {Dell / HPE / Lenovo / Supermicro / Cisco / agnostic}
- 영향 schema: {sections.yml / field_dictionary.yml / baseline / 없음}
- 영향 vault: {vault/<file> / 없음}

## 실패 / 오탐 처리

- {언제 skill이 부적절한가}
- {알려진 한계}

## 관련

- rule: {N}
- agent: {agent-name}
- 정본 reference: {rule 22 (fragment-philosophy) / docs/...}
