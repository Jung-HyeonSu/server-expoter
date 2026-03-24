# Ansible 런타임 요구사항

> 검증일: 2026-03-18

## 1. 실행환경 검증 결과

이 컴퓨터(개발 환경)에서의 검증:

| 항목 | 상태 | 설명 |
|------|------|------|
| Python 3.11 | ✅ 설치됨 | Python 3.11.9 |
| PyYAML | ✅ 설치됨 | 6.0.2 |
| Ansible | ❌ 미설치 | `ansible` 패키지 없음 |
| pywinrm | ❌ 미설치 | Windows 타겟 수집 불가 |
| pyvmomi | ❌ 미설치 | ESXi 수집 불가 |
| redis | ❌ 미설치 | fact caching 불가 (선택) |

**참고**: Jenkins agent에서 실행되므로, Jenkins agent 환경에 설치 필요.

> **Python 최소 요구사항**: Python 3.9 이상 (f-string, `str.removeprefix()` 등 3.9+ 기능 사용)

## 2. 필수 Python 패키지

```bash
pip install ansible>=2.12
pip install pywinrm           # os-gather (Windows 타겟)
pip install pyvmomi>=7.0      # esxi-gather
pip install pyyaml>=5.0       # adapter/vault 로딩
pip install requests          # 일부 모듈 (선택)
pip install redis             # fact caching (선택)
```

## 3. 필수 Ansible 컬렉션

```bash
ansible-galaxy collection install community.vmware   # esxi-gather
ansible-galaxy collection install ansible.windows     # os-gather (Windows)
```

## 4. ansible.cfg 필요 설정

프로젝트 루트에 `ansible.cfg` 생성됨 (2026-03-18). 핵심 설정:

```ini
[defaults]
lookup_plugins  = ./lookup_plugins         # adapter_loader
filter_plugins  = ./filter_plugins         # field_mapper, diagnosis_mapper
callback_plugins = ./callback_plugins       # json_only (단일 사본)
library         = ./common/library:./redfish-gather/library
module_utils    = ./module_utils           # adapter_common
stdout_callback = json_only
callbacks_enabled = json_only
gathering = explicit                        # gather_facts: no
host_key_checking = False
interpreter_python = auto
forks = 20
timeout = 60
```

## 5. 커스텀 플러그인 경로

| 플러그인 타입 | 경로 | 파일 |
|-------------|------|------|
| lookup | `./lookup_plugins/` | `adapter_loader.py` |
| filter | `./filter_plugins/` | `field_mapper.py` (현재 미사용, deprecated), `diagnosis_mapper.py` |
| callback | `./callback_plugins/` | `json_only.py` (단일 사본, ansible.cfg 참조) |
| library | `./common/library/`, `./redfish-gather/library/` | `precheck_bundle.py`, `redfish_gather.py` |
| module_utils | `./module_utils/` | `adapter_common.py` |

### 플러그인 발견 경로 우선순위
1. `ansible.cfg`의 설정값
2. 환경변수 (`ANSIBLE_LOOKUP_PLUGINS` 등)
3. Playbook 인접 디렉토리 (각 채널의 `library/`, `callback_plugins/`)
4. `~/.ansible/plugins/`

**주의**: `ansible.cfg` 없이 실행하면 프로젝트 루트의 `lookup_plugins/`, `filter_plugins/`는 자동 인식되지만,
채널별 `library/` (예: `redfish-gather/library/`)는 인식 안됨. `ansible.cfg` 필수.

## 6. 환경변수

| 변수 | 필수 | 설명 | 설정 위치 |
|------|------|------|----------|
| `REPO_ROOT` | 필수 | 프로젝트 루트 경로 (adapter/vault 로딩에 사용) | Jenkinsfile: `${WORKSPACE}` |
| `INVENTORY_JSON` | 필수 | 포털이 전달하는 호스트 배열 JSON | Jenkinsfile: `${params.inventory_json}` |
| `ANSIBLE_CONFIG` | 권장 | ansible.cfg 경로 (미설정 시 CWD 기준) | Jenkins workspace 루트 |
| `PYTHONPATH` | 선택 | module_utils 경로 (ansible.cfg로 대체 가능) | — |

## 7. Vault 설정

```bash
# vault 비밀번호 파일 방식
ansible-playbook --vault-password-file .vault_pass site.yml

# 환경변수 방식
export ANSIBLE_VAULT_PASSWORD_FILE=.vault_pass

# Jenkins credentials binding 방식 (권장)
withCredentials([file(credentialsId: 'vault-pass', variable: 'VAULT_PASS')]) {
    sh "ansible-playbook --vault-password-file ${VAULT_PASS} site.yml"
}
```

## 8. 실행 명령 예시

```bash
# Redfish gather
cd ${REPO_ROOT}
export REPO_ROOT=$(pwd)
export INVENTORY_JSON='[{"ip":"10.50.11.232","vendor":"lenovo","username":"USERID","password":"VMware1!"}]'
ansible-playbook redfish-gather/site.yml -i redfish-gather/inventory.sh

# OS gather
ansible-playbook os-gather/site.yml -i os-gather/inventory.sh

# ESXi gather
ansible-playbook esxi-gather/site.yml -i esxi-gather/inventory.sh
```

## 9. 바로 실행 가능 여부 판단

| 채널 | 바로 실행 가능? | 누락 항목 |
|------|----------------|----------|
| redfish-gather | ⚠️ 조건부 | Ansible 설치, ansible.cfg (생성 완료), REPO_ROOT 설정 |
| os-gather | ❌ 추가 구성 필요 | + pywinrm, SSH 키 배포, 타겟 서버 접근 |
| esxi-gather | ❌ 추가 구성 필요 | + pyvmomi, community.vmware 컬렉션, vCenter 접근 |

## 10. 설치 우선순위

1. **Python + pip** (기본)
2. **Ansible 2.12+** (핵심)
3. **PyYAML** (adapter 로딩)
4. **ansible.cfg 배치** (플러그인 경로)
5. **pywinrm** (Windows 타겟 시)
6. **pyvmomi + community.vmware** (ESXi 타겟 시)
7. **redis** (선택 — fact caching)
