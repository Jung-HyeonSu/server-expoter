# Harness Full Sweep — 2026-04-28

> 사용자 명시 요청 ("하네스 전체 점검 및 프로젝트 코드 전체점검")으로 실행. cycle-006 (2026-04-28) 직후 시점.

## 0. 요약

| 영역 | CRITICAL | HIGH | MED | LOW | INFO |
|---|---|---|---|---|---|
| 1. skills + agents | 0 | 1 (잔재 어휘) | 2 | 2 | 1 |
| 2. rules + policies | 0 | 3 | 3 | 1 | 5 |
| 3. docs/ai catalogs | 0 | 3 | 3 | 3 | 5 |
| 4. scripts + hooks + settings | 0 | 0 | 2 | 3 | 5 |
| 5. Ansible + Python 코드 | 0 | 3 | 6 | 4 | 4 |
| 6. schema + baseline | 0 | 2 | 4 | 1 | 1 |
| 7. vendor boundary + adapter | 0 | 3 | 3 | 4 | 4 |
| 합계 | **0** | **15** | **23** | **18** | **25** |

**기본 검증 5종 (verify_harness_consistency / verify_vendor_boundary / check_project_map_drift / scan_suspicious_patterns / validate_claude_structure) 모두 PASS** — 그 너머의 의도 / 정합 / 가독성 점검에서 발견된 항목.

---

## 1. drift 통합 명세 (Tier 분류)

### Tier 1 — 자동 적용 (stale 정정 / catalog 갱신)

| ID | 영역 | 변경 |
|---|---|---|
| T1-01 | docs | `docs/ai/CURRENT_STATE.md:108` `(cycle-005 후보)` → `(cycle-007 후보)` |
| T1-02 | docs | `docs/ai/NEXT_ACTIONS.md:49` `(cycle-005 진입 시점)` → `(cycle-007 진입 시점)` |
| T1-03 | docs | `docs/ai/catalogs/PROJECT_MAP.md:6` 일자 → `2026-04-28`, `:34` `# 28 Must + Nice + Skip` → `# 31 Must + 9 Nice + 6 Skip = 46 entries` |
| T1-04 | docs | `docs/ai/catalogs/SCHEMA_FIELDS.md` line 23-29 grep 결과 + line 38 stale "28 Must / 7 Nice / 5 Skip" → 실측 31/9/6/46 일관 정정 |
| T1-05 | docs | `docs/ai/catalogs/TEST_HISTORY.md` cycle-002~006 entry 일괄 추가 (실 결과 기반) |
| T1-06 | docs | `docs/ai/catalogs/EXTERNAL_CONTRACTS.md` 마지막 동기화 일자 갱신 (cycle-006 redfish_gather 변경 trigger) |
| T1-07 | docs | `docs/ai/catalogs/JENKINS_PIPELINES.md:73` "rule 80 정정 검토" 후속 close (rule 80 R1-A 본문 추가됨) |
| T1-08 | rules | `.claude/rules/00-core-repo.md:16` `Field Dictionary 28 Must` → `31 Must + 9 Nice + 6 Skip = 46 entries` |
| T1-09 | rules | `.claude/rules/23-communication-style.md:63` 어휘 치환표 `28 Must` → `31 Must` |
| T1-10 | role | `.claude/role/output-schema/README.md:4,8,51` `28 Must` → `31 Must` (3곳) |
| T1-11 | ai-context | `.claude/ai-context/output-schema/convention.md:42,45` `28 Must / Must (28)` → `31 Must / Must (31)` |
| T1-12 | ai-context | `.claude/ai-context/common/repo-facts.md:47` `(28 Must)` → `(31 Must / 9 Nice / 6 Skip)` |
| T1-13 | ai-context | `.claude/ai-context/common/coding-glossary-ko.md:16` `28 Must` → `31 Must` |
| T1-14 | skills | `.claude/skills/update-output-schema-evidence/SKILL.md:39` 예시 분포 갱신 |
| T1-15 | rules | `.claude/rules/22-fragment-philosophy.md:31-44` Bad/Good 예시의 `❌` 이모지 → `[NG]` ASCII (rule 23 R8) |
| T1-16 | code | `common/library/precheck_bundle.py:72` author `ClovierOne Portal Team` → `server-exporter` |
| T1-17 | code | `lookup_plugins/adapter_loader.py:22` 동일 |
| T1-18 | catalog | `docs/ai/catalogs/CONVENTION_DRIFT.md` DRIFT-008 등재 (이번 sweep에서 발견된 stale 28 Must 6곳 + cycle-006 미반영) — resolved 마커 |

**예상 영향**: docs/ai + .claude/rules + .claude/role + .claude/ai-context + 코드 author 메타 = 약 18개 파일. 기능 영향 0. 기준선 검증 5종 PASS 유지.

---

### Tier 2 — 사용자 승인 필요 (rule 본문 / 코드 / policy 변경)

#### T2-A. Rule 본문 정합

