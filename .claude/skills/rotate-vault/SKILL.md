---
name: rotate-vault
description: 벤더별 또는 채널별 vault 자격증명 회전 절차. vault/<loc>/os/{linux,windows}.yml + vault/<loc>/esxi.yml + vault/<loc>/redfish/<vendor>.yml의 password / username 갱신 안내. ansible-vault rekey 또는 외부 BMC 사용자 자체 변경. 사용자가 "Dell vault 회전", "vault password 변경", "rotate" 등 요청 시. - 분기/반기 정기 회전 / BMC 사용자 변경 / 보안 사고 대응 / 자격증명 stale 발견
---

# rotate-vault

## 목적

server-exporter Vault 자격증명을 안전하게 회전. 두 가지 시나리오:
1. **Vault password 회전**: ansible-vault password 자체를 변경 (`ansible-vault rekey`)
2. **자격증명 회전**: 외부 시스템(BMC / Linux user / vSphere)의 user/password 자체를 변경 → vault 다시 encrypt

## 입력

- 영향 vault 파일 (예: vault/<loc>/redfish/dell.yml)
- 회전 종류 (vault password vs 자격증명)
- 새 자격증명 (외부 시스템 변경 후 확보)

## 출력 / 절차

### 시나리오 1: Vault password rekey (외부 자격증명 동일)

```bash
# 1. 백업 (안전)
cp vault/<loc>/redfish/dell.yml /tmp/dell-vault.bak

# 2. 새 password로 rekey
ansible-vault rekey vault/<loc>/redfish/dell.yml
# (기존 password 입력 → 새 password 입력 2회)

# 3. Jenkins credentials 갱신
# (Jenkins UI → Credentials → ANSIBLE_VAULT_PASSWORD 갱신)

# 4. 검증
ansible-vault view vault/<loc>/redfish/dell.yml
# (새 password로 read 가능한지)
```

### 시나리오 2: 외부 BMC 사용자 자격증명 회전

```bash
# 1. 외부 시스템 (BMC / iDRAC / iLO)에서 사용자 password 변경
# → BMC 운영자가 수행 (server-exporter는 read-only)

# 2. 새 자격증명으로 vault 다시 encrypt
ansible-vault edit vault/<loc>/redfish/dell.yml
# 안에서 vault_redfish_password 갱신

# 3. 검증
ansible-playbook redfish-gather/site.yml \
  -i ... -e "target_ip=10.x.x.1" \
  --vault-password-file ~/.vault_pass

# 4. evidence 기록
echo "2026-04-27: Dell vault rotation (BMC user 변경)" \
  >> tests/evidence/<날짜>-vault-rotation.md
```

### 시나리오 3: 벤더 추가 (새 vault 생성)

```bash
ansible-vault create vault/<loc>/redfish/huawei.yml
# 안에 입력:
# vault_redfish_username: "service_account"
# vault_redfish_password: "..."
```

## 회전 주기 권고

| Vault | 권장 주기 |
|---|---|
| vault password (마스터) | 분기 |
| 자격증명 (BMC / Linux / Windows / ESXi) | 반기 또는 사고 시 |
| 새 vendor vault | 추가 시점 (rule 50 R2 9단계) |

## 자동 반영 메커니즘 (M-C 학습 / rule 27 R6)

vault/<loc>/redfish/<vendor>.yml 변경 시 **다음 ansible 실행에서 자동 반영**. 회전 후 별도 캐시 무효화 작업 불필요.

### 자동 반영 보장 3 단서 (rule 27 R6 정본)

| # | 단서 | 검증 명령 | 기대 결과 |
|---|---|---|---|
| 1 | include_vars cacheable 부재 | `grep -rn 'cacheable' redfish-gather/tasks/load_vault.yml` | 0 결과 |
| 2 | host facts 미등록 | `grep -rn 'cacheable' redfish-gather/tasks/load_vault.yml common/tasks/normalize/` | 0 결과 |
| 3 | vault decrypt 캐시 부재 | `grep -rn 'vault_password_file\|VAULT_PASSWORD_FILE' ansible.cfg` | password file 만 (decrypt 캐시 옵션 없음) |

