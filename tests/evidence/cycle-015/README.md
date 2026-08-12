# cycle-015 evidence — 실장비 lab 권한 확장 + Browser E2E + 자율 매트릭스

## 일자
2026-04-29

## 작업 범위

cycle-014 (4 vendor BMC code path + Jinja2 fix) 직후, 사용자가 lab 전체 (23 호스트 — 정정 후) 권한 + Browser E2E 인프라 명시 결정. cycle-015는 lab 권한 정착 + 자율 검증 매트릭스 일괄 실행.

## evidence 파일

| 파일 | 작업 | 결과 |
|---|---|---|
| `connectivity-2026-04-29.md` | Phase C — 21 호스트 ICMP/TCP protocol | 21/21 PASS + DRIFT-011 검출 |
| `bmc-auth-probe-2026-04-29.{py,json}` | OPS-3 BMC primary auth (lab credentials 검증) | 7/9 PASS — Dell × 5 + HPE + Lenovo. Cisco 1, 3 일시 장애 |
| `linux-probe-2026-04-29.{py,json}` | AI-13 Linux raw fallback (rule 10 R4 실증) | 6/6 SSH PASS. **RHEL 8.10 (Py 3.6.8) → python_incompatible** = raw fallback trigger 실증 |
| `winrm-probe-2026-04-29.{py,json}` | OPS-10 Win 2022 + WinRM | PASS — Win Server 2022 (10.100.64.135), PS 5.1, 8GB, Xeon Silver 4510 |
| `dell-round11-endpoint-coverage.{py,json}` | AI-12 Dell × 5 Round 11 baseline 계획 | 5/5 BMC endpoint 매트릭스 (Systems / Storage / NIC / FW inventory / Accounts) |

## 결정 사항 (사용자 명시)

### 권한 부여 (cycle-015 진입)

> "이 프로젝트는 ai에게 모든 권한을 준다 ... 실장비 권한도 하네스에게 주겠다 어짜피 테스트서버이다"
> "아래와같은 서버에도 모두 접속할수있도록한다 e2e 테스트도 크롬플러그인을 사용하던지 모두 수행할 수 있도록 해라"

### 호스트 정정 (cycle-015 진행 중)

1. **제거 (사내 부재)**:
   - 10.100.15.32 (사용자 라벨 "dell GPU" → 실 응답 AMI Redfish Server) — DRIFT-011 resolved
   - 10.100.15.2 (사용자 라벨 "cisco" → 실 응답 TA-UNODE-G1) — DRIFT-011 resolved
   - 10.100.64.120 (Windows 10) — 사내 부재 확인
2. **IP 정정**: Windows Server 2022 = 10.100.64.132 → **10.100.64.135**
3. **firewall 해제**: 10.100.64.135 (cycle-015 후 사용자 직접)
4. **Jenkinsfile_grafana 제거**: Grafana 적재 미사용 결정

### 호스트 카운트 (정정 후 23대)

- Jenkins master 2 + agent 2 = 4
- Linux VM 5 + baremetal 1 = 6
- Windows VM 1 (Win Server 2022)
- BMC: Dell 5 + HPE 1 + Lenovo 1 + Cisco 2 = 9
- ESXi 3
- 합계: **23대**

## 핵심 발견

### [PASS] OPS-3 진척 — 7/9 BMC primary auth 성공

cycle-014에서 4 vendor BMC 모두 401이었음. cycle-015 lab credentials의 password가 실 BMC와 sync 됐음:

| Vendor | IP | ServiceRoot | Systems | Managers | Note |
|---|---|---|---|---|---|
| Dell | 10.100.15.27 | 200 | 200 | 200 | iDRAC9 (__REDACTED__) |
| Dell | 10.100.15.28 | 200 | 200 | 200 | iDRAC9 |
| Dell | 10.100.15.31 | 200 | 200 | 200 | iDRAC9 |
| Dell | 10.100.15.33 | 200 | 200 | 200 | iDRAC9 (OS=10.100.64.96) |
| Dell | 10.100.15.34 | 200 | 200 | 200 | iDRAC9 |
| HPE | 10.50.11.231 | 200 | 200 | 200 | ProLiant DL380 Gen11 (__REDACTED__) |
| Lenovo | 10.50.11.232 | 200 | 200 | 200 | XCC (__REDACTED__) |
| Cisco | 10.100.15.1 | 503 | 502 | 502 | Bad Gateway — OPS-11 |
| Cisco | 10.100.15.3 | -1 | -1 | -1 | URLError — OPS-11 |

