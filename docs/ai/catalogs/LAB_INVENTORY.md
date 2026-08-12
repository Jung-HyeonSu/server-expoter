# LAB_INVENTORY — 실장비 lab 토폴로지

> 정본: `inventory/lab/*.json` (gitignored — 실 IP) + `vault/.lab-credentials.yml` (gitignored — 자격증명).
> 본 catalog는 sanitized 메타. 작성: 2026-04-29 cycle-015.


> **2026-08-12 (git Location 실장비 검증) 정정** — 정본:
> `tests/evidence/2026-08-12-git-location-live-verification.md`
> - **10.50.11.231 (HPE iLO6) 는 도달 가능하다.** 종전 "TCP 443 timeout / BMC-side 미응답"
>   기록은 stale. 실측 TCP 443 OPEN + Redfish 200 + 수집 success(9/11).
>   ProLiant DL380 Gen11 / iLO 6 v1.73 / hostname `test0004.hynix.com`.
> - **10.100.15.2 (Cisco CIMC) 는 존재한다.** `TA-UNODE-G1` / CIMC `4.1(2g)` /
>   hostname `C220-FCH2116V1V0`. cycle-015 의 "사내 부재" 기록은 stale.
> - **10.100.15.34 는 iDRAC9 다** (16G Monolithic / FW 7.10.70.00 / Redfish 1.20.1).
>   adapter 는 `redfish_dell_idrac10` 을 고르지만 장비는 iDRAC10 이 아니다.
> - 검증에 사용한 git Location 대상: Linux 10.100.64.161 / Windows 10.100.64.120 /
>   ESXi 10.100.64.1 / Lenovo 10.50.11.232 / HPE 10.50.11.231 / Cisco 10.100.15.2 /
>   Dell 10.100.15.34. 통제 노드(Windows)와 WSL 양쪽에서 3개 대역 전부 도달 확인.

## 1. 권한 정책

사용자 명시 결정 (2026-04-29 채팅):
> "이 프로젝트는 ai에게 모든 권한을 준다 ... 실장비 권한도 하네스에게 주겠다 어짜피 테스트서버이다"

→ AI는 본 lab 모든 호스트에 자율 접속 가능 (cycle-011 보안 정책 해제 확장).

관련 ADR:
- `ADR-2026-04-28-security-policy-removal.md` — 보안 정책 자체 해제
- `ADR-2026-04-29-lab-access-grant.md` — 실장비 접근 권한 확장 (cycle-015, 본 작업)

## 2. 호스트 카운트 (총 23대 — cycle-015 정정 후)

| 그룹 | 카운트 | 채널 | 검증 가치 |
|---|---|---|---|
| Jenkins master | 2 | (관리) | 파이프라인 트리거 / Web UI E2E |
| Jenkins agent (Ansible) | 2 | (관리) | 본 수집 실행 환경 (Python 3.12 / ansible-core 2.20) |
| Linux VM | 5 | os-gather | RHEL 8.10 / 9.2 / 9.6 / Rocky 9.6 / Ubuntu 24.04 |
| Linux baremetal | 1 | os-gather | OS↔BMC correlation 검증용 (Dell BMC와 매칭) |
| Windows VM | 1 | os-gather | Win Server 2022 (10.100.64.135 — cycle-015 IP 정정 + Win10 제거) |
| Dell BMC (iDRAC) | 5 | redfish-gather | 10.100.15.34 = OS 10.100.64.96 baremetal 매칭 (cycle-016 Phase L 정정) |
| HPE BMC (iLO) | 1 | redfish-gather | ProLiant DL380 Gen11 / iLO6 |
| Lenovo BMC (XCC) | 1 | redfish-gather | XCC 1.15 |
| Cisco BMC (CIMC) | 2 | redfish-gather | 10.100.15.2 제거 — cycle-015 (사내 부재) |
| ESXi host | 3 | esxi-gather | community.vmware 6.2.0 검증 |

> **cycle-015 변경**: 사용자 명시 결정으로 다음 정정
> - 제거 (사내 부재): 10.100.15.32 (Dell GPU — AMI Redfish), 10.100.64.120 (Windows 10)
> - IP 정정: Windows Server 2022 = 10.100.64.132 → **10.100.64.135**
> - firewall 해제: 10.100.64.135 (cycle-015 후 사용자 직접 작업)
>
> **cycle-016 Phase K 정정 (2026-04-29 사용자 직접 정정)**: cycle-015 의 Cisco IP 매핑 오류 정정
> - 제거 (사내 부재 / non-Redfish): **10.100.15.1** (lab 부재 또는 Redfish 미지원), **10.100.15.3** (ping fail 부재)
> - 추가 (실 작동 BMC): **10.100.15.2** (Cisco TA-UNODE-G1, admin/Goodmit1!) — 빌드 #91 SUCCESS 검증 / DDR4 64GB×16=1TB / SSD SATA 18.2TB

