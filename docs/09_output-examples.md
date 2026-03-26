# 09. 출력 JSON 예시

모든 예시는 표준 스키마(`schema_version: "1"`)와 일치한다.
채널별 대표 1건씩 수록하며, 전체 baseline은 `schema/baseline_v1/` 참조.

---

## 참조 파일

### Field Dictionary

각 필드의 상세 의미, 단위, null 해석은 `schema/field_dictionary.yml`에 정의.

```bash
# 무결성 검사
python3 tests/validate_field_dictionary.py
```

### Baseline v1 출력 샘플

| 파일 | 채널 | 대상 |
|------|------|------|
| `lenovo_baseline.json` | Redfish | Lenovo SR650 V2 |
| `hpe_baseline.json` | Redfish | HPE DL380 Gen11 |
| `dell_baseline.json` | Redfish | Dell R740 |
| `cisco_baseline.json` | Redfish | Cisco TA-UNODE-G1 |
| `ubuntu_baseline.json` | OS | Ubuntu 24.04 |
| `windows_baseline.json` | OS | Windows 10 22H2 |
| `esxi_baseline.json` | ESXi | ESXi 7.0.3 |

### Safe Common 5 필드 (Redfish)

| 필드 | 타입 | 설명 |
|------|------|------|
| `hardware.health` | string\|null | 시스템 Health — OK/Warning/Critical |
| `hardware.power_state` | string\|null | 전원 — On/Off/PoweringOn/PoweringOff |
| `storage.physical_disks[].serial` | string\|null | 디스크 시리얼 |
| `storage.physical_disks[].failure_predicted` | boolean\|null | SMART 고장 예측 |
| `storage.physical_disks[].predicted_life_percent` | integer\|null | 수명 잔량 (0-100) |

### 디스크 필터 정책