**의미**: 운영팀 password 회전 없이도 cycle-015 lab credentials를 vault primary로 흡수 가능.

### [PASS] rule 10 R4 (Linux 2-tier) 실증

| Host | Distro | Python | Mode |
|---|---|---|---|
| 10.100.64.161 | rhel810 | 3.6.8 | **python_incompatible** ← raw fallback trigger |
| 10.100.64.163 | rhel920 | 3.9.1 | python_ok |
| 10.100.64.165 | rhel960 | 3.9.2 | python_ok |
| 10.100.64.167 | ubuntu2404 | 3.12 | python_ok |
| 10.100.64.169 | rocky960 | 3.9.2 | python_ok |
| 10.100.64.96 | linux baremetal | 3.12 | python_ok |

raw fallback 의존 프리미티브 모두 가용:
- `/proc/meminfo MemTotal`: 6/6 응답
- `dmidecode`: 6/6 가용
- `getenforce` (RHEL/Rocky): enforcing 4/4

### [PASS] Browser E2E 활성

- `test_master_dashboard_reachable[chromium]` PASS (마스터 도달)
- `test_master_login_then_dashboard[chromium]` PASS (cloviradmin login + dashboard 진입)

### [PASS] WinRM Win Server 2022 (정정된 IP)

- 10.100.64.135 (정정 후) WinRM 5985 OPEN
- administrator/__REDACTED__ NTLM 인증 PASS
- Get-CimInstance / Get-NetAdapter / $PSVersionTable 모두 응답
- OS: Microsoft Windows Server 2022 Standard Evaluation build 20348
- PS: 5.1.20348.558
- CPU: Intel Xeon Silver 4510 (4 cores)
- Mem: 8 GB

## 후속 (closed)

| OPS / AI | 상태 |
|---|---|
| OPS-10 Win 2022 firewall | resolved (사용자 직접 + IP 정정) |
| OPS-12 Dell 32 라벨 정정 | resolved (호스트 제거) |
| OPS-13 Cisco 2 식별 | resolved (호스트 제거) |
| OPS-15 Grafana endpoint | closed (Jenkinsfile_grafana 제거) |
| AI-13 Linux raw fallback Round | DONE — `linux-probe-2026-04-29.json` |
| AI-14 Browser E2E login 활성 | DONE — `test_master_login_then_dashboard` |
| AI-15 deep_probe AMI/TA-UNODE | obviated (호스트 제거) |

## 후속 (open)

| OPS / AI | 상태 | 차단 사유 |
|---|---|---|
| OPS-3 vault password 회전 | **partially possible** — Dell × 5 + HPE + Lenovo는 lab credentials를 vault primary로 흡수 가능 | 운영팀 결정 (vault re-encrypt 시점) |
| OPS-11 Cisco BMC 1, 3 가용성 | open | 503/timeout — 다음 일과시간 / lab 운영자 |
| OPS-14 Jenkins 사용자 정책 | partially obviated — cloviradmin이 Jenkins 사용자로도 동작 (E2E PASS) | 운영 결정 (API token 정책) |
| OPS-9 repo private 전환 자격증명 정책 | open | private 전환 시점 |
| AI-12 Dell × 5 Round 11 baseline 갱신 | endpoint coverage 통과 → baseline JSON 생성 가능 | 다음 cycle (cycle-016) |

## 정본

- `vault/.lab-credentials.yml` (gitignored) — 정정된 host 매트릭스
- `inventory/lab/{os-linux,os-windows,redfish,esxi,jenkins}.json` (gitignored)
- `docs/ai/catalogs/LAB_INVENTORY.md` — sanitized 23대 토폴로지
- `docs/ai/decisions/ADR-2026-04-29-lab-access-grant.md` — governance trace
- `docs/ai/harness/cycle-015.md` — cycle log
