# 03. Jenkins 마스터 설치

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
