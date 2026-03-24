# 16. 출력 JSON 예시

모든 예시는 GUIDE_FOR_AI.md 의 표준 스키마와 완전히 일치한다.
신규 필드 (`diagnosis`, `meta`, `correlation`) 은 `| default(none)` 처리되어 하위 호환된다.

### 필드 설명 사전 (Field Dictionary)

각 필드의 상세 의미, 단위, null 해석, 채널 간 차이는 `schema/field_dictionary.yml`에 정의되어 있다.

**사용 방법:**
- **포털**: dictionary 파일을 1회 로드하여 필드명 기반으로 help_ko/help_en을 lookup
- **운영자**: 출력 JSON의 특정 필드 의미가 불분명할 때 dictionary에서 검색
- **개발자**: 새 필드 추가 시 코드 반영 후 dictionary에 설명 1항목 추가

**참조 예시 (포털 JavaScript):**
```javascript
// field_dictionary.yml을 파싱한 dict 객체
const help = fieldDict["memory.total_basis"];
// help.help_ko → "total_mb 산출 기준. Redfish=물리 장착, OS=OS 인식..."
// help.help_en → "Basis for total_mb. Redfish=physically installed..."
```

**Dictionary 검증:**
```bash
# field_dictionary.yml 수정 후 무결성 검사
python3 tests/validate_field_dictionary.py
```
검증 항목: YAML 파싱, help_ko/help_en 존재, priority/channel 값, 중복 key, schema 대응

### Baseline v1 출력 샘플

실장비 기준 baseline output 샘플은 `schema/baseline_v1/`에 저장되어 있습니다.

| 파일 | 채널 | 대상 |
|------|------|------|
| `lenovo_baseline.json` | Redfish | Lenovo SR650 V2 |
| `hpe_baseline.json` | Redfish | HPE DL380 Gen11 |
| `dell_baseline.json` | Redfish | Dell R740 |
| `cisco_baseline.json` | Redfish | Cisco TA-UNODE-G1 |
| `ubuntu_baseline.json` | OS | Ubuntu 24.04 |
| `windows_baseline.json` | OS | Windows 10 22H2 |
| `esxi_baseline.json` | ESXi | ESXi 7.0.3 |

> baseline v1 기준: Git HEAD `ea8b8a1`, 2026-03-23

### Safe Common 5 필드 (확정)

Redfish 예시에 반영된 Safe Common 필드:

| 필드 | 타입 | 설명 |
|------|------|------|
| `hardware.health` | string\|null | 시스템 전체 Health — enum: OK/Warning/Critical |
| `hardware.power_state` | string\|null | 전원 상태 — enum: On/Off/PoweringOn/PoweringOff |
| `storage.physical_disks[].serial` | string\|null | 디스크 시리얼 번호 |
| `storage.physical_disks[].failure_predicted` | boolean\|null | SMART 기반 고장 예측 |
| `storage.physical_disks[].predicted_life_percent` | integer\|null | 예상 수명 잔량 (0-100, HPE float→int 변환) |

> **Conditional 필드 (보류)**: `hardware.sku`는 일부 벤더에서만 제공되므로 Conditional로 분류.
> 예시에 포함되어 있으나 모든 벤더에서 보장되지 않음. null 허용.
>
> **기타 보류 (Conditional)**: PowerConsumedWatts, PowerCapacityWatts, PowerMetrics.*,
> Proc.MaxSpeedMHz, System.SKU, PSU.Health, NIC.LinkStatus — 표준 스키마 반영 보류.

### 필터 정책 (Redfish 디스크 수집)

| 정책 | 설명 |
|------|------|
| CapacityBytes == 0 → skip | FlexFlash, Empty Bay 등 가상/빈 드라이브 제외 |
| Name contains "empty" → skip | 빈 베이 이름 패턴 제외 |
| HPE PredictedMediaLifeLeftPercent | float → int() 변환 후 `predicted_life_percent`에 매핑 |

---

## os-gather — success (Linux)

