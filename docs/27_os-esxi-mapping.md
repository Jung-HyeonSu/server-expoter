# 27. OS / ESXi raw → normalize → output 매핑 표

---

### Linux (Ubuntu)

| Output Field | Raw Source | Normalize File | 비고 |
|---|---|---|---|
| `system.os_family` | `ansible_os_family` (setup) | `gather_system.yml` | |
| `system.distribution` | `ansible_distribution` | `gather_system.yml` | |
| `system.version` | `ansible_distribution_version` | `gather_system.yml` | |
| `system.kernel` | `ansible_kernel` | `gather_system.yml` | |
| `system.architecture` | `ansible_architecture` | `gather_system.yml` | |
| `system.uptime_seconds` | `ansible_uptime_seconds \| int` | `gather_system.yml` | |
| `system.selinux` | `ansible_selinux.status` | `gather_system.yml` | |
| `system.fqdn` | `ansible_fqdn` | `gather_system.yml` | |
| `cpu.sockets` | `ansible_processor_count` | `gather_cpu.yml` | |
| `cpu.cores_physical` | `shell grep "cpu cores" × sockets` | `gather_cpu.yml` | |
| `cpu.logical_threads` | `ansible_processor_vcpus` | `gather_cpu.yml` | |
| `cpu.model` | `shell grep "model name"` | `gather_cpu.yml` | |
| `cpu.architecture` | `ansible_architecture` | `gather_cpu.yml` | system.architecture와 동일 값 |
| `memory.total_mb` | `ansible_memtotal_mb` | `gather_memory.yml` | |
| `memory.total_basis` | hardcoded `"os_visible"` | `gather_memory.yml` | |
| `storage.physical_disks[]` | `lsblk -J` | `gather_storage.yml` | |
| `storage.filesystems[]` | `df -BM` | `gather_storage.yml` | |
| `network.interfaces[]` | `ansible_interfaces` + `ansible_{iface}` | `gather_network.yml` | |
| `network.default_gateways[]` | `ansible_default_ipv4.gateway` | `gather_network.yml` | |
| `users[]` | `getent passwd` + `last`/`lastlog` | `gather_users.yml` | |

---

### Windows

| Output Field | Raw Source | Normalize File | 비고 |
|---|---|---|---|
| `system.os_family` | `ansible_os_family` (setup) | `gather_system.yml` | WMI |
| `system.distribution` | `ansible_distribution` | `gather_system.yml` | WMI |
| `system.version` | `ansible_distribution_version` | `gather_system.yml` | WMI |
| `system.kernel` | `ansible_kernel` | `gather_system.yml` | WMI |
| `system.architecture` | `ansible_architecture` (정규화 적용) | `gather_system.yml` | "64비트"/"64-bit"/"AMD64"→"x86_64" 매핑 |
| `system.uptime_seconds` | `ansible_uptime_seconds \| int` | `gather_system.yml` | WMI |
| `system.selinux` | N/A | `gather_system.yml` | Windows에는 SELinux 없음 → null |
| `system.fqdn` | `ansible_fqdn` | `gather_system.yml` | WMI |
| `cpu.sockets` | `Win32_Processor` (WMI) | `gather_cpu.yml` | WMI |
| `cpu.cores_physical` | `Win32_Processor.NumberOfCores` | `gather_cpu.yml` | WMI |
| `cpu.logical_threads` | `Win32_Processor.NumberOfLogicalProcessors` | `gather_cpu.yml` | WMI |
| `cpu.model` | `Win32_Processor.Name` | `gather_cpu.yml` | WMI |
| `cpu.architecture` | `ansible_architecture` (정규화 적용) | `gather_cpu.yml` | `'64' in _arch` 조건으로 "64비트"→"x86_64" 매핑 |
| `memory.total_mb` | `Win32_ComputerSystem.TotalPhysicalMemory` | `gather_memory.yml` | WMI |
| `memory.total_basis` | hardcoded `"physical_installed"` | `gather_memory.yml` | |
| `storage.physical_disks[]` | `Win32_DiskDrive` | `gather_storage.yml` | WMI |
| `storage.filesystems[]` | `Win32_LogicalDisk` | `gather_storage.yml` | WMI |
| `network.interfaces[]` | `Win32_NetworkAdapterConfiguration` | `gather_network.yml` | WMI |
| `network.default_gateways[]` | `Win32_NetworkAdapterConfiguration.DefaultIPGateway` | `gather_network.yml` | WMI |
| `users[]` | `Win32_UserAccount` + `Win32_NetworkLoginProfile` | `gather_users.yml` | WMI |

