# 시크릿 회전 + 히스토리 정리 런북 (SECRET ROTATION RUNBOOK)

> 작성: 2026-05-29 audit-cleanup cycle. 분류: **[CRIT] 운영 보안**.
> 본 cycle 사용자 결정 = **"문서화만"** — 저(AI)는 repo 안 시크릿을 자동 스크럽하지 **않았다**.
> 본 런북은 사용자/운영자가 실행할 회전·정리 절차를 정리한 것이다. 실제 암호 교체와 히스토리 재작성은 사용자 권한.

---

## 1. 무엇이 / 왜 / 영향

| 항목 | 값 (현재 평문 노출) | 실제 역할 | 영향 |
|---|---|---|---|
| **vault 마스터 암호** | `__REDACTED__` | `ansible-vault` 복호화 키 — `vault/**/*.yml` 전체 (linux/windows/esxi + redfish/{vendor}) 를 복호화 | 이 한 줄로 **repo 안 모든 자격(전 벤더 BMC / OS / ESXi)** 복호화 가능 → vault 암호화가 사실상 무효 |
| (동일 값) | `__REDACTED__` | Dell BMC `root` 암호 + lab Linux SSH/sudo 암호 | BMC/호스트 직접 장악 |
| **BMC primary 계정** | `__REDACTED__Infra` (`infraops`) | 5 벤더 통일 primary Redfish 계정 | 전 벤더 BMC 인증 장악 |
| **BMC recovery** | `__REDACTED__` (HPE admin / Lenovo USERID), `__REDACTED__` (Cisco admin) | 공장/복구 계정 — 최고 권한 fallback | BMC 복구 경로 장악 |

> 정본 확인: `docs/operate/05-vault.md` (vault 암호 = `__REDACTED__`), `jenkins/jobs/redfish-account-provision-verify/config.xml:100` (`echo '__REDACTED__' > .vault_pass`).

## 2. 노출 인벤토리 (추적 파일 기준 — 2026-05-29 실측)

총 **387 추적 파일**에 위 시크릿 중 하나 이상 평문 존재. **git 히스토리 전체에도 잔존** (과거 commit).

| 범주 | 파일 수 | 대표 위치 | 비고 |
|---|---|---|---|
| 운영 config | 1 | `jenkins/jobs/redfish-account-provision-verify/config.xml:22,100` | vault 마스터 암호 — **최우선** |
| 활성 코드 (주석/예시) | 4 | `redfish-gather/tasks/try_one_account.yml:48` (주석), `schema/output_examples/redfish_dell_idrac10.jsonc:11`, `schema/output_examples/README.md:75` | site 실측 결과/예시에 평문 |
| dead 일회용 스크립트 | 5 | `scripts/ai/bug_tracker/{inventory_lab_linux.ini,inventory_lab_linux.yml,capture_raw_linux.yml,agent_ops.py}`, `scripts/ai/add_lab_recovery_to_all_vaults.py` | 이미 실행됨 — 재실행 불필요. `echo PASS \| sudo -S` 형태는 런타임 `ps` 노출도 |
| 테스트 | 3 | `tests/unit/test_account_provision_*.py`, `tests/e2e/test_envelope_failure_modes.py` | redaction 테스트가 실제 값을 regex 로 박아둠 |
| 문서 (정본) | 2 | `docs/operate/05-vault.md`, `CLAUDE.md` (이력 주석) | vault 암호 문서화 |
| raw 캡처 (reference) | 289 | `tests/reference/os/**/cmd_sudoers.txt` 등 | `echo PASS \| sudo` 가 명령 출력에 누출. 사용자 결정 "tests/reference 전부 유지" |
| evidence | 65 | `tests/evidence/**/dmi_*.txt` 등 | 동일 누출 패턴. 구조화 raw 캡처라 보존 |

> docs cleanup (task 6) 으로 일부 완료-cycle 덤프(시크릿 포함분)가 HEAD 에서 제거됨 — 단 **히스토리에는 잔존**.

## 3. 회전 절차 (사용자/운영자 실행)

### 3.1 vault 마스터 암호 재키 (rekey) — [CRIT] 최우선
```bash
# 새 강력 암호 생성 후 (예: 32+ random):
NEW=$(openssl rand -base64 24)
for f in $(git ls-files 'vault/**/*.yml'); do
  ansible-vault rekey --new-vault-password-file <(echo "$NEW") "$f"
done
# Jenkins credential 'server-gather-vault-password' 값을 NEW 로 갱신
# (docs/operate/05-vault.md 시나리오 A 참조)
```