```json
{
  "schema_version": "1",
  "target_type": "os",
  "collection_method": "agent",
  "ip": "10.x.x.1",
  "hostname": "10.x.x.1",
  "vendor": null,
  "status": "success",
  "sections": {
    "system":   "success",
    "hardware": "not_supported",
    "bmc":      "not_supported",
    "cpu":      "success",
    "memory":   "success",
    "storage":  "success",
    "network":  "success",
    "firmware": "not_supported",
    "users":    "success"
  },
  "errors": [],
  "data": {
    "system": {
      "os_family": "RedHat",
      "distribution": "Rocky Linux",
      "version": "8.9",
      "kernel": "4.18.0-513.el8.x86_64",
      "architecture": "x86_64",
      "uptime_seconds": 1234567,
      "selinux": "disabled",
      "fqdn": "10.x.x.1"
    },
    "hardware": null,
    "bmc": null,
    "cpu": {
      "sockets": 2,
      "cores_physical": 16,
      "logical_threads": 32,
      "model": "Intel(R) Xeon(R) Gold 6326 CPU @ 2.90GHz",
      "architecture": "x86_64"
    },
    "memory": {
      "total_mb": 32768,
      "total_basis": "physical_installed",
      "installed_mb": 32768,
      "visible_mb": 31836,
      "free_mb": 10240,
      "slots": []
    },
    "storage": {
      "filesystems": [
        {"device": "/dev/sda1", "mount_point": "/", "filesystem": "xfs",
         "total_mb": 102400.0, "used_mb": 40960.0, "available_mb": 61440.0,
         "usage_percent": 40.0, "status": "mounted"}
      ],
      "physical_disks": [
        {"device": "/dev/sda", "model": "SAMSUNG MZILT960", "total_mb": 953869,
         "media_type": "SSD", "protocol": null, "health": null}
      ],
      "datastores": [],
      "controllers": []
    },
    "network": {
      "dns_servers": ["8.8.8.8", "8.8.4.4"],
      "default_gateways": [{"family": "ipv4", "address": "10.x.x.254"}],
      "interfaces": [
        {
          "id": "eth0", "name": "eth0", "kind": "os_nic",
          "mac": "00:11:22:33:44:55", "mtu": 1500, "speed_mbps": 1000,
          "link_status": "up", "is_primary": true,
          "addresses": [
            {"family": "ipv4", "address": "10.x.x.1",
             "prefix_length": 24, "subnet_mask": "255.255.255.0",
             "gateway": "10.x.x.254"}
          ]
        }
      ]
    },
    "users": [
      {"name": "root",  "uid": "0",    "groups": ["root"],
       "home": "/root", "last_access_time": "2026-03-17T08:00:00Z"},
      {"name": "admin", "uid": "1001", "groups": ["sudo","docker"],
       "home": "/home/admin", "last_access_time": "2026-03-15T14:30:00Z"}
    ],
    "firmware": [],
    "power": null
  },
  "diagnosis": {
    "reachable": true,
    "port_open": true,
    "protocol_supported": true,
    "auth_success": true,
    "failure_stage": null,
    "failure_reason": null,
    "probe_facts": {},
    "checked_ports": [22]
  },
  "meta": {
    "started_at": "2026-03-18T10:00:00Z",
    "finished_at": "2026-03-18T10:00:12Z",
    "duration_ms": 12350,
    "adapter_id": "os_linux_generic",
    "adapter_version": "1.0.0",
    "ansible_version": "2.19.1"
  },
  "correlation": {
    "serial_number": null,
    "system_uuid": null,
    "bmc_ip": null,
    "host_ip": "10.x.x.1"
  }
}
```

---

## os-gather — failed (SSH 인증 실패 → rescue 진입)

> rescue 진입 시 모든 supported 섹션이 failed 이므로 status 는 `"failed"` 이다.
> `"partial"` 이 되려면 일부 섹션은 success 이어야 한다.