| ID | 변경 | 근거 |
|---|---|---|
| T2-A1 | rule 23 R4 `5체크 → 6체크` (line 87/90/137) | rule 24 본문 + CLAUDE.md 모두 `6 체크` (rule 24 = 정본) |
| T2-A2 | rule 91 R7 ↔ rule 92 R9 중복 정의 정리 (정본을 91 R7로, 92 R9는 "rule 91 R7 참조"로 단축) | 두 rule이 같은 영역에 별도 R번호 부여 |
| T2-A3 | rule 13 R5 + rule 20 R1 본문 "envelope 6 필드" → "envelope 13 필드" (실 구현 정합) | 실측 envelope: schema_version/target_type/collection_method/ip/hostname/vendor/status/sections/diagnosis/meta/correlation/errors/data |
| T2-A4 | rule 13:14 + rule 80:14 "DRIFT-002 정리" 인용 제거 (rule이 catalog DRIFT 번호에 의존) | catalog 변경 시 rule drift 생산 |
| T2-A5 | rule 92 R5:52 "Flyway 버전 사용자 확인과 동일 정신" → 단어 정정 ("schema 버전 사용자 확인 정책") | rule 00 금지어 위반 |
| T2-A6 | rule 21:5-6 적용 대상 `tests/baseline_v1/**` 제거 (실디렉터리 = `schema/baseline_v1/**` 만) | rule 본문 stale |
| T2-A7 | rule 24/26/41/50/60/70/90 — Default/Allowed/Forbidden/Why 5요소 보강 | template 표준 미준수 7개 rule |

#### T2-B. clovirone 잔재 어휘 정리 (rule 00 본인이 금지)

| ID | 변경 | 위치 |
|---|---|---|
| T2-B1 | "clovirone X에 대응" 매핑 표현 일괄 제거 또는 "역사 메타" 단일 위치(`ecc-adoption-summary.md`)로 이전 | skill description 5곳 + agent description 4곳 (총 9곳: investigate-ci-failure / plan-schema-change / review-adapter-change / update-output-schema-evidence / classify-precheck-layer / vendor-change-impact / schema-migration-worker / schema-mapping-reviewer / output-schema-reviewer / build-verifier / gather-refactor-worker) |
| T2-B2 | `verify_harness_consistency.py` FORBIDDEN_WORDS default 모드 검사 활성화 (rule 00 약속이지만 default skip 중) | 향후 detect 강제 |
| T2-B3 | rule 80:12 "Bitbucket Pipelines 사용 안 함" → 단어 제거 ("CI는 Jenkins multi-pipeline 3종") | rule 00 금지어 위반 |

#### T2-C. 코드 결함 (운영 영향)

| ID | 변경 | 근거 |
|---|---|---|
| T2-C1 | `common/library/precheck_bundle.py` urllib fallback 경로의 timeout 분리 (Redfish 30s / SSH 10s / WinRM 30s) | rule 30 R3 위반 — 현재 `timeout` 인자 단일 변수 혼용 |
| T2-C2 | `common/library/precheck_bundle.py:319-343` Stage 1 (reachable) ↔ Stage 2 (port_open) 분리, `failure_stage` 4단계 정확도 | rule 27 R1 + rule 27 R2 — 운영 진단 오인 가능 |
| T2-C3 | `redfish-gather/library/redfish_gather.py:924-926` `traceback.format_exc(limit=3)` errors detail 노출 → `type(e).__name__` + 일반 메시지로 redaction | rule 60 에러 메시지 정책 위반 |
| T2-C4 | `os-gather/site.yml:281` + `redfish-gather/site.yml:166` + `esxi-gather/site.yml:163` always 블록 fallback envelope 6 필드 보강 (현재 status/errors 2 필드만) | rule 13 R5 / rule 20 R4 위반 — 호출자 파싱 실패 가능 |
| T2-C5 | `filter_plugins/field_mapper.py` DEPRECATED dead code 삭제 (4 라인 + FilterModule 클래스) | rule 00 금지 패턴 — Ansible 로드 시 등록 |
| T2-C6 | `module_utils/adapter_common.py:62-75` `normalize_vendor` 역형 dict 방어 (진입부 dict 형태 validate) | rule 95 R1 #10 mutable/immutable + 잠재 silent pass |
| T2-C7 | `redfish-gather/tasks/detect_vendor.yml:24-35` Jinja2 정확매칭 → 부분매칭 추가 (Python `_normalize_vendor_from_aliases`와 일관성) | rule 95 R1 #11 외부 계약 drift — manufacturer 형변환 시 unknown 증가 |
| T2-C8 | `os-gather/tasks/linux/gather_users.yml:25-63 vs 134-178` `get_last_login` 함수 중복 통합 | rule 10 R3 + 향후 동기화 누락 위험 |

#### T2-D. Schema / Baseline 정합

