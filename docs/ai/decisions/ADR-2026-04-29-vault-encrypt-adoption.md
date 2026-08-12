# ADR-2026-04-29 — vault 8개 파일 ansible-vault encrypt 채택 + Jenkins credential 등록

## 상태

**Accepted** (cycle-012, 2026-04-29)

## rule 70 R8 trigger 분석

| trigger | 해당 여부 | 근거 |
|---|---|---|
| rule 본문 의미 변경 | **미해당** | 본 cycle 변경은 코드 / schema / vault 파일 자체. rule Default/Allowed/Forbidden 절 변경 없음 |
| 표면 카운트 변경 | **미해당** | rules 28, skills 43, agents 49, policies 9 — 변경 없음 |
| 보호 경로 정책 변경 | **미해당** | cycle-011 deprecated stub 잔존 상태. cycle-012에서 protected-paths.yaml 갱신 없음 |

→ **R8 의무 ADR 아님**. 본 ADR은 **advisory governance trace** — vault encrypt 채택은 운영 보안 영향이 크고 후속 cycle에서 password 회전 / credential 회전 / 추가 vault 추가 시 reasoning 참조 가치 있음.

## 컨텍스트 (Why)

cycle-011에서 보안 정책 자체 해제 (rule 60 + protected-paths.yaml + pre_commit_policy 일괄 제거). AI 자동화 권한 부여 + 보안 검사 의무 해제. 그러나 운영 환경에서는 **Jenkins agent 빌드 실행 시 ansible-vault password 주입**이 여전히 필요. 평문 vault 파일을 그대로 commit / push 하면 GitHub 공개 노출.

**P1 commit `fe0be36c`** (vault accounts list 추가) 시점에 평문 password 6종이 vault×8 파일에 1회 노출 commit됨:
- linux: `__REDACTED__` (1차) / `__REDACTED__` (2차)
- windows: `__REDACTED__` / `__REDACTED__`
- esxi: `__REDACTED__` / `__REDACTED__`
- redfish/dell: `__REDACTED__` / `calvin`
- redfish/hpe: `__REDACTED__` / `__REDACTED__`
- redfish/lenovo: `__REDACTED__` / `__REDACTED__`
- redfish/supermicro: `__REDACTED__` / `__REDACTED__`
- redfish/cisco: `__REDACTED__` / `__REDACTED__`

**문제 본질**: Git history에 평문 잔존 → public repo 시 즉시 leak. 그러나 force-push 또는 history rewrite는 cycle-011에서 **사용자 명시 결정**으로 옵션 A1 (평문 1회 노출 후 encrypt 분리) 채택. 즉:

1. encrypt 자체는 별도 commit으로 분리 (audit trail)
2. 평문은 Git history 잔존 — 운영팀이 회전 (OPS-3)
3. 회전된 password는 새 PR에 encrypt + commit

## 결정 (What)

cycle-012 commit `29fee49a`에서 다음 일괄 적용:

### 1. vault 8 파일 ansible-vault AES256 encrypt

```bash
ansible-vault encrypt --vault-password-file <pwd> \
  vault/linux.yml vault/windows.yml vault/esxi.yml \
  vault/redfish/dell.yml vault/redfish/hpe.yml vault/redfish/lenovo.yml \
  vault/redfish/supermicro.yml vault/redfish/cisco.yml
```

vault password = `__REDACTED__` (운영팀 결정).

### 2. Jenkins credential 등록

| 항목 | 값 |
|---|---|
| credential ID | `server-gather-vault-password` |
| credential type | **Secret File** |
| 파일 내용 | vault password 1줄 (`__REDACTED__\n`) |

### 3. Jenkinsfile×3 binding

3 Jenkinsfile (`Jenkinsfile`, `Jenkinsfile_grafana`, `Jenkinsfile_portal`) 모두 Stage 2 (Gather) 직전에:

```groovy
withCredentials([
    file(
        credentialsId: 'server-gather-vault-password',
        variable    : 'VAULT_PASSWORD_FILE',
    ),
]) {
    ansiblePlaybook(
        ...
        extras: "--vault-password-file=${VAULT_PASSWORD_FILE}",
    )
}
```

### 4. docs/01_jenkins-setup.md 갱신

credential 등록 절차 (Manage Jenkins → Credentials → Add Secret File) 추가.

### 5. scripts/bootstrap 갱신

로컬 개발자용 bootstrap 시 vault password 입력 안내 추가.

## 결과 (Impact)

| 영역 | 변경 전 (cycle-011 종료) | 변경 후 (cycle-012 종료) |
|---|---|---|
| vault 파일 8개 | 평문 (Git에 그대로 commit) | ansible-vault AES256 encrypted |
| Git history | 평문 password 6종 1회 commit (`fe0be36c`) — 회전 대상 | 동일 (history는 변경 안 함) |
| Jenkins agent 빌드 | vault password 별도 주입 메커니즘 부재 | `server-gather-vault-password` Secret File credential |
| Jenkinsfile 3종 | vault 처리 없음 | `withCredentials` + `--vault-password-file` 패턴 |
| 운영자 회전 의무 | 없음 | OPS-3 — Git history 잔존 평문 6종 회전 (운영팀 일정) |
| AI 작업 권한 | vault 평문 read 허용 | encrypt 후에도 vault password 노출 시 read 허용 (보안 정책 해제 상태) |

## 대안 비교 (Considered)

### 옵션 A1 — 평문 1회 노출 후 encrypt 분리 (채택)

- pro: audit trail 명확 (어떤 commit이 평문 / 어떤 commit이 encrypt 후), force-push 회피 (rule 93 R1 정신)
- con: Git history 잔존 → 운영팀 password 회전 의무 발생 (OPS-3)

### 옵션 A2 — encrypt만 commit + force-push로 history rewrite

- pro: 평문 유출 위험 즉시 제거
- con: rule 93 R1 force push 금지 위반. 다른 작업자 / 세션의 working tree 강제 reset 필요. cycle-011 보안 정책 해제 결정 후 force-push까지 동원하는 것은 overhead 과대

### 옵션 B — vault 파일 자체 .gitignore 후 외부 secret manager (HashiCorp Vault / AWS SSM)

- pro: 평문 / encrypt 모두 Git 외부 — 완전 분리
- con: 신규 인프라 의존 (운영팀 결정 + 별도 cycle). 현재 server-exporter 운영 규모에서 ansible-vault만으로 충분

→ **A1 채택**. cycle-011 + cycle-012의 하나의 흐름 (보안 정책 해제 + 자동화 가능 + 운영 보안 최소 수준 유지)에 정합.

## 후속 / 회전

- **OPS-3** Git history 잔존 평문 password 6종 회전 — 운영팀 일정 + 실 장비 + 새 PR에 encrypt 후 commit
- **OPS-1** Jenkins 빌드 시범 1회 — credential binding 정상 동작 확인 (envelope `meta.auth.fallback_used` 노출 검증)
- 새 vendor 추가 시 (rule 50 R2 9단계 절차): vault/redfish/{vendor}.yml 작성 후 즉시 encrypt + 본 ADR 절차 따름

## 관련

- cycle-011 ADR: `ADR-2026-04-28-security-policy-removal.md` (보안 정책 해제 — 본 ADR의 전제)
- cycle-012 보고서: `docs/ai/archive/harness/cycle-012.md`
- handoff: `docs/ai/archive/handoff/2026-04-29-cycle-012.md`
- plan: `C:\Users\hshwa\.claude\plans\1-snazzy-haven.md` (P0 Foundation에서 vault binding 명시)
- rule: `93-branch-merge-gate` R1 (force push 금지 — 옵션 A2 거절 근거)