---

### ESXi

| Output Field | Raw Source | Normalize File | 비고 |
|---|---|---|---|
| `system.os_family` | `vmware_host_facts` → `ansible_distribution` | `gather_system.yml` | vSphere API |
| `system.distribution` | `vmware_host_facts` → `ansible_distribution` | `gather_system.yml` | vSphere API |
| `system.version` | `vmware_host_facts` → `ansible_distribution_version` | `gather_system.yml` | vSphere API |
| `system.kernel` | `vmware_host_facts` → build number | `gather_system.yml` | vSphere API |
| `system.architecture` | `vmware_host_facts` → `ansible_processor[0]` | `gather_system.yml` | vSphere API |
| `system.uptime_seconds` | `vmware_host_facts` → uptime | `gather_system.yml` | vSphere API |
| `system.selinux` | N/A | `gather_system.yml` | ESXi에는 SELinux 없음 → null |
| `system.fqdn` | `vmware_host_facts` → FQDN | `gather_system.yml` | vSphere API |
| `hardware.vendor` | `vmware_host_facts` → `ansible_system_vendor` | `gather_hardware.yml` | vSphere API |
| `hardware.model` | `vmware_host_facts` → `ansible_product_name` | `gather_hardware.yml` | vSphere API |
| `hardware.serial` | `vmware_host_facts` → `ansible_product_serial` | `gather_hardware.yml` | vSphere API |
| `hardware.uuid` | `vmware_host_facts` → `ansible_product_uuid` | `gather_hardware.yml` | vSphere API |
| `hardware.bios_version` | `vmware_host_facts` → `ansible_bios_version` | `gather_hardware.yml` | vSphere API |
| `hardware.bios_date` | `vmware_host_facts` → `ansible_bios_date` | `gather_hardware.yml` | vSphere API |
| `cpu.sockets` | `vmware_host_facts` → `ansible_processor_count` | `gather_cpu.yml` | vSphere API |
| `cpu.cores_physical` | `vmware_host_facts` → `ansible_processor_cores` | `gather_cpu.yml` | vSphere API |
| `cpu.logical_threads` | `vmware_host_facts` → `ansible_processor_vcpus` | `gather_cpu.yml` | vSphere API |
| `cpu.model` | `vmware_host_facts` → processor model | `gather_cpu.yml` | vSphere API |
| `cpu.architecture` | N/A | — | 현재 null — 추가 확인 필요 |
| `memory.total_mb` | `vmware_host_facts` → `ansible_memtotal_mb` | `gather_memory.yml` | vSphere API |
| `memory.total_basis` | hardcoded `"hypervisor_visible"` | `gather_memory.yml` | |
| `storage.datastores[]` | `vmware_host_facts` → datastore info | `gather_storage.yml` | vSphere API |
| `network.interfaces[]` | `vmware_host_facts` → vmkernel interfaces | `gather_network.yml` | vSphere API |
| `network.default_gateways[]` | `vmware_host_facts` → default gateway | `gather_network.yml` | vSphere API |

---

### Redfish와의 차이점

| 채널 | system | hardware | bmc | cpu | memory | storage | network | firmware | users | power |
|------|--------|----------|-----|-----|--------|---------|---------|----------|-------|-------|
| **Redfish** | not_supported | success | success | success | success | success | success | success | not_supported | success |
| **OS** | success | not_supported | not_supported | success | success | success | success | not_supported | success | not_supported |
| **ESXi** | success | success | not_supported | success | success | success | success | not_supported | not_supported | not_supported |
