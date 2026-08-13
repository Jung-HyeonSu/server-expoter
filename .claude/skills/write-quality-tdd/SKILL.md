---
name: write-quality-tdd
description: 잘 짜여진 TDD 작성 + 기존 테스트 검수. "구현 설명서" 가 아니라 "행위 명세서"로. 사용자가 "TDD 써줘", "테스트 추가", "테스트 검수" 등 요청 시. - pytest 신규 작성 / 기존 테스트 품질 검수 / 리팩토링 / Round 검증 후 회귀 테스트 추가
---

# write-quality-tdd

## 목적

server-exporter pytest는 redfish_gather.py / precheck_bundle.py / filter_plugins / module_utils 같은 Python 모듈 + baseline 회귀 테스트.

## 원칙 (server-exporter 적용)

1. **행위 명세 (no implementation)**: "redfish_gather.py가 ServiceRoot 무인증 GET 했을 때 Manufacturer 필드 추출" 같이 행위로 기술
2. **mock 사용**: 외부 시스템 호출은 fixture로 mock (실장비 의존 금지, fixture 기반은 빠름)
3. **edge case 의무**:
   - 빈 응답 / 타임아웃 / TLS 핸드셰이크 실패
   - 잘못된 JSON / 누락된 필드
   - 다른 vendor 응답
4. **Production 코드 비판적 검증** (rule 95 R1) §11 — TDD 작성 전 의심 패턴 12종 자동 스캔
5. **`@pytest.mark.skip` 또는 `@pytest.mark.xfail`** 으로 의심 발견을 드러냄 (현재 동작에 맞춰 assertion 작성 금지)

## 의심 패턴 12종 (rule 95 R1)

1. Ansible default(omit) 누락
2. set_fact 재정의로 fragment 침범
3. Jinja2 정규식 dead code
4. adapter score 동률 처리
5. is none / is undefined / length == 0 혼동
6. 빈 callback message
7. int() cast 미방어
8. Single-vendor 분기 silent
9. adapter_loader self-reference
10. mutable / immutable 혼동
11. 외부 시스템 계약 drift (rule 96)

## 절차

1. **production 코드 자동 스캔** (rule 95 R1)
2. **의심 발견 시 `@pytest.mark.xfail` 추가**
3. **TDD 작성**:
   - 행위명: `def test_redfish_extracts_manufacturer_from_serviceroot()`
   - given / when / then 구조
4. **fixture 사용**: `tests/fixtures/<vendor>_serviceroot.json`
5. **회귀 검증**: 새 TDD가 기존 baseline 회귀와 충돌 없음

## 적용 rule / 관련

- **rule 95** (production-code-critical-review) 정본
- rule 40 (qa-pytest-baseline)
- rule 96 (external-contract-integrity)
- skill: `review-existing-code`, `validate-fragment-philosophy`, `prepare-regression-check`
- agent: `tdd-guide`, `qa-regression-worker`
