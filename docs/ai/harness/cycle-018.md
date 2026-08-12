# cycle-018 — 정기 자기개선 cycle (rule 28 drift 정정)

## 일자: 2026-05-01

## 사용자 명시
- "/clear" 후 "계획된 작업 모두 수행해라" → "진행해라" (자율 실행 승인)

## 진입 사유
- cycle-016 이후 자기개선 cycle 공백 (cycle-017은 보강 cycle)
- NEXT_ACTIONS.md "다음 cycle 권장" 1순위 = harness-evolution-coordinator 6단계 정기 cycle

## 6단계 파이프라인 결과

### Stage 1 — Observer (rule 28 11종 측정)

| # | 측정 | 실측 | drift |
|---|---|---|---|
| 1 | field_dict paths | 65 + 10 sections + 16 prefixes | **MED** doc 46 → 65 |
| 2 | PROJECT_MAP | fingerprint match | OK |
| 3 | adapter | 27 + registry.yml = 28 yml | **LOW** doc 25 → 27 |
| 4 | callback URL | rule 31 commit 4ccc1d7 | OK |
| 5 | Jenkinsfile cron | 2 pipeline, cron 0건 | OK (cycle-015 정합) |
| 6 | 표면 카운트 | rules=28/skills=48/agents=59/policies=10/hooks=21 | OK (yaml 일치) |
| 7 | baseline | **8 JSON** (`schema/baseline_v1/`) | **HIGH** SessionStart 0개 — script bug |
| 8 | Fragment 토폴로지 | 5 공통 변수 유지 | OK |
| 9 | branch 갭 | 0/0 | OK |
| 10 | vendor 경계 | clean | OK |
| 11 | 외부 계약 | TTL 미만료 | OK |

**핵심 발견**:
- observer agent가 표면 카운트 hallucinate (rules 32 / policies 11 주장 — 실측 28/10) → rule 25 R7-A 검증 가치 입증
- SessionStart "Baseline 0개" 보고의 근본 원인 = `collect_repo_facts.py:79` 경로 버그 (`tests/baseline_v1` ↔ 실제 `schema/baseline_v1`)

### Stage 2 — Architect (변경 명세)

drift 4건 + 부수 2건에 대한 diff-수준 명세 작성. 라인 번호 일부 어긋남 (메인이 정정).

### Stage 3 — Reviewer (자가 승인 금지)

architect 명세 비판 검수:
- **CRITICAL 발견**: `scripts/ai/vault_decrypt_check.py:97` 하드코딩 password "__REDACTED__" — NEXT_ACTIONS OPS-AUDIT-1 (자격증명 회전 보류)과 직결. "그대로 add" 옵션 REJECT
- 라인 번호 정정 반영
- Drift 2 분류 체계 (Must/Nice/Skip) 유지 여부 → 메인이 실측으로 확인 (must=39, nice=20, skip=6 분포 INTACT)

### Stage 4 — Governor (Tier 분류)

| 항목 | Tier | 결정 |
|---|---|---|
| Drift 1 (collect_repo_facts path bug) | 1 | 자동 적용 |
| Drift 2 (doc 46 → 65) | 1 | 자동 적용 (분류 체계 유지) |
| Drift 3 (adapter 25 → 27) | 1 | 자동 적용 |
| Drift 4 (`_vendor_count` 명명) | 2 | 옵션 C — docstring만 (최소 침습) |
| 부수 1 (.gitignore 9 패턴) | 1 | 자동 적용 |
| 부수 2 (vault_decrypt_check.py) | 2-CRIT | 옵션 B — `.gitignore` 영구 ignore |

ADR 불필요 — rule 70 R8 trigger 미해당 (rule 본문 의미 변경 0 / 표면 카운트 변경 0 / 보호 경로 변경 0).

### Stage 5 — Updater (Tier 1+2 적용)

