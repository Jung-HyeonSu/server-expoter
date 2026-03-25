# REQUIREMENTS — clovirone-portal Gather Pipeline

gather 플레이북 실행을 위한 **대상 서버 / Agent / 포털** 각각의 최소 요구사항이다.
여기에 명시된 버전보다 낮으면 수집이 실패하거나 일부 필드가 `null` 로 반환된다.

---

## 1. os-gather (Linux / Windows)

### 1-1. Linux 대상 서버

| 항목 | 최소 요구사항 | 미충족 시 동작 |
|------|-------------|--------------|
| **SSH 포트** | 22 오픈 | 연결 실패 → `status: failed` |
| **Python** | **Python 3.7 이상** (타겟 서버 요구사항 — Ansible 2.20+ 모듈 실행에 필요. RHEL 8 기본 Python 3.6은 미지원 → `python39` 패키지 설치 필요) | 모듈 실행 실패 → 수집 불가 |
| **배포판** | RHEL/CentOS 6+, Ubuntu 14.04+, Debian 8+, Rocky 8+ | 구버전은 raw fallback 동작 |
| **커널** | 2.6.32+ | `ip` 명령 없으면 `/proc/net` fallback |
| **ip 명령** | `iproute2` 패키지 (`ip addr`) | 네트워크 수집 실패 가능 |
| **lsblk** | util-linux 2.19+ | 없으면 `df` fallback (물리 디스크 정보 제한) |
| **getent** | glibc 포함 (기본 설치) | users 수집 실패 |
| **lastlog / last** | shadow-utils (기본 설치) | `last_access_time` → `null` 반환 |
| **Python3 경로** | `/usr/bin/python3` (3.7 이상) 또는 `/usr/bin/python3.9` | `ansible_python_interpreter`로 경로 지정 가능 |

> **지원 안 됨**: Python 3.6 이하 (RHEL 8 기본 Python 포함). RHEL 8에서는 `sudo yum install python39` 후 `/usr/bin/python3.9` 경로를 사용해야 합니다.

---

### 1-2. Windows 대상 서버

| 항목 | 최소 요구사항 | 미충족 시 동작 |
|------|-------------|--------------|
| **WinRM** | 활성화 (5985 또는 5986 오픈) | 연결 실패 → `status: failed` |
| **PowerShell** | **5.1 이상** | 하위 참고 |
| **OS 버전** | **Windows Server 2016 이상** 권장 | 하위 참고 |
| **WinRM 인증** | NTLM 활성화 | 인증 실패 → `status: failed` |
| **CIM (WMI)** | 활성화 (기본) | 수집 실패 |

**PowerShell 버전별 지원 범위:**

| PowerShell | OS | 지원 내용 |
|------------|---|---------|
| 5.1 (권장) | Server 2016+ | `Get-LocalUser`, `Get-Volume`, `Get-NetIPAddress` 모두 지원 |
| 5.0 | Server 2012 R2+ | `Get-Volume` 가능, `Get-LocalUser` **없음** → WMI fallback (`last_access_time: null`) |
| 3.0–4.0 | Server 2012+ | `Get-NetIPAddress` 가능, `Get-Volume` **없음**, WMI fallback |
| 2.0 이하 | Server 2008 R2 | **미지원** — WinRM NTLM 불안정, `Get-CimInstance` 없음 |

> **지원 안 됨**: Windows Server 2008, Windows Server 2008 R2, Windows 7 이하

---

### 1-3. hosting_type 필드 (OS 채널 전용)

OS 채널은 `system.hosting_type` 필드를 제공한다.

| 값 | 의미 |
|---|---|
| `virtual` | 가상머신 guest (VMware, KVM, Hyper-V 등) |
| `baremetal` | 물리 서버에 직접 설치된 OS |
| `unknown` | 판별 근거 부족 또는 신호 충돌 |

적용 범위:
- OS 채널 (Linux, Windows)에서만 제공한다
- Redfish, ESXi 채널에는 적용하지 않는다
- 물리 서버에 직접 설치된 OS는, 그 위에서 KVM/Hyper-V host 역할을 하더라도 `baremetal`로 분류한다

---

### 1-4. Agent 노드 (Linux → Windows 수집 시)

| 항목 | 최소 요구사항 |
|------|-------------|
| **pywinrm** | 0.4.0 이상 (`pip install pywinrm`) |
| **Ansible** | 2.12 이상 (ansible.windows 컬렉션 포함) |

---

## 2. esxi-gather (VMware ESXi)

### 2-1. ESXi 대상 서버