```json
{
  "schema_version": "1",
  "target_type": "os",
  "collection_method": "agent",
  "ip": "10.x.x.2",
  "hostname": "10.x.x.2",
  "vendor": null,
  "status": "failed",
  "sections": {
    "system":   "failed",
    "hardware": "not_supported",
    "bmc":      "not_supported",
    "cpu":      "failed",
    "memory":   "failed",
    "storage":  "failed",
    "network":  "failed",
    "firmware": "not_supported",
    "users":    "failed"
  },
  "errors": [
    {"section": "linux_gather", "message": "SSH 인증 실패", "detail": null}
  ],
  "data": {
    "system": null, "hardware": null, "bmc": null,
    "cpu": null, "memory": null,
    "storage": {"filesystems":[],"physical_disks":[],"datastores":[],"controllers":[]},
    "network": {"dns_servers":[],"default_gateways":[],"interfaces":[]},
    "users": [], "firmware": [], "power": null
  },
  "diagnosis": {
    "reachable": true,
    "port_open": true,
    "protocol_supported": true,
    "auth_success": false,
    "failure_stage": "auth",
    "failure_reason": "SSH 인증 실패",
    "probe_facts": {},
    "checked_ports": [22]
  },
  "meta": {
    "started_at": "2026-03-18T10:01:00Z",
    "finished_at": "2026-03-18T10:01:08Z",
    "duration_ms": 8120,
    "adapter_id": "os_linux_generic",
    "adapter_version": "1.0.0",
    "ansible_version": "2.19.1"
  },
  "correlation": {
    "serial_number": null,
    "system_uuid": null,
    "bmc_ip": null,
    "host_ip": "10.x.x.2"
  }
}
```

---

## os-gather — failed (포트 감지 실패)

```json
{
  "schema_version": "1",
  "target_type": "os",
  "collection_method": "agent",
  "ip": "10.x.x.3",
  "hostname": "10.x.x.3",
  "vendor": null,
  "status": "failed",
  "sections": {
    "system":   "failed",
    "hardware": "not_supported",
    "bmc":      "not_supported",
    "cpu":      "failed",
    "memory":   "failed",
    "storage":  "failed",
    "network":  "failed",
    "firmware": "not_supported",
    "users":    "failed"
  },
  "errors": [
    {"section": "os_detect",
     "message": "SSH(22)/WinRM(5985/5986) 모두 응답 없음", "detail": null}
  ],
  "data": {
    "system": null, "hardware": null, "bmc": null,
    "cpu": null, "memory": null,
    "storage": {"filesystems":[],"physical_disks":[],"datastores":[],"controllers":[]},
    "network": {"dns_servers":[],"default_gateways":[],"interfaces":[]},
    "users": [], "firmware": [], "power": null
  },
  "diagnosis": {
    "reachable": false,
    "port_open": false,
    "protocol_supported": false,
    "auth_success": false,
    "failure_stage": "reachable",
    "failure_reason": "SSH(22)/WinRM(5985/5986) 모두 응답 없음",
    "probe_facts": {},
    "checked_ports": [22, 5985, 5986]
  },
  "meta": {
    "started_at": "2026-03-18T10:02:00Z",
    "finished_at": "2026-03-18T10:02:31Z",
    "duration_ms": 31040,
    "adapter_id": null,
    "adapter_version": null,
    "ansible_version": "2.19.1"
  },
  "correlation": {
    "serial_number": null,
    "system_uuid": null,
    "bmc_ip": null,
    "host_ip": "10.x.x.3"
  }
}
```

---

## esxi-gather — success

