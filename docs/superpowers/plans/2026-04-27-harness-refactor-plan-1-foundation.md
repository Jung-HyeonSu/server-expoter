# server-exporter 하네스 리팩토링 - Plan 1/3 (Foundation) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** clovirone-base/.claude 풀스펙 하네스의 Foundation 계층(settings + hooks + CLAUDE.md 보강 + rules + policies + role + ai-context + templates + commands)을 server-exporter 도메인 어휘로 1:1 포팅한다. Plan 1 완료 후 Claude Code 세션이 30 rules 활성, 16 hooks 동작, 10 policy YAML 인덱스 보유 상태로 시작 가능.

**Architecture:** 풀스펙 포팅 (Plan 0 설계서 결정사항 1). 출처 파일을 `clovirone-base/.claude/`에서 읽고, 일관 변환 규칙(아래 §1 substitution table)을 적용하여 `.claude/`로 작성. 기존 server-exporter 코드/문서(CLAUDE.md 보강 외) 무수정. 신규 파일만 추가.

**Tech Stack:** Markdown (rules/skills/agents), YAML (policy), JSON (settings.json), Python 3.12 (hooks), Bash (install scripts).

**대상 세션:** 세션 1 (3 세션 분할 중 첫 번째)

**의존:** 설계서 `docs/superpowers/specs/2026-04-27-harness-refactor-design.md`

**후속 plan:** Plan 2 (skills + agents, 세션 2), Plan 3 (docs/ai + 자기개선 루프 검증, 세션 3) — 각 세션 시작 시점에 작성

---

## 1. 일관 변환 규칙 (모든 task 공통)

모든 포팅 task는 출처 파일을 읽어 아래 변환 규칙을 적용한 뒤 대상 위치에 쓴다. 누락된 규칙은 task별 "추가 변환" 절에 명시.

### 1.1 어휘 substitution (대소문자/한국어 모두)

| 출처 (clovirone) | 대상 (server-exporter) |
|---|---|
| `Java`, `Java 19` | `Python`, `Python 3.12` |
| `Spring Boot`, `Spring Boot 3.3.0` | `Ansible`, `Ansible 2.20` |
| `Gradle`, `Gradle 7.6` | `ansible-playbook` |
| `MariaDB` | (제거 — DB 없음, schema/sections.yml로 대체) |
| `MyBatis`, `MyBatis 4-tier` | (제거 — fragment 정규화로 대체) |
| `Flyway` | `schema/sections.yml + field_dictionary.yml versioning` |
| `JPA`, `Hibernate` | (제거) |
| `Freemarker`, `FTL`, `*.ftl` | (제거 — JSON output schema로 대체) |
| `Vue.js`, `Vue 2`, `Vue 3` | (제거) |
| `jQuery` | (제거) |
| `Spock`, `Groovy 테스트` | `pytest` |
| `Playwright`, `Playwright E2E` | `redfish-probe + 실장비 검증` |
| `Xray`, `Jira` | `baseline JSON 회귀` |
| `Bitbucket Pipelines`, `bitbucket-pipelines.yml` | `Jenkins (Jenkinsfile, Jenkinsfile_grafana, Jenkinsfile_portal)` |
| `clovircm-domain` | `common/ + adapters/` |
| `clovircm-web` | `os-gather/ + esxi-gather/ + redfish-gather/` |
| `plugin-posco`, `plugin-smilegate`, `plugin-example`, `plugin-sdk` | `adapters/{redfish,os,esxi}/{vendor}_*.yml + redfish-gather/tasks/vendors/{vendor}/` |
| `KISA`, `INA`, `POSCO`, `SK하이닉스`, `SK하이닉스`, `스마일게이트`, `ClovirOne` (고객사) | `Dell`, `HPE`, `Lenovo`, `Supermicro`, `Cisco` (벤더) |
| `고객사`, `customer` | `벤더`, `vendor` |
| `customer-boundary`, `customer boundary` | `vendor-boundary`, `vendor boundary` |
| `plugin boundary`, `plugin 경계` | `adapter boundary`, `adapter 경계` |
| `branch sk-hynix`, `sk-hynix-dev`, `sk-hynix-claude-hshwang` | `branch main`, `feature/*` |
| `프로필`, `yaml.profile` | (제거 — 벤더 자동 감지로 대체) |
| `BillingCalculator`, `billing` | (제거) |
| `Service Layer (Finder/Maker/Validator/Service/Handler/Hook)` | `Ansible 패턴 (gather_*/normalize_*/build_*/precheck_*)` |
| `Repository`, `Mapper`, `Mapper XML`, `Mapper Interface` | (제거 — sections.yml + field_dictionary.yml로 대체) |
| `Spring Bean`, `생성자 주입`, `@Service`, `@Controller` | `Ansible task / role / module / include_tasks` |
| `Controller`, `RestController`, `@RestController` | (제거 — callback URL 호출) |
| `DTO`, `VO` | (Python dict / Ansible vars) |
| `messages_*.properties`, `i18n` | (제거 — UI 없음) |
| `$springMsg`, `<@spring.message>` | (제거) |
| `ObjectMapper`, `Gson`, `SnakeYaml` | (제거 — Python json / Ansible vars로 대체) |
| `WSL fs` | (제거 — Windows / Agent VM) |
| `qa/.env`, `qa/Playwright` | `tests/redfish-probe/, tests/fixtures/, tests/evidence/` |
| `Renovate` | (그대로 유지 가능) |
| `HashiCorp Vault` | `Ansible Vault` |
| `Bitbucket PR` | `Git PR (origin/main)` |
| `core` (모든 고객사 공유 코드) | `common/ + 3-channel 공유 (gather/normalize/build)` |

### 1.2 외부 시스템 substitution

| 출처 | 대상 |
|---|---|
| `Jenkins / GitLab CI / VMware / OpenStack / Ansible / Harbor / Semaphore / RemoteAccess` | `Redfish API / IPMI / SSH / WinRM / vSphere API` |
| `Jenkins target_type {PRE_OS, ESXI, OS, WINDOWS, LINUX}` | `target_type {os, esxi, redfish}` |
| `VMware vCenter REST API` | `Redfish ServiceRoot + Chassis + Systems + Storage + Volumes` |
| `OpenStack` | (제거) |
| `Harbor` | (제거) |
| `Semaphore (Ansible)` | (제거 — 우리가 Ansible 자체 사용) |
| `RemoteAccess (Guacamole)` | (제거) |

### 1.3 도메인 어휘 신규 (server-exporter 고유)

server-exporter 고유 개념을 출처에 없던 곳에 새로 도입:

| 개념 | 정의 |
|---|---|
| `Fragment 철학` | 각 gather가 자기 fragment(`_data_fragment`, `_sections_<name>_supported_fragment`, `_errors_fragment`)만 만들고 다른 gather의 fragment를 절대 수정하지 않는 원칙. `merge_fragment.yml`이 누적 병합 |
| `Adapter 점수` | `score = priority × 1000 + specificity × 10 + match_score` |
| `3-channel` | os-gather (Linux/Windows) + esxi-gather + redfish-gather (BMC/IPMI) |
| `4단계 Precheck` | ping → port → protocol → auth |
| `Vault 2단계 로딩` | 1단계 무인증 detect → vendor 결정 → 2단계 vendor vault 로드 후 인증 수집 |
| `Linux 2-tier gather` | `python_ok` (Python 3.9+) vs `raw_forced/python_missing/python_incompatible` (raw fallback) |
| `Sections` | system / hardware / bmc / cpu / memory / storage / network / firmware / users / power (10개) |
| `Field Dictionary 28 Must` | field_dictionary.yml의 Must 28필드 + Nice + Skip |
| `Baseline` | tests/baseline_v1/{vendor}_baseline.json — 실장비 회귀 기준선 |
| `loc (ich/chj/yi)` | 운영 사이트, 코드 분기 없음 (Jenkins agent + inventory 분리만) |

### 1.4 경로 substitution

| 출처 경로 | 대상 경로 |
|---|---|
| `clovircm-{domain,web}/src/main/java/**` | `os-gather/, esxi-gather/, redfish-gather/, common/` (역할별) |
| `clovircm-web/src/main/resources/static/**` | `tests/fixtures/, schema/baseline_v1/` |
| `clovircm-domain/src/migration/sql/V*.sql` | `schema/sections.yml + schema/fields/*.yml` |
| `gradle/wrapper/`, `Dockerfile`, `bitbucket-pipelines.yml` | `ansible.cfg, Jenkinsfile, Jenkinsfile_grafana, Jenkinsfile_portal` |
| `qa/.env` | `vault/{linux,windows,esxi}.yml + vault/redfish/{vendor}.yml` |
| `docs/ai/catalogs/PROJECT_MAP.md` (그대로 — 동일 위치) | `docs/ai/catalogs/PROJECT_MAP.md` |
| `scripts/ai/hooks/` (그대로) | `scripts/ai/hooks/` |
| `.claude/rules/`, `.claude/skills/`, `.claude/agents/` (그대로) | 같음 |

### 1.5 보호 경로 (server-exporter)

| 출처 보호 경로 | 대상 보호 경로 |
|---|---|
| `.git/, .gradle/, build/, node_modules/, *.log, qa/.env` | `.git/, vault/**, *.log` |
| `gradle/wrapper/, Dockerfile, bitbucket-pipelines.yml, Jenkinsfile, docker-files/` | `ansible.cfg, Jenkinsfile, Jenkinsfile_grafana, Jenkinsfile_portal, schema/sections.yml, schema/field_dictionary.yml, schema/baseline_v1/**` |
| `plugin-*/, resources/custom/, resources/actions/, resources/billing/` | `adapters/**, redfish-gather/library/**, common/library/**` |

