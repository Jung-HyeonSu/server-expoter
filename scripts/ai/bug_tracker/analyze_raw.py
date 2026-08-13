#!/usr/bin/env python3
"""Analyze captured raw data and verify each bug ticket.

Reads /tmp/se-raw (Redfish) and /tmp/se-raw-os (Linux) directories on Jenkins
agent (or local mirror) and outputs a per-ticket verification report.

For each ticket Bxx:
  - State the claim
  - Pull the relevant raw response field
  - Print: VERIFIED / NOT_REPRODUCED / N/A (no raw data available)

Output format: markdown report saved to docs/ai/tickets/2026-04-29-output-quality/VERIFICATION.md.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

REDFISH_ROOT_DEFAULT = Path("./se-raw-mirror/redfish")
LINUX_ROOT_DEFAULT = Path("./se-raw-mirror/linux")


def load_json(path: Path) -> dict | list | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return ""


def verify_b01_gpu_in_cpu(rf_root: Path) -> dict:
    """B01: GPU in CPU section. Check r760-1 Processors collection for non-CPU types."""
    found = {}
    for host_dir in sorted(rf_root.iterdir()) if rf_root.exists() else []:
        if not host_dir.is_dir():
            continue
        proc_dir = host_dir / "processors_members"
        if not proc_dir.exists():
            continue
        types = []
        for p in sorted(proc_dir.glob("*.json")):
            obj = load_json(p)
            if not obj:
                continue
            ptype = obj.get("ProcessorType")
            mfg = obj.get("Manufacturer")
            model = obj.get("Model")
            types.append({"id": p.stem, "ProcessorType": ptype, "Manufacturer": mfg, "Model": model})
        found[host_dir.name] = types
    return {
        "ticket": "B01",
        "claim": "GPU(Tesla T4)가 redfish CPU 섹션에 합쳐짐 (ProcessorType 필터 부재)",
        "raw_evidence": found,
        "verdict": "VERIFIED" if any(
            any(t.get("ProcessorType") and t["ProcessorType"] != "CPU" for t in tlist)
            for tlist in found.values()
        ) else ("NOT_REPRODUCED" if found else "NO_DATA"),
    }


def verify_b02_dns_unspecified(rf_root: Path) -> dict:
    """B02: DNS unspecified IP (0.0.0.0/::) in Redfish."""
    found = {}
    for host_dir in sorted(rf_root.iterdir()) if rf_root.exists() else []:
        if not host_dir.is_dir():
            continue
        # Manager EthernetInterfaces have NameServers
        mgr_dir = host_dir / "managers_members"
        if not mgr_dir.exists():
            continue
        ns_lists = []
        for f in sorted(mgr_dir.glob("*__eth_*.json")):
            obj = load_json(f)
            if not obj:
                continue
            ns = obj.get("NameServers") or obj.get("StaticNameServers") or []
            if ns:
                ns_lists.append({"file": f.name, "NameServers": ns})
        # NetworkProtocol may have DNS too
        for f in sorted(mgr_dir.glob("*__network_protocol.json")):
            obj = load_json(f)
            if obj:
                dns = (obj.get("DNS") or {})
                ns_lists.append({"file": f.name, "NameServers": dns.get("NameServers")})
        found[host_dir.name] = ns_lists
    has_unspec = False
    for h, lst in found.items():
        for entry in lst:
            ns = entry.get("NameServers") or []
            if isinstance(ns, list):
                for x in ns:
                    if x in ("0.0.0.0", "::", "0:0:0:0:0:0:0:0"):
                        has_unspec = True
    return {
        "ticket": "B02",
        "claim": "Redfish DNS unspecified IP(0.0.0.0/::) 그대로 노출",
        "raw_evidence": found,
        "verdict": "VERIFIED" if has_unspec else ("NOT_REPRODUCED" if found else "NO_DATA"),
    }


def verify_b09_memory_locator(rf_root: Path) -> dict:
    """B09: memory.slots[*].locator. Check Memory members for DeviceLocator/MemoryLocation."""
    found = {}
    for host_dir in sorted(rf_root.iterdir()) if rf_root.exists() else []:
        if not host_dir.is_dir():
            continue
        mem_dir = host_dir / "memory_members"
        if not mem_dir.exists():
            continue
        slots = []
        for f in sorted(mem_dir.glob("*.json"))[:6]:
            obj = load_json(f)
            if not obj:
                continue
            slots.append({
                "id": f.stem,
                "DeviceLocator": obj.get("DeviceLocator"),
                "MemoryLocation": obj.get("MemoryLocation"),
                "Manufacturer": obj.get("Manufacturer"),
                "OperatingSpeedMhz": obj.get("OperatingSpeedMhz"),
                "AllowedSpeedsMHz": obj.get("AllowedSpeedsMHz"),
                "PartNumber": obj.get("PartNumber"),
            })
        found[host_dir.name] = slots
    has_locator = any(any(s.get("DeviceLocator") or s.get("MemoryLocation") for s in lst) for lst in found.values())
    return {
        "ticket": "B09",
        "claim": "Redfish memory.slots[*].locator 모두 None — DeviceLocator/MemoryLocation 추출 누락",
        "raw_evidence": found,
        "verdict": "VERIFIED" if has_locator else ("NOT_REPRODUCED" if found else "NO_DATA"),
    }


def verify_b10_drive_capacity(rf_root: Path) -> dict:
    """B10: Drive.CapacityBytes. Check storage_members/*__drive_*.json."""
    found = {}
    for host_dir in sorted(rf_root.iterdir()) if rf_root.exists() else []:
        if not host_dir.is_dir():
            continue
        stg_dir = host_dir / "storage_members"
        if not stg_dir.exists():
            continue
        drives = []
        for f in sorted(stg_dir.glob("*__drive_*.json"))[:6]:
            obj = load_json(f)
            if not obj:
                continue
            drives.append({
                "id": f.stem,
                "CapacityBytes": obj.get("CapacityBytes"),
                "Model": obj.get("Model"),
                "MediaType": obj.get("MediaType"),
            })
        found[host_dir.name] = drives
    has_cap = any(any(d.get("CapacityBytes") for d in lst) for lst in found.values())
    return {
        "ticket": "B10",
        "claim": "Redfish Drive.CapacityBytes 추출 누락 (capacity_gb=None)",
        "raw_evidence": found,
        "verdict": "VERIFIED" if has_cap else ("NOT_REPRODUCED" if found else "NO_DATA"),
    }


def verify_b41_psu_count(rf_root: Path) -> dict:
    """B41: Dell PSU 1 vs actual count. Count Power.PowerSupplies members."""
    found = {}
    for host_dir in sorted(rf_root.iterdir()) if rf_root.exists() else []:
        if not host_dir.is_dir():
            continue
        power = load_json(host_dir / "power.json")
        if not power:
            continue
        psus = power.get("PowerSupplies") or []
        pc = power.get("PowerControl") or []
        found[host_dir.name] = {
            "psu_count": len(psus),
            "psu_names": [p.get("Name") or p.get("MemberId") for p in psus],
            "psu_health": [p.get("Status", {}).get("Health") for p in psus],
            "psu_capacity_w": [p.get("PowerCapacityWatts") for p in psus],
            "power_control_count": len(pc),
            "power_control_keys": [list(c.keys()) for c in pc[:2]] if pc else [],
        }
    return {
        "ticket": "B41/B45",
        "claim": "Dell PSU 1개 노출 — PS2 누락 의심",
        "raw_evidence": found,
        "verdict": "INSPECT_RAW",  # decision after looking at raw counts
    }


def verify_b58_psu_critical(rf_root: Path) -> dict:
    """B58: PSU Critical health不在 summary."""
    found = {}
    for host_dir in sorted(rf_root.iterdir()) if rf_root.exists() else []:
        if not host_dir.is_dir():
            continue
        power = load_json(host_dir / "power.json")
        if not power:
            continue
        psus = power.get("PowerSupplies") or []
        crit = [p for p in psus if (p.get("Status", {}) or {}).get("Health") == "Critical"]
        if crit:
            found[host_dir.name] = [
                {"Name": p.get("Name"), "Health": p.get("Status", {}).get("Health"),
                 "State": p.get("Status", {}).get("State"), "Manufacturer": p.get("Manufacturer")}
                for p in crit
            ]
    return {
        "ticket": "B58",
        "claim": "PSU.Status.Health=Critical인데 summary에 critical_count 노출 없음",
        "raw_evidence": found,
        "verdict": "VERIFIED" if found else "NO_CRITICAL_PSU_IN_LAB",
    }


def verify_b46_power_control_dict(rf_root: Path) -> dict:
    """B46: power.power_control = list of strings (builder bug, but raw should be list of dicts)."""
    found = {}
    for host_dir in sorted(rf_root.iterdir()) if rf_root.exists() else []:
        if not host_dir.is_dir():
            continue
        power = load_json(host_dir / "power.json")
        if not power:
            continue
        pc = power.get("PowerControl") or []
        found[host_dir.name] = {
            "power_control_count": len(pc),
            "first_item_type": type(pc[0]).__name__ if pc else None,
            "first_item_keys": list(pc[0].keys()) if pc and isinstance(pc[0], dict) else None,
            "sample_values": pc[:1],
        }
    return {
        "ticket": "B46",
        "claim": "envelope의 power.power_control이 list of strings 형태 — Redfish raw는 list of dicts",
        "raw_evidence": found,
        "verdict": "RAW_IS_DICT" if any(
            isinstance(v.get("first_item_type"), str) and v["first_item_type"] == "dict"
            for v in found.values()
        ) else "NO_DATA",
    }


def verify_b04_dns_systemd(linux_root: Path) -> dict:
    """B04: Ubuntu DNS=127.0.0.53 stub."""
    found = {}
    for host_dir in sorted(linux_root.iterdir()) if linux_root.exists() else []:
        if not host_dir.is_dir():
            continue
        rc = read_text(host_dir / "dns_resolv_conf.txt")
        rs = read_text(host_dir / "dns_resolvectl_status.txt")
        rd = read_text(host_dir / "dns_runtime_resolv.txt")
        found[host_dir.name] = {
            "resolv_conf_first3": [l for l in rc.splitlines() if not l.startswith("#") and l.strip()][:3],
            "resolvectl_dns_lines": [l.strip() for l in rs.splitlines() if "DNS Servers" in l or "Current DNS" in l][:3],
            "runtime_resolv_first3": [l for l in rd.splitlines() if not l.startswith("#") and l.strip()][:3],
        }
    return {
        "ticket": "B04",
        "claim": "Ubuntu DNS=127.0.0.53 (systemd-resolved stub) — /etc/resolv.conf만 보면 stub만 잡힘",
        "raw_evidence": found,
        "verdict": "INSPECT_RAW",
    }


def verify_b17_users(linux_root: Path) -> dict:
    """B17: Linux users.username=None — getent passwd 출력 vs 파싱 결과."""
    found = {}
    for host_dir in sorted(linux_root.iterdir()) if linux_root.exists() else []:
        if not host_dir.is_dir():
            continue
        getent = read_text(host_dir / "users_getent_passwd.txt")
        first_lines = [l for l in getent.splitlines() if l and ":" in l and not l.startswith("#")][:5]
        found[host_dir.name] = first_lines
    return {
        "ticket": "B17",
        "claim": "getent passwd 첫 컬럼이 username — 빌더 매핑 누락 의심",
        "raw_evidence": found,
        "verdict": "INSPECT_RAW",
    }


def verify_b19_baremetal_dmi(linux_root: Path) -> dict:
    """B19: r760-6 baremetal hardware 미수집 — dmidecode 출력 비교."""
    found = {}
    for host_dir in sorted(linux_root.iterdir()) if linux_root.exists() else []:
        if not host_dir.is_dir():
            continue
        chassis = read_text(host_dir / "dmi_chassis.txt")
        sysd = read_text(host_dir / "dmi_system.txt")
        manuf = read_text(host_dir / "dmi_manuf.txt")
        product = read_text(host_dir / "dmi_product.txt")
        serial = read_text(host_dir / "dmi_serial.txt")
        found[host_dir.name] = {
            "manuf": manuf.strip().splitlines()[-1] if manuf.strip() else "(empty)",
            "product": product.strip().splitlines()[-1] if product.strip() else "(empty)",
            "serial": serial.strip().splitlines()[-1] if serial.strip() else "(empty)",
            "chassis_present": "Chassis Information" in chassis,
            "system_present": "System Information" in sysd,
        }
    return {
        "ticket": "B19/B80",
        "claim": "Baremetal Linux의 dmidecode hardware 정보 미수집 (sections.hardware=not_supported)",
        "raw_evidence": found,
        "verdict": "INSPECT_RAW",
    }


def verify_b25_disk_capacity(linux_root: Path) -> dict:
    """B25: Linux disk capacity_gb=None — lsblk -b 출력 비교."""
    found = {}
    for host_dir in sorted(linux_root.iterdir()) if linux_root.exists() else []:
        if not host_dir.is_dir():
            continue
        lsblk = read_text(host_dir / "lsblk_disks.txt")
        sb = read_text(host_dir / "sys_block_size.txt")
        # Pull disk type rows
        disk_lines = [l for l in lsblk.splitlines() if "disk" in l.lower() and not l.startswith("#")][:5]
        found[host_dir.name] = {
            "lsblk_disk_lines": disk_lines,
            "sys_block_first3": [l for l in sb.splitlines() if l and not l.startswith("#")][:5],
        }
    return {
        "ticket": "B25",
        "claim": "Linux storage.physical_disks.capacity_gb=None — lsblk/sys block size 미사용",
        "raw_evidence": found,
        "verdict": "INSPECT_RAW",
    }


def verify_b26_b65_b66_filesystems(linux_root: Path) -> dict:
    """B26/B65/B66: filesystem fstype/free/read_only — df / findmnt / /proc/mounts."""
    found = {}
    for host_dir in sorted(linux_root.iterdir()) if linux_root.exists() else []:
        if not host_dir.is_dir():
            continue
        df = read_text(host_dir / "df_T.txt")
        findmnt = read_text(host_dir / "findmnt.txt")
        mounts = read_text(host_dir / "proc_mounts.txt")
        # Sample
        df_lines = [l for l in df.splitlines() if l and not l.startswith("#") and "Filesystem" not in l][:4]
        findmnt_lines = [l for l in findmnt.splitlines() if l and not l.startswith("#") and "TARGET" not in l][:4]
        mount_lines = [l for l in mounts.splitlines() if l and not l.startswith("#")][:4]
        found[host_dir.name] = {
            "df_T_sample": df_lines,
            "findmnt_sample": findmnt_lines,
            "proc_mounts_sample": mount_lines,
        }
    return {
        "ticket": "B26/B65/B66",
        "claim": "Linux fs.fstype/free_mb/read_only=None — df -T / findmnt / /proc/mounts 미사용",
        "raw_evidence": found,
        "verdict": "INSPECT_RAW",
    }


def verify_b68_ipv6(linux_root: Path) -> dict:
    """B68: IPv6 addresses — ip -6 addr 출력 vs envelope 노출."""
    found = {}
    for host_dir in sorted(linux_root.iterdir()) if linux_root.exists() else []:
        if not host_dir.is_dir():
            continue
        ip6 = read_text(host_dir / "ip6_addr.txt")
        # Count link-local + global
        ll = sum(1 for l in ip6.splitlines() if "fe80::" in l)
        glob = sum(1 for l in ip6.splitlines() if "inet6" in l and "fe80::" not in l and "::1" not in l)
        found[host_dir.name] = {"link_local": ll, "global": glob}
    return {
        "ticket": "B68",
        "claim": "Linux interfaces.addresses에 IPv6 0개 — ip -6 addr 미사용",
        "raw_evidence": found,
        "verdict": "INSPECT_RAW",
    }


def verify_b78_b80_serial_vendor(linux_root: Path) -> dict:
    """B78/B80: VM serial 정규화 + envelope.vendor=None."""
    found = {}
    for host_dir in sorted(linux_root.iterdir()) if linux_root.exists() else []:
        if not host_dir.is_dir():
            continue
        s = read_text(host_dir / "dmi_serial.txt").strip().splitlines()
        m = read_text(host_dir / "dmi_manuf.txt").strip().splitlines()
        found[host_dir.name] = {
            "serial": s[-1] if s else "(empty)",
            "manuf": m[-1] if m else "(empty)",
        }
    return {
        "ticket": "B78/B80",
        "claim": "Linux VM serial 길고(정규화 필요), 베어메탈 envelope.vendor=None (dmidecode 미사용)",
        "raw_evidence": found,
        "verdict": "INSPECT_RAW",
    }


CHECKS = [
    verify_b01_gpu_in_cpu,
    verify_b02_dns_unspecified,
    verify_b09_memory_locator,
    verify_b10_drive_capacity,
    verify_b41_psu_count,
    verify_b46_power_control_dict,
    verify_b58_psu_critical,
    verify_b04_dns_systemd,
    verify_b17_users,
    verify_b19_baremetal_dmi,
    verify_b25_disk_capacity,
    verify_b26_b65_b66_filesystems,
    verify_b68_ipv6,
    verify_b78_b80_serial_vendor,
]


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--rf-root", default=str(REDFISH_ROOT_DEFAULT))
    p.add_argument("--linux-root", default=str(LINUX_ROOT_DEFAULT))
    p.add_argument("--out", default="docs/ai/bug-verification.md")
    a = p.parse_args()

    rf_root = Path(a.rf_root)
    linux_root = Path(a.linux_root)

    redfish_checks = [verify_b01_gpu_in_cpu, verify_b02_dns_unspecified, verify_b09_memory_locator,
                      verify_b10_drive_capacity, verify_b41_psu_count, verify_b46_power_control_dict,
                      verify_b58_psu_critical]
    linux_checks = [verify_b04_dns_systemd, verify_b17_users, verify_b19_baremetal_dmi,
                    verify_b25_disk_capacity, verify_b26_b65_b66_filesystems, verify_b68_ipv6,
                    verify_b78_b80_serial_vendor]

    results = []
    for fn in redfish_checks:
        results.append(fn(rf_root))
    for fn in linux_checks:
        results.append(fn(linux_root))

    md = ["# 2026-04-29 Bug Ticket Verification Report\n",
          f"raw_redfish_root: `{rf_root}` (exists: {rf_root.exists()})",
          f"raw_linux_root: `{linux_root}` (exists: {linux_root.exists()})\n"]
    for r in results:
        md.append(f"\n---\n## {r['ticket']}: {r['verdict']}")
        md.append(f"\n**Claim**: {r['claim']}\n")
        md.append("\n```json\n" + json.dumps(r["raw_evidence"], indent=2, ensure_ascii=False)[:3500] + "\n```\n")

    out_path = Path(a.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(md), encoding="utf-8")
    print(f"wrote {out_path} ({len(results)} checks)")

    # Console summary
    print("\nSUMMARY:")
    for r in results:
        print(f"  {r['ticket']:14s} -> {r['verdict']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