```json
{
  "schema_version": "1",
  "target_type": "esxi",
  "collection_method": "vsphere_api",
  "ip": "10.x.x.10",
  "hostname": "10.x.x.10",
  "vendor": "HPE",
  "status": "success",
  "sections": {
    "system":   "success",
    "hardware": "success",
    "bmc":      "not_supported",
    "cpu":      "success",
    "memory":   "success",
    "storage":  "success",
    "network":  "success",
    "firmware": "not_supported",
    "users":    "not_supported"
  },
  "errors": [],
  "data": {
    "system": {
      "os_family": "VMware ESXi", "distribution": "VMware ESXi",
      "version": "8.0.2", "kernel": "21825811",
      "architecture": "x86_64", "uptime_seconds": 864000,
      "selinux": null, "fqdn": "10.x.x.10"
    },
    "hardware": {
      "vendor": "HPE", "model": "ProLiant DL380 Gen10",
      "serial": "CZ12345678", "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
      "bios_version": "U30 v2.60", "bios_date": "2023-11-10"
    },
    "bmc": null,
    "cpu": {
      "sockets": 2, "cores_physical": 24, "logical_threads": 48,
      "model": "Intel(R) Xeon(R) Gold 6248R CPU @ 3.00GHz",
      "architecture": "x86_64"
    },
    "memory": {
      "total_mb": 196608, "total_basis": "hypervisor_visible",
      "installed_mb": null, "visible_mb": 196608, "free_mb": 131072, "slots": []
    },
    "storage": {
      "filesystems": [], "physical_disks": [],
      "datastores": [
        {"name": "datastore1", "type": "VMFS",
         "total_mb": 10485760, "free_mb": 2097152,
         "used_mb": 8388608, "usage_percent": 80.0, "accessible": true}
      ],
      "controllers": []
    },
    "network": {
      "dns_servers": ["10.x.x.53"],
      "default_gateways": [{"family": "ipv4", "address": "10.x.x.254"}],
      "interfaces": [
        {"id": "vmk0", "name": "vmk0", "kind": "vmkernel",
         "mac": "00:11:22:33:44:66", "mtu": 1500, "speed_mbps": null,
         "link_status": "up", "is_primary": true,
         "addresses": [
           {"family": "ipv4", "address": "10.x.x.10",
            "prefix_length": 24, "subnet_mask": "255.255.255.0",
            "gateway": "10.x.x.254"}
         ]}
      ]
    },
    "users": [], "firmware": [], "power": null
  },
  "diagnosis": {
    "reachable": true,
    "port_open": true,
    "protocol_supported": true,
    "auth_success": true,
    "failure_stage": null,
    "failure_reason": null,
    "probe_facts": {},
    "checked_ports": [443]
  },
  "meta": {
    "started_at": "2026-03-18T10:03:00Z",
    "finished_at": "2026-03-18T10:03:15Z",
    "duration_ms": 15230,
    "adapter_id": "esxi_generic",
    "adapter_version": "1.0.0",
    "ansible_version": "2.19.1"
  },
  "correlation": {
    "serial_number": "CZ12345678",
    "system_uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "bmc_ip": null,
    "host_ip": "10.x.x.10"
  }
}
```

---

## esxi-gather — partial (datastore 수집 실패)

