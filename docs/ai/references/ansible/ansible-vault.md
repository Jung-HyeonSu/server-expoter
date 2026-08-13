# Ansible Vault — server-exporter 시크릿 관리

> Source: https://docs.ansible.com/ansible/latest/user_guide/vault.html
> server-exporter 적용: `vault/<loc>/os/{linux,windows}.yml + vault/<loc>/esxi.yml + vault/<loc>/redfish/<vendor>.yml`

## 핵심 명령

| 명령 | 용도 |
|---|---|
| `ansible-vault create <file>` | 새 암호화 파일 생성 |
| `ansible-vault edit <file>` | 암호화 파일 직접 편집 |
| `ansible-vault encrypt <file>` | 평문 → 암호화 변환 |
| `ansible-vault decrypt <file>` | 암호화 → 평문 변환 (디버그용, commit 금지) |
| `ansible-vault rekey <file>` | password 회전 |
| `ansible-vault view <file>` | 내용 보기 (편집 안 함) |
| `ansible-vault encrypt_string '...'` | 인라인 암호화 string (variable 안에 박을 때) |

## server-exporter Vault 구조

```
vault/
├── linux.yml                # SSH 자격증명 (Linux gather)
├── windows.yml              # WinRM 자격증명 (Windows gather)
├── esxi.yml                 # vSphere 자격증명 (ESXi gather)
└── redfish/
    ├── dell.yml
    ├── hpe.yml
    ├── lenovo.yml
    ├── supermicro.yml
    ├── cisco.yml
    └── generic.yml          # vendor 미매치 fallback
```

각 vault 파일은 ansible-vault encrypt 운영 권장 (cycle-011: rule 60 해제 / cycle-012: 8 vault encrypt 채택).

## Vault 파일 내용 예시

```yaml
# vault/<loc>/redfish/dell.yml (decrypt 후 보임)
vault_redfish_username: "service_account"
vault_redfish_password: "..."
```

암호화된 상태:
```
$ANSIBLE_VAULT;1.1;AES256
3963346...
6533393...
```

## Playbook 통합

```bash
# 인터랙티브 password
ansible-playbook -i inv site.yml --ask-vault-pass

# password 파일
ansible-playbook -i inv site.yml --vault-password-file ~/.vault_pass

# 환경변수
export ANSIBLE_VAULT_PASSWORD_FILE=~/.vault_pass
ansible-playbook -i inv site.yml
```

server-exporter Jenkins는 password 파일 또는 환경변수 사용 (Jenkins credentials store).

## Vault 2단계 로딩 (server-exporter Redfish 특화 — rule 27)

```yaml
# 1단계: 무인증으로 vendor 감지
- redfish_gather:
    ip: "{{ target_ip }}"
  register: _rf_probe

# 2단계: vendor에 맞는 vault 동적 로드
- include_vars:
    file: "vault/<loc>/redfish/{{ _rf_detected_vendor }}.yml"
    name: _rf_vault

# 3단계: 인증으로 본 수집
- redfish_gather:
    ip: "{{ target_ip }}"
    username: "{{ _rf_vault.vault_redfish_username }}"
    password: "{{ _rf_vault.vault_redfish_password }}"
```

## Multiple Vault IDs

여러 password 사용 가능 (예: production / development 분리):

```bash
ansible-playbook \
  --vault-id prod@~/.vault_prod \
  --vault-id dev@~/.vault_dev \
  site.yml
```

server-exporter는 일반적으로 **단일 vault password** (운영 단순화).

## 회전 절차 (rotate-vault skill)

1. 기존 vault password 확보
2. `ansible-vault rekey vault/<loc>/redfish/<vendor>.yml` 새 password 입력
3. 또는 외부 시스템 (BMC user) 자격증명 자체 변경 → vault 새로 encrypt
4. Jenkins credentials 갱신
5. dry-run 검증
6. `docs/ai/CURRENT_STATE.md` 갱신 + tests/evidence/ 기록

## Best Practices for server-exporter

1. **모든 vault encrypt** (운영 권장): 평문 commit 비권장 (cycle-011: rule 60 + pre_commit_policy.py 모두 제거 — 정책 강제 없음)
2. **password 파일 안전**: `chmod 600 ~/.vault_pass` + Jenkins credentials store
3. **명명 규칙**: vault 변수는 `vault_<scope>_<name>` (예: `vault_redfish_password`)
4. **회전 주기**: 분기/반기 정기 + 사고 시 즉시
5. **Vault 2단계** (Redfish): 무인증 detect 우선 → 잘못된 vendor vault 로드 방지

## Forbidden 패턴

- 평문 vault commit (cycle-011: pre_commit_policy.py 제거됨, 운영자 권장 차단)
- `--extra-vars "password=..."` 평문 CLI (Jenkins log 노출)
- environment variable로 password 전달 (process list 노출 가능)
- vault 파일을 직접 편집 (`vim vault/<loc>/redfish/dell.yml`) — `ansible-vault edit` 사용

## 적용 rule

- (cycle-011: rule 60 해제 — vault 운영은 권장 수준)
- rule 27 (precheck-guard-first / Vault 2단계)
- rule 50 (vendor-adapter-policy)
- rule 92 R5 (의존성 / 버전 사용자 확인)