수정 12 파일:
- `scripts/ai/collect_repo_facts.py` — line 79 path fix + `_vendor_count` docstring
- `CLAUDE.md` — adapter 25→27, field_dict 46→65, baseline 7개→8
- `.claude/rules/00-core-repo.md` — adapter / field_dict / fixture / baseline 갱신
- `.claude/rules/13-output-schema-fields.md` — field_dict 갱신
- `.claude/rules/23-communication-style.md` — 어휘 치환표 갱신
- `.claude/ai-context/common/coding-glossary-ko.md` — Field Dictionary 정의 갱신
- `.claude/ai-context/common/repo-facts.md` — adapter / Schema 행 갱신
- `.claude/ai-context/output-schema/convention.md` — "Field Dictionary 39 Must" 절 갱신
- `.claude/role/output-schema/README.md` — 3곳 갱신
- `.claude/skills/update-output-schema-evidence/SKILL.md` — 분포 예시 갱신
- `docs/ai/catalogs/PROJECT_MAP.md` — field_dict + baseline 행 갱신
- `docs/ai/catalogs/SCHEMA_FIELDS.md` — cycle-018 history 1행 append
- `.gitignore` — 9 untracked 패턴 + vault_decrypt_check.py

### Stage 6 — Verifier

| 검증 | 결과 |
|---|---|
| `verify_harness_consistency.py` | PASS (rules=28, skills=48, agents=59, policies=10) |
| `verify_vendor_boundary.py` | PASS |
| `output_schema_drift_check.py` | PASS (sections=10 fd_paths=65 fd_section_prefixes=16) |
| `check_project_map_drift.py` | PASS (fingerprint 일치) |
| `py_compile collect_repo_facts.py` | PASS |
| `pytest tests/unit/` | **94/94 PASS** |
| `collect_repo_facts.py` 실행 | "Baseline: 8개" 정상 출력 (이전: 0개) |
| `git status` 후 untracked 검증 | 9 로그 + vault_decrypt_check.py 모두 ignore됨 |

## 표면 카운트 변동
- rules: 28 (변동 없음)
- skills: 48 (변동 없음)
- agents: 59 (변동 없음)
- policies: 10 (변동 없음)
- hooks: 21 (변동 없음)

→ surface-counts.yaml 갱신 불필요. ADR 불필요.

## 잔여 / 후속

### closed (본 cycle)
- F-CYCLE-018-1: SessionStart "Baseline 0개" 버그 → 해결 (`tests` → `schema` 경로 fix)
- F-CYCLE-018-2: field_dictionary doc 46 entries stale → 해결 (실측 65로 8 파일 동기화)
- F-CYCLE-018-3: adapter 25개 doc stale → 해결 (실측 27 + registry.yml로 3 파일 동기화)
- F-CYCLE-018-4: `_vendor_count()` 명명 오용 → docstring으로 의미 명확화
- F-CYCLE-018-5: untracked 로그 9건 + vault_decrypt_check.py → `.gitignore`로 영구 ignore

### 후속 (외부 의존, AI 자체 불가)
- OPS-AUDIT-1: __REDACTED__ 자격증명 회전 — vault_decrypt_check.py에 잔재. 회전 후 fallback 평문 제거 권장
- (기존 NEXT_ACTIONS P2/P3 잔존 — 변동 없음)

## 정본 reference 갱신
- `docs/ai/CURRENT_STATE.md` — 별도 commit 갱신
- `docs/ai/NEXT_ACTIONS.md` — 별도 commit 갱신
- `docs/ai/catalogs/PROJECT_MAP.md` — 본 cycle 갱신
- `docs/ai/catalogs/SCHEMA_FIELDS.md` — 본 cycle history 1행 append

## commit / push
- 단일 commit: `harness: cycle-018 정기 self-improvement — rule 28 drift 정정`
- main 자율 push (rule 93 R1 + R4)

---

**산출**: 12 파일 변경 / 0 회귀 / 분류 체계 유지 / 보안 평문 차단
