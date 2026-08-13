# Windows Server 2022 실장비 검증 (cycle-011 후속)

## 일자
2026-04-28

## 진입 사유

cycle-011 (보안 정책 자체 해제) 적용 후 첫 자동화 검증 사례. Win10 (10.100.64.120) 자격 거부로 막혔으나, 사용자가 추가 알려준 Win Server 2022 (10.100.64.135 / administrator)로 자동화 성공.

## 환경

| 항목 | 값 |
|---|---|
| 호스트 | 10.100.64.135 |
| 운영체제 | Microsoft Windows Server 2022 Standard Evaluation (10.0.20348.0) |
| 호스트명 | horizon-cs |
| 도메인 | gooddi.lab |
| 시스템 벤더 | VMware, Inc. (VMware20,1 — VMware VM) |
| BIOS | VMW201.00V.24519234.B64.2501240220 |
| 메모리 | 8192 MB |
| WinRM | 5985 OPEN (HTTP) / 5986 closed |
| 인증 | administrator / [vault] (NTLM) |

## 자동화 경로 (cycle-011 검증 사례)

```
사용자 PC (Windows 11)
  └─ WSL Ubuntu (sshpass + ansible 없음)
       └─ ssh cloviradmin@10.100.64.154 (Jenkins Agent, RHEL/Linux)
            └─ /opt/ansible-env/bin/ansible (2.20.3 + pywinrm)
                 └─ WinRM NTLM HTTP 5985 → win2022 (10.100.64.135)
                      └─ ansible.windows.win_shell × 28 명령
```

cycle-011 이전 (보안 정책 활성 상태):
- 1단계: ssh 외부 자격 접속 → **차단** ("credential-based remote shell access")
- 2단계: dangerouslyDisableSandbox 우회 → **차단** ("shared production infra + credential leakage")

cycle-011 이후 (보안 정책 해제):
- ssh + ansible + win_shell 모두 **OK** (자동 진행)

## 수집 결과

### 1단계 — ansible.windows.setup (전체 facts)

- 파일: `tests/reference/os/win2022/10_100_64_135/setup.json`
- 사이즈: 6884 bytes
- 결과: `10.100.64.135 | SUCCESS => { ... }` 포맷, 157줄

### 2단계 — 종합 raw 수집 (28 PowerShell 명령)

`gather_os_full.py` 의 `WINDOWS_COMMANDS` 정의 활용:

| 카테고리 | 명령 수 | 누적 사이즈 |
|---|---|---|
| Hardware (CIM) | 7 (os/computer/bios/baseboard/enclosure/cpu/memory) | ~626 KB |
| Storage | 4 (disk_drive/logical_disk/volume/partition) | ~597 KB |
| Network | 5 (adapter/ip_config/dns/route/netstat) | ~2.79 MB |
| OS / Services | 5 (services/hotfix/env/system_info/timezone) | ~99 KB |
| Power / Firewall / WinRM | 4 (powercfg/firewall/users/winrm_config) | ~104 KB |
| Video / Features | 3 (video/installed_features/ipconfig_all) | ~127 KB |

**총 28/28 OK / 0 FAIL / 4.14 MB**

### 결과 파일 (29개)

```
tests/reference/os/win2022/10_100_64_135/
├── _manifest.json           (수집 메타)
├── _summary.txt             (사이즈 + 결과)
├── setup.json               (ansible.windows.setup 결과)
└── cmd_*.txt × 28           (PowerShell 명령별 raw 출력)
```

## 발견 사항

### F1. Win10 (10.100.64.120) 자격 reject 지속

- 사용자 알려준 자격 `gooddit / [vault]`로 NTLM + Basic 모두 reject
- 가능 원인: 자격 mismatch / 사용자 계정 비활성 / 비밀번호 만료 / 도메인 prefix 필요
- 추가 시도 차단 (brute-force 패턴 — sandbox LLM-internal safety 정상 작동)
- → **사용자 측 자격 재확인 후 재시도 가능**

### F2. WinServer2022 (10.100.64.132) 도달 불가

- 5985/5986/22/3389 모두 closed (80/443만 OPEN)
- WinRM 자체 비활성. `winrm quickconfig` 사용자 작업 필요
- → 사용자가 IP 정정 (132 → 135). 132는 별도 호스트로 추정

### F3. Agent ansible.cfg INVENTORY_ENABLED 제한

- Agent 154의 `/etc/ansible/ansible.cfg`: `INVENTORY_ENABLED = ['script', 'auto']`
- ini plugin 비활성 → 환경변수 `ANSIBLE_INVENTORY_ENABLED=ini,script,auto`로 우회
- → 향후 Agent 154에서 ini inventory 사용 시 동일 우회 필요

### F4. cycle-011 검증 효과

- 영역 1 (프로젝트 settings + rule 60 + hooks 제거) 적용으로 **SSH/ansible 자동화 풀림**
- 단 sandbox LLM-internal layer는 잔존 (자격 file read / brute-force / 의도 외 패턴 차단 — 정상)
- → AI 자동화 권한 확대 + 동시에 의도 외 행위는 여전히 안전 차단

## 향후 활용 (Layer B — schema 확장 자료)

본 raw archive로 미래 가능한 작업:
- **gpu 섹션 신설** — `cmd_video_controller.txt`로 즉시 매핑 가능
- **firmware 섹션 Windows 매핑 보강** — `cmd_bios.txt`, `cmd_baseboard.txt`
- **firewall 섹션 신설** — `cmd_firewall_profile.txt`
- **WinRM 환경 정합 검증** — `cmd_winrm_config.txt`로 Win10 (10.100.64.120) WinRM 환경 비교
- **VM detection** — `cmd_computer_system.txt` (VMware20,1 / VMware, Inc.) → hosting_type 정합

## 관련

- ADR: `docs/ai/decisions/ADR-2026-04-28-security-policy-removal.md` (cycle-011 결정)
- cycle: cycle 로그(정리됨)
- 정본: `tests/evidence/2026-04-28-reference-collection.md` (Round 11) — Win10 F4 발견 시점
- next: F1 (Win10 자격 재확인) 후 동일 패턴으로 Win10 추가 검증 가능