| 항목 | 최소 요구사항 | 미충족 시 동작 |
|------|-------------|--------------|
| **ESXi 버전** | **6.5 이상** | 하위 버전은 vSphere API 일부 미지원 |
| **HTTPS 포트** | 443 오픈 (vSphere API) | 연결 실패 → `status: failed` |
| **라이선스** | **유료 라이선스 필요** (Essentials 이상) | Free 라이선스는 API write access 없어 수집 불가 |
| **관리자 계정** | 읽기 권한 이상 (`ReadOnly` role) | 인증 실패 → `status: failed` |

**ESXi 버전별 수집 가능 항목:**

| ESXi 버전 | 수집 가능 여부 | 비고 |
|----------|-------------|------|
| 8.x | ✅ 완전 지원 | |
| 7.x | ✅ 완전 지원 | |
| 6.7 | ✅ 완전 지원 | |
| 6.5 | ✅ 대부분 지원 | 일부 항목 `null` 가능 |
| 6.0 이하 | ❌ 미지원 | `community.vmware` 모듈 호환 안 됨 |

> **중요**: Free ESXi(vSphere Hypervisor)는 API write access 가 없어 `vmware_host_facts` 실행 시 오류 발생

---

### 2-2. Agent 노드

| 항목 | 최소 요구사항 |
|------|-------------|
| **Python** | 3.9 이상 |
| **pyvmomi** | 7.0 이상 (`pip install pyvmomi`) |
| **Ansible Collection** | `community.vmware` 3.0 이상 (`ansible-galaxy collection install community.vmware`) |

---

## 3. redfish-gather (Dell / HPE / Lenovo / Supermicro / Cisco BMC)

### 3-1. BMC 대상 서버

**공통 요구사항:**

| 항목 | 최소 요구사항 | 미충족 시 동작 |
|------|-------------|--------------|
| **HTTPS 포트** | 443 오픈 (Redfish API) | 연결 실패 → `status: failed` |
| **Redfish 버전** | DSP0266 1.0 이상 | 하위 버전 미지원 |
| **인증** | Basic Authentication 지원 | 인증 실패 → `status: failed` |

**벤더별 최소 BMC 버전:**

| 벤더 | BMC | 최소 버전 | Systems URI | Managers URI |
|------|-----|---------|-------------|-------------|
| **Dell** | iDRAC | **iDRAC 9** (FW 3.00+) | `Systems/System.Embedded.1` | `Managers/iDRAC.Embedded.1` |
| **HPE** | iLO | **iLO 5** (FW 1.10+) | `Systems/1` | `Managers/1` |
| **Lenovo** | XCC | **XCC** (FW 1.xx+, X11 이상) | `Systems/1` | `Managers/1` |
| **Supermicro** | BMC | **X10 이상** (BMC FW 3.xx+) | `Systems/1` | `Managers/1` |
| **Cisco** | CIMC | **CIMC** (UCS C-Series M4+) | 동적 탐색 (Members[0]) | `Managers/CIMC` |

**벤더별 지원/미지원 상세:**

| 벤더 | 지원 | 미지원 |
|------|------|--------|
| Dell | iDRAC 9 (PowerEdge 14G+) | iDRAC 7/8 (PowerEdge 12G/13G) — Redfish 미성숙 |
| HPE | iLO 5 (ProLiant Gen10+), iLO 6 (Gen11) | iLO 4 이하 — `Oem.Hp` 구조 달라 일부 수집 제한 |
| Lenovo | ThinkSystem (X11, SR/ST/SD 시리즈) | ThinkServer — Redfish 미지원 |
| Supermicro | X10/X11/X12/X13/H11/H12 이상 | X9 이하 — Redfish 미지원 |
| Cisco | UCS C-Series M4+ (CIMC Redfish 지원) | UCS C-Series M3 이하 — Redfish 미지원 |

**벤더별 서버 세대 ↔ BMC 버전 호환성 매트릭스:**

> 코드는 Redfish 표준 API(DSP0266)를 동적 탐색(API Discovery)하므로,
> Redfish 를 지원하는 모든 모델에서 **표준 필드**는 정상 수집된다.
> OEM 확장 필드(`data.*.oem`)는 아래 표의 BMC 버전에 맞춰 수집된다.

