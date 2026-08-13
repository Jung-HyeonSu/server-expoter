# PyWinRM — Python WinRM client

> Source: https://github.com/diyan/pywinrm
> Fetched: 2026-04-27
> Version (server-exporter 검증 기준): pywinrm 0.5.0

server-exporter os-gather Windows Play3에서 ansible.windows의 backend로 사용.

## Connection 패턴

### Session API (high-level)

```python
import winrm
s = winrm.Session('windows-host', auth=('user', 'password'),
                  transport='ntlm',
                  server_cert_validation='ignore')
r = s.run_cmd('ipconfig', ['/all'])
print(r.std_out)
```

### Protocol API (low-level)

```python
from winrm.protocol import Protocol
p = Protocol(
    endpoint='https://host:5986/wsman',
    transport='ntlm',
    username='user',
    password='secret',
    server_cert_validation='ignore'
)
shell_id = p.open_shell()
cid = p.run_command(shell_id, 'cmd', ['/c', 'ver'])
out, err, status = p.get_command_output(shell_id, cid)
p.cleanup_command(shell_id, cid)
p.close_shell(shell_id)
```

## 인증

| 방법 | 용도 |
|---|---|
| Basic | local account, base64 (HTTPS 권장) |
| NTLM | local + 도메인. server-exporter 기본 |
| Kerberos | 도메인 환경 (kinit 필요) |
| CredSSP | double-hop (`requests-credssp`, HTTPS 필수) |
| Certificate | 인증서 → local account 매핑 |

server-exporter Agent는 일반적으로 **NTLM** 사용.

## Endpoint

| Port | 용도 |
|---|---|
| 5985 | HTTP (winrm/wsman) |
| 5986 | HTTPS (winrm/wsman) |

WinRM은 기본적으로 unencrypted 거부 → HTTPS 또는 message encryption (NTLM/Kerberos/CredSSP) 필수.

`message_encryption`:
- `auto` (default) — HTTPS 아니고 auth가 지원하면 암호화
- `never` — 비활성
- `always` — 강제

## PowerShell vs cmd

```python
# cmd
r = s.run_cmd('hostname')

# PowerShell (UTF-16 LE + base64 자동 인코딩)
r = s.run_ps('Get-WmiObject Win32_BIOS | ConvertTo-Json')
```

CLIXML 에러 형식 → 사람이 읽기 쉬운 텍스트로 자동 변환.

## 시스템 요구사항

- Python 3.8+
- pywinrm 0.5.0
- (Kerberos) gcc, libkrb5-dev, requests-kerberos
- (CredSSP) requests-credssp

## 원격 호스트 설정

```powershell
# 기본 HTTP 활성
winrm quickconfig

# 인증 활성
winrm set winrm/config/service/auth '@{Basic="true"}'
winrm set winrm/config/service/auth '@{Negotiate="true"}'  # NTLM

# CredSSP (필요 시)
Enable-WSManCredSSP -Role Server -Force
```

## status code

- 0 = 성공
- 그 외 = 실패 (std_err 확인)

## Best Practices for server-exporter

1. **HTTPS 권장**: production은 5986 + 정식 cert 또는 self-signed + ignore
2. **NTLM transport**: `ansible_winrm_transport: ntlm`
3. **자격증명 vault**: `vault/<loc>/os/windows.yml`의 `vault_windows_user/password`
4. **timeout 명시**: `read_timeout_sec` / `operation_timeout_sec` (Ansible inventory 변수)
5. **CredSSP는 신중**: double-hop 필요 시만. 보안 영향 큼

## 적용 rule

- rule 10 (gather-core)
- rule 27 (precheck-guard-first / WinRM 4단계)
- rule 30 (integration)
- (cycle-011: rule 60 해제 — NTLM 전송 / cert 검증은 운영자 결정)