| ID | 변경 | 근거 |
|---|---|---|
| T2-D1 | `common/tasks/normalize/init_fragments.yml:42-46` + `build_empty_data.yml:24-28` + `build_failed_output.yml:79-80` 의 storage 뼈대에 `logical_volumes: []` 추가 | sections.yml + field_dictionary 정의했으나 3 builder 누락 — rule 13 R5 위반, 호출자 파싱 NG 가능 |
| T2-D2 | `schema/baseline_v1/cisco_baseline.json` `data.users: null` → `[]` (다른 vendor 일관) | rule 21 R1 + sections.yml `users.empty_value: []` 위반 |
| T2-D3 | `schema/examples/` 에 `failed` envelope 예시 JSON 추가 | rule 13 R5 학습 자료 부재 |
| T2-D4 | `tests/validate_field_dictionary.py` WARN 6건 해소 (`users[].name|uid|groups|home|last_access_time` + `system.hosting_type` examples 반영) | cycle-006 신규 필드 examples 미반영 |

#### T2-E. Vendor / Adapter 경계

| ID | 변경 | 근거 |
|---|---|---|
| T2-E1 | `.claude/policy/vendor-boundary-map.yaml` 실디렉터리 기준 rewrite (hpe_synergy / lenovo_xcc_legacy / supermicro_x12 / supermicro_legacy 미존재 참조 정리, cisco oem path null) | policy 파일이 stale → 새 vendor 추가 시 진실 원천 혼란 |
| T2-E2 | redfish 12개 adapter (dell×3 / hpe×4 / lenovo×2 / supermicro×3 / cisco×1) 각각 metadata origin 주석 일괄 추가 | rule 96 R1 — vendor / firmware / tested_against / oem_path 명시 |
| T2-E3 | cisco oem 처리 결정: (a) `redfish-gather/tasks/vendors/cisco/collect_oem.yml` placeholder 추가 / (b) `vendor-boundary-map.yaml` cisco oem_tasks: null 명시 | strategy: standard_only이지만 policy 참조 깨짐 |
| T2-E4 | `adapters/redfish/{supermicro_x11,supermicro_x9,supermicro_bmc}.yml` `match.vendor` 에 마침표 없는 변형 `"Super Micro Computer"` 추가 | vendor_aliases.yml과 일관성 (현재는 normalize_vendor가 통과하나 명시적 일관성) |

#### T2-F. Settings / Hooks 동기화

| ID | 변경 | 근거 |
|---|---|---|
| T2-F1 | `.claude/settings.json` 의도 명시 주석 추가 (`Bash(*)` allow + `acceptEdits` + deny 패턴 정책 의도) | rule 60 추가 정책 명시 |
| T2-F2 | `.claude/policy/protected-paths.yaml` ↔ `settings.json` deny 동기화 (id_rsa/CLAUDE.local.md/*.log/.env.* 등 6 항목 양방향 정합) | 단방향 의존 — pre_edit_guard.py가 보완하나 drift 위험 |
| T2-F3 | `scripts/ai/hooks/output_schema_drift_check.py` 분류 명시 (CI/수동 도구 — git hook도 Claude hook도 아님) | 현재 hooks/ 디렉터리에 있어 분류 모호 |

---

### Tier 3 — 사용자 에스컬레이션 (스킵, 깊은 결정)

| ID | 항목 | 사용자 결정 필요 |
|---|---|---|
| T3-01 | precheck_bundle.py `requests` 라이브러리 의존 유지 vs 제거 (rule 10 R2 stdlib only는 redfish_gather.py만 명시) | 의존 정책 |
| T3-02 | HPE iLO5/iLO6 priority 동률 100 → 차등 부여 여부 | 실 펌웨어 매칭 변경 |
| T3-03 | Lenovo generic fallback adapter 추가 여부 (priority=10 lenovo_generic.yml) | adapter 정책 |
| T3-04 | adapter `version: "1.0.0"` 25개 동일 → 의미 있는 버전 추적 메커니즘 도입 여부 | 추적 정책 |
| T3-05 | redfish_gather.py:476-493 BMC IP 수집 N+1 호출 최적화 | 성능 vs 단순성 |
| T3-06 | docs/ai/decisions/ ADR 정책 — DRIFT-006 같은 governance 결정의 ADR 필수 여부 | 거버넌스 trace 강도 |

---

## 2. 검증 baseline (sweep 시작 시점)

```
verify_harness_consistency.py  → PASS (rules: 29, skills: 43, agents: 51, policies: 10)
verify_vendor_boundary.py       → PASS (vendor 하드코딩 0건)
check_project_map_drift.py     → PASS (fingerprint 일치)
scan_suspicious_patterns.py    → PASS (rule 95 R1 11 패턴 0건)
validate_claude_structure.py   → PASS

field_dictionary.yml 실측: 31 Must / 9 Nice / 6 Skip = 46 entries (CLAUDE.md 일치)
adapters/ 실측: 25 (redfish 13 + os 7 + esxi 4 + registry.yml 1)
schema/baseline_v1/ 실측: 7 baseline (cisco/dell/hpe/lenovo/esxi/ubuntu/windows)
docs/ai/harness/cycle-*.md: 6 (cycle-001~006)
```

---

## 3. 진행 계획

1. **Tier 1 (T1-01~T1-18)**: 사용자 승인 없이 자동 적용 (stale 정정 / docs 갱신)
2. **Tier 2 (T2-A~T2-F)**: 사용자 승인 후 적용 — sub-tier별 분할 commit
3. **Tier 3**: 본 보고서에 기록만, 별도 결정 세션