```json
{
  "schema_version": "1",
  "target_type": "esxi",
  "collection_method": "vsphere_api",
  "ip": "10.x.x.11",
  "hostname": "10.x.x.11",
  "vendor": "Dell Inc.",
  "status": "partial",
  "sections": {
    "system":   "success",
    "hardware": "success",
    "bmc":      "not_supported",
    "cpu":      "success",
    "memory":   "success",
    "storage":  "failed",
    "network":  "success",
    "firmware": "not_supported",
    "users":    "not_supported"
  },
  "errors": [],
  "data": {
    "system": {"os_family": "VMware ESXi", "distribution": "VMware ESXi",
               "version": "7.0.3", "kernel": "19193900",
               "architecture": "x86_64", "uptime_seconds": 432000,
               "selinux": null, "fqdn": "10.x.x.11"},
    "hardware": {"vendor": "Dell Inc.", "model": "PowerEdge R740",
                 "serial": "DEF5678", "uuid": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
                 "bios_version": "2.14.0", "bios_date": "2022-08-01"},
    "bmc": null,
    "cpu": {"sockets": 2, "cores_physical": 20, "logical_threads": 40,
            "model": "Intel(R) Xeon(R) Gold 5218R", "architecture": "x86_64"},
    "memory": {"total_mb": 131072, "total_basis": "hypervisor_visible",
               "installed_mb": null, "visible_mb": 131072,
               "free_mb": 65536, "slots": []},
    "storage": {"filesystems": [], "physical_disks": [],
                "datastores": [], "controllers": []},
    "network": {
      "dns_servers": [],
      "default_gateways": [{"family": "ipv4", "address": "10.x.x.254"}],
      "interfaces": [
        {"id": "vmk0", "name": "vmk0", "kind": "vmkernel",
         "mac": "00:aa:bb:cc:dd:ee", "mtu": 1500, "speed_mbps": null,
         "link_status": "up", "is_primary": true,
         "addresses": [
           {"family": "ipv4", "address": "10.x.x.11",
            "prefix_length": 24, "subnet_mask": "255.255.255.0",
            "gateway": "10.x.x.254"}
         ]}
      ]
    },
    "users": [], "firmware": [], "power": null
  },
  "diagnosis": {
    "reachable": true,
    "port_open": true,
    "protocol_supported": true,
    "auth_success": true,
    "failure_stage": null,
    "failure_reason": null,
    "probe_facts": {},
    "checked_ports": [443]
  },
  "meta": {
    "started_at": "2026-03-18T10:04:00Z",
    "finished_at": "2026-03-18T10:04:20Z",
    "duration_ms": 20150,
    "adapter_id": "esxi_generic",
    "adapter_version": "1.0.0",
    "ansible_version": "2.19.1"
  },
  "correlation": {
    "serial_number": "DEF5678",
    "system_uuid": "yyyyyyyy-yyyy-yyyy-yyyy-yyyyyyyyyyyy",
    "bmc_ip": null,
    "host_ip": "10.x.x.11"
  }
}
```

---

## redfish-gather — success (Dell)

```json
{
  "schema_version": "1",
  "target_type": "redfish",
  "collection_method": "redfish_api",
  "ip": "10.x.x.201",
  "hostname": "10.x.x.201",
  "vendor": "dell",
  "status": "success",
  "sections": {
    "system":   "not_supported",
    "hardware": "success",
    "bmc":      "success",
    "cpu":      "success",
    "memory":   "success",
    "storage":  "success",
    "network":  "success",
    "firmware": "success",
    "users":    "not_supported"
  },
  "errors": [],
  "data": {
    "system": {"os_family": null, "distribution": null, "version": null,
               "kernel": null, "architecture": null, "uptime_seconds": null,
               "selinux": null, "fqdn": null},
    "hardware": {"vendor": "Dell Inc.", "model": "PowerEdge R750",
                 "serial": "ABC1234",
                 "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                 "bios_version": "1.5.6", "bios_date": null,
                 "health": "OK", "power_state": "On",
                 "sku": "SKU-R750-01"},
    "bmc": {"name": "iDRAC", "firmware_version": "5.10.50.00",
            "model": "iDRAC9", "health": "OK"},
    "cpu": {"sockets": 2, "cores_physical": null, "logical_threads": 64,
            "model": "Intel(R) Xeon(R) Gold 6326 CPU @ 2.90GHz",
            "architecture": null},
    "memory": {"total_mb": 65536, "total_basis": "physical_installed",
               "installed_mb": 65536, "visible_mb": null, "free_mb": null,
               "slots": [
                 {"id": "DIMM.Socket.A1", "capacity_mib": 16384,
                  "type": "DDR4", "speed_mhz": 3200,
                  "manufacturer": "Samsung", "health": "OK"}
               ]},
    "storage": {
      "filesystems": [],
      "physical_disks": [
        {"device": "Disk.Bay.0", "model": "SAMSUNG MZILT960",
         "total_mb": 953869, "media_type": "SSD",
         "protocol": "SAS", "health": "OK",
         "serial": "S6ESNX0T100123", "failure_predicted": false,
         "predicted_life_percent": null}
      ],
      "datastores": [],
      "controllers": [
        {"id": "RAID.Slot.1-1", "name": "PERC H755", "health": "OK",
         "drives": [
           {"device": "Disk.Bay.0", "model": "SAMSUNG MZILT960",
            "total_mb": 953869, "media_type": "SSD",
            "protocol": "SAS", "health": "OK",
            "serial": "S6ESNX0T100123", "failure_predicted": false,
            "predicted_life_percent": null}
         ]}
      ]
    },
    "network": {
      "dns_servers": [],
      "default_gateways": [{"family": "ipv4", "address": "10.x.x.254"}],
      "interfaces": [
        {"id": "NIC.Slot.1-1", "name": "Integrated NIC 1 Port 1",
         "kind": "server_nic", "mac": "00:11:22:33:44:77",
         "mtu": null, "speed_mbps": 10000, "link_status": "up",
         "is_primary": false,
         "addresses": [
           {"family": "ipv4", "address": "10.x.x.201",
            "prefix_length": null, "subnet_mask": "255.255.255.0",
            "gateway": "10.x.x.254"}
         ]}
      ]
    },
    "users": [],
    "firmware": [
      {"id": "BIOS.Setup.1-1", "name": "System BIOS",
       "version": "1.5.6", "component": "BIOS"}
    ],
    "power": {
      "power_supplies": [
        {"name": "PSU1", "model": "PWR-1400-AC",
         "power_capacity_w": 1400, "firmware_version": "00.1D.1B",
         "health": "OK", "state": "Enabled"}
      ]
    }
  },
  "diagnosis": {
    "reachable": true,
    "port_open": true,
    "protocol_supported": true,
    "auth_success": true,
    "failure_stage": null,
    "failure_reason": null,
    "probe_facts": {
      "vendor": "Dell Inc.",
      "firmware": "iDRAC 9 v5.10.50.00"
    },
    "checked_ports": [443]
  },
  "meta": {
    "started_at": "2026-03-18T10:05:00Z",
    "finished_at": "2026-03-18T10:05:18Z",
    "duration_ms": 18420,
    "adapter_id": "redfish_dell_idrac9",
    "adapter_version": "1.0.0",
    "ansible_version": "2.19.1"
  },
  "correlation": {
    "serial_number": "ABC1234",
    "system_uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
    "bmc_ip": "10.x.x.201",
    "host_ip": null
  }
}
```

