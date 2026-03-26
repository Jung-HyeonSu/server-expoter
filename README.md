# server-exporter — 서버 정보 수집 파이프라인

**포털에 등록되기 전 서버**의 하드웨어/OS 정보를 수집한다.
포털 → Jenkins → Ansible → 포털 흐름으로 동작한다.

---

## 원칙

**계정은 vault 에서 관리한다.** 포털이 전달하는 것은 `ip` 와 `target_type` 뿐이다.
OS 타입과 벤더를 모르는 상태로 시작하며, gather 가 직접 감지하여 분기한다.

```
포털 → inventory_json = [{"ip": "10.x.x.1"}]
     → Jenkins (target_type: os|esxi|redfish)
          → 포트 감지 / Manufacturer 감지
          → vault 자동 로딩 → 수집 → OUTPUT JSON (schema_version: "1")
```

**Fragment 기반 수집 구조:**
각 gather 태스크는 전체 JSON 을 만들지 않고 자기 역할의 fragment 만 생성한다.
공통 builder (`common/tasks/normalize/`) 가 fragment 들을 병합해 최종 JSON 을 만든다.
새 수집 항목이 생기면 새 yml 추가 + fragment 생성 + `merge_fragment.yml` 호출만으로 확장된다.

---

## 전체 실행 흐름

```
포털
 └─ Jenkins Job 트리거 (HTTPS 443)
      ├─ Validate  : ip 필드 검증
      └─ Gather    : Ansible Playbook 실행
           ├─ os-gather/site.yml
           │    Play1: SSH(22) / WinRM(5985/5986) 포트 감지
           │    Play2: Linux  → vault/linux.yml → tasks/linux/*
           │    Play3: Windows → vault/windows.yml → tasks/windows/*
           │         └─ tasks/normalize/build_output.yml → OUTPUT
           ├─ esxi-gather/site.yml
           │    vault/esxi.yml → vmware_host_facts → OUTPUT
           └─ redfish-gather/site.yml
                Step1: Manufacturer 자동 감지
                Step2: vault/redfish/{vendor}.yml 로딩
                Step3: 전체 재수집 → OUTPUT
```

---

## 디렉터리 구조

```
server-exporter/
  Jenkinsfile
  ansible.cfg                 ← callback_plugins 경로 등 Ansible 설정 통합
  vault/
    linux.yml / windows.yml / esxi.yml
    redfish/dell.yml / hpe.yml / lenovo.yml / supermicro.yml / cisco.yml
  callback_plugins/json_only.py  ← 유일한 사본 (ansible.cfg에서 참조)

  common/
    tasks/normalize/
      build_sections.yml    ← _sec_* → sections 딕셔너리 (3개 gather 공통)
      build_errors.yml      ← raw errors → 표준 형식
      build_empty_data.yml  ← failed 시 빈 data 뼈대
      build_output.yml      ← 최종 _output 조립

  os-gather/
    site.yml                ← orchestration (Play1:감지, Play2:Linux, Play3:Windows)
    inventory.sh
    tasks/
      linux/
        preflight.yml       ← Python 경로 감지, 명령 존재 확인
        gather_system.yml / gather_cpu.yml / gather_memory.yml
        gather_storage.yml / gather_network.yml / gather_users.yml
      windows/
        gather_system.yml / gather_cpu.yml / gather_memory.yml
        gather_storage.yml / gather_network.yml / gather_users.yml
      normalize/build_output.yml  ← OS 전용 → common 호출

  esxi-gather/
    site.yml / inventory.sh
    tasks/
      collect_facts.yml / collect_config.yml / collect_datastores.yml
      normalize_system.yml / normalize_network.yml / normalize_storage.yml

  redfish-gather/
    site.yml / inventory.sh
    library/redfish_gather.py
    tasks/
      detect_vendor.yml / load_vault.yml / collect_standard.yml / normalize_standard.yml
      vendors/{dell|hpe|lenovo|supermicro|cisco}/collect_oem.yml + normalize_oem.yml

  docs/
```

---

## 포털 Input Parameters

| 파라미터 | 필수 | 설명 |
|---------|------|------|
| `loc` | 필수 | Jenkins agent label: `ich` / `chj` / `yi` |
| `target_type` | 필수 | `os` / `esxi` / `redfish` |
| `inventory_json` | 필수 | `[{"ip": "10.x.x.1"}]` |

---

## inventory_json 형식

```json
[{"ip": "10.x.x.1"}, {"ip": "10.x.x.2"}]
```

ip 만 전달한다. hostname / username / password / vendor 는 전달하지 않는다.

---

## 표준 Output JSON 스키마

> **필드 설명 사전**: 각 필드의 상세 의미, null 해석, 채널 간 차이는
> `schema/field_dictionary.yml`을 참조하세요. 포털에서 필드명 기반 lookup으로 사용합니다.

