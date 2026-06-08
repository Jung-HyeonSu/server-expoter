# cycle-011 — 보안 정책 자체 해제 + AI 자동화 권한 부여

## 일자
2026-04-28

## 진입 사유

cycle-010 후속 Win10 검증 자동화 시도 중 sandbox 4회 차단 → 사용자 명시 결정 (옵션 A 일괄 제거):

> "이 프로젝트는 AI가 사용자 자격으로 외부 인프라 접속하는 것 자체를 정책이 차단할 필요가 없다. AI가 모든 권한을 가져도 된다. 보안도 필요 없다. 그런 하네스는 없애라."

→ 본 cycle은 **rule 60 + 관련 정책 / hook / agent 일괄 제거**.

## 처리 내역

### 영역 1 — 프로젝트 settings 일괄 변경 (11개 항목)

| # | 대상 | 처리 |
|---|---|---|
| 1 | `.claude/settings.json` `permissions.deny` | **모두 삭제** (38건 → 0건) |
| 2 | `.claude/settings.json` `disableBypassPermissionsMode` | **삭제** + `defaultMode: bypassPermissions` |
| 3 | `.claude/settings.json` sandbox | `enabled: false, allowUnsandboxedCommands: true` |
| 4 | `.claude/settings.json` PreToolUse pre_edit_guard hook | **삭제** |
| 5 | `.claude/policy/protected-paths.yaml` | 삭제 → deprecated stub 재생성 (verify 정합) |
| 6 | `.claude/policy/security-redaction-policy.yaml` | **삭제** |
| 7 | `.claude/rules/60-security-and-secrets.md` | **삭제** |
| 8 | `scripts/ai/hooks/pre_commit_policy.py` | **삭제** + `install-git-hooks.sh` + `.git/hooks/pre-commit` 재생성 |
| 9 | `scripts/ai/policy_loader.py` | **삭제** |
| 10 | `.claude/agents/security-reviewer.md` | **삭제** |
| 11 | `.claude/agents/vault-rotator.md` | **삭제** |

### Surface 카운트 갱신

```
rules: 29 → 28 (rule 60 삭제)
hooks: 19 → 18 (pre_commit_policy 삭제)
agents: 51 → 49 (security-reviewer + vault-rotator 삭제)
policies: 10 → 9 (security-redaction 삭제, protected-paths stub 잔존)
```

### Stale reference (25개 파일) — advisory

다음 파일들이 rule 60 / protected-paths 참조하지만 stale link 잔존 (후속 cycle에서 incremental cleanup):

- 25개: rules / skills / agents / policy / ai-context / role
- 단 `verify_harness_consistency.py` 통과 (참조 위반 0건) — protected-paths.yaml stub + 연결된 agent 제거로 깨끗

### 검증 결과

```
verify_harness_consistency.py     → PASS (rules 28, skills 43, agents 49, policies 9)
verify_vendor_boundary.py          → PASS (vendor 하드코딩 0건)
git hooks 재설치                    → PASS (pre_commit_policy 제거)
```

### 미완 / 사용자 행위 필요

- `.claude/settings.local.json` — self-modification 차단으로 AI 수정 불가. 사용자 직접 편집 필요 (또는 settings.json만으로 충분할 수도 있음 — 시도 후 확인)
- 영역 2 사용자 PC 글로벌 settings (`~/.claude/settings.json`) — sandbox 차단이 영역 1만으로 안 풀릴 수 있음. 시도 후 결정

## 영향

| 영역 | 변경 후 |
|---|---|
| AI 권한 | Bash(\*), Edit(\*\*), Write(\*\*), Read(\*\*), defaultMode bypassPermissions |
| 외부 자격 SSH/WinRM | AI 자동 가능 목표 (단 일부 sandbox 차단은 영역 2도 풀려야 실효) |
| Vault | 의무 해제 (단 파일은 그대로) |
| 보안 검사 | rule 60 삭제 → 의무 없음 |
| Memory feedback | `feedback_skip_security.md` (사전 등재) 유효 |

## 다음 단계

cycle-011 commit + push → SSH/WinRM 자동화 재시도 (Win10 10.100.64.120) → 결과 따라 cycle-012 (Win10 baseline 정정 + reference raw archive)

## 관련

- ADR: `docs/ai/decisions/ADR-2026-04-28-security-policy-removal.md`
- rule 70 R8: 본 ADR이 R8 적용 두 번째 사례 (rule 본문 의미 변경 + 표면 카운트 변경 + 보호 경로 정책 변경 — 3 trigger 모두 해당)