---

## redfish-gather — partial (firmware 실패)

```json
{
  "schema_version": "1",
  "target_type": "redfish",
  "collection_method": "redfish_api",
  "ip": "10.x.x.202",
  "hostname": "10.x.x.202",
  "vendor": "hpe",
  "status": "partial",
  "sections": {
    "system":   "not_supported",
    "hardware": "success",
    "bmc":      "success",
    "cpu":      "success",
    "memory":   "success",
    "storage":  "success",
    "network":  "success",
    "firmware": "failed",
    "users":    "not_supported"
  },
  "errors": [
    {"section": "firmware", "message": "FirmwareInventory HTTP 404", "detail": null}
  ],
  "data": {
    "system": {"os_family": null, "distribution": null, "version": null,
               "kernel": null, "architecture": null, "uptime_seconds": null,
               "selinux": null, "fqdn": null},
    "hardware": {"vendor": "HPE", "model": "ProLiant DL380 Gen10",
                 "serial": "CZ99887766",
                 "uuid": "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz",
                 "bios_version": "U30 v2.60", "bios_date": null,
                 "health": "OK", "power_state": "On",
                 "sku": null},
    "bmc": {"name": "iLO", "firmware_version": "2.72",
            "model": "iLO 5", "health": "OK"},
    "cpu": {"sockets": 2, "cores_physical": null, "logical_threads": 48,
            "model": "Intel(R) Xeon(R) Gold 6248R CPU @ 3.00GHz",
            "architecture": null},
    "memory": {"total_mb": 131072, "total_basis": "physical_installed",
               "installed_mb": 131072, "visible_mb": null, "free_mb": null,
               "slots": []},
    "storage": {
      "filesystems": [], "datastores": [],
      "physical_disks": [
        {"device": "1I:1:1", "model": "EG001200JWJNK",
         "total_mb": 1144870, "media_type": "HDD",
         "protocol": "SAS", "health": "OK",
         "serial": "WBN0A1234567", "failure_predicted": false,
         "predicted_life_percent": null}
      ],
      "controllers": [
        {"id": "SmartArray", "name": "Smart Array P408i-a",
         "health": "OK",
         "drives": [
           {"device": "1I:1:1", "model": "EG001200JWJNK",
            "total_mb": 1144870, "media_type": "HDD",
            "protocol": "SAS", "health": "OK",
            "serial": "WBN0A1234567", "failure_predicted": false,
            "predicted_life_percent": null}
         ]}
      ]
    },
    "network": {
      "dns_servers": [],
      "default_gateways": [],
      "interfaces": [
        {"id": "NIC.Embedded.1-1", "name": "Embedded FlexibleLOM 1 Port 1",
         "kind": "server_nic", "mac": "aa:bb:cc:dd:ee:ff",
         "mtu": null, "speed_mbps": 25000, "link_status": "up",
         "is_primary": false,
         "addresses": [
           {"family": "ipv4", "address": "10.x.x.202",
            "prefix_length": null, "subnet_mask": null, "gateway": null}
         ]}
      ]
    },
    "users": [], "firmware": [], "power": null
  },
  "diagnosis": {
    "reachable": true,
    "port_open": true,
    "protocol_supported": true,
    "auth_success": true,
    "failure_stage": null,
    "failure_reason": null,
    "probe_facts": {
      "vendor": "HPE",
      "firmware": "iLO 5 v2.72"
    },
    "checked_ports": [443]
  },
  "meta": {
    "started_at": "2026-03-18T10:06:00Z",
    "finished_at": "2026-03-18T10:06:14Z",
    "duration_ms": 14680,
    "adapter_id": "redfish_hpe_ilo",
    "adapter_version": "1.0.0",
    "ansible_version": "2.19.1"
  },
  "correlation": {
    "serial_number": "CZ99887766",
    "system_uuid": "zzzzzzzz-zzzz-zzzz-zzzz-zzzzzzzzzzzz",
    "bmc_ip": "10.x.x.202",
    "host_ip": null
  }
}
```