| 벤더 | 서버 세대 | 대표 모델 | BMC 버전 | 지원 |
|------|----------|----------|---------|------|
| **Dell** | 16G | PowerEdge R660, R760, R6625 | iDRAC 9 (FW 7.x) | ✅ 완전 지원 |
| Dell | 15G | PowerEdge R650, R750 | iDRAC 9 (FW 5.x–6.x) | ✅ 완전 지원 |
| Dell | 14G | PowerEdge R640, R740, R940 | iDRAC 9 (FW 3.x–4.x) | ✅ 완전 지원 |
| Dell | 13G | PowerEdge R630, R730 | iDRAC 8 | ❌ Redfish 미성숙 |
| Dell | 12G | PowerEdge R620, R720 | iDRAC 7 | ❌ Redfish 미지원 |
| **HPE** | Gen11 | ProLiant DL360/DL380 Gen11 | iLO 6 (FW 1.x+) | ✅ 완전 지원 |
| HPE | Gen10 Plus | ProLiant DL360/DL380 Gen10+ | iLO 5 (FW 2.x+) | ✅ 완전 지원 |
| HPE | Gen10 | ProLiant DL360/DL380 Gen10 | iLO 5 (FW 1.x+) | ✅ 완전 지원 |
| HPE | Gen9 | ProLiant DL360/DL380 Gen9 | iLO 4 | ⚠️ 부분 지원 (`Oem.Hp` 폴백, OEM 필드 제한) |
| HPE | Gen8 이하 | ProLiant DL360/DL380 Gen8 | iLO 4 이하 | ❌ Redfish 미지원 |
| **Lenovo** | X11+ | ThinkSystem SR650 V3, SR630 V3 | XCC2 (FW 4.x+) | ✅ 완전 지원 |
| Lenovo | X11 | ThinkSystem SR650, SR630 | XCC (FW 1.x+) | ✅ 완전 지원 |
| Lenovo | — | ThinkServer RD650, TD350 | — | ❌ Redfish 미지원 |
| **Supermicro** | X13/H13 | SYS-621C, SYS-222 시리즈 | BMC (FW 12.x+) | ✅ 완전 지원 |
| Supermicro | X12/H12 | SYS-120C, AS-2024 시리즈 | BMC (FW 10.x+) | ✅ 완전 지원 |
| Supermicro | X11/H11 | SYS-6019, AS-2023 시리즈 | BMC (FW 3.x+) | ✅ 완전 지원 |
| Supermicro | X10 | SYS-6018 시리즈 | BMC (FW 3.x+) | ✅ 지원 (일부 엔드포인트 제한 가능) |
| Supermicro | X9 이하 | — | IPMI only | ❌ Redfish 미지원 |
| **Cisco** | M5+ | UCS C220 M5, C240 M5, C220 M6 | CIMC (FW 4.x+) | ✅ 완전 지원 |
| Cisco | M4 | UCS C220 M4, C240 M4 | CIMC (FW 3.x+) | ✅ 지원 (일부 엔드포인트 제한 가능) |
| Cisco | M3 이하 | — | — | ❌ Redfish 미지원 |

---

### 3-2. Agent 노드

| 항목 | 최소 요구사항 |
|------|-------------|
| **Python** | **3.9 이상** |
| **외부 라이브러리** | **없음** — stdlib(urllib, ssl, socket) 만 사용 |

---

## 4. Jenkins Agent 공통 요구사항

| 항목 | 최소 요구사항 | 비고 |
|------|-------------|------|
| **OS** | RHEL/CentOS 7+, Ubuntu 18.04+, Rocky 8+ | |
| **Python** | **3.9 이상** | f-string, removeprefix 등 3.9+ 기능 사용 |
| **Java** | **21 이상** | Jenkins Agent 실행 (OpenJDK 21 권장) |
| **Ansible** | **2.12 이상** | `ansible.builtin.set_fact` 최신 필터 사용 |
| **ansible.windows** | 1.x 이상 | Windows 수집 시 필요 |
| **community.vmware** | 3.0 이상 | ESXi 수집 시 필요 |
| **pywinrm** | 0.4.0 이상 | Windows WinRM 연결 |
| **pyvmomi** | 7.0 이상 | ESXi vSphere API 연결 |
| **redis (Python)** | 4.0 이상 | Ansible Fact 캐싱 |

---

## 5. 네트워크 요구사항

| 방향 | 포트 | 용도 |
|------|------|------|
| Agent → Linux 대상 | TCP 22 | SSH |
| Agent → Windows 대상 | TCP 5985 또는 5986 | WinRM HTTP / HTTPS |
| Agent → ESXi 대상 | TCP 443 | vSphere API (HTTPS) |
| Agent → BMC (Redfish) | TCP 443 | Redfish API (HTTPS) |

---

## 6. 빠른 설치 체크리스트 (Agent 노드)