### 1.6 Rule 번호 매핑 (Plan 1 적용 대상)

설계서 §5 표 그대로. 핵심:
- `00-core-repo`, `10-gather-core`, `11-gather-output-boundary`, `12-adapter-vendor-boundary`, `13-output-schema-fields`
- `20-output-json-callback`, `21-output-baseline-fixtures`, `22-fragment-philosophy`
- `23-communication-style`, `24-completion-gate`, `25-parallel-agents`, `26-multi-session-guide`, `27-precheck-guard-first`, `28-empirical-verification-lifecycle`
- `30-integration-redfish-vmware-os`, `31-integration-callback`
- `40-qa-pytest-baseline`, `41-mermaid-visualization`
- `50-vendor-adapter-policy`, `60-security-and-secrets`, `70-docs-and-evidence-policy`, `80-ci-jenkins-policy`
- `90-commit-convention`, `91-task-impact-gate`, `92-dependency-and-regression-gate`, `93-branch-merge-gate`, `95-production-code-critical-review`, `96-external-contract-integrity`, `97-incoming-merge-review`

---

## 2. File Structure (Plan 1 완료 후 TO-BE)

```
server-exporter/
├── CLAUDE.md                          ← 보강 (Tier 0 정본 패턴 흡수)
├── .claude/
│   ├── settings.json                  ← 신규
│   ├── settings.local.json            ← 기존 보존
│   ├── rules/                         ← 30 파일 신규
│   │   ├── 00-core-repo.md
│   │   ├── 10-gather-core.md
│   │   ├── 11-gather-output-boundary.md
│   │   ├── 12-adapter-vendor-boundary.md
│   │   ├── 13-output-schema-fields.md
│   │   ├── 20-output-json-callback.md
│   │   ├── 21-output-baseline-fixtures.md
│   │   ├── 22-fragment-philosophy.md
│   │   ├── 23-communication-style.md
│   │   ├── 24-completion-gate.md
│   │   ├── 25-parallel-agents.md
│   │   ├── 26-multi-session-guide.md
│   │   ├── 27-precheck-guard-first.md
│   │   ├── 28-empirical-verification-lifecycle.md
│   │   ├── 30-integration-redfish-vmware-os.md
│   │   ├── 31-integration-callback.md
│   │   ├── 40-qa-pytest-baseline.md
│   │   ├── 41-mermaid-visualization.md
│   │   ├── 50-vendor-adapter-policy.md
│   │   ├── 60-security-and-secrets.md
│   │   ├── 70-docs-and-evidence-policy.md
│   │   ├── 80-ci-jenkins-policy.md
│   │   ├── 90-commit-convention.md
│   │   ├── 91-task-impact-gate.md
│   │   ├── 92-dependency-and-regression-gate.md
│   │   ├── 93-branch-merge-gate.md
│   │   ├── 95-production-code-critical-review.md
│   │   ├── 96-external-contract-integrity.md
│   │   └── 97-incoming-merge-review.md
│   ├── policy/                        ← 10 YAML 신규
│   │   ├── approval-authority.yaml
│   │   ├── vendor-boundary-map.yaml
│   │   ├── measurement-targets.yaml
│   │   ├── channel-ownership.yaml
│   │   ├── project-map-fingerprint.yaml
│   │   ├── protected-paths.yaml
│   │   ├── review-matrix.yaml
│   │   ├── security-redaction-policy.yaml
│   │   ├── surface-counts.yaml
│   │   └── test-selection-map.yaml
│   ├── role/                          ← 6 README 신규
│   │   ├── gather/README.md
│   │   ├── output-schema/README.md
│   │   ├── infra/README.md
│   │   ├── qa/README.md
│   │   ├── po/README.md
│   │   └── tpm/README.md
│   ├── ai-context/                    ← 6 디렉터리 + convention.md
│   │   ├── common/{repo-facts.md, project-map.md, coding-glossary-ko.md, convention-drift.md, ecc-adoption-summary.md}
│   │   ├── gather/convention.md
│   │   ├── output-schema/convention.md
│   │   ├── infra/convention.md
│   │   ├── vendors/{dell.md, hpe.md, lenovo.md, supermicro.md, cisco.md}
│   │   └── external/integration.md
│   ├── templates/                     ← 신규 (prototype-skeleton 제외)
│   │   ├── CURRENT_STATE.template.md
│   │   ├── DISCOVERY_STATE_TEMPLATE.json
│   │   ├── NEW_AGENT_TEMPLATE.md
│   │   ├── NEW_RULE_TEMPLATE.md
│   │   ├── NEW_SKILL_TEMPLATE.md
│   │   ├── NEXT_ACTIONS.template.md
│   │   ├── REQUIREMENT_ANALYSIS.template.md
│   │   ├── REVIEW_SUMMARY.template.md
│   │   ├── SKILL.template.md
│   │   └── TEST_HISTORY.template.md
│   └── commands/                      ← 5 신규
│       ├── harness-cycle.md
│       ├── harness-full-sweep.md
│       ├── review-guide.md
│       ├── scheduler-guide.md
│       └── usage-guide.md
└── scripts/
    └── ai/
        └── hooks/                     ← 신규 16 파일
            ├── session_start.py
            ├── pre_edit_guard.py
            ├── post_edit_hint.py
            ├── post_edit_jinja_check.py    (← post_edit_ftl_i18n_check.py 대체)
            ├── skill_edit_validate.py
            ├── stop_writeback.py
            ├── subagent_stop_log.py
            ├── notification_log.py
            ├── user_prompt_router.py
            ├── detect_self_approval.py
            ├── post_merge_incoming_review.py
            ├── commit_msg_check.py
            ├── verify_harness_consistency.py
            ├── verify_vendor_boundary.py    (← verify_customer_boundary.py 대체)
            ├── check_project_map_drift.py
            ├── check_gap_against_main.py    (← check_gap_against_dev.py 단순화)
            └── install-git-hooks.sh
```

총 신규 파일: 30 (rules) + 10 (policy) + 6 (role) + 약 12 (ai-context) + 10 (templates) + 5 (commands) + 17 (hooks) + 1 (settings.json) = 약 91 파일. CLAUDE.md 보강 1개.

---

## Phase 1: 골격 (Skeleton)

### Task 1.1: Bootstrap 디렉터리 구조

**Files:**
- Create dir: `.claude/{rules,policy,role,ai-context,templates,commands}/`
- Create dir: `.claude/role/{gather,output-schema,infra,qa,po,tpm}/`
- Create dir: `.claude/ai-context/{common,gather,output-schema,infra,vendors,external}/`
- Create dir: `scripts/ai/hooks/`

- [ ] **Step 1: 디렉터리 생성**

```bash
cd C:/github/server-exporter
mkdir -p .claude/rules .claude/policy .claude/templates .claude/commands
mkdir -p .claude/role/{gather,output-schema,infra,qa,po,tpm}
mkdir -p .claude/ai-context/{common,gather,output-schema,infra,vendors,external}
mkdir -p scripts/ai/hooks
```

- [ ] **Step 2: 검증**

```bash
ls -d .claude/rules .claude/policy .claude/role/gather .claude/ai-context/vendors scripts/ai/hooks
```

Expected: 5 디렉터리 모두 존재

- [ ] **Step 3: Commit (no files yet, skip if empty)** — 디렉터리만 있으면 git이 추적하지 않음. 다음 task에서 첫 파일 추가 시 함께 commit.

---

### Task 1.2: Port settings.json (Tier 0 hook 등록)

**Files:**
- Create: `.claude/settings.json`

**Source reference:** `clovirone-base/.claude/settings.json` (152줄)

**추가 변환 (어휘 substitution 외):**
- `post_edit_ftl_i18n_check.py` → `post_edit_jinja_check.py` (Jinja2 변수 정합성)
- `disableBypassPermissionsMode` 부재 시 추가 (`"disable"`)
- 보호 경로 deny 목록에 server-exporter 보호 경로 추가:
  - `Edit(vault/**)`, `Edit(schema/baseline_v1/**)`
  - `Edit(adapters/**)` — 신중한 변경만
  - `Edit(Jenkinsfile*)` — 티켓 필요
- `enabledPlugins.chrome-devtools-mcp` 제거 (server-exporter 무관)

- [ ] **Step 1: settings.json 작성**

전체 내용:

```json
{
  "$schema": "https://json.schemastore.org/claude-code-settings.json",
  "permissions": {
    "allow": [
      "Bash(*)",
      "Edit(**)",
      "Write(**)",
      "Read(**)",
      "Glob(**)",
      "Grep(**)"
    ],
    "deny": [
      "Bash(rm -rf *)",
      "Bash(rm -fr *)",
      "Bash(sudo *)",
      "Bash(git push --force *)",
      "Bash(git push -f *)",
      "Bash(git push --force-with-lease *)",
      "Bash(git push * main)",
      "Bash(git push * main *)",
      "Bash(git push * master)",
      "Bash(git push * master *)",
      "Bash(git reset --hard *)",
      "Bash(git clean -fd *)",
      "Bash(git clean -fdx *)",
      "Bash(git rebase -i *)",
      "Bash(git filter-branch *)",
      "Bash(git update-ref *)",
      "Bash(curl * | sh)",
      "Bash(curl * | bash)",
      "Bash(wget * | sh)",
      "Bash(wget * | bash)",
      "Bash(docker system prune *)",
      "Bash(docker rm -f *)",
      "Edit(vault/**)",
      "Edit(**/*.env)",
      "Edit(**/credentials*)",
      "Edit(**/*.pem)",
      "Edit(**/*.key)",
      "Edit(**/*.jks)",
      "Edit(**/*.p12)",
      "Edit(schema/baseline_v1/**)",
      "Edit(Jenkinsfile)",
      "Edit(Jenkinsfile_grafana)",
      "Edit(Jenkinsfile_portal)"
    ],
    "ask": [],
    "defaultMode": "acceptEdits",
    "disableBypassPermissionsMode": "disable"
  },
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          { "type": "command", "command": "python scripts/ai/hooks/session_start.py", "timeout": 15 }
        ]
      }
    ],
    "PreToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "python scripts/ai/hooks/pre_edit_guard.py", "timeout": 10 }
        ]
      }
    ],
    "PostToolUse": [
      {
        "matcher": "Edit|Write",
        "hooks": [
          { "type": "command", "command": "python scripts/ai/hooks/post_edit_hint.py", "timeout": 10 },
          { "type": "command", "command": "python scripts/ai/hooks/skill_edit_validate.py", "timeout": 10 },
          { "type": "command", "command": "python scripts/ai/hooks/post_edit_jinja_check.py", "timeout": 10 }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          { "type": "command", "command": "python scripts/ai/hooks/stop_writeback.py", "timeout": 15 }
        ]
      }
    ],
    "Notification": [
      {
        "hooks": [
          { "type": "command", "command": "python scripts/ai/hooks/notification_log.py", "timeout": 10 }
        ]
      }
    ],
    "SubagentStop": [
      {
        "hooks": [
          { "type": "command", "command": "python scripts/ai/hooks/subagent_stop_log.py", "timeout": 10 },
          { "type": "command", "command": "python scripts/ai/hooks/detect_self_approval.py", "timeout": 10 }
        ]
      }
    ],
    "UserPromptSubmit": [
      {
        "hooks": [
          { "type": "command", "command": "python scripts/ai/hooks/user_prompt_router.py", "timeout": 5 }
        ]
      }
    ]
  },
  "sandbox": { "enabled": false },
  "autoMemoryEnabled": false,
  "enabledPlugins": {}
}
```

- [ ] **Step 2: JSON 문법 검증**

```bash
python -c "import json; json.load(open('.claude/settings.json'))"
```

Expected: 출력 없음 (정상). 에러 시 JSON 문법 수정.

- [ ] **Step 3: hook 파일 부재 안내**

이 시점에는 `scripts/ai/hooks/*.py`가 아직 없어 새 세션에서 Claude Code가 실행 시 hook 실패 알림이 뜬다. Task 1.3에서 hook을 모두 작성해야 정상화.

- [ ] **Step 4: Commit**

```bash
cd C:/github/server-exporter
git add .claude/settings.json
git commit -m "harness: .claude/settings.json 추가 (16 hooks 등록 + 보호 경로)"
```

---

### Task 1.3: Port Python hooks (16 + install 스크립트)

**Files:**
- Create: `scripts/ai/hooks/{session_start,pre_edit_guard,post_edit_hint,post_edit_jinja_check,skill_edit_validate,stop_writeback,subagent_stop_log,notification_log,user_prompt_router,detect_self_approval,post_merge_incoming_review,commit_msg_check,verify_harness_consistency,verify_vendor_boundary,check_project_map_drift,check_gap_against_main}.py`
- Create: `scripts/ai/hooks/install-git-hooks.sh`

**Source reference:** `clovirone-base/scripts/ai/hooks/*.py`

**전체 변환 절차 (각 hook 동일 적용):**
1. 출처 파일을 Read
2. 어휘 substitution table 적용
3. clovirone-specific 로직 제거 (예: clovircm-domain 모듈 의존, sk-hynix 브랜치 특이 처리)
4. server-exporter 도메인 추가 (예: 보호 경로 vault/, schema/baseline_v1/)
5. 출력 메시지의 한국어 어휘를 server-exporter용으로 갱신

**Hook별 핵심 변환:**

