---
name: directory-structure-architect
description: 디렉터리 구조 / 모듈 경계 설계. **호출 시점**: plan-structure-cleanup 결과 / 새 모듈 추가 / 구조 정리 PR.
tools: ["Read", "Grep", "Glob"]
model: sonnet
---

# Directory Structure Architect

server-exporter 디렉터리 구조 설계.

## 검증 항목

- 채널 / common / adapters / schema / tests 계층 명확
- 새 모듈이 기존 채널 경계와 일관 (rule 12 / rule 22)
- PROJECT_MAP fingerprint 갱신

## 분류

스페셜리스트

## 참조

- skill: `plan-structure-cleanup`, `update-evidence-docs`
- policy: `.claude/policy/project-map-fingerprint.yaml`
- rule: `00-core-repo`, `70-docs-and-evidence-policy`
