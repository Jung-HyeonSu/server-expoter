# tests/reference/esxi/ — ESXi 종합 정보 reference

## 수집 도구

`tests/reference/scripts/gather_esxi_full.py` — paramiko SSH (esxcli/vim-cmd) + pyvmomi (vSphere API).

## 수집 항목

### SSH 통한 esxcli / vim-cmd (~50개)

- **System**: vmware -v/-l, hostname, uptime, esxcli system version/uuid/hostname/module/settings (advanced/kernel)/stats uptime/account
- **Hardware**: esxcli hardware platform/cpu (global/list)/memory/pci/clock/bootdevice/trustedboot
- **Storage**: esxcli storage core (device/path)/filesystem/vmfs (extent/snapshot)/nvme (controller/namespace)/iscsi/san fc+sas
- **Network**: esxcli network nic/ip (interface/ipv4/route)/dns/vswitch (standard/dvs)/portgroup/firewall
- **Software**: esxcli software vib/profile/baseimage
- **VM**: esxcli vm process
- **vSAN**: esxcli vsan (storage/cluster)
- **IPMI** (deprecated): esxcli hardware ipmi (sel/fru)
- **Host Daemon**: vim-cmd hostsvc (hosthardware/hostsummary/service status_all), vmsvc/getallvms
- **Logs**: tail /var/log/vmkernel.log, hostd.log, vobd.log
- **Config**: /etc/vmware/esx.conf, services.xml

### pyvmomi (vSphere API)

`pyvmomi_host_dump.json` — host object 전체 dump:
- name / hardware_systemInfo / config_product / runtime
- network: pnic / vnic / vswitch / portgroup
- storage: device (scsiLun) / hba / filesystem
- service / firewall_rules / dns_config
- host_summary

## 디렉터리 컨벤션

```text
tests/reference/esxi/<ip-with-underscore>/
├── _manifest.json
├── pyvmomi_host_dump.json
└── esxcli_<name>.txt
```

## 수집 대상 (2026-04-28)

| IP | SSH | vSphere API | 비고 |
|---|---|---|---|
| 10.100.64.1 | FAIL (port 22 closed) | OK | SSH 비활성화. ESXi 기본 상태 — 활성화 시 esxcli 53종 추가 가능 |
| 10.100.64.2 | OK | OK | 53 esxcli + pyvmomi |
| 10.100.64.3 | FAIL (port 22 closed) | OK | SSH 비활성화 |

**SSH 활성화 방법**: vSphere Web Client → Host → Configure → Services → SSH → Start

## 활용

1. **esxi-gather adapter 검증**: adapters/esxi/*.yml의 capabilities ↔ 실 esxcli 출력
2. **community.vmware 매핑 확인**: pyvmomi_host_dump.json ↔ Ansible vmware_host_facts 결과

## 재실행

```bash
wsl python3 tests/reference/scripts/gather_esxi_full.py --skip-existing
wsl python3 tests/reference/scripts/gather_esxi_full.py --target esxi-10.100.64.1
```