| 정책 | 설명 |
|------|------|
| CapacityBytes == 0 → skip | FlexFlash, Empty Bay 제외 |
| Name contains "empty" → skip | 빈 베이 패턴 제외 |

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
    "system": "success", "hardware": "not_supported", "bmc": "not_supported",
    "cpu": "success", "memory": "success", "storage": "success",
    "network": "success", "firmware": "not_supported", "users": "success"
  },
  "errors": [],
  "data": {
    "system": {
      "os_family": "RedHat", "distribution": "Rocky Linux", "version": "8.9",
      "kernel": "4.18.0-513.el8.x86_64", "architecture": "x86_64",
      "uptime_seconds": 1234567, "selinux": "disabled", "fqdn": "10.x.x.1"
    },
    "hardware": null, "bmc": null,
    "cpu": { "sockets": 2, "cores_physical": 16, "logical_threads": 32,
             "model": "Intel(R) Xeon(R) Gold 6326 CPU @ 2.90GHz", "architecture": "x86_64" },
    "memory": { "total_mb": 32768, "total_basis": "physical_installed",
                "installed_mb": 32768, "visible_mb": 31836, "free_mb": 10240, "slots": [] },
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
      "datastores": [], "controllers": []
    },
    "network": {
      "dns_servers": ["8.8.8.8"], "default_gateways": [{"family": "ipv4", "address": "10.x.x.254"}],
      "interfaces": [
        {"id": "eth0", "name": "eth0", "kind": "os_nic", "mac": "00:11:22:33:44:55",
         "mtu": 1500, "speed_mbps": 1000, "link_status": "up", "is_primary": true,
         "addresses": [{"family": "ipv4", "address": "10.x.x.1",
                        "prefix_length": 24, "subnet_mask": "255.255.255.0", "gateway": "10.x.x.254"}]}
      ]
    },
    "users": [
      {"name": "root", "uid": "0", "groups": ["root"], "home": "/root", "last_access_time": "2026-03-17T08:00:00Z"}
    ],
    "firmware": [], "power": null
  },
  "diagnosis": { "reachable": true, "port_open": true, "protocol_supported": true,
                 "auth_success": true, "failure_stage": null, "failure_reason": null,
                 "probe_facts": {}, "checked_ports": [22] },
  "meta": { "started_at": "2026-03-18T10:00:00Z", "finished_at": "2026-03-18T10:00:12Z",
            "duration_ms": 12350, "adapter_id": "os_linux_generic",
            "adapter_version": "1.0.0", "ansible_version": "2.19.1" },
  "correlation": { "serial_number": null, "system_uuid": null, "bmc_ip": null, "host_ip": "10.x.x.1" }
}
```

> **failed 예시**: 모든 supported 섹션이 `"failed"`, `diagnosis.failure_stage`에 실패 단계 기록.
> 상세는 `schema/examples/` 또는 baseline 참조.

---

## esxi-gather — success

```json
{
  "schema_version": "1",
  "target_type": "esxi",
  "collection_method": "vsphere_api",
  "ip": "10.x.x.10", "hostname": "10.x.x.10", "vendor": "HPE",
  "status": "success",
  "sections": {
    "system": "success", "hardware": "success", "bmc": "not_supported",
    "cpu": "success", "memory": "success", "storage": "success",
    "network": "success", "firmware": "not_supported", "users": "not_supported"
  },
  "errors": [],
  "data": {
    "system": { "os_family": "VMware ESXi", "distribution": "VMware ESXi",
                "version": "8.0.2", "kernel": "21825811", "architecture": "x86_64",
                "uptime_seconds": 864000, "selinux": null, "fqdn": "10.x.x.10" },
    "hardware": { "vendor": "HPE", "model": "ProLiant DL380 Gen10",
                  "serial": "CZ12345678", "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                  "bios_version": "U30 v2.60", "bios_date": "2023-11-10" },
    "bmc": null,
    "cpu": { "sockets": 2, "cores_physical": 24, "logical_threads": 48,
             "model": "Intel(R) Xeon(R) Gold 6248R CPU @ 3.00GHz", "architecture": "x86_64" },
    "memory": { "total_mb": 196608, "total_basis": "hypervisor_visible",
                "installed_mb": null, "visible_mb": 196608, "free_mb": 131072, "slots": [] },
    "storage": { "filesystems": [], "physical_disks": [],
                 "datastores": [{"name": "datastore1", "type": "VMFS", "total_mb": 10485760,
                                 "free_mb": 2097152, "used_mb": 8388608, "usage_percent": 80.0, "accessible": true}],
                 "controllers": [] },
    "network": { "dns_servers": ["10.x.x.53"],
                 "default_gateways": [{"family": "ipv4", "address": "10.x.x.254"}],
                 "interfaces": [{"id": "vmk0", "name": "vmk0", "kind": "vmkernel",
                                 "mac": "00:11:22:33:44:66", "mtu": 1500, "speed_mbps": null,
                                 "link_status": "up", "is_primary": true,
                                 "addresses": [{"family": "ipv4", "address": "10.x.x.10",
                                                "prefix_length": 24, "subnet_mask": "255.255.255.0",
                                                "gateway": "10.x.x.254"}]}] },
    "users": [], "firmware": [], "power": null
  },
  "diagnosis": { "reachable": true, "port_open": true, "protocol_supported": true,
                 "auth_success": true, "failure_stage": null, "failure_reason": null,
                 "probe_facts": {}, "checked_ports": [443] },
  "meta": { "started_at": "2026-03-18T10:03:00Z", "finished_at": "2026-03-18T10:03:15Z",
            "duration_ms": 15230, "adapter_id": "esxi_generic",
            "adapter_version": "1.0.0", "ansible_version": "2.19.1" },
  "correlation": { "serial_number": "CZ12345678", "system_uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                   "bmc_ip": null, "host_ip": "10.x.x.10" }
}
```

---

## redfish-gather — success (Dell)

```json
{
  "schema_version": "1",
  "target_type": "redfish",
  "collection_method": "redfish_api",
  "ip": "10.x.x.201", "hostname": "10.x.x.201", "vendor": "dell",
  "status": "success",
  "sections": {
    "system": "not_supported", "hardware": "success", "bmc": "success",
    "cpu": "success", "memory": "success", "storage": "success",
    "network": "success", "firmware": "success", "users": "not_supported"
  },
  "errors": [],
  "data": {
    "system": { "os_family": null, "distribution": null, "version": null, "kernel": null,
                "architecture": null, "uptime_seconds": null, "selinux": null, "fqdn": null },
    "hardware": { "vendor": "Dell Inc.", "model": "PowerEdge R750", "serial": "ABC1234",
                  "uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                  "bios_version": "1.5.6", "bios_date": null,
                  "health": "OK", "power_state": "On", "sku": "SKU-R750-01" },
    "bmc": { "name": "iDRAC", "firmware_version": "5.10.50.00", "model": "iDRAC9", "health": "OK" },
    "cpu": { "sockets": 2, "cores_physical": null, "logical_threads": 64,
             "model": "Intel(R) Xeon(R) Gold 6326 CPU @ 2.90GHz", "architecture": null },
    "memory": { "total_mb": 65536, "total_basis": "physical_installed",
                "installed_mb": 65536, "visible_mb": null, "free_mb": null,
                "slots": [{"id": "DIMM.Socket.A1", "capacity_mib": 16384, "type": "DDR4",
                           "speed_mhz": 3200, "manufacturer": "Samsung", "health": "OK"}] },
    "storage": {
      "filesystems": [],
      "physical_disks": [
        {"device": "Disk.Bay.0", "model": "SAMSUNG MZILT960", "total_mb": 953869,
         "media_type": "SSD", "protocol": "SAS", "health": "OK",
         "serial": "S6ESNX0T100123", "failure_predicted": false, "predicted_life_percent": null}
      ],
      "datastores": [],
      "controllers": [{"id": "RAID.Slot.1-1", "name": "PERC H755", "health": "OK", "drives": ["..."]}]
    },
    "network": {
      "dns_servers": [], "default_gateways": [{"family": "ipv4", "address": "10.x.x.254"}],
      "interfaces": [
        {"id": "NIC.Slot.1-1", "name": "Integrated NIC 1 Port 1", "kind": "server_nic",
         "mac": "00:11:22:33:44:77", "mtu": null, "speed_mbps": 10000, "link_status": "up",
         "is_primary": false,
         "addresses": [{"family": "ipv4", "address": "10.x.x.201",
                        "prefix_length": null, "subnet_mask": "255.255.255.0", "gateway": "10.x.x.254"}]}
      ]
    },
    "users": [],
    "firmware": [{"id": "BIOS.Setup.1-1", "name": "System BIOS", "version": "1.5.6", "component": "BIOS"}],
    "power": { "power_supplies": [{"name": "PSU1", "model": "PWR-1400-AC",
               "power_capacity_w": 1400, "firmware_version": "00.1D.1B", "health": "OK", "state": "Enabled"}] }
  },
  "diagnosis": { "reachable": true, "port_open": true, "protocol_supported": true,
                 "auth_success": true, "failure_stage": null, "failure_reason": null,
                 "probe_facts": {"vendor": "Dell Inc.", "firmware": "iDRAC 9 v5.10.50.00"},
                 "checked_ports": [443] },
  "meta": { "started_at": "2026-03-18T10:05:00Z", "finished_at": "2026-03-18T10:05:18Z",
            "duration_ms": 18420, "adapter_id": "redfish_dell_idrac9",
            "adapter_version": "1.0.0", "ansible_version": "2.19.1" },
  "correlation": { "serial_number": "ABC1234", "system_uuid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
                   "bmc_ip": "10.x.x.201", "host_ip": null }
}
```

> **partial/failed 예시**: `schema/baseline_v1/` 및 `schema/examples/` 참조.
> partial은 일부 섹션만 failed, failed는 모든 supported 섹션이 failed.
