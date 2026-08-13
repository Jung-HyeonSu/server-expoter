# ADR-2026-05-07 — 7개 우려사항 리팩토링 검토 cycle

## 컨텍스트 (Why)

개발자가 server-exporter 코드 전반에 대한 7개 우려를 제기:

1. 코드 가독성 (특히 Redfish API 호출 흐름)
2. 디버깅 어려움 (실패 시 어느 파일을 봐야 할지)
3. 디렉터리 구조 직관성 (precheck 분산 / normalize 8 빌더 / schema 5 위치)
4. 벤더별 로직 분리 (합집합 vs 교집합 — 공통 로직 설계 의도)
5. 신규 세대/모델 추가 절차 불명확
6. 회귀 사고 반복 (A 고치면 B 깨짐 — 3 패턴 반복)
7. hostname=IP 표시 (버그/의도 확인)

본 cycle 은 7 우려 각각에 대해 진단 (실제 침습 작업 / 문서·가시성 / 의도된 설계) 분류 후 8 Phase 로 침습 최소화 + 침투력 최대 패키지로 처리.

## 결정 (What)

### 7 우려 진단 + 처리

| # | 우려 | 진단 | 처리 | 산출물 |
|---|---|---|---|---|
| 1 | 가독성 (Redfish) | 함수 분리 OK, docstring + priority 정책 부재 | **Fix (소형)** | redfish_gather.py 4 함수 docstring + `_ACCOUNT_CREATE_STRATEGY` 매핑 (Phase C/H) |
| 2 | 디버깅 어려움 | adapter 선택 추적 불가, 실패 stage→파일 매핑 부재 | **Fix (중형)** | `docs/develop/06-debugging.md` 신설 + adapter_loader.py -vvv 강화 (Phase C) |
| 3 | 디렉터리 구조 | 책임 분산 OK, 진입 가이드 부재 | **문서화** | 5개 README (common/normalize/schema/tests/redfish-library) (Phase G) |
| 4 | 벤더 분리 (합집합 vs 교집합) | **합집합 모델 맞음** (개발자 의도와 일치) | **명세 보강** | `docs/develop/04-add-vendor.md` 절차 B + `_ACCOUNT_CREATE_STRATEGY` 매트릭스 (Phase F/H) |
| 5 | 신규 세대/모델 | rule 50 R2 9단계 있으나 priority 정책 + 5 파일 매트릭스 부재 | **Fix (소형)** | `docs/develop/04-add-vendor.md` 절차 B + `docs/develop/03-adapter-system.md` priority 정책표 (Phase C/F) |
| 6 | 회귀 (A 고치고 B 깨짐) | 3 반복 패턴 (Jinja2 namespace / HTTP header drift / Fragment skeleton drift) | **Fix (대형)** | tests/regression/ 107 검증 + 2 hooks (jinja_namespace + skeleton_sync) (Phase A/B) |
| 7 | hostname=IP | **의도된 fallback** (DMTF spec) | **문서화** | `docs/contract/03-fields.md` 7절 신설 — fallback chain + 4 시나리오 (Phase E) |

### 8 Phase 산출물

| Phase | 산출물 | commit |
|---|---|---|
| A | tests/regression/ (107 검증, 1 xfail cisco drift 검출) + capture-site-fixture skill 보강 | a196162b |
| B | pre_commit_jinja_namespace_check + pre_commit_fragment_skeleton_sync (advisory + blocking) | 8044b7bf |
| C | `docs/develop/06-debugging.md` + `docs/develop/03-adapter-system.md` priority 정책표 + adapter_loader.py -vvv + redfish_gather.py docstring | a6f1439f |
| E | `docs/contract/03-fields.md` 7절 hostname fallback chain | fb34d8e1 |
| F | `docs/develop/04-add-vendor.md` 절차 B 신 vendor / 새 세대 가이드 | a4cc1b4e |
| H | redfish_gather.py `_ACCOUNT_CREATE_STRATEGY` 매핑 (refactor only) | 9c33d6fd |
| G | 5개 README (common/normalize/schema/tests/library) | 3eced3d1 |
| 8 | 본 ADR + PROJECT_MAP fingerprint 갱신 | (이 commit) |

## 결과 (Impact)

### 측정 가능한 변화

- **pytest 테스트**: 32 → **441 passed + 1 xfailed** (회귀 차단 폭 +13× / cisco hostname drift 1 known)
- **hooks**: 26 → **28** (+2 advisory/blocking)
- **docs**: `docs/reference/compatibility-matrix.md` → `docs/develop/06-debugging.md` 신설 + `docs/develop/03-adapter-system.md` / `docs/develop/04-add-vendor.md` / `docs/contract/03-fields.md` 확장
- **README**: 0 → 5 (디렉터리 진입 가이드)
- **rule 본문**: 변경 0 (R1~R8 중 어느 것도 의미 변경 없음)

### 우려 답변 표 (호출자 시스템 reference)