### 3.2 실제 자격 교체 (BMC/호스트 — vault 안 값 자체)
- Dell BMC `root` (= `__REDACTED__`), lab Linux SSH/sudo: 각 장비에서 암호 변경 후 `vault/redfish/dell.yml` / `vault/linux.yml` 갱신
- primary `infraops/__REDACTED__Infra`: 전 벤더 BMC 에서 변경 후 `vault/redfish/{vendor}.yml` 갱신
- recovery `__REDACTED__` / `__REDACTED__`: HPE/Lenovo/Cisco BMC recovery 계정 변경 후 vault 갱신
> 회전 후 `vault/**` 재암호화 (3.1 의 NEW 키로). 회전 전·후 모두 `git ls-files vault/` 가 암호화 상태인지 확인.

### 3.3 운영 메커니즘 수정 — config.xml
`jenkins/jobs/redfish-account-provision-verify/config.xml:99-101` 의
```
if [[ ! -f .vault_pass ]]; then echo '__REDACTED__' > .vault_pass; ...
```
→ Jenkins **credentials binding** 으로 교체 (다른 파이프라인 `Jenkinsfile` 은 이미 `withCredentials` 사용):
```
withCredentials([string(credentialsId: 'server-gather-vault-password', variable: 'VP')]) {
  writeFile file: '.vault_pass', text: VP
}
```
> **주의**: repo 안 config.xml 은 *사본*이다. 실제 Jenkins job(서버) 도 동일하게 수정해야 효과. 이 변경은 운영 job 인증 방식 변경 → 사용자 확인 후 적용 (본 audit 에서는 미적용).

## 4. git 히스토리 정리 (선택 — force-push 필요, rule 93)

회전(3.x)을 먼저 하면 히스토리의 옛 값은 "이미 폐기된 값"이 되어 위험이 크게 감소한다. 그래도 히스토리에서 제거하려면:
```bash
# git filter-repo 권장 (BFG 대안)
pip install git-filter-repo
git filter-repo --replace-text <(printf '__REDACTED__==>REDACTED\n__REDACTED__Infra==>REDACTED\n__REDACTED__==>REDACTED\n__REDACTED__==>REDACTED\n')
```
> **[CRIT] 제약**: 히스토리 재작성은 **force-push** 가 필수 (rule 93 R1 — AI 자율 금지, **사용자 명시 승인 필요**). 모든 클론/포크가 재clone 해야 함. github + gitlab 양쪽(rule 93 R7) 좌표. 본 audit 에서는 **미수행** (사용자 결정 "문서화만" + force-push 미승인).

## 5. 본 audit 가 한 것 / 안 한 것

- **안 함 (사용자 "문서화만")**: 시크릿 자동 스크럽, config.xml 수정, vault 회전, 히스토리 재작성.
- **함**: 본 런북 작성 + 인벤토리. (task 6 docs cleanup 이 일부 완료-cycle 덤프 시크릿분을 HEAD 에서 부수적 제거 — 의도는 doc 정리.)

## 6. 검증 체크리스트 (회전 후)
- [ ] `ansible-vault view vault/redfish/dell.yml` 가 NEW 키로만 열림 (옛 키 거부)
- [ ] `git grep -I 'Goodmit0802\|__REDACTED__Infra\|__REDACTED__\|__REDACTED__'` → 0 (스크럽 선택 시)
- [ ] Jenkins `redfish-account-provision-verify` job 이 credential binding 으로 동작
- [ ] BMC 로그인: 옛 암호 거부 / NEW 암호 허용
- [ ] (히스토리 정리 시) `git log -S '__REDACTED__' --oneline` → 0

## 관련
- rule: `60-security-and-secrets`(해제됨, 참고), `93-branch-merge-gate` R1(force-push), `27-precheck-guard-first` R6(vault)
- 정본: `docs/operate/05-vault.md`, `docs/ai/policy/SECURITY_POLICY.md`
- 인접 권고(인증 동작): `docs/ai/contracts/account-write-vendor-compat.md` §AUTH (lockout/dryrun)
