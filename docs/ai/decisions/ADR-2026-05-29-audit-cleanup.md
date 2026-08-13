# ADR-2026-05-29: 전수 audit + 안전 정리 cycle

- 상태: Accepted
- 일자: 2026-05-29
- 결정자: hshwang1994 (사용자) + AI 실행
- 브랜치: `refactor/audit-cleanup-20260529`

## 컨텍스트 (Why)

사용자가 ultracode 모드로 전수 audit 를 요청: dead code, 중복, 리팩토링, 성능, 예외처리, 아키텍처, 기술부채, "개더링 안 되는데 스키마에 잡아넣은 것"(schema bloat), 쓰레기 문서 삭제, CSUS 3200 출력 재검토. 제약: "운영에 문제 생기면 안 됨, **특히 인증**", "아는 것도 재검증(web 포함)". 본 환경 한계: ansible 미설치(syntax/런타임 검증 불가), 실장비(lab) 없음 — pytest(699) + py_compile + harness 스크립트만 검증 가능.

8-auditor 병렬 전수조사 + web 검증(BMC lockout 동작 / HPE Superdome RMC 멀티-파티션 Redfish 모델) 수행.

## 결정 (What)

**검증 가능 + 무위험인 것만 적용. 검증 불가(ansible)·인증 동작 변경·실장비 필요·계약 변경은 문서화하고 미적용.**

사용자 4개 결정:
1. **시크릿** = "문서화만" → repo 스크럽 안 함, 회전·purge 런북만 작성 (`SECRET-ROTATION-RUNBOOK.md`). 시크릿 보유 일회용 스크립트(bug_tracker/add_*_vault)도 dead 이지만 보존.
2. **tests/reference 133MB** = "전부 유지" → 변경 없음.
3. **문서** = "덤프 삭제 + 히스토리성 archive" → 완료-cycle 덤프 164 삭제, summary/origin-evidence 26 archive.
4. **CSUS** = "정직성 정리 + mock 분리 (계약 변경 없음)" → mock baseline 태그·downgrade·가드 테스트. 필드 삭제·normalize 재작성 안 함.

적용: stale 26 정정 / dead code 5건 제거 / redfish `_ne`·`_ne_p` dedup / docs 정리 190건 / CSUS 정직성 + 가드 테스트 4 / 신규 문서 3.

## 결과 (Impact)

- 검증: pytest **699→703 PASS** (CSUS 가드 4 신규), `verify_harness_consistency` / `verify_vendor_boundary` PASS, dangling ref 0.
- envelope 13 필드 / `data.*` shape / schema 83 entries **변경 0** (호출자 계약 안전).
- 미적용 backlog → `docs/ai/contracts/account-write-vendor-compat.md` + `NEXT_ACTIONS.md §0` (보안 회전[사용자] / AUTH lockout·dryrun[lab] / esxi vendor 버그·perf·refactor[ansible 검증]).
- 핵심 발견: schema "bloat" 대부분이 fake 아님 (stale baseline + lab 하드웨어 부재). 유일 mock-only = CSUS `multi_node`(gated null). 최대 운영 리스크 = vault 마스터 암호 평문 노출(387 파일 + 히스토리).

## 대안 비교 (Considered)

- **(거절) 인증/perf 동작 변경까지 적용**: detect 선인증 4-GET 축소 / dryrun 기본 flip / SSL memoize 등은 본 환경 미검증(ansible/lab) + 인증 경로 → 사용자 "특히 인증" 위반 위험. 문서화로 위임.
- **(거절) 시크릿 자동 스크럽 + config.xml 재배선**: 운영 job 인증 메커니즘 변경 → 사용자 "문서화만" 결정. 런북으로 위임.
- **(거절) registry.yml 삭제**: auditor 가 dead 로 플래그했으나 실측 결과 test 3곳 소비 → 보존 (rule 95 R2 — 답변 맹신 금지, 실측 우선).
- **(거절) tests/reference trim/untrack**: 재생성에 lab 필요(부재) → 사용자 "전부 유지".

## 관련
- rule: 70 R5/R6/R7 (문서 보존/archive), 93 R1 (force-push 사용자 승인), 13 R5 (envelope 계약), 25 R7-A-1/R7-B (실측>spec, 추정 격상 금지)
- 문서: `docs/ai/contracts/account-write-vendor-compat.md`, `docs/ai/policy/SECRET-ROTATION-RUNBOOK.md`