| Hook | 핵심 변환 |
|---|---|
| `session_start.py` | 브랜치 매핑 (sk-hynix, posco, smilegate → 단일 main + feature/*). PROJECT_MAP fingerprint drift 체크는 그대로. 갭 체크 (`check_gap_against_main.py` 호출). measurement targets(rule 28) 캐시 상태 출력. |
| `pre_edit_guard.py` | 보호 경로: `qa/.env, gradle/wrapper/, plugin-*/` → `vault/**, schema/baseline_v1/**, Jenkinsfile*, adapters/{redfish,os,esxi}/{vendor}_*.yml`. 메시지 한글 갱신. |
| `post_edit_hint.py` | 라우팅 룰: FTL/Vue 편집 → 출력 schema 편집 매핑. MyBatis Mapper 편집 → adapter YAML 편집 매핑. |
| `post_edit_jinja_check.py` (← post_edit_ftl_i18n_check.py) | FTL i18n 키 검사 → Jinja2 템플릿(`{{ }}`, `{% %}`) 변수 정합성. 대상 파일: `*.j2`, `*.yml` 안의 inline Jinja2. |
| `skill_edit_validate.py` | 그대로. SKILL.md description 1024자 제한 등 일반 규칙. |
| `stop_writeback.py` | 그대로. `docs/ai/CURRENT_STATE.md` 갱신 권고. |
| `subagent_stop_log.py` | 그대로. |
| `notification_log.py` | 그대로. |
| `user_prompt_router.py` | 키워드 매핑 갱신: "스케줄러 변경" → scheduler-change-playbook (Jenkins cron 대상). "고객사" → "벤더". "Mapper" → "adapter". |
| `detect_self_approval.py` | 그대로. |
| `post_merge_incoming_review.py` | 자동 검사 5종 변경: <br>(a) `@Scheduled` → Jenkinsfile cron 변경 검사 <br>(b) Java 의심 패턴 → Ansible/Python/YAML 의심 패턴 (raw 모듈 권한, vault 누설, fragment 침범) <br>(c) Java enum origin 주석 → adapter YAML metadata 주석 (vendor, firmware, tested_against) <br>(d) Flyway 중복 → schema/sections.yml + field_dictionary.yml 버전 충돌 <br>(e) (그대로) |
| `commit_msg_check.py` | type 목록 그대로 (feat/fix/refactor/docs/test/chore/harness/hotfix). 50자 제한 그대로. 금지어 그대로. |
| `verify_harness_consistency.py` | EXPECTED_REFERENCES 갱신 — server-exporter rules/skills/agents 매핑. clovirone whitelist 어휘 (java, mybatis, ftl 등) 잔재 검출 추가. |
| `verify_vendor_boundary.py` (← verify_customer_boundary.py) | adapter 경계 검증: gather 코드가 특정 vendor 이름 하드코딩 금지. plugin 모듈 → adapters/* 경로로 변경. |
| `check_project_map_drift.py` | 그대로 (PROJECT_MAP 비교 로직 동일). 다만 server-exporter 모듈 fingerprint 기준 갱신. |
| `check_gap_against_main.py` (← check_gap_against_dev.py) | base 브랜치 sk-hynix-dev → main 단순화. 단일 origin/main 비교만. |

- [ ] **Step 1: clovirone 출처 hook 16개 일괄 읽기**

```bash
ls C:/github/server-exporter/clovirone-base/scripts/ai/hooks/*.py
ls C:/github/server-exporter/clovirone-base/scripts/ai/hooks/*.sh
```

Expected: clovirone hook 파일 목록 출력.

- [ ] **Step 2: 각 hook 포팅 — 1개씩**

각 hook마다:
1. clovirone 출처 Read
2. §1 변환 규칙 + 위 표의 핵심 변환 적용
3. `.py`로 작성 (한국어 메시지/주석 유지)
4. 단위 smoke test:
   ```bash
   echo '{}' | python scripts/ai/hooks/<hook_name>.py 2>&1 | head -5
   ```
   Expected: stdout/stderr가 정상 (Hook이 stdin JSON을 받지 못해 일부는 에러 가능 — 적어도 import 에러 없어야 함).

   특히 import 에러 (ModuleNotFoundError, SyntaxError) 발생 시 즉시 수정.

- [ ] **Step 3: install-git-hooks.sh 포팅**

clovirone `scripts/ai/hooks/install-git-hooks.sh` 출처를 그대로 복제. shebang `#!/usr/bin/env bash` 유지. 변환 적용 후 실행 권한 부여:

```bash
chmod +x scripts/ai/hooks/install-git-hooks.sh
```

- [ ] **Step 4: 일괄 import 검증**

```bash
for f in scripts/ai/hooks/*.py; do
  python -c "import ast; ast.parse(open('$f').read())" && echo "OK $f" || echo "FAIL $f"
done
```

Expected: 모두 `OK ...`. FAIL 시 해당 파일 syntax 수정.

- [ ] **Step 5: Commit**

```bash
git add scripts/ai/hooks/
git commit -m "harness: scripts/ai/hooks/ Python 16개 + install 스크립트 포팅 (clovirone → server-exporter 어휘)"
```

---

### Task 1.4: Boost CLAUDE.md (Tier 0 정본 패턴 흡수)

**Files:**
- Modify: `CLAUDE.md` (기존 384줄, append + 일부 섹션 갱신)

**Source reference:** 
- `clovirone-base/CLAUDE.md` Tier 0 패턴 (절대 금지사항, 세션 시작 프로세스, 자기개선 루프, 컨텍스트 자동 로드, Service Layer/Repository 안내)
- 기존 `CLAUDE.md` 그대로 보존하되 누락된 Tier 0 패턴을 흡수

**추가할 섹션:**
1. **세션 시작 프로세스** — 자동 추론 먼저, 질문은 최소한 (rule 23 R3 결정 주체 명시 R7 대비 갭 리포트 해석 주의 포함)
2. **세션 시작 컨텍스트 선택** — AskUserQuestion으로 작업 유형 선택(gather / output-schema / infra / qa / po / tpm)
3. **Step 4 task-impact-preview** — 코드 변경 요청 진입 게이트
4. **Step 5 티켓 생성 후 다음 작업 흐름** — 같은 세션 자동 진행 + Agent tool 병렬 + 세션 분리 예외
5. **Step 6 AI 커뮤니케이션 원칙** — 일상어 + WHY/WHAT/IMPACT/결정 주체 (rule 23 참조)
6. **Step 7 자율 판단 원칙** — R1 자율 진행 / R2 명시 승인 필요 / R3 완료 게이트
7. **절대 금지사항 8개** (server-exporter 어휘로 변환):
   - 비밀값 하드코딩 금지 (vault/redfish/{vendor}.yml + vault/{linux,windows,esxi}.yml)
   - 보호 경로 자율 수정 금지 (vault/, schema/baseline_v1/, Jenkinsfile*, adapters/)
   - 벤더 경계 위반 금지 (gather 코드에 vendor 이름 하드코딩 금지)
   - DELETE/PUT/PATCH HTTP 메서드 금지 → (제거; 우리는 callback URL POST만)
   - Gson 사용 금지 → (제거; Python json / Ansible vars)
   - 문서 갱신 누락 금지
   - bypassPermissions 금지
   - 전역 설정 자율 수정 금지
8. **하네스 자기개선 루프** — 두 개 루프 (제품 / 하네스), 6단계 파이프라인, Tier 1/2/3 분류 (clovirone 그대로)
9. **하네스 구조 안내** — `.claude/{rules,skills,agents,role,ai-context,policy,templates,commands}/` + `docs/ai/` + `scripts/ai/`
10. **핵심 컨벤션 요약** — server-exporter용으로 갱신:
    - Fragment 철학 (각 gather 자기 fragment만)
    - Adapter 점수 계산 (priority × 1000 + specificity × 10 + match_score)
    - Vault 2단계 로딩 (Redfish 무인증 detect → vendor vault 로드 → 인증 수집)
    - Linux 2-tier gather (Python ok / raw fallback)
    - JSON output envelope (status/sections/data/errors/meta/diagnosis)
    - 4단계 Precheck (ping → port → protocol → auth)
11. **컨텍스트 자동 로드 매핑**:
    - `os-gather/, esxi-gather/, redfish-gather/` 편집 → `ai-context/gather/convention.md`
    - `schema/, common/tasks/normalize/` 편집 → `ai-context/output-schema/convention.md`
    - `Jenkinsfile*, ansible.cfg, scripts/` 편집 → `ai-context/infra/convention.md`
    - `tests/` 편집 → role/qa/README.md
    - `adapters/{vendor}_*.yml, redfish-gather/tasks/vendors/{vendor}/` 편집 → `ai-context/vendors/{vendor}.md`
    - 외부 시스템 (Redfish/IPMI/SSH/WinRM/vSphere) 작업 → `ai-context/external/integration.md`

**보존 섹션 (수정 안 함):**
- 개요 / 아키텍처 / 기술 스택 / 파일 구조 / ECC 활용 / 주의사항 & Best Practices / Git 워크플로우 / 3-채널 지원 현황 / 트러블슈팅 / 주요 문서 / 알려진 제한사항

- [ ] **Step 1: 기존 CLAUDE.md 백업 (안전)**

```bash
cp CLAUDE.md CLAUDE.md.bak
```

- [ ] **Step 2: 기존 CLAUDE.md 구조 분석**

기존 섹션 (Read로 파악): 개요 / 아키텍처 / 기술 스택 / 파일 구조 / ECC 활용 / 주의사항 / Git 워크플로우 / 3-채널 지원 현황 / 트러블슈팅 / 주요 문서 / 알려진 제한사항.

이 11 섹션은 그대로 보존. 위 11개 신규 섹션은 `## 개요` 직전 또는 `## 주의사항 & Best Practices` 직후에 삽입.

- [ ] **Step 3: 신규 섹션 작성 (clovirone CLAUDE.md 패턴 흡수, server-exporter 어휘로 변환)**

11개 섹션을 추가. 각 섹션은 clovirone CLAUDE.md의 동일 섹션을 §1 어휘 substitution 적용해 작성.

핵심 변환 예시:
- "ClovirONE 2.0 / SK하이닉스 (브랜치: sk-hynix-claude-hshwang)" → "server-exporter (브랜치: main)"
- "역할 추론" 매핑 갱신 (Java/Service → Ansible/Python module)
- "고객사 분리 원칙" 절 제거, 대신 "벤더 어댑터 분리 원칙" 신설
- "core 수정이 plugin에 영향" → "common 수정이 adapter/gather에 영향"

- [ ] **Step 4: CLAUDE.md 끝부분 추가 — 컨텍스트 자동 로드 매핑**

기존 CLAUDE.md 마지막에 컨텍스트 자동 로드 6 매핑 추가.

- [ ] **Step 5: 검증 — 어휘 잔재 grep**

```bash
grep -nE "MyBatis|Spring Boot|FTL|Vue|jQuery|Gradle|MariaDB|Flyway|sk-hynix|posco|smilegate" CLAUDE.md
```

Expected: 출력 없음 (또는 명시적 비교/대조 목적의 인용만 — 그 경우 인용임을 표시).

- [ ] **Step 6: 백업 정리 + Commit**

```bash
rm CLAUDE.md.bak
git add CLAUDE.md
git commit -m "harness: CLAUDE.md 보강 — Tier 0 정본 패턴 11 섹션 흡수"
```

---

## Phase 2: 정책 / 메타 (Policy / Meta)

### Task 2.1: Port policy YAMLs (10개)

**Files (10):**
- Create: `.claude/policy/{approval-authority,vendor-boundary-map,measurement-targets,channel-ownership,project-map-fingerprint,protected-paths,review-matrix,security-redaction-policy,surface-counts,test-selection-map}.yaml`

**Source reference:** `clovirone-base/.claude/policy/*.yaml`

**파일별 핵심 변환:**

| 출처 → 대상 | 핵심 변환 |
|---|---|
| `approval-authority.yaml` → 같음 | 승인권자 hshwang 그대로. 보호 경로 deny 영역을 server-exporter 보호 경로로 갱신 |
| `customer-boundary-map.yaml` → `vendor-boundary-map.yaml` | customers (POSCO/sk-hynix/...) → vendors (Dell/HPE/Lenovo/Supermicro/Cisco). plugin 경로 → adapters 경로 |
| `measurement-targets.yaml` → 같음 | rule 28 카탈로그 12 항목을 server-exporter용으로: <br>1. DB 스키마 → 출력 스키마 (sections.yml + field_dictionary.yml) <br>2. PROJECT_MAP → 그대로 <br>3. 프론트엔드 컴포넌트 → 제거 <br>4. API endpoint → callback URL endpoint <br>5. i18n 키 → 제거 <br>6. Scheduler → Jenkinsfile cron <br>7. 하네스 표면 수 → 그대로 <br>8. 고객사 기능 토글 → 벤더 adapter 매트릭스 <br>9. 모듈 의존성 → ansible collection / pip 의존성 <br>10. 브랜치 갭 → 단일 main, 비활성 <br>11. Plugin boundary → adapter boundary <br>12. Flyway 이력 → schema/sections.yml 버전 |
| `module-ownership.yaml` → `channel-ownership.yaml` | 모듈 (clovircm-domain/web/plugin) → 채널 (os-gather/esxi-gather/redfish-gather/common) |
| `project-map-fingerprint.yaml` → 같음 | server-exporter 디렉터리 fingerprint 재계산 (ls + sha) |
| `protected-paths.yaml` → 같음 | 보호 경로 list: <br>- 절대 보호: `.git/, vault/**, *.log` <br>- 티켓 필요: `ansible.cfg, Jenkinsfile, Jenkinsfile_grafana, Jenkinsfile_portal, schema/sections.yml, schema/field_dictionary.yml, schema/baseline_v1/**` <br>- 벤더 경계: `adapters/**, redfish-gather/library/**, common/library/**, vault/redfish/**` |
| `review-matrix.yaml` → 같음 | 4축 리뷰 (구조/품질/보안/벤더경계) |
| `security-redaction-policy.yaml` → 같음 | 비밀값 패턴 갱신: BMC password, vault password, IDRAC/iLO/XCC user, redfish basic auth |
| `surface-counts.yaml` → 같음 | rules / skills / agents / policies 카운트 갱신 |
| `test-selection-map.yaml` → 같음 | 변경 영역별 테스트 매핑 갱신 (gather → tests/redfish-probe + 실장비 baseline; schema → field_dictionary 정합 검증) |

- [ ] **Step 1: 출처 YAML 일괄 Read**

```bash
ls C:/github/server-exporter/clovirone-base/.claude/policy/
```

- [ ] **Step 2: 10개 YAML 1개씩 포팅**

각 파일마다:
1. 출처 Read
2. §1 어휘 + 위 표 변환 적용
3. 대상 위치 작성
4. YAML 문법 검증:
   ```bash
   python -c "import yaml; yaml.safe_load(open('.claude/policy/<name>.yaml'))"
   ```
   Expected: 출력 없음.

- [ ] **Step 3: Commit**

```bash
git add .claude/policy/
git commit -m "harness: .claude/policy/ 10개 YAML 포팅 (vendor-boundary-map, channel-ownership 등 어휘 치환)"
```

---

### Task 2.2: Role README 6개

**Files:**
- Create: `.claude/role/{gather,output-schema,infra,qa,po,tpm}/README.md`

**Source reference:** `clovirone-base/.claude/role/{backend,frontend,infra,qa,po,tpm}/README.md`

**역할별 변환:**

| 출처 role | 대상 role | 담당 영역 |
|---|---|---|
| backend | **gather** | os-gather/, esxi-gather/, redfish-gather/, common/library/, filter_plugins/, lookup_plugins/, module_utils/ |
| frontend | **output-schema** | schema/sections.yml, schema/field_dictionary.yml, schema/baseline_v1/, common/tasks/normalize/, callback_plugins/ |
| infra | **infra** | Jenkinsfile, Jenkinsfile_grafana, Jenkinsfile_portal, ansible.cfg, scripts/ai/, vault/, docs/03_agent-setup |
| qa | **qa** | tests/redfish-probe/, tests/fixtures/, tests/evidence/, tests/scripts/, deep_probe_redfish.py, baseline_v1/ |
| po | **po** | REQUIREMENTS.md, 새 벤더 추가 결정, 새 섹션 추가 결정, customer 요구사항 |
| tpm | **tpm** | docs/19_decision-log, Round 검증 진행률, 릴리즈, docs/ai/CURRENT_STATE 갱신 |

각 README는 ~150줄. 핵심 섹션:
- 담당 영역 (파일 경로)
- 자동 로드 ai-context (`../../ai-context/<role>/convention.md` 또는 다중)
- 자주 호출하는 skill 목록
- 자주 호출하는 agent 목록
- 핵심 규칙 참조 (rule 번호 + 풀이)
- 작업 시작 체크리스트

- [ ] **Step 1: 6개 README 1개씩 포팅**

각 파일에 §1 변환 + 위 매핑 적용. 핵심 skill/agent 참조는 Plan 2/3에 포팅 예정인 이름으로 미리 명시 (예: gather README의 "자주 호출 agent: gather-refactor-worker, fragment-engineer, adapter-author"). Plan 2 작성 시 일치 검증.

- [ ] **Step 2: Commit**

```bash
git add .claude/role/
git commit -m "harness: .claude/role/ 6개 README 포팅 (gather/output-schema/infra/qa/po/tpm)"
```

---

### Task 2.3: ai-context 6개 디렉터리 + 콘텐츠

**Files (약 12):**
- Create: `.claude/ai-context/common/{repo-facts.md, project-map.md, coding-glossary-ko.md, convention-drift.md, ecc-adoption-summary.md}`
- Create: `.claude/ai-context/gather/convention.md`
- Create: `.claude/ai-context/output-schema/convention.md`
- Create: `.claude/ai-context/infra/convention.md`
- Create: `.claude/ai-context/vendors/{dell.md, hpe.md, lenovo.md, supermicro.md, cisco.md}`
- Create: `.claude/ai-context/external/integration.md`

**Source reference:** `clovirone-base/.claude/ai-context/{backend,common,external}/`

**콘텐츠 원칙:** ai-context는 **인덱스/요약**이며, 본문은 server-exporter 정본(REQUIREMENTS.md, README.md, docs/01~19)을 reference로 가리킨다 (rule 70 중복 보존 금지).

| 파일 | 내용 |
|---|---|
| `common/repo-facts.md` | 검증 기준 Agent (10.100.64.154) ansible-core 2.20.3 / Python 3.12.3 / Java 21 / Jinja2 3.1.6 / Collections + pip 패키지 list. REQUIREMENTS.md §4 reference |
| `common/project-map.md` | 디렉터리 트리 요약. CLAUDE.md "파일 구조" 섹션 reference |
| `common/coding-glossary-ko.md` | server-exporter 용어 사전 (Fragment / Adapter / Precheck / Vault 2단계 / 3-channel / 4단계 진단 / Sections 10 / Field Dictionary 28 Must / Baseline / loc / target_type) |
| `common/convention-drift.md` | 발견된 컨벤션 위반/drift list (초기 비어있음) |
| `common/ecc-adoption-summary.md` | (선택) ECC 채택 현황 — server-exporter는 단순 진입 단계로 비어있거나 짧은 placeholder |
| `gather/convention.md` | 1) Fragment 철학 (rule 22 (fragment-philosophy) reference) <br>2) gather_*.yml 명명 규칙 <br>3) raw 수집 vs fragment 생성 분리 <br>4) merge_fragment.yml 호출 순서 <br>5) Linux 2-tier (preflight.yml _l_python_mode) <br>6) precheck_bundle.py 4단계 |
| `output-schema/convention.md` | 1) sections.yml 10 섹션 list <br>2) field_dictionary.yml 28 Must + Nice + Skip <br>3) baseline_v1/ 갱신 절차 <br>4) build_*.yml 빌더 5종 (sections, status, errors, meta, correlation, output) <br>5) callback_plugins/json_only.py JSON envelope 형식 |
| `infra/convention.md` | 1) Jenkinsfile 3종 (main / grafana / portal) 차이 <br>2) Agent 노드 구성 (docs/03 reference) <br>3) Vault 구조 (`vault/{linux,windows,esxi}.yml + vault/redfish/{vendor}.yml`) <br>4) Redis fact cache <br>5) ansible.cfg 핵심 설정 |
| `vendors/dell.md` | iDRAC8/9 OEM 특이사항. 펌웨어 버전별 Redfish path 차이. adapter 우선순위 |
| `vendors/hpe.md` | iLO5/6 OEM 특이사항 |
| `vendors/lenovo.md` | XCC OEM 특이사항 |
| `vendors/supermicro.md` | BMC OEM 특이사항 |
| `vendors/cisco.md` | CIMC OEM 특이사항 |
| `external/integration.md` | Redfish ServiceRoot / IPMI / SSH (paramiko) / WinRM (pywinrm) / vSphere (pyvmomi) 외부 시스템 노트 |

각 파일 50~150줄.

- [ ] **Step 1: ai-context 12개 파일 작성**

각 파일을 §1 변환 + 위 표 핵심 + reference 링크로 작성.

- [ ] **Step 2: Reference 링크 검증**

```bash
grep -nE "GUIDE_FOR_AI\.md|REQUIREMENTS\.md|docs/0[0-9]_|docs/1[0-9]_" .claude/ai-context/**/*.md
```

Expected: 모든 reference가 server-exporter 실제 파일을 가리킴 (출처 파일 존재 확인 가능).

- [ ] **Step 3: Commit**

```bash
git add .claude/ai-context/
git commit -m "harness: .claude/ai-context/ 12 파일 (common/gather/output-schema/infra/vendors/external)"
```

---

### Task 2.4: Templates 10개

**Files:**
- Create: `.claude/templates/{CURRENT_STATE.template.md, DISCOVERY_STATE_TEMPLATE.json, NEW_AGENT_TEMPLATE.md, NEW_RULE_TEMPLATE.md, NEW_SKILL_TEMPLATE.md, NEXT_ACTIONS.template.md, REQUIREMENT_ANALYSIS.template.md, REVIEW_SUMMARY.template.md, SKILL.template.md, TEST_HISTORY.template.md}`

**제거 대상:** `prototype-skeleton/` (UI 프로토타입 없음 — 설계서 §3 비범위)

**Source reference:** `clovirone-base/.claude/templates/*.md`

**변환:** 어휘 substitution + 예시 치환 (clovircm/POSCO 예시 → server-exporter/Dell/Lenovo 예시)

- [ ] **Step 1: 10개 template 파일 포팅**

각 파일을 §1 변환 + 도메인 예시 갱신으로 작성.

- [ ] **Step 2: Commit**

```bash
git add .claude/templates/
git commit -m "harness: .claude/templates/ 10개 (prototype-skeleton 제외)"
```

---

### Task 2.5: Commands 5개

**Files:**
- Create: `.claude/commands/{harness-cycle,harness-full-sweep,review-guide,scheduler-guide,usage-guide}.md`

**Source reference:** `clovirone-base/.claude/commands/*.md`

**변환:** 어휘 substitution + 예시 명령 치환 (`./gradlew test` → `pytest tests/redfish-probe/` 등)

- [ ] **Step 1: 5개 command 포팅**

- [ ] **Step 2: Commit**

```bash
git add .claude/commands/
git commit -m "harness: .claude/commands/ 5개 가이드 포팅"
```

---

## Phase 3: 룰 (Rules)

### Task 3.1: Port rule 00-core-repo

**Files:**
- Create: `.claude/rules/00-core-repo.md`

**Source reference:** `clovirone-base/.claude/rules/00-core-repo.md`

**핵심 변환 (어휘 substitution 외):**
- "현재 관찰된 현실" 모듈/줄수/테스트 카운트 → server-exporter 실측: 3-channel + adapters 25개 + 12 plugin/Python + 145 fixture + 7 baseline
- 빌드 명령 `./gradlew clean build -x test` → `ansible-playbook --syntax-check; pytest tests/ -v`
- 모듈 계층 다이어그램: domain/web/plugin → os-gather/esxi-gather/redfish-gather + adapters + common
- 증거 문서 갱신 매핑 그대로 (DB → schema/sections.yml)
- Rule 번호 가이드 표 갱신: 10번대(gather), 20번대(output+communication+gates), 30번대(integration), 50번대(vendor-adapter), 90번대(commit/gates) 등 Plan 1 매핑과 일치
- 보호 경로: `.git/, .gradle/, build/, node_modules/, qa/.env` → `.git/, vault/**, *.log`. 티켓 필요: `ansible.cfg, Jenkinsfile*, schema/sections.yml, schema/baseline_v1/`. 벤더 경계: `adapters/**, redfish-gather/library/**, common/library/**`

- [ ] **Step 1: rule 00 작성**

clovirone 출처 Read → §1 변환 + 위 핵심 변환 → `.claude/rules/00-core-repo.md` Write.

- [ ] **Step 2: 어휘 잔재 검사**

```bash
grep -nE "Java|Spring|MyBatis|FTL|Vue|jQuery|Gradle|MariaDB|Flyway|clovircm|sk-hynix|posco|smilegate" .claude/rules/00-core-repo.md
```

Expected: 출력 없음.

- [ ] **Step 3: Commit (다음 rule들과 함께 묶음 commit)**

다음 task에서 묶어서 commit.

---

### Task 3.2: Port rules 10-13 (gather + boundary + schema)

**Files:**
- Create: `.claude/rules/10-gather-core.md`
- Create: `.claude/rules/11-gather-output-boundary.md`
- Create: `.claude/rules/12-adapter-vendor-boundary.md`
- Create: `.claude/rules/13-output-schema-fields.md`

**Source reference:** `clovirone-base/.claude/rules/{10-backend-core, 11-backend-domain-web-boundary, 12-backend-plugin-boundary, 13-backend-database-mybatis-jpa}.md`

**rule별 핵심 변환:**

| 대상 rule | 핵심 변환 |
|---|---|
| `10-gather-core` | Java/Spring → Ansible/Python. raw 수집 + fragment 생성 원칙. `Service Layer (Finder/Maker/Validator/Service/Handler/Hook)` → `Ansible 패턴 (gather_*/normalize_*/build_*/precheck_*)`. HTTP method 절 제거 (callback URL POST만). Gson/ObjectMapper 절 제거. 파일 500줄/함수 15줄 한계 그대로. Exception 메시지 i18n 절 제거 |
| `11-gather-output-boundary` | "domain ↔ web 경계" → "gather ↔ normalize 경계". gather가 build_*.yml에 직접 손대지 말 것. merge_fragment.yml 경유. Spring Bean 의존성 절 → Ansible include_tasks 의존성 |
| `12-adapter-vendor-boundary` | plugin-{posco,smilegate,example} → adapters/{redfish,os,esxi}/{vendor}_*.yml. plugin-sdk → adapter_loader (lookup plugin). 인터페이스 변경 시 호환성 → adapter YAML schema 변경 시 adapter_loader 영향 검증 |
| `13-output-schema-fields` | MyBatis 4-tier → sections.yml + field_dictionary.yml 2-tier. Mapper XML → field_dictionary.yml. JOIN 최소화 → 섹션 간 cross-reference 최소화. Flyway 버전 → schema/sections.yml + field_dictionary.yml 버전 (rule 92 R5 연동). DB 스키마 주기 갱신 → output schema 주기 갱신 (rule 28 #1) |

- [ ] **Step 1: 4개 rule 1개씩 포팅**

- [ ] **Step 2: 어휘 잔재 검사 (4개 모두)**

```bash
grep -nE "Java|Spring|MyBatis|FTL|Vue|Gradle|MariaDB|Flyway|sk-hynix|posco" .claude/rules/{10,11,12,13}-*.md
```

Expected: 출력 없음.

- [ ] **Step 3: Commit (rules 00-13 묶음)**

```bash
git add .claude/rules/{00,10,11,12,13}-*.md
git commit -m "harness: rules 00-13 포팅 (core-repo + gather + boundary + schema)"
```

---

### Task 3.3: Port rules 20-22 (output + fragment)

**Files:**
- Create: `.claude/rules/20-output-json-callback.md`
- Create: `.claude/rules/21-output-baseline-fixtures.md`
- Create: `.claude/rules/22-fragment-philosophy.md` ⭐ (가장 중요한 server-exporter 고유 rule)

**Source reference:** `clovirone-base/.claude/rules/{20-frontend-ftl-jquery-vue, 21-frontend-static-assets, 22-frontend-shared-components-reuse}.md`

**rule별 핵심 변환:**

| 대상 rule | 핵심 변환 |
|---|---|
| `20-output-json-callback` | Vue/FTL/jQuery → JSON output schema. `$springMsg` 제거. 출력 envelope 규칙: status/sections/data/errors/meta/diagnosis. callback_plugins/json_only.py 보호 (스토우드웃 OUTPUT 태스크만 JSON). Jinja2 `{{ }}` 변수 정합성 (post_edit_jinja_check 연동) |
| `21-output-baseline-fixtures` | static assets → tests/fixtures/, schema/baseline_v1/. CSS/JS 충돌 → fixture 중복 vs baseline 회귀. 보호 경로: schema/baseline_v1/** |
| `22-fragment-philosophy` ⭐ | **rule 22를 server-exporter 핵심 게이트로 재구성.** 공통 컴포넌트 재사용 → Fragment 철학. <br>R1: 각 gather는 자기 fragment(`_data_fragment`, `_sections_<name>_supported_fragment`, `_errors_fragment`)만 만든다 <br>R2: 다른 gather의 fragment를 set_fact로 수정 금지 (구현 시작 전 승인 게이트) <br>R3: merge_fragment.yml 호출 순서 보장 <br>R4: 새 섹션 추가는 sections.yml + field_dictionary.yml + baseline 3종 동반 갱신 <br>R5: vendor-specific 로직은 adapter YAML, gather 코드 하드코딩 금지 <br>R6: 새 gather 추가 전 기존 gather 패턴 조사 의무 (rule 22 (fragment-philosophy) reference) <br>R7~R11: 사용 사례별 추가 (clovirone R6~R11 패턴 보존하되 server-exporter 어휘) |

- [ ] **Step 1: 3개 rule 1개씩 포팅. rule 22는 가장 신중히 작성 (서버-exporter 핵심)**

- [ ] **Step 2: rule 22의 R1~R5 의무 사항이 rule 22 (fragment-philosophy) / 기존 코드 패턴과 일치 확인**

```bash
grep -nE "fragment|merge_fragment|sections\.yml|field_dictionary" .claude/rules/22-fragment-philosophy.md
```

Expected: 핵심 키워드 다수 등장.

- [ ] **Step 3: Commit**

```bash
git add .claude/rules/{20,21,22}-*.md
git commit -m "harness: rules 20-22 포팅 (output-json + baseline + fragment-philosophy ⭐)"
```

---

### Task 3.4: Port rules 23-28 (communication, completion, parallel, multi-session, precheck-guard, empirical)

**Files:**
- Create: `.claude/rules/23-communication-style.md`
- Create: `.claude/rules/24-completion-gate.md`
- Create: `.claude/rules/25-parallel-agents.md`
- Create: `.claude/rules/26-multi-session-guide.md`
- Create: `.claude/rules/27-precheck-guard-first.md`
- Create: `.claude/rules/28-empirical-verification-lifecycle.md`

**Source reference:** `clovirone-base/.claude/rules/{23-communication-style, 24-completion-gate, 25-parallel-agents, 26-multi-session-guide, 27-frontend-guard-first, 28-empirical-verification-lifecycle}.md`

**rule별 핵심 변환:**

| 대상 rule | 핵심 변환 |
|---|---|
| `23-communication-style` | 거의 그대로. R2 어휘 치환표를 server-exporter용으로: <br>- `Spock`, `MyBatis`, `Flyway` 등 제거 <br>- `Fragment`, `Adapter 점수`, `Vault 2단계`, `Linux 2-tier`, `Sections 10`, `Field Dictionary 28 Must`, `Baseline`, `Precheck 4단계`, `loc`, `target_type` 추가 <br>- 그 외 영문 약어 풀이는 그대로 |
| `24-completion-gate` | 5체크 갱신: <br>1. 정적 검증: ansible-lint + yamllint + pytest <br>2. 발견 가능한 버그 0건 <br>3. 문서 4종 갱신 (CURRENT_STATE / TEST_HISTORY / EPIC.md / CONTINUATION.md) <br>4. 후속 작업 식별 <br>5. Git 태그 + push <br>6. (UI 변경 → 제거) <br>UI 변경 → 출력 schema/JSON envelope 변경 시 verify-json-output skill 통과 의무 |
| `25-parallel-agents` | 그대로 |
| `26-multi-session-guide` | 단일 main 브랜치라 주로 worktree 사용. CONTINUATION.md 위치 그대로 |
| `27-precheck-guard-first` (← 27-frontend-guard-first) | "Frontend Guard First" → "Precheck Guard First". precheck_bundle.py 4단계 (ping → port → protocol → auth) 통과 후 본 수집. 각 단계 실패 시 graceful degradation. validation layer 분류 (어떤 검증을 어디서 차단할지: precheck / gather 중간 / fragment merge 후) |
| `28-empirical-verification-lifecycle` | 그대로. R1 카탈로그 12 항목을 server-exporter용으로 재편 (Task 2.1 measurement-targets.yaml 변환과 동일) |

- [ ] **Step 1: 6개 rule 1개씩 포팅**

- [ ] **Step 2: 어휘 잔재 검사**

```bash
grep -nE "Java|Spring|MyBatis|FTL|Vue|Gradle|MariaDB|Flyway|sk-hynix|posco" .claude/rules/{23,24,25,26,27,28}-*.md
```

Expected: 출력 없음.

- [ ] **Step 3: Commit**

```bash
git add .claude/rules/{23,24,25,26,27,28}-*.md
git commit -m "harness: rules 23-28 포팅 (communication/completion/parallel/multi-session/precheck-guard/empirical)"
```

---

### Task 3.5: Port rules 30-31 (integration)

**Files:**
- Create: `.claude/rules/30-integration-redfish-vmware-os.md`
- Create: `.claude/rules/31-integration-callback.md`

**Source reference:** `clovirone-base/.claude/rules/{30-integration-vmware-server-semaphore, 31-integration-remote-access}.md`

**핵심 변환:**

| 대상 rule | 핵심 변환 |
|---|---|
| `30-integration-redfish-vmware-os` | 외부 시스템 list 변경: VMware/Server/Semaphore → Redfish API + IPMI + SSH (paramiko) + WinRM (pywinrm) + vSphere (pyvmomi). 외부 시스템 응답 schema 변경 시 영향 분석 의무 |
| `31-integration-callback` | RemoteAccess (Guacamole) → callback URL (Jenkinsfile post 단계 호출자에 결과 통지). callback URL 무결성 (이전 commit `4ccc1d7`에 fix 있음 — 공백/후행 슬래시 방어) |

- [ ] **Step 1: 2개 rule 포팅**

- [ ] **Step 2: Commit**

```bash
git add .claude/rules/{30,31}-*.md
git commit -m "harness: rules 30-31 포팅 (integration redfish/vmware/os + callback)"
```

---

### Task 3.6: Port rules 40-41 (qa, mermaid)

**Files:**
- Create: `.claude/rules/40-qa-pytest-baseline.md`
- Create: `.claude/rules/41-mermaid-visualization.md`

**Source reference:** `clovirone-base/.claude/rules/{40-qa-playwright-xray, 41-mermaid-visualization}.md`

**핵심 변환:**

| 대상 rule | 핵심 변환 |
|---|---|
| `40-qa-pytest-baseline` | Playwright → pytest. Xray (Jira 통합) → baseline JSON 회귀 검증. 테스트 분류: tests/redfish-probe/ (live) + tests/fixtures/ (mock) + tests/baseline_v1/ (회귀 기준선) + tests/evidence/ (Round 검증). 실장비 검증 절차. probe_redfish.py / deep_probe_redfish.py 사용법 |
| `41-mermaid-visualization` | 그대로 (R1~R17 모두 유지). 예시만 server-exporter 도메인으로 (resource-request → 3-channel gather flow) |

- [ ] **Step 1: 2개 rule 포팅**

- [ ] **Step 2: Commit**

```bash
git add .claude/rules/{40,41}-*.md
git commit -m "harness: rules 40-41 포팅 (qa-pytest-baseline + mermaid)"
```

---

### Task 3.7: Port rule 50 (vendor-adapter)

**Files:**
- Create: `.claude/rules/50-vendor-adapter-policy.md`

**Source reference:** `clovirone-base/.claude/rules/50-customer-branch-policy.md`

**핵심 변환:** customer (POSCO/SK하이닉스 등) → vendor (Dell/HPE/Lenovo/Supermicro/Cisco). branch 3계층 (배포/dev/personal) → main + feature/* 단순. 매핑 표 갱신:

| 출처 | 대상 |
|---|---|
| 브랜치 → 고객사/버전 매핑 표 | 디렉터리 → 벤더 매핑 표 (`adapters/redfish/dell_*.yml` → Dell, etc) |
| 고객사별 기능 차이 (GPU=true/false 등) | 벤더별 OEM 특이사항 (iDRAC8 vs iDRAC9 path 차이 등) |
| core 변경 시 영향 분석 | common/ + 3-channel 변경 시 모든 adapter에서 동작 확인 |

- [ ] **Step 1: rule 50 포팅**

- [ ] **Step 2: Commit**

```bash
git add .claude/rules/50-vendor-adapter-policy.md
git commit -m "harness: rule 50 포팅 (customer-branch → vendor-adapter)"
```

---

### Task 3.8: Port rules 60, 70, 80 (security, docs, ci)

**Files:**
- Create: `.claude/rules/60-security-and-secrets.md`
- Create: `.claude/rules/70-docs-and-evidence-policy.md`
- Create: `.claude/rules/80-ci-jenkins-policy.md`

**Source reference:** `clovirone-base/.claude/rules/{60-security-and-secrets, 70-docs-and-evidence-policy, 80-ci-and-release-policy}.md`

**핵심 변환:**

| 대상 rule | 핵심 변환 |
|---|---|
| `60-security-and-secrets` | 비밀값 관리: vault/{linux,windows,esxi}.yml + vault/redfish/{vendor}.yml. SQL 인젝션 절 제거. XSS 절 제거. 인증/인가: callback URL 인증. 에러 메시지: stacktrace 누설 금지. 로그: BMC password / vault password / iDRAC user redaction (security-redaction-policy.yaml 연동) |
| `70-docs-and-evidence-policy` | 그대로. docs/ai/ 갱신 트리거 표 그대로 (DB → 출력 schema). PROJECT_MAP fingerprint 그대로. 문서 보존 판정 기준 그대로. Archive 진입 기준 그대로 |
| `80-ci-jenkins-policy` | Bitbucket Pipelines → Jenkins 3종 (Jenkinsfile, Jenkinsfile_grafana, Jenkinsfile_portal). Pipeline 실패 분석 → Jenkins 실패 분석. CI 통과 의무 → Jenkinsfile 4-Stage 통과 (Validate / Gather / Validate Schema / E2E Regression) |

- [ ] **Step 1: 3개 rule 포팅**

- [ ] **Step 2: Commit**

```bash
git add .claude/rules/{60,70,80}-*.md
git commit -m "harness: rules 60/70/80 포팅 (security/docs-evidence/ci-jenkins)"
```

---

### Task 3.9: Port rules 90-93 (commit, task-impact, dependency, branch-merge)

**Files:**
- Create: `.claude/rules/90-commit-convention.md`
- Create: `.claude/rules/91-task-impact-gate.md`
- Create: `.claude/rules/92-dependency-and-regression-gate.md`
- Create: `.claude/rules/93-branch-merge-gate.md`

**Source reference:** `clovirone-base/.claude/rules/{90-commit-convention, 91-task-impact-gate, 92-dependency-and-regression-gate, 93-branch-merge-gate}.md`

**핵심 변환:**

| 대상 rule | 핵심 변환 |
|---|---|
| `90-commit-convention` | type 목록 (feat/fix/refactor/docs/test/chore/harness/hotfix) 그대로. 50자 제한 그대로. 금지어 그대로. 예시만 server-exporter 도메인 (BillingCalculator → field_dictionary 등) |
| `91-task-impact-gate` | preview 5섹션: 영향 모듈 / 영향 벤더 / 함께 바뀔 것 (테스트 / 문서 / adapter / **외부 시스템 계약: Redfish/IPMI/SSH/WinRM/vSphere**) / 리스크 top 3 / 진행 확인. 자동 호출 키워드 그대로. R7 회귀 검사 자동 식별 → 공통 fragment 영역 + adapter 추가/수정 + Jenkinsfile cron 변경 + 출력 schema 변경 |
| `92-dependency-and-regression-gate` | R1 의존성: build.gradle → ansible.cfg requirements.yml + Python pip. R2: convention 맹신 의존성 제거 금지. R3 회귀 체크리스트: 공통 팝업 → 공통 fragment, 공통 JS → callback_plugins, 공통 Vue 컴포넌트 → schema/sections.yml. R5 Flyway 버전 → schema/sections.yml + field_dictionary.yml 버전 사용자 확인. R7 라이브러리 충돌 → ansible collection 충돌. R8 Spring Bean 추가 → ansible play/role 의존성 추가. R9 자동 회귀 포함 → 공통 fragment / 공통 callback / Jenkinsfile cron / 출력 schema 변경 시 |
| `93-branch-merge-gate` | 단일 main 단순화: <br>- "고객사 배포 브랜치 보호" 절 제거 (해당 없음) <br>- "활성 개발 브랜치" 개념 제거 <br>- main + feature/*만. main 보호: force push 금지, 직접 push 금지(PR 경유 권장 또는 사용자 명시 승인). 머지 전략: feature → main는 squash 기본. R6 기본 squash 그대로 |

- [ ] **Step 1: 4개 rule 포팅**

- [ ] **Step 2: Commit**

```bash
git add .claude/rules/{90,91,92,93}-*.md
git commit -m "harness: rules 90-93 포팅 (commit/task-impact/dependency/branch-merge)"
```

---

### Task 3.10: Port rules 95-97 (production-critical, external-contract, incoming-merge)

**Files:**
- Create: `.claude/rules/95-production-code-critical-review.md`
- Create: `.claude/rules/96-external-contract-integrity.md`
- Create: `.claude/rules/97-incoming-merge-review.md`

**Source reference:** `clovirone-base/.claude/rules/{95-production-code-critical-review, 96-external-contract-integrity, 97-incoming-merge-review}.md`

**핵심 변환:**

| 대상 rule | 핵심 변환 |
|---|---|
| `95-production-code-critical-review` | 의심 패턴 11종 server-exporter용으로 재구성: <br>1. Null 체크 누락 → Ansible `default(omit)` 누락 <br>2. Stream 재사용 → set_fact 재정의로 인한 fragment 침범 <br>3. Regex lookaround dead code → Jinja2 정규식 dead code <br>4. Mapper case 의존 → adapter score 동률 처리 <br>5. hasLength/hasText 혼동 → `is none` vs `is undefined` vs `length == 0` 혼동 <br>6. 빈 i18n 메시지 → 빈 callback message <br>7. NumberFormatException → `int()` cast 미방어 <br>8. Single-branch TODO → 단일 vendor 분기 (다른 vendor 미지원 silent) <br>9. Self-reference 무한 재귀 → adapter_loader self-reference <br>10. mutable/immutable 혼동 → ansible vars dict의 deep copy 누락 <br>11. **외부 시스템 계약 drift** — adapter YAML의 vendor 목록 ↔ 실제 BMC 펌웨어 지원 집합 drift (rule 96 연동) <br>R4 Cross-branch → Cross-vendor (다른 vendor adapter와 비교) <br>R1 자동 스캔 대상 변경 (Java → Python/Ansible YAML) |
| `96-external-contract-integrity` | enum/상수 → adapter YAML metadata. Jenkins/GitLab/VMware/OpenStack/Ansible/Harbor → Redfish ServiceRoot path / IPMI sensor list / SSH 명령 출력 형식 / WinRM session 형식 / vSphere API 객체. Origin 주석 의무: adapter YAML에 `tested_against:` `firmware:` `oem_path:` 등. R3 영향 범위: adapter 값 변경 시 동일 vendor 다른 adapter / vendor_aliases.yml / vault/redfish/{vendor}.yml / OEM tasks |
| `97-incoming-merge-review` | 자동 검사 5종 server-exporter용 (Task 1.3 post_merge_incoming_review.py 변환과 동일): <br>(a) Jenkinsfile cron 변경 검사 <br>(b) Ansible/Python/YAML 의심 패턴 (raw 모듈 권한, vault 누설, fragment 침범) <br>(c) adapter YAML metadata 주석 누락 <br>(d) schema/sections.yml + field_dictionary.yml 버전 충돌 <br>(e) 결과 보고 출력 |

- [ ] **Step 1: 3개 rule 포팅 (rule 95의 11 패턴 재구성에 신중히)**

- [ ] **Step 2: 어휘 잔재 + 일관성 최종 검사**

```bash
grep -nE "Java|Spring|MyBatis|FTL|Vue|jQuery|Gradle|MariaDB|Flyway|sk-hynix|posco|smilegate|kisa|ina" .claude/rules/*.md
```

Expected: 출력 없음 (rule 23 R2 치환표 본문은 예외 — 인용임이 명시).

- [ ] **Step 3: Commit**

```bash
git add .claude/rules/{95,96,97}-*.md
git commit -m "harness: rules 95-97 포팅 (production-critical 11 패턴 server-exporter용 재구성 + external-contract + incoming-merge)"
```

---

## Phase 4: 검증 (Verification)

### Task 4.1: Hooks dry-run

- [ ] **Step 1: 각 hook 파이썬 import 검증**

```bash
cd C:/github/server-exporter
for f in scripts/ai/hooks/*.py; do
  python -c "import ast; ast.parse(open('$f').read())" && echo "OK $f" || echo "FAIL $f"
done
```

Expected: 모두 OK.

- [ ] **Step 2: session_start.py 실제 실행**

```bash
echo '{}' | python scripts/ai/hooks/session_start.py
```

Expected: 정상 종료 (브랜치 main 출력 + measurement targets 캐시 상태). 에러 시 디버그.

- [ ] **Step 3: pre_edit_guard.py 실제 실행 (편집 시뮬레이션)**

```bash
echo '{"tool_input": {"file_path": "vault/redfish/dell.yml"}}' | python scripts/ai/hooks/pre_edit_guard.py
```

Expected: 보호 경로 deny 메시지 (vault/** 보호).

- [ ] **Step 4: commit_msg_check.py self-test**

```bash
python scripts/ai/hooks/commit_msg_check.py --self-test
```

Expected: 통과.

---

### Task 4.2: Rule 참조 정합성 검증

- [ ] **Step 1: verify_harness_consistency.py 실행**

```bash
python scripts/ai/hooks/verify_harness_consistency.py
```

Expected: rules / policies / role / ai-context 간 참조 정합 통과. EXPECTED_REFERENCES 위반 시 list 출력 → 해당 rule 수정.

- [ ] **Step 2: surface-counts.yaml 갱신**

`.claude/policy/surface-counts.yaml`의 rules count를 30, policies count를 10, role count를 6, templates count를 10, commands count를 5, hooks count를 16으로 갱신 (skills/agents는 0 — Plan 2/3 후 갱신).

- [ ] **Step 3: Commit**

```bash
git add .claude/policy/surface-counts.yaml
git commit -m "harness: surface-counts.yaml 갱신 (Plan 1 완료 — rules 30, policies 10)"
```

---

### Task 4.3: PR 머지 전 최종 점검

- [ ] **Step 1: 전체 어휘 잔재 final scan**

```bash
grep -rnE "Java|Spring Boot|MyBatis|FTL|Vue\.js|jQuery|Gradle|MariaDB|Flyway|clovircm-(domain|web)|plugin-(posco|smilegate|example|sdk)|sk-hynix|posco|smilegate|kisa|ina" .claude/ scripts/ai/hooks/ CLAUDE.md
```

Expected: 출력 없음 (또는 명시적 인용 — 그 경우 rule 23 R8 ASCII 태그 또는 인용 표시).

- [ ] **Step 2: server-exporter 어휘 등장 빈도 확인**

```bash
grep -rnE "Fragment|adapter|vendor|Dell|HPE|Lenovo|Supermicro|Cisco|Redfish|IPMI|3-channel|sections\.yml|field_dictionary|baseline" .claude/ | wc -l
```

Expected: 100건 이상 (충분한 도메인 어휘 존재).

- [ ] **Step 3: 디렉터리 트리 출력**

```bash
ls -R .claude/ scripts/ai/hooks/
```

설계서 §4 TO-BE와 일치 확인.

- [ ] **Step 4: Plan 1 완료 commit**

```bash
git log --oneline | head -15
```

Expected: 약 12 commit (Phase별 commit 분할 — Task 1.2/1.3/1.4, 2.1~2.5, 3.2~3.10, 4.2). 모든 commit 메시지 `harness: ` prefix.

- [ ] **Step 5: docs/ai/CURRENT_STATE.md 초기 갱신 (Plan 1 완료 명시)**

(Plan 3에서 docs/ai/ 골격 작성 예정. 여기서는 placeholder commit으로 종료.)

```bash
mkdir -p docs/ai/
cat > docs/ai/CURRENT_STATE.md <<'EOF'
# server-exporter 현재 상태

- 2026-04-27: 하네스 Plan 1 완료
  - .claude/ 골격 (settings.json + rules 30 + policy 10 + role 6 + ai-context 12 + templates 10 + commands 5)
  - scripts/ai/hooks/ Python 16개 + install 스크립트
  - CLAUDE.md Tier 0 보강
  - 다음: Plan 2 (skills + agents) — 별도 세션
EOF
git add docs/ai/CURRENT_STATE.md
git commit -m "docs: docs/ai/CURRENT_STATE.md 초기화 (Plan 1 완료 기록)"
```

---

## 3. 완료 기준 (Plan 1)

- [ ] `.claude/settings.json` 존재 + JSON 문법 통과 + 16 hooks 등록
- [ ] `.claude/rules/` 30 파일 모두 작성 + 어휘 잔재 0
- [ ] `.claude/policy/` 10 YAML 모두 작성 + YAML 문법 통과
- [ ] `.claude/role/{gather,output-schema,infra,qa,po,tpm}/README.md` 6 파일 작성
- [ ] `.claude/ai-context/{common,gather,output-schema,infra,vendors,external}/` 12 파일 작성
- [ ] `.claude/templates/` 10 파일 작성 (prototype-skeleton 제외)
- [ ] `.claude/commands/` 5 파일 작성
- [ ] `scripts/ai/hooks/` Python 16개 + install-git-hooks.sh + import smoke 통과
- [ ] `CLAUDE.md` Tier 0 정본 패턴 11 섹션 추가 + 어휘 잔재 0
- [ ] `verify_harness_consistency.py` 통과
- [ ] git history 약 12 commit (`harness:` prefix) 분할
- [ ] 기존 server-exporter 코드 / rule 22 (fragment-philosophy) / REQUIREMENTS.md / README.md / docs/01~19 무수정
- [ ] `docs/ai/CURRENT_STATE.md` Plan 1 완료 기록

---

## 4. 비범위 (Plan 1 NOT in scope)

다음은 Plan 2, 3에서 다룬다:
- `.claude/skills/` 약 38개 SKILL.md (Plan 2)
- `.claude/agents/` 약 49개 (Plan 2)
- `docs/ai/` 풀 골격 (CURRENT_STATE 외 모든 catalogs/decisions/policy/workflows/harness/handoff/impact/incoming-review/roadmap/onboarding) (Plan 3)
- 자기개선 루프 dry-run 검증 (Plan 3)

---

## 5. 위험 (Plan 1)

| 위험 | 완화 |
|---|---|
| hook 16개 변환 중 import 오류 | Task 1.3 Step 4 일괄 ast.parse 검증. Step 2의 단위 smoke test로 조기 발견 |
| settings.json hook 등록 vs 실파일 부재 (Task 1.2 → 1.3 사이) | settings.json 작성 후 새 Claude Code 세션 시작 금지. 1.3 완료 후 재개 안내 |
| CLAUDE.md 보강 시 기존 내용 손상 | Task 1.4 Step 1 백업. 신규 섹션은 기존 섹션 사이에 삽입, 기존 내용 변경 최소 |
| 어휘 잔재 누락 | Phase별 commit 직전 grep 검사. Task 4.3 final scan으로 이중 검증 |
| rule 22 (Fragment 철학)이 rule 22 (fragment-philosophy)와 drift | Task 3.3 Step 2의 reference 검증. 정본은 rule 22는 인덱스 |
| settings.json `disableBypassPermissionsMode` 환경 비호환 | clovirone에는 이 키가 없었음. server-exporter에 신규 추가 시 Claude Code 버전 확인 필요. 미지원 시 제거 |
| measurement-targets.yaml의 12 항목 중 server-exporter에 없는 것 | Task 2.1에서 항목별 명시적 처리 (제거 / 변환 / 비활성). 결과를 rule 28에도 반영 |

---

## 승인 기록

| 일시 | 승인자 | 내역 |
|---|---|---|
| 2026-04-27 | hshwang1994 | 설계서 + Plan 1 작성 승인 (대화 "응 진행") |