```bash
# Python 3.9+ 확인
python3 --version

# Ansible 2.12+ 확인
ansible --version

# 필수 Python 패키지
pip install ansible pywinrm pyvmomi redis --break-system-packages

# Ansible Collection
ansible-galaxy collection install community.vmware ansible.windows

# ansible.cfg 확인 (프로젝트 루트의 ansible.cfg 우선 적용)
# 프로젝트에 ansible.cfg 포함 — callback_plugins, stdout_callback 등 설정 통합
grep "stdout_callback\|callback_plugins" ansible.cfg
```

---

## 7. tasks/ 구조 요구사항

3개 gather 모두 `tasks/` 디렉터리로 수집/정규화 로직이 분리되어 있다.

### os-gather/tasks/

| 파일 | 주요 명령 / 의존성 |
|------|-----------------|
| `linux/preflight.yml` | `python3`, `dmidecode`, `lsblk`, `lastlog`, `last` 존재 확인 |
| `linux/gather_system.yml` | `ansible.builtin.setup`, `/proc/meminfo` fallback |
| `linux/gather_memory.yml` | `dmidecode -t memory` (없으면 `/proc/meminfo` fallback) |
| `linux/gather_storage.yml` | `lsblk -J` (없으면 `ansible_mounts` fallback) |
| `linux/gather_network.yml` | `ansible_interfaces`, `ansible_default_ipv4` |
| `linux/gather_users.yml` | `getent passwd/group`, `lastlog`, `last -F`, `utmpdump` |
| `windows/gather_memory.yml` | `Win32_PhysicalMemory` (CIM) |
| `windows/gather_storage.yml` | `Get-Volume`, `Win32_DiskDrive` |
| `windows/gather_network.yml` | `Get-DnsClientServerAddress`, `Get-NetIPAddress` |
| `windows/gather_users.yml` | `Get-LocalUser` → `Win32_UserAccount` fallback |
| `normalize/build_output.yml` | common/tasks/normalize 호출 (Ansible 2.12+) |

### esxi-gather/tasks/

| 파일 | 의존성 |
|------|--------|
| `collect_facts.yml` | `community.vmware.vmware_host_facts` |
| `collect_config.yml` | `community.vmware.vmware_host_config_info` |
| `collect_datastores.yml` | `community.vmware.vmware_datastore_info` |
| `normalize_*.yml` | Jinja2 필터 |

### redfish-gather/tasks/

| 파일 | 의존성 |
|------|--------|
| `detect_vendor.yml` | `library/redfish_gather.py` (stdlib only) |
| `load_vault.yml` | `vault/redfish/{vendor}.yml` |
| `collect_standard.yml` | `library/redfish_gather.py` |
| `normalize_*.yml` | Jinja2 필터 |

### common/tasks/normalize/

모든 gather 가 공통으로 사용하는 normalize 태스크.
`REPO_ROOT` 환경변수로 경로를 참조하므로 Jenkins 에서 `REPO_ROOT=${WORKSPACE}` 설정 필수.

| 파일 | 역할 |
|------|------|
| `init_fragments.yml` | 누적 변수 초기화 |
| `merge_fragment.yml` | fragment 재귀 병합 엔진 |
| `build_sections.yml` | `_all_sec_*` → sections dict |
| `build_errors.yml` | `_raw_errors` → 표준 errors 배열 |
| `build_empty_data.yml` | failed 시 null/[] data 뼈대 |
| `build_output.yml` | `_out_*` → `_output` 최종 조립 |

---

## 8. 미지원 환경 요약

| 환경 | 이유 |
|------|------|
| Windows Server 2008 / 2008 R2 | WinRM NTLM 불안정, PowerShell 2.0, CIM 미지원 |
| Windows Server 2012 / 2012 R2 | `Get-LocalUser` 없음 (`last_access_time: null`), `Get-Volume` 없음 (볼륨 수집 제한) |
| ESXi 6.0 이하 | `community.vmware` 모듈 미지원 |
| ESXi Free 라이선스 | API write access 없음 |
| Dell iDRAC 7 / 8 | Redfish API 미성숙 (일부 엔드포인트 없음) |
| HPE iLO 4 이하 | `Oem.Hpe` 구조 없음 (`Oem.Hp` — OEM 수집 제한) |
| Lenovo ThinkServer | Redfish 미지원 |
| Supermicro X9 이하 | Redfish 미지원 |
| Cisco UCS C-Series M3 이하 | Redfish 미지원 |
| Python 3.8 이하 (Agent) | 3.9+ 기능(removeprefix 등) 미지원 → 수집 모듈 실행 불가 |
| Python 3.6 이하 (타겟 Linux 서버) | Ansible 2.20 모듈 실행 시 `from __future__ import annotations` 에러 → RHEL 8 기본 Python 3.6 해당. `python39` 설치 필요 |
