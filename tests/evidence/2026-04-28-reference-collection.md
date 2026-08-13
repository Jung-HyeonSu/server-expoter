# Reference Collection — 2026-04-28 (Round 11)

> 실장비 종합 raw 정보 수집. 향후 schema 추가 / 매핑 검증 / vendor 온보딩 / 회귀 비교 reference 자산.
>
> 본 수집은 `tests/baseline_v1/` (회귀 기준선)이나 `tests/fixtures/` (회귀 input)를 변경하지 않음. 별도 `tests/reference/` 디렉터리에 저장.

## 수집 환경

- **수집 host**: hshwang1994 PC (Windows + WSL Ubuntu)
- **수집 도구** (tests/reference/scripts/):
  - `crawl_redfish_full.py` — ServiceRoot부터 모든 link 재귀 (Python stdlib + PyYAML)
  - `gather_os_full.py` — paramiko SSH + ansible setup
  - `gather_esxi_full.py` — paramiko SSH + pyvmomi
  - `gather_agent_env.py` — paramiko SSH
- **자격**: `tests/reference/local/targets.yaml` (gitignored, 사용자 채팅 전달 자격)
- **Skip 처리**: SEL log / LC log / IML log / Sessions / Tasks / Subscriptions

## 수집 대상 / 결과 요약

### Redfish (BMC 11대 시도 — 9 OK / 2 환경 이슈 / 1 vendor 미상)

| Vendor | IP | 상태 | files | 비고 |
|---|---|---|---|---|
| Dell | 10.100.15.27 | OK | 2419 | iDRAC9, JsonSchemas 포함 / 596s |
| Dell | 10.100.15.28 | OK | 1606 | iDRAC9 / 430s |
| Dell | 10.100.15.31 | OK | 1625 | iDRAC9 / 429s |
| Dell | 10.100.15.33 | OK | 1600 | iDRAC9 (10.100.64.96 OS의 BMC) / 419s |
| Dell | 10.100.15.34 | OK | 1737 | iDRAC9 / 467s |
| HPE | 10.50.11.231 | OK | 2531 | iLO5 (ProLiant DL380 Gen11), IML+Event+SL log 포함 |
| Lenovo | 10.50.11.232 | OK | 2807 | XCC |
| Cisco | 10.100.15.1 | **FAIL** | 3 | F3 — HTTP 503 (CIMC 서비스 다운, BMC 재기동 필요) |
| Cisco | 10.100.15.2 | OK | 760 | TA-UNODE-G1 (CIMC), JsonSchemas+Logs 포함 / 889s (BMC ~2초/req) |
| Cisco | 10.100.15.3 | **FAIL** | — | F3 — connect timeout (BMC 도달 불가) |

### OS (7대 시도)

| Distro | IP | 상태 | 명령 | 디스크 |
|---|---|---|---|---|
| RHEL 8.10 | 10.100.64.161 | OK | 105 + ansible_setup | 911K |
| RHEL 9.2 | 10.100.64.163 | OK | 106 + ansible_setup | 848K |
| RHEL 9.6 | 10.100.64.165 | OK | 106 + ansible_setup | 856K |
| Rocky 9.6 | 10.100.64.169 | OK | 106 + ansible_setup | 818K |
| Ubuntu 24.04 | 10.100.64.167 | OK | 106 + ansible_setup | 950K |
| Windows 10 | 10.100.64.120 | **FAIL** | 0 | 0 | F4 — WinRM 환경 |
| RHEL bare-metal | 10.100.64.96 | OK | 106 + ansible_setup | 1.5MB |

### ESXi (3대)

| IP | SSH | vSphere API | 명령 | 디스크 |
|---|---|---|---|---|
| 10.100.64.1 | FAIL | OK | 1 | 2.2MB |
| 10.100.64.2 | OK | OK | 53 + pyvmomi | 4.4MB |
| 10.100.64.3 | FAIL | OK | 1 | 3.8MB |

### Jenkins Agent / Master (4대)

| Role | IP | 명령 | 디스크 | elapsed |
|---|---|---|---|---|
| Agent | 10.100.64.154 | 39 | 98K | 33s |
| Agent | 10.100.64.155 | 39 | 95K | 26s |
| Master | 10.100.64.152 | 39 | 101K | 145s |
| Master | 10.100.64.153 | 39 | 26K → 149K | 142s |

## 사고 / 발견

### F1. Dell BMC user 정정

- **발견**: targets.yaml 초안에 `user: admin` (사용자 채팅 전달분 그대로)
- **실측**: 10.100.15.27/28/31/33/34 모두 `admin` HTTP 401, `root` HTTP 200
- **사용자 확인**: 2026-04-28 채팅 — "10.100.15.27 (dell) (root / __REDACTED__) ... 이다. 맞다."
- **수정**: targets.yaml의 Dell user 모두 `root`로 정정
- **rule**: 12 R1 (vendor 경계) — 예외 아님, 단순 자격 정정

### F3. Cisco 10.100.15.1 / 15.3 도달 불가

- **발견**: 15.1 HTTP 503, 15.3 connect timeout (15초)
- **15.2는 정상**: TA-UNODE-G1 (Cisco Systems Inc) — admin/__REDACTED__ OK
- **현재**: 15.2만 수집, 15.1/15.3 skip
- **사용자 확인 필요**: 15.1/15.3 가동 상태

