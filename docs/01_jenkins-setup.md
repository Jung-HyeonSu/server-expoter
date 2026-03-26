# 01. Jenkins 마스터 설치 및 설정

개발 / 운영 Jenkins 마스터를 완전히 분리하여 각각 설치한다.
아래 절차를 개발 마스터, 운영 마스터 각각에 동일하게 수행한다.

> 모든 명령은 **root** 또는 **sudo** 로 실행한다.

---

## 1. Java 설치

```bash
# RHEL 계열
yum install -y java-21-openjdk

# Debian 계열
apt update && apt install -y openjdk-21-jdk

# 확인
java -version
```

> **Java 21 필수**: Jenkins 는 2026-03-31 부터 Java 17 지원을 종료한다.
> Java 21 은 Jenkins LTS 2.426.1 부터 지원되며, 신규 설치 시 반드시 Java 21 을 사용한다.
> 기존 Java 17 환경은 위 패키지 설치 후 Jenkins 재시작으로 전환 가능하다.

---

## 2. Jenkins 설치

```bash
# RHEL 계열
wget -O /etc/yum.repos.d/jenkins.repo https://pkg.jenkins.io/redhat-stable/jenkins.repo
rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io-2026.key
yum install -y jenkins

# Debian 계열
curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2026.key \
  | tee /usr/share/keyrings/jenkins-keyring.asc > /dev/null
echo "deb [signed-by=/usr/share/keyrings/jenkins-keyring.asc] \
  https://pkg.jenkins.io/debian-stable binary/" \
  | tee /etc/apt/sources.list.d/jenkins.list > /dev/null
apt update && apt install -y jenkins
```

> **GPG 키 갱신**: 기존 `jenkins.io-2023.key` 는 2026-03-26 만료.
> 이미 설치된 환경에서는 아래 명령으로 키만 교체할 수 있다.
> ```bash
> # RHEL
> rpm --import https://pkg.jenkins.io/redhat-stable/jenkins.io-2026.key
> # Debian
> curl -fsSL https://pkg.jenkins.io/debian-stable/jenkins.io-2026.key \
>   | tee /usr/share/keyrings/jenkins-keyring.asc > /dev/null
> ```

---

## 3. 서비스 시작

```bash
systemctl enable jenkins --now
systemctl status jenkins

# 초기 관리자 비밀번호
cat /var/lib/jenkins/secrets/initialAdminPassword
```

---

## 4. 초기 설정

1. 브라우저에서 `http://{마스터IP}:8080` 접속
2. 초기 관리자 비밀번호 입력
3. **Install suggested plugins** 선택
4. 관리자 계정 생성

---

## 5. 방화벽 설정

```bash
# RHEL 계열
firewall-cmd --permanent --add-port=8080/tcp
firewall-cmd --reload

# Debian 계열
ufw allow 8080/tcp
```

---

## 6. 플러그인 설치

경로: Jenkins → Manage Jenkins → Plugins → Available plugins

> §4 초기 설정에서 **Install suggested plugins** 를 선택하면
> Pipeline, Credentials, Git 등 기본 플러그인은 자동 설치된다.
> 아래 표에서 ★ 표시가 없는 항목만 별도 설치하면 된다.

### 필수 플러그인

| 플러그인 | 용도 | suggested 포함 |
|----------|------|:--------------:|
| **Ansible** | `ansiblePlaybook()` 스텝 | |
| **GitLab** | GitLab SCM 연동 | |
| **Role-based Authorization Strategy** | Job 단위 권한 분리 | |
| **Credentials** | GitLab 계정 중앙 관리 | ★ |
| **Pipeline** | Declarative Pipeline 실행 | ★ |
| **Pipeline Utility Steps** | `readJSON` 스텝 (Jenkinsfile 파라미터 파싱) | |
| **AnsiColor** | `ansiColor('xterm')` 옵션 — Ansible 컬러 출력 | |
| **Git** | SCM checkout | ★ |

### 권장 플러그인

| 플러그인 | 용도 |
|----------|------|
| **Pipeline: Stage View** | Stage 별 실행 결과 시각화 |
| **Blue Ocean** | 파이프라인 흐름 UI |
| **Timestamper** | 콘솔 로그 타임스탬프 |
| **Workspace Cleanup** | 빌드 후 workspace 자동 정리 |

### Ansible 플러그인 경로 설정

경로: Jenkins → Manage Jenkins → Tools → Ansible installations

| 항목 | 값 |
|------|----|
| Name | `ansible` |
| Path to ansible executables directory | `/opt/ansible-env/bin` |

> 이 경로는 03_agent-setup.md §5 에서 Agent 에 가상환경을 생성한 뒤 실제로 동작한다.
> 마스터에서는 경로만 미리 등록해두면 된다.

---

## 7. Credentials 등록

경로: Jenkins → Manage Jenkins → Credentials → System → Global credentials → Add Credentials

### gitlab-credentials

GitLab 레포지토리 checkout 에 사용하는 계정.

| 항목 | 값 |
|------|----|
| Kind | Username with password |
| Username | GitLab 계정 아이디 |
| Password | GitLab Access Token (api 권한) — 비밀번호가 아닌 토큰 입력 |
| ID | `gitlab-credentials` |

**GitLab Access Token 발급**
1. GitLab → Preferences → Access Tokens
2. Scopes: `api` 체크
3. Create → 발급된 토큰을 Password 에 입력

> vault-password Credentials 는 등록하지 않는다.
> vault 파일은 plain text 로 repo 에 포함되며 GitLab 접근 권한으로 보안을 통제한다.

---

## 8. RBAC 권한 설정

Role Strategy Plugin 으로 Job 단위 접근 권한을 제어한다.
Job 이름이 Pattern 과 일치하면 권한이 자동 적용되므로 신규 Job 추가 시 별도 권한 설정 불필요.

### Global Roles

경로: Jenkins → Manage Jenkins → Manage and Assign Roles → Manage Roles → Global roles

| Role | Overall 권한 | 설명 |
|------|-------------|------|
| `admin` | Administer | 시스템 전체 관리자 |
| `portal` | Read | 포털 서비스 계정 |
| `engineer` | Read | 인프라 엔지니어 |

### Item Roles

| Role | Pattern | 부여 권한 |
|------|---------|----------|
| `portal` | `server-exporter.*` | Job Build, Read |
| `engineer` | `infra-automation.*` | Job Build, Create, Configure, Read |

### 동작 확인

- `engineer` 계정 로그인 시 `server-exporter.*` Job 이 보이지 않아야 함
- `portal` 계정 로그인 시 `infra-automation.*` Job 이 보이지 않아야 함