### 회전 후 다음 run 자동 반영 흐름

```
1. vault edit / rekey 후 vault/<loc>/redfish/dell.yml 변경
2. 다음 ansible-playbook 실행 시:
   - include_vars 가 vault file 디스크에서 새로 read (캐시 없음)
   - ansible-vault decrypt 매번 수행 (캐시 없음)
   - _rf_vault_data → _rf_accounts (task scope, host facts 영역 아님)
   - try_one_account.yml 이 새 password 로 BMC 인증
3. 결과: 새 password 자동 반영 (별도 작업 불필요)
```

### 단일 run 내 vault 변경 (반영 안 됨)

- 한 run 시작 후 vault 파일을 mid-run 변경해도 같은 run 내에는 반영 안 됨 (이미 include_vars 한 후 task 변수 캐시)
- 다음 run 부터 반영
- → **회전은 ansible-playbook 종료 후 수행 권장**

## 검증 절차

1. `ansible-vault view <vault>` — 새 password로 read 가능
2. dry-run: `ansible-playbook --syntax-check`
3. **자동 반영 3 단서 검증** (rule 27 R6):
   - `grep -rn 'cacheable' redfish-gather/tasks/load_vault.yml common/tasks/normalize/` 0 결과
   - `ansible.cfg` 에 vault decrypt 캐시 옵션 없음 (vault_password_file 만)
4. 실장비 1대 대상 본 수집 시도 (target_type별)
5. callback 결과 envelope의 `meta.vendor` 정상
6. console log에 평문 password 노출 없음 확인

## 보안 주의 (rule 60)

- 회전 절차 중 임시로 평문 password 메모는 메모리 only (파일 / clipboard 제거)
- Jenkins credentials는 server-exporter 외부 (Jenkins controller 권한 최소)
- 회전 이력은 `tests/evidence/<날짜>-vault-rotation.md` (날짜 + 대상만, password 자체는 절대 기록 안 함)
- ansible-vault password 파일 (`~/.vault_pass`)은 `chmod 600`

## 실패 / 오탐 처리

- rekey 후 일부 호스트 인증 실패 → BMC 측 password sync 안 됨 (외부 시스템 운영자에게 escalate)
- 회전 후 dry-run FAIL → 즉시 backup 으로 revert + 원인 분석
- vault edit 도중 vim 종료 → `.swp` 파일 잔재 (절대 commit 금지, .gitignore 확인)

## server-exporter 도메인 적용

- 영향 채널: rotation 대상에 따라 (주로 redfish — vendor별 vault)
- 영향 vendor: 회전 대상 1개 또는 다수
- 영향 schema: 없음

## 적용 rule / 관련

- (cycle-011: rule 60 보안 정책 해제. 본 skill은 운영 절차 가이드로만 유효)
- **rule 27 R6** (vault 자동 반영 단서 3개 — M-C 학습 형식화)
- rule 50 R2 (새 vendor 추가 시 vault 9단계)
- rule 70 (docs-and-evidence) — evidence 기록
- skill: `add-new-vendor`, `debug-precheck-failure` (auth 실패 시)
- agent: 본 skill의 운영 실행자는 사용자 (cycle-011: vault-rotator + security-reviewer agent 제거)
- 정본 코드: `redfish-gather/tasks/load_vault.yml`
- 정본 docs: `docs/operate/02-agent-node.md` 보안 부분, `docs/operate/05-vault.md` (M-C 결과 정본)
- reference: 외부 API 공식 문서
- 회귀 fixture: M-C3 commit (9건 mock — vault rekey / vault edit / vendor 추가 시나리오)

## Forbidden

- 평문 password를 chat / Jenkins log / commit에 노출
- vault edit 중 임시 파일 (.swp) commit
- Jenkins credentials를 server-exporter `.claude/` 안에 보관 (Jenkins controller 책임)
- AI가 자체적으로 vault 회전 결정 (사용자 명시 승인 필요)
