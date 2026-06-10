# tests/reference/os/ — OS 종합 정보 reference

## 수집 도구

`tests/reference/scripts/gather_os_full.py` — paramiko SSH (Linux) + pywinrm (Windows) + ansible setup.

## 수집 항목

### Linux (~80개 명령)

- **System ID**: hostnamectl, uname, /etc/os-release, /etc/redhat-release, machine-id, uptime, timedatectl
- **Hardware (DMI/SMBIOS)**: dmidecode 7종 (system / chassis / baseboard / processor / memory / bios / oem-strings) — sudo 필요
- **CPU**: lscpu (-J / -e), /proc/cpuinfo, scaling_cur_freq
- **Memory**: /proc/meminfo, free -h, vmstat, swapon
- **Storage**: lsblk -JO, df -hT, findmnt -J, blkid, smartctl --scan/-a, nvme list, /proc/mdstat, LVM (pvs/vgs/lvs), multipath -ll, storcli (RAID)
- **Network**: ip -j (addr/link/route/route6/neigh/tunnel/vrf), bridge (link/vlan), bonding, ss -tlnp/-tnp estab, ethtool (-i/-k 전 NIC), nmcli, /etc/resolv.conf, /etc/hosts, /etc/nsswitch.conf, iptables, nftables, firewalld
- **PCI/USB/OEM**: lspci -vv/-nn/-tv, lsusb -v/-t, lshw -json/-short, inxi -Fxz, hwinfo --short
- **BIOS/Firmware**: biosdecode, /sys/firmware/efi/efivars, ipmitool (mc/lan/sel/sensor/chassis/fru), racadm (Dell)
- **Kernel/Module**: /proc/cmdline, lsmod, dmesg -T, sysctl -a
- **Services/Process**: systemctl (list-units/--failed/list-timers), ps auxfww, crontab/cron.d
- **Packages**: rpm -qa, dpkg -l, yum/dnf repolist, apt sources
- **Users/Auth**: getent passwd/group, sshd_config, sudoers, getenforce/sestatus, aa-status, who/w/last
- **Time/Locale**: locale, /etc/locale.conf, chrony/ntpq/timedatectl
- **Container/Virt**: virt-what, systemd-detect-virt, docker/podman/k8s
- **Logs**: tail messages/syslog, journalctl -p err

### Windows (~30개 PowerShell 명령)

- **System**: Win32_OperatingSystem, Win32_ComputerSystem, Win32_BIOS, Win32_BaseBoard, Win32_SystemEnclosure
- **Hardware**: Win32_Processor, Win32_PhysicalMemory, Win32_DiskDrive, Win32_LogicalDisk, Win32_Volume, Win32_DiskPartition, Win32_VideoController
- **Network**: Get-NetAdapter, Get-NetIPConfiguration, Get-DnsClientServerAddress, Get-NetRoute, Get-NetFirewallProfile
- **OS**: Get-Service, Get-Process, Get-HotFix, systeminfo, ipconfig /all, netstat -ano, powercfg /list
- **Driver**: Win32_PnPSignedDriver
- **Logs**: Get-WinEvent (System errors)
- **Users**: Get-LocalUser, Get-LocalGroup
- **Features**: Get-WindowsOptionalFeature

### Ansible

- `ansible_setup.json` — `ansible -m setup` 모듈 전체 facts 출력 (~40-100KB per host)

## 디렉터리 컨벤션

```text
tests/reference/os/<distro>/<ip-with-underscore>/
├── _manifest.json
├── _summary.txt
├── ansible_setup.json   (Linux) / setup.json (Windows)
└── cmd_<name>.txt        (Linux shell + Windows PowerShell 명령 출력)
```

각 파일 헤더:
```text
# command: <원본 명령>
# rc: <exit code>
# requires_root: <true/false>
# fetched: <ISO timestamp>
#
<출력>
# === stderr ===
<stderr 있을 시>
```

## 수집 대상 (2026-04-28 1차)

| Distro | IP | OS |
|---|---|---|
| RHEL 8.10 | 10.100.64.161 | VM |
| RHEL 9.2 | 10.100.64.163 | VM |
| RHEL 9.6 | 10.100.64.165 | VM |
| Ubuntu 24.04 | 10.100.64.167 | VM |
| Rocky 9.6 | 10.100.64.169 | VM |
| Windows Server 2022 | 10.100.64.135 | VM (WinRM 5985 NTLM) |
| RHEL bare-metal | 10.100.64.96 | 베어메탈 (Dell 10.100.15.33 BMC) |

## 활용

1. **Linux 2-tier (Python ok / raw fallback) 검증**: cmd_python_versions.txt vs ansible_setup.json
2. **새 distro 추가 시 비교**: 기존 OS의 cmd 출력을 baseline으로
3. **field_dictionary 매핑 검증**: cmd_dmidecode_*.txt → schema의 system.serial / hardware.model 등 매핑 정합
4. **Bare-metal vs VM 차이**: cmd_dmidecode_system.txt → manufacturer / product comparison

## 재실행

```bash
wsl python3 tests/reference/scripts/gather_os_full.py --skip-existing
wsl python3 tests/reference/scripts/gather_os_full.py --target rhel810-10.100.64.161
wsl python3 tests/reference/scripts/gather_os_full.py --linux-only
wsl python3 tests/reference/scripts/gather_os_full.py --windows-only
wsl python3 tests/reference/scripts/gather_os_full.py --parallel 5
```
