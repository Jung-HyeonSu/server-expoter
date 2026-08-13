---
name: plan-structure-cleanup
description: 디렉터리 / 명명 / 모듈 경계 정리 계획. 기능 변경 없는 lane. 사용자가 "구조 정리", "폴더 통일", "naming convention" 등 요청 시. - 디렉터리 / 네이밍 / 경계 정리 (기능 변경 없음)
---

# plan-structure-cleanup

## 목적

server-exporter 구조적 정리 (기능 변경 없음). 비례적 변경 lane (rule 92 R2 즉시 수정 금지 정신과 정합).

## 정리 대상 후보

- 디렉터리 / 파일 명명 일관성 (snake_case / kebab-case)
- adapter 파일 명명 (vendor_generation_*.yml)
- gather task 명명 (`gather_<section>.yml` / `normalize_<section>.yml`)
- fragment 변수 명명 (`_data_fragment` 등)
- 중복 task 통합
- 사용 안 하는 변수 / task / fixture 정리

## 절차

1. **현황 실측**: `Glob` / `Grep`으로 명명 일관성 평가
2. **정리 후보 list**: 변경 비용 + 영향 분석
3. **단계 분할**:
   - SUB-1: 가장 명확한 일탈 (예: `gatherCpu.yml` → `gather_cpu.yml`)
   - SUB-2: 영향 큰 일탈 (다른 파일 참조 갱신 필요)
4. **테스트 전략**: ansible-playbook --syntax-check + pytest
5. **회귀 영역**: rule 91 R7 자동 포함

## Forbidden

- 기능 변경 동반 (이 skill은 nonfunctional만)
- convention 맹신으로 정상 동작 코드 수정 (rule 92 R2)

## 적용 rule / 관련

- rule 92 R2 (convention 위반 즉시 수정 금지)
- rule 70 (docs-and-evidence) — CONVENTION_DRIFT.md 기록
- skill: `task-impact-preview`, `prepare-regression-check`
- agent: `refactor-worker`, `naming-consistency-reviewer`, `directory-structure-architect`, `repo-hygiene-planner`
