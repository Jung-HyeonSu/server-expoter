# server-exporter 하네스 리팩토링 설계서

- 일시: 2026-04-27
- 작성자: Claude (hshwang1994 협업)
- 출처 하네스: `clovirone-base/.claude/` (Java/Spring/Vue/MyBatis/multi-customer/plugin 도메인)
- 대상 프로젝트: `C:\github\server-exporter` (Ansible/Python/Jenkins/multi-vendor/adapter/fragment 도메인)
- 설계 방식: 풀스펙 포팅 (1:1 구조 보존, 도메인 어휘 치환)

---

## 1. 목적과 동기

**무엇** — clovirone-base의 정교한 자기개선 하네스(46 agents · 46 skills · 30 rules · 10 policy YAML · ai-context · role · hooks · templates · self-improvement loop)를 server-exporter 프로젝트에 맞도록 1:1 풀포팅한다.

**왜** — server-exporter는 엔터프라이즈급 멀티벤더 서버 정보 수집 파이프라인으로, 이미 프로덕션 준비 완료(Round 7~10 검증) 상태이다. 향후 새 벤더 추가, 새 섹션 확장, 실장비 회귀 검증, Jenkins 파이프라인 운영, 외부 시스템 계약 변경 등 다양한 작업이 예상된다. clovirone에서 검증된 게이트(task-impact-preview, completion-gate, production-critical-review, external-contract-integrity 등)와 자기개선 루프(observer→architect→reviewer→governor→updater→verifier)를 server-exporter 도메인에 이식하면 동일한 운영 안정성을 확보할 수 있다.

**영향** — 신규 약 200 파일 추가. 기존 server-exporter 코드(ansible playbook, python module, schema, vault, tests, docs/01~19, CLAUDE.md, REQUIREMENTS.md, README.md) 무수정.

**결정 주체** — 사용자가 2026-04-27 대화에서 풀스펙 포팅 / vendor만 customer-plugin slot 매핑 / 6분류 직접 매핑 / 기존 문서 보존 + 추가 의 4개 핵심 결정 + 나머지 추천안 일괄 채택을 승인.

---

## 2. 합의된 핵심 결정사항

