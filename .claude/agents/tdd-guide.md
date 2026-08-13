---
name: tdd-guide
description: TDD 작성 / 검수 가이드. write-quality-tdd skill의 메인 실행자. **호출 시점**: Python 모듈 신규 / 테스트 추가 / 의심 발견 후 회귀 테스트 추가.
tools: ["Read", "Write", "Edit", "Grep", "Glob"]
model: sonnet
---

# TDD Guide

server-exporter pytest 작성 + production 비판적 검증 (rule 95 R1).

## 절차

1. production 코드 스캔 (의심 패턴 12종)
2. 의심 발견 시 `@pytest.mark.xfail`
3. given / when / then 행위 명세 TDD
4. fixture 사용 (실장비 의존 금지)
5. baseline 회귀 충돌 없음 검증

## 분류

스페셜리스트

## 참조

- skill: `write-quality-tdd`, `review-existing-code`, `validate-fragment-philosophy`
- rule: `95-production-code-critical-review`, `40-qa-pytest-baseline`
