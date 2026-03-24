# 08. Agent 노드 구성

Jenkins Agent 는 로케이션(이천 / 청주 / 용인)별로 구성하며,
개발 / 운영 마스터 각각에 연결된 Agent 가 분리되어 있다.
아래 절차를 각 Agent 노드마다 반복 수행한다.

---

## 1. 기본 패키지 설치

```bash
# RHEL 계열
yum install -y java-21-openjdk python3 git jq redis

# Debian 계열
apt update && apt install -y openjdk-21-jdk python3 python3-venv git jq redis-tools
```

> `redis` (RHEL) / `redis-tools` (Debian) 는 `redis-cli` 를 포함한다.
> Agent 에서 마스터 Redis 연결 확인 시 사용한다.

---

## 2. cloviradmin 계정 생성

```bash
useradd -m -s /bin/bash cloviradmin
```

---

## 3. Ansible 가상환경 설치

### Python 패키지

```bash
sudo python3 -m venv /opt/ansible-env
sudo /opt/ansible-env/bin/pip install --upgrade pip
sudo /opt/ansible-env/bin/pip install 'ansible>=2.12'  # Ansible 풀패키지 (ansible-core + 주요 Collection)
sudo /opt/ansible-env/bin/pip install redis            # Ansible fact_caching Redis 백엔드
sudo /opt/ansible-env/bin/pip install pywinrm          # Windows WinRM 연결
sudo /opt/ansible-env/bin/pip install 'pyvmomi>=7.0'   # VMware ESXi API (community.vmware 의존)
sudo /opt/ansible-env/bin/pip install jmespath         # json_query 필터 (JSON 데이터 파싱)
sudo /opt/ansible-env/bin/pip install netaddr          # ipaddr 필터 (IP/서브넷 연산)
sudo /opt/ansible-env/bin/pip install lxml             # VMware 모듈 XML 파싱

# 확인
/opt/ansible-env/bin/ansible --version
```

### Python 인터프리터 경로 확인

Agent 서버에 `/usr/bin/python3` 경로로 Python 3.9 이상이 존재해야 합니다.
Ansible 커스텀 모듈 실행 시 이 경로를 사용합니다.

```bash
# 확인
ls -la /usr/bin/python3

# 없으면 심볼릭 링크 생성
sudo ln -sf $(which python3) /usr/bin/python3
```

대부분의 Linux 배포판(RHEL 8+, Ubuntu 20.04+, Rocky 8+)에서 기본 설치되어 있습니다.

### Ansible Collection

`pip install ansible` (풀패키지) 설치 시 아래 Collection 은 기본 포함된다.
`ansible-core` 만 설치한 경우 수동 설치가 필요하다.

```bash
# 프로젝트에서 사용하는 Collection
sudo /opt/ansible-env/bin/ansible-galaxy collection install community.vmware    # esxi-gather
sudo /opt/ansible-env/bin/ansible-galaxy collection install ansible.windows     # Windows gather
sudo /opt/ansible-env/bin/ansible-galaxy collection install ansible.posix       # Linux (cron, sysctl, authorized_key 등)
sudo /opt/ansible-env/bin/ansible-galaxy collection install community.general   # 범용 (timezone, modprobe, parted 등)
sudo /opt/ansible-env/bin/ansible-galaxy collection install ansible.utils       # 유틸리티 필터 (ipaddr, validate 등)

# 확인
/opt/ansible-env/bin/ansible-galaxy collection list
```

> `/opt/ansible-env` 는 사용자 계정에 의존하지 않는 시스템 공용 경로다.
> Jenkins Agent 사용자에게 읽기+실행 권한만 있으면 동작한다.

---

## 4. /etc/ansible/ansible.cfg 배치

모든 계정에서 동일하게 적용되도록 `/etc/ansible/ansible.cfg` 에 배치한다.

> **ansible.cfg 우선순위**: Ansible은 `ANSIBLE_CONFIG` 환경변수 → CWD의 `ansible.cfg` → `~/.ansible.cfg` → `/etc/ansible/ansible.cfg` 순으로 탐색한다.
> Jenkins 빌드 시 프로젝트 루트의 `ansible.cfg`가 CWD에 위치하므로 아래 시스템 설정보다 우선 적용된다.
> 여기서 설정하는 `/etc/ansible/ansible.cfg`는 프로젝트 외부에서 Ansible을 실행할 때의 기본값이다.

```bash
sudo mkdir -p /etc/ansible

sudo tee /etc/ansible/ansible.cfg > /dev/null << 'EOF'
[defaults]
host_key_checking       = False
bin_ansible_callbacks   = True
retry_files_enabled     = False
gathering               = smart
interpreter_python      = auto
forks                   = 20
timeout                 = 60
deprecation_warnings    = False
fact_caching            = redis
fact_caching_connection = {Jenkins_마스터_IP}:6379:0:{Redis비밀번호}
fact_caching_timeout    = 86400

[inventory]
enable_plugins = script, auto

[ssh_connection]
pipelining = True

[winrm]
transport = ntlm
EOF
```

> `{Jenkins_마스터_IP}`, `{Redis비밀번호}` 는 실제 값으로 교체한 뒤 실행한다.