---

## redfish-gather — failed

```json
{
  "schema_version": "1",
  "target_type": "redfish",
  "collection_method": "redfish_api",
  "ip": "10.x.x.203",
  "hostname": "10.x.x.203",
  "vendor": null,
  "status": "failed",
  "sections": {
    "system":   "not_supported",
    "hardware": "failed",
    "bmc":      "failed",
    "cpu":      "failed",
    "memory":   "failed",
    "storage":  "failed",
    "network":  "failed",
    "firmware": "failed",
    "users":    "not_supported"
  },
  "errors": [
    {"section": "redfish_gather",
     "message": "Redfish 수집 완전 실패 — BMC 연결 또는 인증 문제",
     "detail": null}
  ],
  "data": {
    "system": null, "hardware": null, "bmc": null,
    "cpu": null, "memory": null,
    "storage": {"filesystems":[],"physical_disks":[],"datastores":[],"controllers":[]},
    "network": {"dns_servers":[],"default_gateways":[],"interfaces":[]},
    "users": [], "firmware": [], "power": null
  },
  "diagnosis": {
    "reachable": true,
    "port_open": true,
    "protocol_supported": false,
    "auth_success": false,
    "failure_stage": "protocol",
    "failure_reason": "Redfish ServiceRoot (/redfish/v1/) 응답 없음 — iDRAC 7 등 구 세대 추정",
    "probe_facts": {},
    "checked_ports": [443]
  },
  "meta": {
    "started_at": "2026-03-18T10:07:00Z",
    "finished_at": "2026-03-18T10:07:05Z",
    "duration_ms": 5230,
    "adapter_id": null,
    "adapter_version": null,
    "ansible_version": "2.19.1"
  },
  "correlation": {
    "serial_number": null,
    "system_uuid": null,
    "bmc_ip": "10.x.x.203",
    "host_ip": null
  }
}
```
