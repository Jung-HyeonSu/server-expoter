# Harness Retrospective — 2주간 사고/부족 회고 (2026-04-17 ~ 2026-05-01)

> 사용자 명시 (2026-05-01): "2주일간 나온 문제와 부족한 점 모든 에이전트 통해 전면 검사하고 하네스를 보강하라."

## A. 2주간 발생 사고 timeline

### cycle-014 (2026-04-XX)
- production-audit 4 agent 전수조사 (Redfish + OS-ESXi-common + Schema-callback + Tests-baselines-pipelines)
- HIGH 30+건 일괄 fix (skeleton drift / cross-channel JSON / vendor alias 정규화 / Cisco trailing whitespace / HPE placeholder filter / Power.PowerControl 비-dict 방어)

### cycle-015 (2026-04-XX)
- `Jenkinsfile_grafana` 제거 (사용자 명시 — Grafana 적재 미사용)
- multi-pipeline 2종으로 정리 (Jenkinsfile / Jenkinsfile_portal)

### cycle-016 (2026-04-29)
- 9 파일 namespace pattern (Jinja2 loop scoping fix)
- 9 inline `{# ... #}` Jinja2 코멘트 제거
- summary grouping 강화 (cpu/memory/storage/network/firmware/power)
- raw API 풍부 필드 추가 (asset_tag/system_type/part_number/last_reset/tpm)

### 2026-04-30 cycle (HTTP 406 + reverse regression hotfix)
- 사용자 사이트 보고: Lenovo BMC "Redfish 미지원" false-positive
- Root cause: `precheck_bundle.py` http_get 가 `Accept` 헤더 누락 → BMC 펌웨어 1.17.0 등이 406 거부
- 첫 fix: Accept + OData-Version + User-Agent 추가 → **Lenovo XCC reverse regression**
- Hotfix: Accept만 유지
- 부수 fix: 401/403 강제 failed (vault fallback 정상화) / verbosity 토글 / alias 보강

### 2026-05-01 cycle (404→not_supported + 인프라)
- 사용자 사이트 보고: Dell host envelope errors[2] (power 404 / network_adapters 404)
- Root cause: 코드가 404 (endpoint 부재 = 미지원) 를 'failed' 분류 → errors[] noise
- Fix: 404 → 'not_supported' 분류 + PowerSubsystem fallback (DMTF 2020.4) + 3채널 fragment 인프라
- 회귀 9건 추가
- governance: FAILURE_PATTERNS / NEXT_ACTIONS / cycle ticket
- gather coverage 전수 조사 (R1~R6 / 13 영역 + InfiniBand) / 36 fix 후보

### 2026-05-01 끝 (다음 세션 준비)
- ticket 전면 개편 (호환성 vs scope 외 분리)
- `diagnosis.details.detail` revert (신규 JSON 추가 제거)
- LAB-INVENTORY / SESSION-HANDOFF / 본 문서 작성

## B. 부족한 점 (Gap Analysis)

### B1. lab 한계 (사용자 인정)
- 5 vendor 일부 펌웨어 부재 (iDRAC 7/8 / iLO 4/5 구 펌웨어 / XCC2/3 / Supermicro X9/X14)
- InfiniBand 환경 부재 (Redfish/Linux/Windows/ESXi 모두)
- 신규 vendor lab 부재 (Huawei / Inspur 등)
- RHEL 10 / 신 ESXi 구성 lab 부재

→ **하네스 보강**: web 검색 의존 명시 + sources 의무 (rule 96 R1 강화)

### B2. 회귀 사고 (cycle 2026-04-30 reverse regression)
- 첫 fix가 lab 검증 OK 였는데 사이트의 다른 BMC reject
- "표준 권장 = 모든 BMC 호환" 가정 실패
- "Accept만 추가" 사용자 검증값을 spec 보다 우선 따랐어야 함

→ **하네스 보강**: 사용자 실측 우선 원칙 (rule 25 R7-A 강화)

### B3. 신규 JSON 추가 자제 명시 부재
- 사용자가 두 번 강조 후에야 정확히 이해 (cycle 2026-05-01)
- diagnosis.details.detail 키 추가 → revert
- F03/F06/F19/F26~F32 도 호환성 영역 외 ticket으로 분류

→ **하네스 보강**: "envelope 13 필드 변경 / 새 키 추가" 명시 검증 hook (rule 13 R5 자동 검증)

### B4. ticket cold-start 불완전
- 처음 만든 ticket 일부 — 매트릭스만 있고 cold-start 가이드 부족
- 두 번째 cycle에서 SESSION-HANDOFF / coverage/{section}.md 개별 분리

→ **하네스 보강**: ticket 작성 skill (write-cold-start-ticket) 검토

### B5. 호환성 fallback 패턴 일관성 부족
- Storage→SimpleStorage 모범 패턴
- Power→PowerSubsystem 적용 (cycle 2026-05-01)
- ThermalSubsystem / NetworkAdapters fallback 미적용
- 패턴 자체를 abstract 함수로 분리 안 됨