| # | 결정 | 선택 |
|---|---|---|
| 1 | 야심 규모 | A. 풀스펙 포팅 (clovirone과 동일 표면적, 도메인만 치환) |
| 2 | customer-plugin-branch 매핑 | A. vendor만 customer-plugin slot. branch는 main + feature/* 2계층. loc/pipeline은 운영 토폴로지 |
| 3 | role 분류 | A. 6분류 직접 매핑 (backend→gather, frontend→output-schema, infra/qa/po/tpm 그대로) |
| 4 | 기존 문서 통합 | A. 보존 + 추가 (기존 무수정, .claude/ + docs/ai/ 신규 추가) |
| 5 | 자기개선 루프 | 7 harness agents 그대로 유지 |
| 6 | 신규 파일 수 | 약 200 파일 (Phase별 commit 분할) |
| 7 | 진행 방식 | 3 세션 분할 (P1~3 / P4~5 / P6~8) |
| 8 | prototype 자산 | server-exporter는 UI 없음 → 전부 제거 |

---

## 3. 핵심 매핑 표 (clovirone → server-exporter 어휘)

| 카테고리 | clovirone | server-exporter |
|---|---|---|
| 언어 | Java 19 + Spring Boot 3.3 | Ansible 2.20 + Python 3.12 |
| 프론트엔드 | FTL + Vue.js + jQuery | (없음 → 3-channel JSON 출력 schema) |
| DB | MariaDB + MyBatis + Flyway | (없음 → sections.yml + field_dictionary.yml + baseline JSON) |
| 빌드 | Gradle 7.6 | (없음 → ansible-playbook 실행) |
| CI | Bitbucket Pipelines | Jenkins (Jenkinsfile, Jenkinsfile_grafana, Jenkinsfile_portal) |
| 테스트 | Spock + Playwright | pytest baseline + redfish-probe + 실장비 검증 |
| 시크릿 | Properties + ENV | Ansible Vault (vault/redfish/{vendor}.yml) |
| 모듈 | clovircm-{domain,web} + plugin-{posco,smilegate,...} | os-gather + esxi-gather + redfish-gather + common + adapters/{redfish,os,esxi}/{vendor}*.yml |
| 고객사 | KISA / INA / POSCO / SK하이닉스 / 스마일게이트 | (제거) |
| 벤더 | (해당 없음) | Dell / HPE / Lenovo / Supermicro / Cisco |
| plugin 모듈 | plugin-{posco,smilegate,example} | adapters/{channel}/{vendor}_*.yml + redfish-gather/tasks/vendors/{vendor}/ |
| branch 정책 | sk-hynix / sk-hynix-dev / sk-hynix-claude-* (3계층) | main / feature/new-vendor-* / fix/* (2계층 단순) |
| loc | (해당 없음) | ich / chj / yi (운영 토폴로지로만, 코드 분기 없음) |
| fragment 철학 | 공통 컴포넌트 재사용 (rule 22) | 각 gather 자기 fragment만, merge_fragment.yml이 누적 |
| adapter 점수 | (해당 없음) | priority × 1000 + specificity × 10 + match_score |
| Service Layer | Finder / Maker / Validator / Service / Handler / Hook | gather_* / normalize_* / build_* / precheck_* / include_tasks 패턴 |
| 외부 시스템 | Jenkins / GitLab / VMware / OpenStack / Ansible / Harbor | Redfish / IPMI / SSH / WinRM / vSphere API |

---

## 4. 디렉터리 구조 (TO-BE)

```
server-exporter/
├── CLAUDE.md                        ← 기존 보존, Tier 0 정본 패턴 흡수해 보강
├── README.md                        ← 무수정
├── rule 22 (fragment-philosophy)                  ← 무수정
├── REQUIREMENTS.md                  ← 무수정
├── ansible.cfg                      ← 무수정
├── Jenkinsfile, Jenkinsfile_grafana, Jenkinsfile_portal  ← 무수정
├── adapters/                        ← 무수정 (도메인 코드)
├── callback_plugins/                ← 무수정
├── common/                          ← 무수정
├── esxi-gather/                     ← 무수정
├── filter_plugins/                  ← 무수정
├── lookup_plugins/                  ← 무수정
├── module_utils/                    ← 무수정
├── os-gather/                       ← 무수정
├── redfish-gather/                  ← 무수정
├── schema/                          ← 무수정
├── tests/                           ← 무수정
├── tools/                           ← 무수정
├── vault/                           ← 무수정 (시크릿)
├── docs/
│   ├── 01_jenkins-setup ~ 19_decision-log  ← 기존 19개 무수정 (운영자 정본)
│   ├── superpowers/specs/           ← 본 설계서 위치
│   └── ai/                          ← 신규 (AI 협업 메타 문서)
│       ├── CURRENT_STATE.md
│       ├── NEXT_ACTIONS.md
│       ├── catalogs/                ← FAILURE_PATTERNS, PROJECT_MAP, TEST_HISTORY,
│       │                              CONVENTION_DRIFT, VENDOR_ADAPTERS,
│       │                              SCHEMA_FIELDS, EXTERNAL_CONTRACTS,
│       │                              JENKINS_PIPELINES (8종)
│       ├── decisions/               ← ADR-YYYY-MM-DD-*.md
│       ├── policy/                  ← SECURITY_POLICY, SESSION_ROUTING_POLICY,
│       │                              SKILL_EXECUTION_POLICY, DYNAMIC_ROUTING_RULES,
│       │                              HARNESS_CHANGE_POLICY
│       ├── workflows/               ← HARNESS_EVOLUTION_MODEL, HARNESS_GOVERNANCE,
│       │                              HARNESS_FEEDBACK_LOOP, IMPACT_VALIDATION_TRIAD
│       ├── harness/                 ← cycle-001 등 self-improvement 로그
│       ├── handoff/                 ← 세션 인계 문서
│       ├── impact/                  ← 사고 분석
│       ├── incoming-review/         ← 머지 후 자동 리뷰 보고서
│       ├── roadmap/                 ← 기술 범위/방향
│       └── onboarding/              ← AI/사람 진입 가이드
├── scripts/
│   └── ai/
│       └── hooks/                   ← Python hooks
│           ├── session_start.py
│           ├── pre_edit_guard.py
│           ├── post_edit_hint.py
│           ├── skill_edit_validate.py
│           ├── post_edit_jinja_check.py    (← post_edit_ftl_i18n_check 대체)
│           ├── stop_writeback.py
│           ├── subagent_stop_log.py
│           ├── notification_log.py
│           ├── user_prompt_router.py
│           ├── detect_self_approval.py
│           ├── post_merge_incoming_review.py
│           ├── commit_msg_check.py
│           ├── install-git-hooks.sh
│           ├── verify_harness_consistency.py
│           ├── check_project_map_drift.py
│           ├── check_gap_against_dev.py    (단일 main이라 gap 체크 단순화)
│           └── verify_vendor_boundary.py   (← verify_customer_boundary 대체)
└── .claude/
    ├── settings.json
    ├── settings.local.json
    ├── rules/                       ← 30 rules
    ├── skills/                      ← 약 42 skills (각 폴더 SKILL.md)
    ├── agents/                      ← 약 42 agents (각 .md)
    ├── role/                        ← gather, output-schema, infra, qa, po, tpm 6 README
    ├── ai-context/
    │   ├── common/                  ← repo-facts, project-map, coding-glossary-ko,
    │   │                              convention-drift, ecc-adoption-summary
    │   ├── gather/                  ← convention.md (Fragment 철학은 rule 22 (fragment-philosophy) 참조)
    │   ├── output-schema/           ← convention.md (sections / field_dictionary)
    │   ├── infra/                   ← convention.md (Jenkins / Agent / Vault / Redis)
    │   ├── vendors/                 ← Dell, HPE, Lenovo, Supermicro, Cisco 별 OEM 메모
    │   └── external/                ← Redfish / IPMI / SSH / WinRM / vSphere 외부 시스템 노트
    ├── policy/                      ← 10 YAML
    │   ├── approval-authority.yaml
    │   ├── vendor-boundary-map.yaml      (← customer-boundary-map 대체)
    │   ├── measurement-targets.yaml
    │   ├── channel-ownership.yaml        (← module-ownership 대체)
    │   ├── project-map-fingerprint.yaml
    │   ├── protected-paths.yaml          (vault/, adapters/, Jenkinsfile*, schema/ 보호)
    │   ├── review-matrix.yaml
    │   ├── security-redaction-policy.yaml
    │   ├── surface-counts.yaml
    │   └── test-selection-map.yaml
    ├── templates/                   ← CURRENT_STATE.template.md 등 (prototype-skeleton 제거)
    └── commands/                    ← harness-cycle, harness-full-sweep,
                                        review-guide, scheduler-guide, usage-guide
```

---

## 5. Rules 매핑 (30개)

| 번호 | clovirone | server-exporter | 변경 핵심 |
|---|---|---|---|
| 00 | core-repo | 00-core-repo | 모듈 계층(domain/web/plugin) → channel(os/esxi/redfish) + adapter + common |
| 10 | backend-core | 10-gather-core | Java/Spring → Ansible/Python, raw 수집 + fragment 생성 원칙 |
| 11 | backend-domain-web-boundary | 11-gather-output-boundary | gather가 output 정규화에 직접 손대지 말 것 |
| 12 | backend-plugin-boundary | 12-adapter-vendor-boundary | vendor adapter 경계 보호 |
| 13 | backend-database-mybatis-jpa | 13-output-schema-fields | sections.yml + field_dictionary.yml 28 Must + baseline JSON |
| 20 | frontend-ftl-jquery-vue | 20-output-json-callback | callback_plugins/json_only.py 보호, JSON envelope 규칙 |
| 21 | frontend-static-assets | 21-output-baseline-fixtures | tests/fixtures, baseline_v1 보호 |
| 22 | frontend-shared-components | **22-fragment-philosophy** | 각 gather 자기 fragment만 (server-exporter 핵심 rule) |
| 23 | communication-style | 23-communication-style | 그대로 (어휘 치환표 server-exporter용으로 갱신) |
| 24 | completion-gate | 24-completion-gate | ansible-lint/yamllint/pytest/schema validate/baseline diff |
| 25 | parallel-agents | 25-parallel-agents | 그대로 |
| 26 | multi-session-guide | 26-multi-session-guide | 그대로 |
| 27 | frontend-guard-first | 27-precheck-guard-first | 4단계 진단(ping→port→protocol→auth) 통과 후 본 수집 |
| 28 | empirical-verification-lifecycle | 28-empirical-verification-lifecycle | 측정 대상 재편 |
| 30 | integration-vmware-server-semaphore | 30-integration-redfish-vmware-os | 3-channel 외부 시스템 |
| 31 | integration-remote-access | 31-integration-callback | 호출자 callback URL 무결성 |
| 40 | qa-playwright-xray | 40-qa-pytest-baseline | Playwright→pytest, Xray→baseline JSON 회귀 |
| 41 | mermaid-visualization | 41-mermaid-visualization | 그대로 |
| 50 | customer-branch-policy | 50-vendor-adapter-policy | branch 부분 단순화, vendor 경계 강화 |
| 60 | security-and-secrets | 60-security-and-secrets | 그대로 + vault/redfish/{vendor}.yml |
| 70 | docs-and-evidence-policy | 70-docs-and-evidence-policy | 그대로 |
| 80 | ci-and-release-policy | 80-ci-jenkins-policy | Bitbucket→Jenkins 3종 |
| 90 | commit-convention | 90-commit-convention | 그대로 |
| 91 | task-impact-gate | 91-task-impact-gate | 영향 분석에 fragment/adapter/schema/vendor baseline 추가 |
| 92 | dependency-and-regression-gate | 92-dependency-and-regression-gate | Gradle→ansible collection/pip, Flyway→schema YAML 버전 |
| 93 | branch-merge-gate | 93-branch-merge-gate | main + feature/* 단순화 |
| 95 | production-code-critical-review | 95-production-code-critical-review | 의심 패턴 11종 server-exporter용 (fragment 침범, vendor 하드코딩, vault 누설, raw fallback 누락 등) |
| 96 | external-contract-integrity | 96-external-contract-integrity | Redfish/SSH/WinRM/IPMI 응답 schema drift |
| 97 | incoming-merge-review | 97-incoming-merge-review | 자동 검사 5종 server-exporter용 |

(94는 clovirone에도 비어있음)

---

## 6. Skills 매핑 (약 38개)

### 6.1 그대로 유지 (어휘만 갱신)
mermaid-visualization, plan-feature-change, plan-product-change, plan-structure-cleanup,
analyze-new-requirement, compare-feature-options, recommend-product-direction,
discuss-feature-direction, write-spec, write-impact-brief, write-feature-flowchart,
update-flowchart-after-change, visualize-flow, harness-cycle, harness-full-sweep,
measure-reality-snapshot, update-evidence-docs, prepare-regression-check,
scheduler-change-playbook (Jenkins cron 대상), task-impact-preview, write-quality-tdd,
debug-external-integrated-feature, review-existing-code, review-incoming-merge,
investigate-ci-failure (Jenkins 로그 대상), handoff-driven-implementation (prototype 부분 제거)

### 6.2 어휘 치환
- `bitbucket-pr-review-playbook` → **`pr-review-playbook`** (또는 `jenkins-pr-review-playbook`; CI 시스템 따라)
- `customer-change-impact` → **`vendor-change-impact`**
- `verify-plugin-boundary` → **`verify-adapter-boundary`**
- `classify-validation-layer` → **`classify-precheck-layer`** (4단계 진단 어디서 차단할지)
- `review-sql-change` → **`review-adapter-change`** (adapter YAML 변경 리뷰)
- `run-ui-smoke` → **`run-baseline-smoke`** (벤더 fixture 빠른 검증)
- `verify-ui-rendering` → **`verify-json-output`** (3-channel JSON envelope 검증)
- `update-db-schema-evidence` → **`update-output-schema-evidence`** (sections + field_dictionary 정합)
- `plan-db-change` → **`plan-schema-change`**
- `pull-and-analyze-dev` → 단일 main이라 단순화 (`pull-and-analyze-main` 또는 단순 git fetch)

### 6.3 제거 (UI 없음)
prototype-ui, revise-prototype, open-prototype-preview

### 6.4 신규 (server-exporter 고유)
- `validate-fragment-philosophy` — 다른 gather의 fragment 침범 안 했는지 검증
- `score-adapter-match` — 점수 계산 디버깅 (adapter_loader -vvv 분석)
- `add-new-vendor` — 벤더 추가 3단계 가이드
- `probe-redfish-vendor` — 새 펌웨어 프로파일링 (deep_probe_redfish.py)
- `update-vendor-baseline` — 실장비 검증 후 baseline JSON 갱신
- `debug-precheck-failure` — 4단계 진단 어디서 막혔는지
- `rotate-vault` — 벤더별 vault 회전

---

## 7. Agents 매핑 (약 49개)

### 7.1 도메인 워커
| clovirone | server-exporter |
|---|---|
| backend-refactor-worker | gather-refactor-worker |
| frontend-refactor-worker | output-schema-refactor-worker |
| billing-refactor-worker | (제거 — 도메인 없음) |
| scheduler-refactor-worker | jenkins-refactor-worker |
| migration-worker | schema-migration-worker |
| nonfunctional-refactor-worker | 그대로 |
| qa-regression-worker | 그대로 |
| chrome-ui-e2e-worker | baseline-validation-worker |

### 7.2 리뷰어
| clovirone | server-exporter |
|---|---|
| mybatis-reviewer | schema-mapping-reviewer |
| frontend-ftl-vue-reviewer | output-schema-reviewer |
| dba-reviewer | schema-reviewer |
| plugin-boundary-reviewer | adapter-boundary-reviewer |
| customer-boundary-guardian | vendor-boundary-guardian |
| security-reviewer, naming-consistency-reviewer, integration-impact-reviewer, flowchart-reviewer | 그대로 |

### 7.3 코디네이터/스페셜리스트 (대부분 그대로)
- 그대로: decision-recorder, deploy-orchestrator, directory-structure-architect, discovery-facilitator, docs-sync-worker, feature-flowchart-designer, flow-visualizer, impact-brief-writer, option-generator, product-planner, regression-planner, release-manager, repo-hygiene-planner, rollback-advisor, spec-writer, change-impact-analyst, build-verifier, ci-failure-investigator
- query-tuning-investigator → **ansible-perf-investigator** (작업 시간 분석)
- wave-coordinator → 그대로
- prototype-feedback-coordinator → **제거**
- ui-prototype-designer / ui-prototype-worker → **제거**

### 7.4 자기개선 루프 (7 agents 그대로 유지)
harness-architect, harness-evolution-coordinator, harness-governor, harness-observer, harness-reviewer, harness-updater, harness-verifier

### 7.5 신규 (server-exporter 고유)
- `fragment-engineer` — Fragment 철학 보호, merge_fragment.yml 검증
- `adapter-author` — 벤더 adapter YAML 작성 전문
- `vendor-onboarding-worker` — 새 벤더 추가 (vendor_aliases.yml + adapter YAML + OEM tasks 3단계)
- `precheck-engineer` — 4단계 진단 / common/library/precheck_bundle.py
- `vault-rotator` — 벤더별 vault 회전
- `jenkinsfile-engineer` — Jenkinsfile 3종 보호

---

## 8. Hooks (Python, scripts/ai/hooks/)

| clovirone | server-exporter | 변경 |
|---|---|---|
| session_start.py | session_start.py | 단일 main + feature/* 단순화, 측정 대상 drift는 server-exporter용 |
| pre_edit_guard.py | pre_edit_guard.py | 보호 경로: vault/, adapters/, Jenkinsfile*, schema/ |
| post_edit_hint.py | post_edit_hint.py | 그대로 (라우팅 룰 갱신) |
| post_edit_ftl_i18n_check.py | post_edit_jinja_check.py | Jinja2 템플릿 변수 정합성 |
| skill_edit_validate.py | 그대로 | |
| stop_writeback.py | 그대로 | |
| subagent_stop_log.py, detect_self_approval.py | 그대로 | |
| notification_log.py, user_prompt_router.py | 그대로 | |
| post_merge_incoming_review.py | 그대로 | 자동 검사 5종 server-exporter용 (Jenkinsfile cron, adapter 의심, schema 버전 중복, vendor enum drift) |
| commit_msg_check.py | 그대로 | |
| verify_harness_consistency.py | 그대로 | |
| check_project_map_drift.py | 그대로 | |
| check_gap_against_dev.py | (단순화) | 단일 main이라 gap 체크 축소 |
| verify_customer_boundary.py | verify_vendor_boundary.py | |

---

## 9. Phase 분할 (실행 순서)

| Phase | 산출물 | 예상 분량 | 세션 |
|---|---|---|---|
| **P1. 골격** | settings.json + settings.local.json + CLAUDE.md 보강 + .claude/ 디렉터리 + 핵심 6 rules (00, 23, 24, 90, 91, 95) + 기본 templates | ~10 파일 | 1 |
| **P2. 정책/메타** | policy YAML 10개 + ai-context 6 role + role/ README 6개 + 나머지 templates | ~25 파일 | 1 |
| **P3. 룰** | 나머지 24 rules | ~24 파일 | 1 |
| **P4. 스킬** | 약 38 skills | ~38 파일 | 2 |
| **P5. 에이전트** | 약 49 agents | ~49 파일 | 2 |
| **P6. 훅** | scripts/ai/hooks/ Python 약 13개 + commit_msg_check + install-git-hooks.sh + verify_* | ~16 파일 | 3 |
| **P7. 운영 문서** | docs/ai/ (CURRENT_STATE, NEXT_ACTIONS, catalogs 8종, decisions/, policy/, workflows/, harness/, onboarding/, handoff/, impact/, incoming-review/, roadmap/) 초기 골격 | ~25 파일 | 3 |
| **P8. 자기개선 루프 검증** | harness-cycle dry-run + verify_harness_consistency.py 통과 확인 | 검증만 | 3 |

총 약 200 파일 신규. 기존 코드/문서 무수정.

---

## 10. 위험과 완화

| 위험 | 영향 | 완화 |
|---|---|---|
| 200 파일 일시 추가로 commit history 폭증 | git 검색 시 노이즈 | Phase별 commit 분할 (`harness:` 타입 prefix, 8 commit) |
| clovirone 어휘 잔재 (FTL/Vue/MyBatis 등) 유출 | 어휘 일관성 훼손 | verify_harness_consistency.py에 server-exporter 어휘 whitelist 추가, 잔재 grep 검사 |
| ai-context가 server-exporter 정본(rule 22 (fragment-philosophy) 등)과 drift | 두 문서 불일치 | ai-context는 reference만 명시, 실 내용은 정본에서 — 중복 보존 금지 원칙 |
| 자기개선 루프 7 agents가 실 운영에서 사용되지 않음 | 표면적 낭비 | 도입 후 1 cycle 직접 돌려보고 keep/drop 재결정 (ADR로 기록) |
| skill/agent 본문이 server-exporter 도메인을 충분히 반영 못함 | 신규 작업자가 hint 없이 헤맴 | Phase 4~5 작성 시 각 skill/agent에 server-exporter 실제 파일 경로 1개 이상 인용 의무 |
| 기존 server-exporter CLAUDE.md와 새 .claude/ 룰 충돌 | 우선순위 모호 | CLAUDE.md를 Tier 0 정본으로 명시, .claude/rules/는 Tier 1 (구체화 계층) |

---

## 11. 비범위 (NOT in scope)

- **server-exporter 코드 변경 일체** (ansible playbook, python module, schema, vault, tests, tools, Jenkinsfile, ansible.cfg)
- **기존 docs/01~19 운영 문서 수정**
- **기존 CLAUDE.md/rule 22 (fragment-philosophy)/REQUIREMENTS.md/README.md 내용 변경** (CLAUDE.md는 Tier 0 패턴 흡수 목적의 보강만 허용 — append-only)
- **새 벤더/채널 추가 작업** (하네스 인프라만 깐다, 실 도메인 작업은 별도 티켓)
- **Jenkins/Agent 인프라 변경** (docs/operate/02-agent-node.md 영역)
- **clovirone-base 폴더 정리** (참조용으로 그대로 두며, 향후 사용자가 별도 정리)

---

## 12. 완료 기준 (Definition of Done)

- [ ] .claude/settings.json 생성, hooks 9개 등록 완료
- [ ] .claude/rules/ 30개 파일 작성 완료, 모두 server-exporter 어휘
- [ ] .claude/skills/ 약 38개 SKILL.md 작성 완료
- [ ] .claude/agents/ 약 49개 작성 완료
- [ ] .claude/policy/ 10개 YAML 작성 완료
- [ ] .claude/role/ 6개 README 작성 완료
- [ ] .claude/ai-context/ 6개 디렉터리, 각 convention.md 작성 완료
- [ ] .claude/templates/ 작성 완료 (prototype-skeleton 제외)
- [ ] .claude/commands/ 5개 작성 완료
- [ ] scripts/ai/hooks/ Python 16개 작성 완료, 실행 권한 부여 (install-git-hooks.sh)
- [ ] docs/ai/ 초기 골격 25개 작성 완료
- [ ] CLAUDE.md 보강 완료 (Tier 0 정본 패턴 흡수)
- [ ] verify_harness_consistency.py 통과 (server-exporter 어휘 whitelist)
- [ ] harness-cycle dry-run 1회 성공
- [ ] git history Phase별 8 commit 분할
- [ ] clovirone-base 폴더는 무수정 유지 (참조용)

---

## 13. 관련 문서

- 출처 하네스: `clovirone-base/.claude/` 전체
- 출처 패턴: `clovirone-base/CLAUDE.md` (Tier 0 정본), `clovirone-base/docs/ai/*` (AI 협업 문서 패턴)
- 대상 정본: `CLAUDE.md`, `REQUIREMENTS.md`, `README.md`
- 대상 운영 문서: `docs/operate/01-jenkins-master.md` ~ `docs/reference/decision-log.md`
- 대상 코드: `os-gather/`, `esxi-gather/`, `redfish-gather/`, `common/`, `adapters/`, `schema/`

---

## 승인 기록

| 일시 | 승인자 | 내역 |
|---|---|---|
| 2026-04-27 | hshwang1994 | 풀스펙 포팅 + vendor만 customer-plugin slot + 6분류 직접 매핑 + 보존 추가 + 나머지 추천안 일괄 채택 (대화 승인) |