> **2026-08-12 실측 정정 (Location Vault Pilot — `tests/evidence/2026-08-12-location-vault-jenkins-pilot.md`)**
> - **10.100.64.135 는 Windows 가 아니다.** 실측 결과 RHEL 계열 Linux
>   (`auto-install-test02.gooddi.lab`, Python 3.9.21, adapter `os_linux_rhel`). 위 cycle-015
>   기록("Windows Server 2022 = 10.100.64.135")은 그 사이 환경이 바뀌어 stale.
> - **10.100.64.120 은 살아 있다.** cycle-015 가 "사내 부재" 로 제거했지만 Windows 수집이
>   정상 동작한다(7 sections, adapter `os_windows_*`). 2026-06-22 evidence 와도 일치하므로
>   **현재 유일하게 확인된 Windows 대상**이다.
> - **10.50.11.231 (HPE iLO6) 미응답** — TCP 443 timeout. 같은 대역 10.50.11.232(Lenovo XCC)
>   는 정상이므로 라우팅이 아니라 BMC 자체 문제. Round 12 는 이 장비 복구 후에나 가능.
> - **Jenkins agent 는 1대다** — `jenkins-agent-ops` 한 노드가 `ich/chj/yi/git` 4 label 을
>   모두 갖는다. Location 별 물리 분리는 현재 없다.

## 3. 네트워크 zone

| Zone | CIDR | 용도 |
|---|---|---|
| Service / OS | 10.100.64.0/24 | Jenkins master/agent + OS gather VM + ESXi |
| Dell + Cisco BMC | 10.100.15.0/24 | iDRAC + CIMC |
| HPE + Lenovo BMC | 10.50.11.0/24 | iLO + XCC |

→ Jenkins agent (10.100.64.0/24)에서 모든 zone 도달 가능 (production routing).

## 4. 특이 호스트 (검증 우선순위)

| 호스트 그룹 | 특이사항 | 검증 가치 |
|---|---|---|
| Linux RHEL 8.10 | Python 3.6 환경 | rule 10 R4 (raw fallback) 실증 |
| Linux baremetal | Dell BMC와 같은 머신 (10.100.64.96 ↔ 10.100.15.33) | OS data ↔ BMC data correlation envelope 검증 |
| Win Server 2022 | administrator account, firewall 해제됨 (cycle-015) | WinRM 5985 / domain-less |
| Cisco BMC × 2 | UCS 시리즈 | 동일 vendor 다수 — adapter score tie-break 검증 |

## 5. 검증 라운드 매핑

| Round | 영역 | 우선순위 | 비고 |
|---|---|---|---|
| Round 11 (cycle-015 endpoint 검증 PASS) | Dell × 5 baseline 갱신 | HIGH | 모두 PowerEdge R760 BIOS 2.3.5 / Xeon Silver 4510. 256GB×4 + 128GB×1 |
| Round 12 (예정) | HPE 231 / Lenovo 232 baseline | MED | cycle-015 auth PASS. ProLiant DL380 Gen11 + XCC |
| Round 13 (예정) | Cisco × 2 baseline (1, 3) | MED | OPS-11 가용성 회복 후 |
| Round 14 (cycle-015 raw 실증 PASS) | Linux raw fallback | DONE | RHEL 8.10 Py 3.6.8 = python_incompatible 분기 검증됨 |
| Round 15 (cycle-015 WinRM PASS) | Win Server 2022 | DONE (auth) | OS Build 20348, PS 5.1, Xeon Silver 4510 |
| Round 16 (예정) | ESXi 회귀 | LOW | 3대로 community.vmware 안정성 |
| Browser E2E (cycle-015 활성) | Jenkins UI login | DONE | cloviradmin 인증 PASS (test_master_login_then_dashboard) |
| Browser E2E (예정) | BMC Web UI (iDRAC/iLO/XCC/CIMC) | LOW | 후속 cycle |
| HPE CSUS 3200 lab (예정) | RMC 멀티-노드 (cycle 2026-05-12 hpe-csus-rmc-multi-node) | MED | 사이트 fixture 캡처 후 (NEXT_ACTIONS C1~C8) — 합성 fixture `tests/fixtures/redfish/hpe_csus_3200/` 정정 의무 |
| HPE Superdome Flex lab (예정) | RMC + iLO5 dual-manager | MED | 사이트 fixture 캡처 후 — `tests/fixtures/redfish/hpe_superdome_flex/` multi-partition 보강 |

## 6. 자격증명 정책

- **현재** (2026-04-29 ~ private 전환 전): `vault/.lab-credentials.yml` 평문 로컬 + gitignored
- **private 전환 후 옵션**:
  - (A) ansible-vault encrypt → 기존 `vault/redfish/{vendor}.yml` 등으로 흡수
  - (B) gitignored 평문 영구 유지 (lab 운영 단순)
- **결정 시기**: 사용자가 repo private 전환 시점에 (NEXT_ACTIONS 추적)

## 7. 참고 파일

- `inventory/lab/os-linux.json` — 6 호스트 (`service_ip`)
- `inventory/lab/os-windows.json` — 2 호스트 (`service_ip`)
- `inventory/lab/redfish.json` — 11 호스트 (`bmc_ip`)
- `inventory/lab/esxi.json` — 3 호스트 (`service_ip`)
- `inventory/lab/jenkins.json` — 4 호스트 (`service_ip`, 참고)
- `vault/.lab-credentials.yml` — 자격증명 그룹 5종

## 8. 갱신 trigger

다음 시 본 catalog 갱신:
- 새 호스트 추가/제거
- vendor 추가
- Round 검증 완료 후 row 5 (검증 라운드 매핑) 진행률 갱신
- repo visibility 전환 후 row 6 (자격증명 정책) 결정 기록