> **범용 설정 원칙**: 이 파일은 모든 프로젝트(clovirone-portal, skhynix-infraops 등)의 공통 기본값이다.
> Ansible은 ansible.cfg를 병합하지 않고 우선순위 1개만 사용하므로,
> 프로젝트 루트에 `ansible.cfg`가 있으면 이 시스템 설정은 무시된다.
>
> - **clovirone-portal**: 프로젝트 루트 `ansible.cfg`에서 `stdout_callback = json_only`,
>   `gathering = explicit`, 커스텀 플러그인 경로 등을 설정하므로 이 파일과 무관.
> - **skhynix-infraops**: 프로젝트 `ansible.cfg` 없음 → 이 시스템 설정이 그대로 적용됨.
>
> `[inventory] enable_plugins = script, auto` — 동적 인벤토리 스크립트(inventory.sh)를
> INI 파서보다 먼저 인식시킨다. 이 설정이 없으면 Python 스크립트가 INI로 파싱되어 실패한다.

---

## 5. 신규 프로젝트 인벤토리 스크립트 실행 권한

Windows 에서 커밋된 `.sh` 파일은 Git 에 실행 권한(100755)이 기록되지 않아
Jenkins checkout 후 Ansible 동적 인벤토리가 동작하지 않는다.

신규 프로젝트를 생성하거나 `inventory.sh` / `my_inventory.sh` 를 새로 추가한 경우,
아래 명령으로 실행 권한을 Git 에 기록한 뒤 커밋한다.

```bash
# 프로젝트 clone 후
git update-index --chmod=+x inventory/my_inventory.sh   # 또는 {channel}-gather/inventory.sh
git commit -m "fix: inventory 스크립트 실행 권한 추가"
git push
```

> 한 번 커밋하면 이후 모든 clone / checkout 에서 실행 권한이 유지된다.
> 기존 프로젝트(clovirone-portal, skhynix-infraops)는 이미 적용 완료.

---

## 6. Jenkins 노드 등록

경로: Jenkins → Manage Jenkins → Nodes → New Node

### 기본 설정

| 항목 | 값 | 비고 |
|------|-----|------|
| Name | `agent-{loc}-{dev\|ops}` | 예: `agent-ich-ops`, `agent-chj-dev` |
| Description | `{로케이션} {개발\|운영} Agent` | 예: `이천 운영 Agent` |
| Number of executors | `2` | 동시 실행 잡 수. 서버 사양에 따라 조정 |
| Remote root directory | `/home/cloviradmin/jenkins-agent` | Agent 워크스페이스 경로 |
| Labels | 로케이션 코드 | 아래 표 참조 |
| Usage | `Only build jobs with label expressions matching this node` | 라벨 매칭 잡만 실행 |
| Launch method | `Launch agents via SSH` | 아래 상세 참조 |
| Availability | `Keep this agent online as much as possible` | |

### Labels 설정

Jenkinsfile 의 `agent { label "${params.loc}" }` 기준:

| 슬레이브 노드 | Labels 값 |
|-------------|----------|
| 이천 | `ich` |
| 청주 | `chj` |
| 용인 | `yi` |

### Launch method (SSH)

| 항목 | 값 |
|------|-----|
| Host | Agent 노드 IP |
| Credentials | `cloviradmin` SSH 계정 (Jenkins Credentials 에 미리 등록) |
| Host Key Verification Strategy | `Non verifying Verification Strategy` |

> SSH Credentials 등록: Jenkins → Manage Jenkins → Credentials → Add Credentials
> Kind: `SSH Username with private key`, Username: `cloviradmin`, Private Key: 마스터에서 생성한 SSH 키

---

## 7. Node Properties 설정

경로: Jenkins → Manage Jenkins → Nodes → {노드} → Configure → Node Properties

### Environment variables

| Name | Value |
|------|-------|
| `PATH+ANSIBLE` | `/opt/ansible-env/bin` |

> `PATH+ANSIBLE` 은 Jenkins 가 기존 PATH 에 `/opt/ansible-env/bin` 을 **추가**하는 문법이다.
> Jenkinsfile 에서 Ansible 실행 경로를 하드코딩하지 않아도 된다.

### Tool Locations

| Tool | Home |
|------|------|
| Ansible (`ansible`) | `/opt/ansible-env/bin` |

> Jenkins → Manage Jenkins → Tools → Ansible 에서 등록한 경로와 동일해야 한다.
> Agent 에서 실제로 해석되는 값이므로 Agent 의 가상환경 경로와 일치시킨다.

---

## 8. Redis 연결 테스트

07_redis-install.md 의 마스터 Redis 설정이 완료된 상태에서 실행한다.

```bash
# Agent 에서 마스터 Redis 접속 확인
redis-cli -h {Jenkins_마스터_IP} -a {Redis비밀번호} ping
# 응답: PONG

# Ansible fact caching 동작 확인 (json_only 는 프로젝트 전용 콜백이므로 테스트 시 default 로 우회)
ANSIBLE_STDOUT_CALLBACK=default /opt/ansible-env/bin/ansible -m setup localhost | head -5
redis-cli -h {Jenkins_마스터_IP} -a {Redis비밀번호} DBSIZE
# 응답: (integer) 1 이상
```

> 연결 실패 시 마스터의 `bind`, `requirepass`, 방화벽(6379) 설정을 재확인한다.