### F4. Win10 WinRM 수집 불가

- **발견**:
  - Windows 측: HTTPS 5986 connection refused, HTTP 5985 자격 reject (Basic 미허용 또는 자격 오류)
  - WSL 측: pywinrm 0.4.3 → 0.5.0 업그레이드 + pyspnego 설치 후에도 NTLM이 OpenSSL 3.0의 MD4 미지원으로 실패
- **현재**: Win10 수집 0
- **follow-up**: task #10
  - **옵션 A**: Windows 측 `winrm quickconfig -transport:https` + Basic 허용 + WSL Python 측 ntlm 라이브러리 변경
  - **옵션 B**: ansible의 `ansible.windows.setup` 모듈 사용 (다른 라이브러리 경로)
  - **옵션 C**: PowerShell 직접 실행 (장비 가서)
- **rule**: 96 R2 — 외부 환경 의존, 사용자 결정

### F5. ESXi 10.100.64.1 / .3 SSH 비활성

- **발견**: 22번 포트 connection refused
- **수집된 데이터**: pyvmomi vSphere API 통한 host object dump만 (esxcli 53종 미수집)
- **해결**: vSphere Web Client → Host → Configure → Services → SSH → Start. 완료 후 `--skip-existing`로 재실행
- **현재**: pyvmomi만으로도 핵심 정보 (hardware/network/storage/service) 확보 — 부분 수집

### F6. Master 10.100.64.153 sudo 명령 timeout

- **현상**: 첫 sudo 명령 (`jenkins_status`)에서 ~120초 대기 후 진행
- **원인 추정**: sudo 설정 또는 sudo prompt 처리 issue
- **결과**: 모든 39 명령 완료 (각 timeout=120s 적용으로 자동 진행)
- **개선**: `tests/reference/scripts/gather_agent_env.py` `requires_root` 명령들의 sudo 처리 검토

## 디렉터리 트리

```
tests/reference/
├── README.md                    ← 전체 사용법 / 보안 / 재실행
├── INDEX.md                     ← 카탈로그 (실측 갱신)
├── redfish/
│   ├── README.md
│   └── <vendor>/<ip>/{_manifest, _summary, *.json}
├── os/
│   ├── README.md
│   └── <distro>/<ip>/{_manifest, _summary, ansible_setup, cmd_*}
├── esxi/
│   ├── README.md
│   └── <ip>/{_manifest, pyvmomi_host_dump, esxcli_*}
├── agent/
│   ├── README.md
│   ├── agent/<ip>/{_manifest, cmd_*}
│   └── jenkins_master/<ip>/{_manifest, cmd_*}
├── scripts/
│   ├── crawl_redfish_full.py
│   ├── gather_os_full.py
│   ├── gather_esxi_full.py
│   └── gather_agent_env.py
└── local/                       ← .gitignore
    ├── targets.yaml             ← 자격 (commit 금지)
    └── targets.yaml.sample      ← 빈 password
```

## 누적 통계 (수집 완료 2026-04-28 17:15)

- **총 파일 수: 15964** (commit 대상; tests/reference/local/ 제외)
- **총 디스크 사용: 126MB**
  - redfish: 108MB (9 vendor 수집 OK)
  - os: 5.8MB (6 distro)
  - esxi: 11MB (3 host)
  - agent: 399K (4 host)

## 활용 시나리오

1. **새 vendor 온보딩**: 그 vendor의 redfish endpoint list (`_summary.txt`)로 OEM path 파악
2. **schema 필드 추가**: cross-vendor 비교 (`redfish/dell/.../*_oem_*` vs `redfish/hpe/.../*_oem_*`)
3. **OS 매핑 검증**: `cmd_dmidecode_*.txt` ↔ ansible_setup ↔ field_dictionary 정합 (rule 13 R1)
4. **Bare-metal vs VM 차이 분석**: 10.100.64.96 (RHEL bare-metal) vs 10.100.64.161 (RHEL VM) cmd_virt_what / dmidecode_system 비교
5. **회귀 비교**: 펌웨어 / OS 업그레이드 후 동일 명령 재수집 → diff
6. **REQUIREMENTS.md 검증**: agent 디렉터리 ansible/python/collection 버전 ↔ 문서 명시

## 후속 작업

| # | 작업 | 우선순위 |
|---|---|---|
| F3 | Cisco 10.100.15.1/15.3 가동 상태 사용자 확인 | LOW |
| F4 | Win10 WinRM 환경 정비 (task #10) | MED |
| F5 | ESXi .1/.3 SSH 활성화 후 재수집 | LOW |
| F6 | gather_agent_env.py sudo 처리 검토 | LOW |
| - | BMC 11대 완료 후 INDEX 수치 갱신 | (BMC 완료 후) |

## rule / 정본 참조

- rule 13 (output-schema-fields), 21 (output-baseline-fixtures), 96 (external-contract-integrity), 70 (docs-and-evidence-policy)
- 정본 문서: `docs/reference/live-validation.md`, `docs/reference/decision-log.md`
- skill: `update-vendor-baseline`, `probe-redfish-vendor`, `add-new-vendor`