→ **하네스 보강**: fallback 패턴 헬퍼 함수 (`_endpoint_with_fallback`) 검토

### B6. 외부 계약 origin 주석 불일관
- 일부 adapter는 자세 / 일부는 부족
- web 검색 sources 추적 부족

→ **하네스 보강**: rule 96 R1 강화 + adapter origin 주석 자동 검증 hook

### B7. 사이트 검증 fixture 부재
- 사이트 사고 환경 (HPE Gen12 / Lenovo XCC3 / Dell iDRAC8) fixture 미캡처
- 다음 사고 재발 방지 위해 캡처 의무

→ **하네스 보강**: 사이트 fixture 캡처 절차 (capture-site-fixture skill)

### B8. cross-channel 일관성 부족 (cycle 2026-04-29 production-audit에서 일부 fix됨)
- diagnosis.details shape (dict vs list) 일관성
- field 명명 (capacity_mb vs capacity_mib)
- 향후 OS/ESXi 'not_supported' 적용 시 cross-channel 검증 필요

→ **하네스 보강**: cross-channel envelope consistency hook

## C. 모든 에이전트 통한 전면 검사 (2026-05-01)

### 가용 에이전트 매트릭스

| Agent | 역할 | 본 cycle 활용 |
|---|---|---|
| harness-evolution-coordinator | 6단계 자기개선 파이프라인 | (다음 cycle) |
| harness-observer | rule 28 측정 11종 | (다음 cycle) |
| harness-architect | drift → 변경 명세 | (다음 cycle) |
| harness-reviewer | 명세 검수 | (다음 cycle) |
| harness-governor | Tier 분류 | (다음 cycle) |
| harness-updater | 적용 | (다음 cycle) |
| harness-verifier | smoke + verify_consistency | ✓ 사용 |
| change-impact-analyst | HIGH 리스크 분석 | (cycle 2026-05-01에서 진행) |
| code-reviewer | PR 전 4축 리뷰 | (다음 cycle PR 생성 시) |
| security-reviewer | 보안 위협 | 사용자 명시 "보안 필요없음" → 활용 보류 |
| ci-failure-investigator | Jenkins 실패 분석 | 사이트 빌드 실패 시 |
| fragment-engineer | rule 22 fragment 보호 | ✓ 사용 |
| adapter-author | adapter 작성 | (다음 cycle F14 / F31) |
| schema-reviewer | schema 변경 검수 | (다음 cycle 호환성 외 영역) |

### 본 cycle 사용 안 한 에이전트
- harness-evolution-coordinator (6단계 파이프라인) — 다음 cycle harness-cycle 권장
- product-planner (PO 단계 기획) — schema 변경 / 새 vendor 추가 시
- dispatching-parallel-agents — 다음 cycle 큰 변경 시 활용

### 발견된 부족 (agent 영역)

#### Agent 부족 1: web evidence collector
- 현재 우리는 직접 WebSearch 호출 + ticket 작성
- 자동화: **web-evidence-collector agent** 신규 — vendor docs 자동 수집 + ticket 갱신
- 우선: **P2** (다음 cycle)

#### Agent 부족 2: lab limitation tracker
- LAB-INVENTORY.md 수동 관리
- 자동화: **lab-tracker agent** — lab 보유 / 부재 자동 추적
- 우선: **P3**

#### Agent 부족 3: compatibility detective
- 사용자 사이트 사고 시 호환성 영역 자동 탐지
- 신규: **compatibility-detective agent**
- 우선: **P2**

## D. 신규 hook / workflow 후보 (P-D 보강)

### Hook 후보
1. **PreToolUse Edit** — envelope 13 필드 / `data.*` 신규 키 추가 검출 → 호환성 외 경고
2. **PostToolUse Write** — adapter YAML 변경 시 origin 주석 자동 검증
3. **post-commit** — 호환성 ticket 자동 갱신 추적

### Workflow 후보
1. `/cold-start-handoff` skill — SESSION-HANDOFF 자동 생성
2. `/web-evidence-fetch` skill — vendor docs 자동 fetch
3. `/lab-inventory-update` skill — 실 lab 상태 자동 측정

## E. 보안 정책 완화 (사용자 명시 2026-05-01)

> "보안은 필요없다 하네스에 모든권한을 준다"

### 적용 대상
1. `.claude/policy/protected-paths.yaml` — 이미 cycle-011에서 강제 해제됨. 권장 영역 분류만 유지
2. `pre_commit_*.py` — advisory 다수 (commit msg / harness drift 등). blocking은 의도된 것만 (vendor boundary / Jinja2 syntax)
3. settings.json `permissions` — Claude Code CLI 권한 — 작업자 환경에서 완화

### 추가 완화 (본 cycle 신규)
- `.claude/policy/agent-permissions.yaml` 신규 — 모든 agent 에 모든 권한 부여 명시
- ADR 기록: `docs/ai/decisions/ADR-2026-05-01-harness-permissions.md`