| 우려 | 답변 |
|---|---|
| 1 가독성 | docstring 보강 + priority 정책표 / 라이브러리 분할은 위험 (rule 10 R2 stdlib only) — 미실시 |
| 2 디버깅 | `docs/develop/06-debugging.md` 매트릭스 + adapter_loader -vvv breakdown / envelope schema 변경 없음 |
| 3 디렉터리 구조 | 5 README 추가 / 폴더 이동 없음 (Ansible 컨벤션 + Fragment 철학에 합리적) |
| 4 벤더 분리 (합집합) | **현재 설계가 맞음** — 합집합 모델 (개발자 의도와 일치) |
| 5 신규 세대 | `docs/develop/04-add-vendor.md` 절차 B 5 파일 매트릭스 + priority 정책 흐름도 |
| 6 회귀 사고 | 107 cross-channel 검증 + 2 hook (jinja namespace + skeleton sync) + 사이트 fixture skill |
| 7 hostname=IP | **의도된 fallback** (DMTF spec 권장) — `docs/contract/03-fields.md` 7절 명시 |

### 사용자 영향

- 호출자 시스템 영향: **0** (envelope 13 필드 / sections 10 / field_dictionary 65 의미 변경 없음)
- vault 변경: **0**
- Jenkinsfile cron 변경: **0**
- 의존성 추가: **0** (stdlib only 유지)

### 후속 사고 추적 (cycle 2026-05-07-post 모두 [DONE])

| # | 사고 | 처리 | commit |
|---|---|---|---|
| 1 | `cisco_baseline.json` hostname=null drift | "10.100.15.2" 보정 (build_output.yml fallback 의도대로) + xfail → 정 PASS | 151c1386 |
| 2 | `gather_network.yml:99` Jinja `val=val-bit` netmask 사고 | `val` namespace 포함 (`ns.val`) — `/23, /30` 등 비표준 mask 잘못 계산 차단 | 151c1386 |
| 3 | `esxi normalize_network.yml:67` 동일 사고 | 동일 namespace fix | 151c1386 |
| 4 | `gather_users.yml:77, 212` set groups self-ref advisory | `ns.groups` namespace 통일 — 의도 명확화 + advisory silence | 151c1386 |

### 잔여 후속 회귀 검증

- pytest 461 PASS (cycle 진입 32 → +13× 보호 폭)
- 신규 회귀 19 (`tests/unit/test_netmask_cidr_jinja_fix.py`) — broken algorithm 사고 명시 + fixed algorithm 정답
- xfail → PASS 격상 1 (`test_hostname_never_null[cisco_redfish]`)
- Jinja namespace hook 0 의심 (모든 advisory 패턴 silence)

### 외부 의존 (다음 cycle)

- **lab Cisco UCS 도입 시**: `cisco_baseline.json` `hostname="10.100.15.2"` 가 실 BMC 응답과 일치 재검증. 만약 실 BMC 가 hostname 응답하면 baseline 갱신.

## 대안 비교 (Considered)

### A1. 7 우려 모두 침습 작업 (전면 리팩토링)

- **장점**: 모든 우려 1 cycle 에 해결
- **단점**: 회귀 위험 매우 큼. envelope 13 필드 / vendor 분리 / 디렉터리 이동 등 핵심 정본 변경 → 호출자 시스템 영향
- **거부 사유**: rule 92 R2 (Additive only), rule 13 R5 (envelope 보존), rule 95 R1 (회귀 차단). 7 우려 중 일부는 의도된 설계 (4, 7) → 변경 자체가 잘못된 결정

### A2. 회귀 보호만 (P0 만)

- **장점**: 가장 낮은 위험, 가장 높은 ROI
- **단점**: 디버깅 / 가독성 / 신 vendor 가이드 미완 → 다음 cycle 부담
- **거부 사유**: 사용자가 "P0~P5 전체" 명시 (2026-05-07)

### A3 (선택) — 8 Phase 분할 + 침습 최소화

- **장점**: envelope schema 변경 0 + 회귀 0 + 사용자 영향 0 / 7 우려 모두 답변
- **단점**: 1 cycle 에 8 commit (관리 비용)
- **승인 사유**: 사용자 명시 "P0~P5 전체" + envelope 변경 없음 + adapter -vvv 로그만 강화 (3 결정 받음)

## 회귀 검증

- pytest tests/ 441 passed + 1 xfailed (cisco baseline drift 추적 중)
- verify_harness_consistency.py 통과 (28 rules / 51 skills / 60 agents / 10 policies)
- verify_vendor_boundary.py 통과 (vendor 하드코딩 0)
- check_project_map_drift.py 갱신 완료 (5 디렉터리 변경)

## 관련

- rule 70 R8 trigger: surface count 변경 (hooks 26 → 28) → 본 ADR 작성 의무
- 정본 plan: `C:\Users\hshwa\.claude\plans\steady-honking-goblet.md` (사용자 승인 2026-05-07)
- 후속 cycle 추적: `docs/ai/NEXT_ACTIONS.md` 2026-05-07 entry
