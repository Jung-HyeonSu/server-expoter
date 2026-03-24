# 07. Redis 설치 및 설정

Ansible `gather_facts` 결과를 Redis 에 캐싱하여 반복 실행 성능을 높인다.
Redis 는 Jenkins 마스터 노드에 설치하며, Agent 가 마스터의 Redis 에 접속하는 구조다.

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

> Agent 측 Redis 연동(`pip install redis`, `ansible.cfg` 의 `fact_caching`, 연결 테스트)은
> **08_agent-setup.md** 에서 Ansible 가상환경 설치와 함께 수행한다.
