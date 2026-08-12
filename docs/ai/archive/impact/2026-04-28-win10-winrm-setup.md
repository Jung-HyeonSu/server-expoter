# Win10 WinRM 수집 환경 follow-up (task #10)

> 일자: 2026-04-28
> task: #10 (`[follow-up] Windows 10 WinRM 수집 환경 정비`)
> 근본 원인: Round 11 reference 수집 시 10.100.64.120 (win10) WinRM 접속 실패

## 발견 (Round 11)

| 측면 | 상태 |
|---|---|
| Windows 측 HTTPS WinRM (port 5986) | **connection refused** (listener 미설정) |
| Windows 측 HTTP WinRM (port 5985) | **자격 reject** (Basic 미허용 또는 자격 오류) |
| WSL Python 측 NTLM 처리 | **`UnsupportedDigestmodError: md4`** (OpenSSL 3.0 + `requests_ntlm` 1.3.0의 구 hashlib 의존) |

**증상**: 3 layer 모두 실패. 어느 한 곳만 고쳐도 안 됨.

## 옵션 매트릭스

### 옵션 A: Windows 측 정비 (권장)

장비 측에서 WinRM 활성화. Jenkins agent (검증 기준 154/155)에서는 ansible.windows 통한 수집이 정상 작동할 것으로 기대.

**Windows 측 PowerShell 명령** (관리자 권한):

```powershell
# 1. WinRM 빠른 설정 (HTTP 5985 활성화)
winrm quickconfig -force

# 2. HTTPS listener 추가 (자체 서명 인증서)
$cert = New-SelfSignedCertificate -DnsName "10.100.64.120" -CertStoreLocation Cert:\LocalMachine\My
winrm create winrm/config/Listener?Address=*+Transport=HTTPS "@{Hostname=`"10.100.64.120`"; CertificateThumbprint=`"$($cert.Thumbprint)`"}"

# 3. Basic 인증 허용 (개발 환경 한정 — 운영은 NTLM/Kerberos 권장)
winrm set winrm/config/service/auth '@{Basic="true"}'
winrm set winrm/config/service '@{AllowUnencrypted="true"}'

# 4. 방화벽
New-NetFirewallRule -DisplayName "WinRM HTTP-In" -Direction Inbound -LocalPort 5985 -Protocol TCP -Action Allow
New-NetFirewallRule -DisplayName "WinRM HTTPS-In" -Direction Inbound -LocalPort 5986 -Protocol TCP -Action Allow

# 5. 검증
winrm enumerate winrm/config/listener
winrm get winrm/config/service/auth
```

검증:
```bash
# WSL 또는 Jenkins agent에서
curl -k https://10.100.64.120:5986/wsman -X POST -d '<test/>' -H "Content-Type: application/soap+xml"
# 응답: HTTP 401 Unauthorized + WWW-Authenticate header 가 나오면 listener 동작 OK
```

### 옵션 B: WSL Python 환경 정비 (gather_os_full.py에서 직접 수집 가능하도록)

WSL의 NTLM 라이브러리 교체. `requests_ntlm`은 구식 → `pyspnego`/`requests-spnego` 또는 ansible의 ansible.windows 통한 우회.

**WSL 명령**:

```bash
# OpenSSL legacy provider 활성화 (md4 임시 복원 — 비권장, 보안 취약)
# ~/.wslconfig 또는 환경에 OPENSSL_CONF 설정 (legacy section 명시)

# 또는 pywinrm + spnego 우선 인증으로 우회
pip install --upgrade pywinrm pyspnego
# pywinrm 0.5.0 + auth='ntlm'은 여전히 requests_ntlm을 사용. spnego transport 직접 호출 필요.
```

**더 권장**: gather_os_full.py를 ansible.windows.setup 호출로 변경 (ansible-core가 NTLM 처리에 spnego 사용 — md4 의존 우회). 단 Win10에 미리 ssh / WinRM open 필요.

### 옵션 C: 검증 기준 Agent (10.100.64.154/155)에서 수집

Jenkins agent는 ansible 13.4.0 + pywinrm 0.5.0 + 정상 PATH 환경. 거기서 본 가이드를 활용해 수집 가능. WSL 측 환경 부담 없음.

```bash
# 154 SSH로 접속
ssh cloviradmin@10.100.64.154

# /opt/ansible-env activate
source /opt/ansible-env/bin/activate

# inventory 작성 (또는 기존 사용)
cat > /tmp/win.ini << 'EOF'
[win]
10.100.64.120 ansible_user=administrator ansible_password=__REDACTED__ ansible_connection=winrm ansible_winrm_server_cert_validation=ignore ansible_winrm_transport=ntlm
EOF

# setup module 통한 수집
ansible -i /tmp/win.ini win -m ansible.windows.setup --tree /tmp/win10_facts/

# 결과를 reference로 이동
scp /tmp/win10_facts/* hshwa@<this-pc>:/c/github/server-exporter/tests/reference/os/windows10/10_100_64_120/
```

### 추천 조합

1. **즉시**: 옵션 C (검증 기준 Agent에서 수집) — 환경 변경 없이 데이터 확보
2. **운영 준비**: 옵션 A (Windows 측 WinRM HTTPS 활성화) — 운영 정합
3. **별도 PR**: 옵션 B (WSL 환경 정비) — 우선순위 LOW (필요 시)

## 의사결정 (사용자 영역)

이 follow-up 작업은 다음 셋 중 하나 결정 필요:

- (1) 옵션 A 진행 (Windows 측 작업) → Win10 측 PowerShell 1회 실행
- (2) 옵션 C 진행 (Agent에서 수집) → 별도 세션에서 ansible 수집 + scp
- (3) 보류 (Round 12 또는 운영 안정화 후)

## 관련

- task: #10 ([follow-up] Windows 10 WinRM 수집 환경 정비)
- evidence: `tests/evidence/2026-04-28-reference-collection.md` F4
- skill: `gather-os-full.py` (WinRM 호출 부분)
- rule: 96 R2 (외부 시스템 디버깅 시 사용자 질의 우선)
