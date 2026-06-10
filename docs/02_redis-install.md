# 02. Redis 설치 및 설정

> **이 문서는** Jenkins 마스터에 Redis 를 올리고, Agent 들이 안전하게 접속하도록 설정하는 절차다.
>
> **왜 Redis 가 필요한가?**
> Ansible 의 `gather_facts` 결과를 Redis 에 캐싱하면 같은 호스트에 대한 반복 실행이 빨라진다.
> 캐싱이 없으면 매 실행마다 SSH/WinRM 으로 다시 정보를 긁어와야 한다.
>
> **구조**: Redis 는 Jenkins 마스터에 1대만 설치하고, 모든 Agent 가 마스터의 Redis 에 붙는다.

> [!NOTE]
> server-exporter 의 프로젝트 `ansible.cfg` 는 `gathering = explicit` 라 fact 캐싱을 쓰지 않는다. 위 캐싱 설명은 Agent 공통 `/etc/ansible/ansible.cfg` 를 쓰는 외부 실행에 해당한다. 프로젝트 빌드 경로에서는 Redis 캐시가 비어 보이는 게 정상이다 (`docs/18_ansible-project-config.md` 참조).

> 모든 명령은 **root** 또는 **sudo** 로 실행한다.

---

## 1. Redis 서버 설치 (마스터 노드)

### RHEL 계열

```bash
sudo yum install -y redis
sudo systemctl enable redis --now
```

### Debian / Ubuntu 계열

```bash
sudo apt update && sudo apt install -y redis-server
sudo systemctl enable redis-server --now
```

> Debian 계열은 서비스명이 `redis-server` 이다 (`redis` 가 아님).

### 설치 확인

```bash
redis-cli ping
# 응답: PONG
```

---

## 2. Redis 설정 변경

Agent 가 외부에서 접속할 수 있도록 설정을 변경한다.

### 설정 파일 위치

| OS | 경로 |
|----|------|
| RHEL | `/etc/redis.conf` |
| Debian | `/etc/redis/redis.conf` |

### 변경할 항목

설정 파일을 열어 아래 값을 수정(또는 추가)한다:

```bash
# RHEL 예시
sudo vi /etc/redis.conf

# Debian 예시
sudo vi /etc/redis/redis.conf
```

```ini
# Agent 가 접속할 수 있도록 마스터 IP 바인딩 (기본값: 127.0.0.1)
# 권장: 마스터 실제 IP 를 명시한다. 0.0.0.0 은 가급적 피한다.
bind 127.0.0.1 {마스터_실제_IP}

# 비밀번호 설정 (내부망이라도 설정 권장)
requirepass {Redis비밀번호}

# protected-mode 는 requirepass 설정 시 자동으로 우회되므로 yes 유지
protected-mode yes

# 메모리 제한 (호스트 약 1만대 기준)
maxmemory 1gb

# 메모리 초과 시 오래된 키 자동 삭제
maxmemory-policy allkeys-lru
```

> **보안 권장**: `bind 0.0.0.0` + `protected-mode no` 조합은 Redis 를 모든 네트워크에 무인증 노출시킨다.
> 내부망이라도 `bind {마스터IP}` + `requirepass` 조합을 사용하는 것이 안전하다.
> `requirepass` 를 설정하면 `protected-mode yes` 상태에서도 인증된 외부 접속이 허용된다.

### 서비스 재시작 및 확인

```bash
# RHEL 계열
sudo systemctl restart redis

# Debian 계열
sudo systemctl restart redis-server

# 설정 반영 확인
redis-cli -a {Redis비밀번호} CONFIG GET bind
redis-cli -a {Redis비밀번호} CONFIG GET protected-mode
redis-cli -a {Redis비밀번호} CONFIG GET maxmemory
redis-cli -a {Redis비밀번호} ping   # PONG
```

---

## 3. 방화벽 설정

```bash
# RHEL 계열
sudo firewall-cmd --permanent --add-port=6379/tcp
sudo firewall-cmd --reload

# Debian 계열
sudo ufw allow 6379/tcp
```

> 6379 포트는 Agent ↔ 마스터 내부망만 오픈. 외부 차단 필수.

---

## 4. Agent 측 설정

Agent 가 마스터의 Redis 에 어떻게 붙는지는 별도 문서에서 다룹니다 (모든 Agent 노드에 공통 적용).

| 작업 | 문서 |
|------|------|
| `pip install redis` | [03_agent-setup.md](03_agent-setup.md) 5절 (Python venv 와 함께) |
| `ansible.cfg` 의 `fact_caching` 설정 | [18_ansible-project-config.md](18_ansible-project-config.md) |
| 연결 테스트 (`redis-cli -h MASTER_IP -a PASS ping`) | [03_agent-setup.md](03_agent-setup.md) 끝부분 |

---

## 자주 막히는 곳

| 증상 | 원인 / 해결 |
|------|------------|
| Agent → 마스터 Redis 연결 거부 | 마스터 `bind` 에 마스터 실제 IP 가 누락됨 |
| `NOAUTH Authentication required` | Agent 측 `ansible.cfg` 의 `fact_caching_connection` 에 `requirepass` 누락 |
| 마스터에서 ping 은 OK 인데 Agent 에서 실패 | 6379 방화벽 차단 — 마스터 firewall-cmd / ufw 확인 |
| `protected-mode no` 상태로 외부 노출 | requirepass 설정 후 `protected-mode yes` 로 되돌리고 Redis 재시작 |
