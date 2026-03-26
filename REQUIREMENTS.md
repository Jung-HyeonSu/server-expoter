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

> 코드는 Redfish 표준 API(DSP0266)를 동적 탐색(API Discovery)하므로,
> Redfish 를 지원하는 모든 모델에서 **표준 필드**는 정상 수집된다.
> OEM 확장 필드(`data.*.oem`)는 위 표의 BMC 버전에 맞춰 수집된다.

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

## 6. tasks/ 구조 개요

3개 gather 모두 `tasks/` 디렉터리로 수집/정규화 로직이 분리되어 있다.
상세 구조와 흐름은 [docs/06_gather-structure.md](docs/06_gather-structure.md) 참조.

> `REPO_ROOT` 환경변수로 공통 태스크 경로를 참조하므로 Jenkins 에서 `REPO_ROOT=${WORKSPACE}` 설정 필수.

---

## 7. OS 채널 식별자 및 엔티티 연결 정책

### 7-1. 식별자 필드

- OS 채널은 `system.serial_number`와 `system.system_uuid`를 제공할 수 있다.
- 값이 없거나 의미없는 센티널 값(NA, Not Specified 등)은 `null`로 정규화한다.
- Linux에서 정확한 DMI 식별자 수집을 위해 `become` 권한 사용을 권장한다.

### 7-2. Cross-channel 연결 정책

- `system_uuid`가 존재하면 cross-channel 엔티티 연결의 우선 키로 사용할 수 있다.
- `serial_number`는 채널 및 벤더에 따라 의미가 다를 수 있으므로, direct match 시 추가 검증이 필요하다.
- `hosting_type`이 `virtual`이면 물리 Redfish와 직접 매칭하지 않는다.
- 물리 서버에 직접 설치된 OS는, 그 위에서 KVM/Hyper-V host 역할을 하더라도 `baremetal`로 분류한다.

### 7-3. 식별자 수집 권한 정책

- 권한 부족 또는 source 값 부재 시 식별자는 null로 반환한다.
- 식별자 미수집은 gather 실패가 아니며, 수집은 계속 진행된다 (non-fatal).
- 미수집 원인은 non-fatal diagnostic으로 errors 배열에 기록할 수 있다 (status/sections 판정에 무영향).
  - `insufficient_privilege`: 권한 부족으로 DMI/WMI 접근 불가
  - `identifier_not_available`: source가 유효한 값을 제공하지 않음
- 정확한 식별자 수집을 위해 `become_password` 제공을 권장한다.

> 수집 우선순위, fallback 동작, baseline 기준 등 구현 상세는 [docs/16_os-esxi-mapping.md](docs/16_os-esxi-mapping.md) §식별자 수집 경로 참조.

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