### 최상위 구조 (3개 gather 공통)

```json
{
  "target_type":       "os | esxi | redfish",
  "collection_method": "agent | vsphere_api | redfish_api",
  "ip":       "10.x.x.1",
  "hostname": "10.x.x.1",
  "vendor":   "dell | hpe | lenovo | supermicro | cisco | null",
  "status":   "success | partial | failed",
  "sections": {
    "system":   "success | failed | not_supported",
    "hardware": "success | failed | not_supported",
    "cpu":      "success | failed | not_supported",
    "memory":   "success | failed | not_supported",
    "storage":  "success | failed | not_supported",
    "network":  "success | failed | not_supported",
    "bmc":      "success | failed | not_supported",
    "firmware": "success | failed | not_supported",
    "users":    "success | failed | not_supported",
    "power":    "success | failed | not_supported"
  },
  "errors": [{"section": "...", "message": "...", "detail": null}],
  "data": { ... }
}
```

### sections 값 의미

| 값 | 의미 |
|----|------|
| `success` | 수집 성공 |
| `failed` | 지원하지만 이번에 실패 |
| `not_supported` | 이 gather 타입에서 원래 수집 불가 |

### data.memory.total_basis

| 값 | 의미 |
|----|------|
| `physical_installed` | dmidecode / Win32_Physical / Redfish DIMM |
| `os_visible` | OS 인식 메모리 (fallback) |
| `hypervisor_visible` | 하이퍼바이저 인식 (ESXi) |

### data.network 구조

```json
"network": {
  "dns_servers": ["8.8.8.8"],
  "default_gateways": [{"family": "ipv4", "address": "10.x.x.254"}],
  "interfaces": [{
    "id": "eth0", "name": "eth0",
    "kind": "os_nic | vmkernel | server_nic",
    "mac": "...", "mtu": 1500, "speed_mbps": 1000,
    "link_status": "up", "is_primary": true,
    "addresses": [{"family": "ipv4", "address": "10.x.x.1",
                   "prefix_length": 24, "subnet_mask": "255.255.255.0",
                   "gateway": "10.x.x.254"}]
  }]
}
```

### data.storage 구조

```json
"storage": {
  "filesystems":    [{"device", "mount_point", "filesystem",
                      "total_mb", "used_mb", "available_mb", "usage_percent"}],
  "physical_disks": [{"device", "model", "total_mb", "media_type", "protocol", "health",
                      "serial", "failure_predicted", "predicted_life_percent"}],
  "datastores":     [{"name", "type", "total_mb", "free_mb", "used_mb", "usage_percent"}],
  "controllers":    [{"id", "name", "health", "drives"}]
}
```

---

## 각 Playbook 역할

### os-gather (include_tasks 분리 구조)
- `tasks/linux/gather_memory.yml` — dmidecode 물리 메모리, /proc/meminfo fallback
- `tasks/linux/gather_storage.yml` — lsblk 물리 디스크 + ansible_mounts 파일시스템
- `tasks/linux/gather_network.yml` — is_primary, gateway, dns, speed 포함
- `tasks/linux/gather_users.yml` — getent group 멤버십, lastlog→last→utmpdump 3단계
- `tasks/windows/*` — Win32_PhysicalMemory, Get-LocalUser→WMI fallback
- `tasks/normalize/build_output.yml` — 확정 스키마로 조립

### esxi-gather
- `vmware_host_facts` — 기본 facts
- `vmware_host_config_info` — Gateway/DNS
- `vmware_datastore_info` — 데이터스토어 상세

### redfish-gather
- `library/redfish_gather.py` — Python stdlib 만 사용 (v4: HPE Controllers fallback, chassis_uri 직접 전달, HealthRollup/IndicatorLED/HostName 빈문자열 fallback, 주요 필드 누락 경고)
- 2단계 vault 로딩: 빈 계정으로 Manufacturer 감지 → 해당 vault 로딩 → 재수집
- 지원 벤더: Dell iDRAC 9+ / HPE iLO 5+ (iLO 6 전용 어댑터 포함) / Lenovo XCC / Supermicro X10+ / Cisco CIMC

---

## 실패 시 동작

| 상황 | 동작 |
|------|------|
| SSH/WinRM 응답 없음 | `status: failed`, sections 전체 `failed` |
| gather_facts 실패 | raw 명령 fallback |
| Redfish 연결 실패 | `status: failed`, errors 에 기록 |
| Redfish 일부 섹션 실패 | `status: partial`, 성공 섹션 포함 |
| ESXi API 실패 | rescue → `status: failed` |

---

## Agent 의존성

```bash
pip install ansible pywinrm pyvmomi --break-system-packages
ansible-galaxy collection install community.vmware ansible.windows
```

자세한 버전 요구사항은 `REQUIREMENTS.md` 참고.