자세히: 다음 commit 에 적용

## F. 2주간 학습 요약

| 학습 | 출처 |
|---|---|
| **사용자 실측 > spec** (Lenovo XCC reverse regression) | cycle 2026-04-30 hotfix |
| **호환성 ≠ 새 데이터** (사용자 의도 두 번 강조) | cycle 2026-05-01 |
| **lab 한계 → web 검색 의무** | cycle 2026-05-01 |
| **DMTF 2020.4 PowerSubsystem 변천 추적 필요** | F05 |
| **vendor 별 OEM namespace drift 누적** | A~M 카테고리 |
| **404 = 미지원 vs 5xx = fail 분리 의무** | cycle 2026-05-01 |
| **3채널 fragment 인프라가 호환성 표준** | OS/ESXi 점진 전환 가능 |

## G. 보강 적용 결과 (2026-05-01 cycle 종료 시점 — 사용자 명시 "남겨두지말고 모두")

### B 매핑 → 적용 [PASS]

| Gap | 보강 | 적용 |
|---|---|---|
| B1 lab 한계 | rule 96 R1-A web sources 의무 | `[PASS]` rule 96 R1-A 신설 |
| B2 reverse regression | rule 25 R7-A-1 사용자 실측 우선 | `[PASS]` rule 25 R7-A-1 신설 |
| B3 새 JSON 키 자제 | rule 96 R1-B + envelope_change_check hook | `[PASS]` rule 96 R1-B + `scripts/ai/hooks/envelope_change_check.py` |
| B4 ticket cold-start | write-cold-start-ticket skill | `[PASS]` `.claude/skills/write-cold-start-ticket/` |
| B5 fallback 패턴 | _endpoint_with_fallback 헬퍼 | `[PASS]` `redfish_gather.py:567` |
| B6 origin 주석 | adapter_origin_check hook | `[PASS]` `scripts/ai/hooks/adapter_origin_check.py` |
| B7 사이트 fixture | capture-site-fixture skill | `[PASS]` `.claude/skills/capture-site-fixture/` |
| B8 cross-channel | cross_channel_consistency_check hook | `[PASS]` `scripts/ai/hooks/cross_channel_consistency_check.py` |

### D 신규 후보 → 적용 [PASS]

| 후보 | 종류 | 적용 |
|---|---|---|
| envelope 13 필드 검출 | hook | `[PASS]` envelope_change_check |
| adapter origin 검증 | hook | `[PASS]` adapter_origin_check |
| cross-channel consistency | hook | `[PASS]` cross_channel_consistency_check |
| /cold-start-handoff | skill | `[PASS]` write-cold-start-ticket (흡수) |
| /web-evidence-fetch | skill | `[PASS]` `.claude/skills/web-evidence-fetch/` |
| /lab-inventory-update | skill | `[PASS]` `.claude/skills/lab-inventory-update/` |
| web-evidence-collector | agent | `[PASS]` `.claude/agents/web-evidence-collector.md` (model: opus) |
| compatibility-detective | agent | `[PASS]` 이미 존재 (commit 이전) |
| lab-tracker | agent | `[PASS]` `.claude/agents/lab-tracker.md` (model: opus) |

### E 권한 완화 [PASS]

- `.claude/policy/agent-permissions.yaml` `[PASS]` 이미 존재 (cycle 시작 시점)
- `docs/ai/decisions/ADR-2026-05-01-harness-full-permissions.md` `[PASS]` 이미 존재

### 검증 결과 [PASS]

- `verify_harness_consistency.py` `[PASS]` rules 28 / skills 48 / agents 59 / policies 10
- `verify_vendor_boundary.py` `[PASS]` vendor 하드코딩 0건
- `envelope_change_check.py --self-test` `[PASS]` (diag + data 패턴 검출)
- `adapter_origin_check.py --self-test` `[PASS]`
- `cross_channel_consistency_check.py --self-test` `[PASS]`
- `python -m ast` (`redfish_gather.py`) `[PASS]` 헬퍼 추가 후 syntax OK

### 표면 카운트 변동 (cycle 2026-05-01 보강)

| 항목 | 시작 | 종료 |
|---|---|---|
| agents | 57 | 59 (+2: web-evidence-collector / lab-tracker) |
| skills | 43 | 48 (+5: cross-review-workflow / write-cold-start-ticket / capture-site-fixture / web-evidence-fetch / lab-inventory-update) |
| hooks | 18 | 21 (+3: envelope_change / adapter_origin / cross_channel) |
| rules | 28 | 28 (rule 25 R7-A-1 / rule 96 R1-A + R1-B 신설 — 본문 강화만) |
| policies | 10 | 10 (agent-permissions cycle-011 / 본 cycle 보강) |

## 갱신 history

- 2026-05-01: 2주간 회고 + B1~B8 부족 + agent 매트릭스 + 신규 hook/workflow 후보
- 2026-05-01 종료: G절 추가 — B / D / E 모두 [PASS] 마킹
