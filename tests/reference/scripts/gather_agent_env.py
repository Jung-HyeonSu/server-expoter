#!/usr/bin/env python3
"""gather_agent_env.py — Jenkins agent + master 환경 정보 수집.

목적: ansible / python / collection / pip 패키지 / OS / 네트워크 등
      Jenkins 인프라 환경을 시스템 가이드 (REQUIREMENTS.md) 검증용으로 캡처.

사용:
    wsl python3 tests/reference/scripts/gather_agent_env.py
    wsl python3 tests/reference/scripts/gather_agent_env.py --target agent-10.100.64.154
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    import yaml  # type: ignore
except ImportError:
    print("ERROR: PyYAML required", file=sys.stderr)
    sys.exit(2)

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


REPO_ROOT = Path(__file__).resolve().parents[3]
TARGETS_FILE = REPO_ROOT / "tests" / "reference" / "local" / "targets.yaml"
OUTPUT_BASE = REPO_ROOT / "tests" / "reference" / "agent"

AGENT_COMMANDS: list[tuple[str, str, bool]] = [
    # name, cmd, requires_root
    ("os_release",        "cat /etc/os-release",                                       False),
    ("uname",             "uname -a",                                                  False),
    ("hostnamectl",       "hostnamectl status 2>&1",                                   False),
    ("uptime",            "uptime",                                                    False),
    # Java
    ("java_version",      "java -version 2>&1; readlink -f $(which java) 2>&1",        False),
    ("java_alt",          "update-alternatives --display java 2>&1",                   False),
    # Python
    ("python_versions",   "for p in python python2 python3 python3.9 python3.10 python3.11 python3.12 /opt/ansible-env/bin/python; do echo '=== '$p' ==='; $p --version 2>&1; readlink -f $(which $p 2>/dev/null) 2>/dev/null; done", False),
    ("pip_freeze_default","pip3 freeze 2>&1 | sort",                                   False),
    ("pip_freeze_ansible_env", "/opt/ansible-env/bin/pip freeze 2>&1 | sort",          False),
    # Ansible
    ("ansible_version",   "ansible --version 2>&1",                                    False),
    ("ansible_config_dump","ansible-config dump --only-changed 2>&1",                  False),
    ("ansible_collections","ansible-galaxy collection list 2>&1",                      False),
    ("ansible_roles",     "ansible-galaxy role list 2>&1",                             False),
    # Jenkins
    ("jenkins_status",    "systemctl status jenkins 2>&1; ls -la /var/lib/jenkins/ 2>&1 | head -30", True),
    ("jenkins_user",      "id jenkins 2>&1; getent passwd jenkins 2>&1",               False),
    ("jenkins_jobs",      "ls /var/lib/jenkins/jobs/ 2>&1",                            True),
    # Network
    ("ip_addr",           "ip -j addr 2>&1",                                           False),
    ("ip_route",          "ip -j route 2>&1",                                          False),
    ("resolv_conf",       "cat /etc/resolv.conf",                                      False),
    ("hosts_file",        "cat /etc/hosts",                                            False),
    ("listening_ports",   "ss -tlnp 2>&1",                                             True),
    ("firewall_state",    "firewall-cmd --list-all 2>&1; iptables -L -n 2>&1 | head -50", True),
    # Filesystem / Disk
    ("disk_layout",       "lsblk -fJ 2>&1",                                            False),
    ("df_h",              "df -hT",                                                    False),
    ("mount",             "mount",                                                     False),
    # Project structure
    ("se_project_layout", "ls -la /home/cloviradmin/server-exporter/ 2>&1; ls -la /opt/server-exporter/ 2>&1", False),
    ("ansible_cfg",       "find / -name 'ansible.cfg' 2>/dev/null | head -10; cat /etc/ansible/ansible.cfg 2>&1 | head -100", False),
    # Vault
    ("vault_files",       "find / -name 'vault.yml' 2>/dev/null | head -20; find / -path '*/vault/*' -name '*.yml' 2>/dev/null | head -20", False),
    # Tools
    ("smartctl",          "smartctl --version 2>&1 | head -3",                         False),
    ("ipmitool",          "ipmitool -V 2>&1",                                          False),
    ("nvme_cli",          "nvme version 2>&1",                                         False),
    ("racadm",            "racadm version 2>&1; which racadm 2>&1",                   False),
    ("storcli",           "/opt/MegaRAID/storcli/storcli64 version 2>&1; storcli version 2>&1", False),
    # Redis (per `docs/operate/02-agent-node.md`)
    ("redis_status",      "systemctl status redis 2>&1; redis-cli ping 2>&1; redis-cli info server 2>&1 | head -20", False),
    # Time
    ("time_sync",         "timedatectl 2>&1; chronyc sources 2>&1; chronyc tracking 2>&1", False),
    # Process
    ("running_processes", "ps -eo pid,ppid,user,comm,cmd | head -100",                 False),
    # System resource
    ("cpu_summary",       "lscpu",                                                     False),
    ("memory_summary",    "free -h",                                                   False),
    # Logs
    ("journal_recent",    "journalctl -p err -b --no-pager 2>&1 | tail -50",           True),
]


def load_targets() -> dict[str, Any]:
    if not TARGETS_FILE.exists():
        print(f"ERROR: {TARGETS_FILE} 없음", file=sys.stderr)
        sys.exit(2)
    with TARGETS_FILE.open(encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_ssh(host: str, user: str, password: str, cmd: str, timeout: int = 60, become: bool = False, become_pw: str | None = None) -> tuple[int, str, str]:
    try:
        import paramiko
    except ImportError:
        return -1, "", "paramiko required"
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(host, username=user, password=password, timeout=15, banner_timeout=15, auth_timeout=15, look_for_keys=False, allow_agent=False)
    except Exception as e:
        return -1, "", f"SSH connect fail: {e}"
    try:
        if become and become_pw:
            qc = "'" + cmd.replace("'", "'\"'\"'") + "'"
            full = f"sudo -S -p '' bash -c {qc}"
            stdin, stdout, stderr = client.exec_command(full, timeout=timeout, get_pty=True)
            stdin.write(become_pw + "\n")
            stdin.flush()
        else:
            _, stdout, stderr = client.exec_command(cmd, timeout=timeout)
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")
        rc = stdout.channel.recv_exit_status()
        return rc, out, err
    except Exception as e:
        return -1, "", f"exec fail: {e}"
    finally:
        client.close()


def gather_one(target: dict[str, Any], role: str, skip_existing: bool = False) -> dict[str, Any]:
    name = target["name"]
    ip = target["ip"]
    user = target["user"]
    password = target["password"]
    become_pw = target.get("become_password", password)

    out_dir = OUTPUT_BASE / role / ip.replace(".", "_")
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"\n=== {role}: {name} ({ip}) → {out_dir.relative_to(REPO_ROOT)} ===")

    summary: dict[str, Any] = {"target": name, "ip": ip, "role": role,
                                "started_at": datetime.now(timezone.utc).isoformat(),
                                "commands": [], "errors": []}
    started = time.monotonic()

    rc, _, err = run_ssh(ip, user, password, "echo OK", timeout=15)
    if rc != 0:
        summary["errors"].append({"step": "connect", "rc": rc, "err": err})
        print(f"  CONNECT FAIL: {err}")
        return summary
    print(f"  CONNECT OK")

    for cmd_name, cmd, requires_root in AGENT_COMMANDS:
        out_file = out_dir / f"cmd_{cmd_name}.txt"
        if skip_existing and out_file.exists() and out_file.stat().st_size > 0:
            summary["commands"].append({"name": cmd_name, "status": "cached"})
            continue
        rc, out, err = run_ssh(ip, user, password, cmd, timeout=120, become=requires_root, become_pw=become_pw)
        with out_file.open("w", encoding="utf-8") as f:
            f.write(f"# command: {cmd}\n# rc: {rc}\n# requires_root: {requires_root}\n# fetched: {datetime.now(timezone.utc).isoformat()}\n#\n")
            f.write(out)
            if err.strip():
                f.write("\n# === stderr ===\n")
                f.write(err)
        summary["commands"].append({"name": cmd_name, "rc": rc, "size": len(out)})
        tag = "OK" if rc == 0 else f"rc={rc}"
        print(f"  [{tag:8s}] {cmd_name:30s} ({len(out):6d}b)")

    summary["elapsed_seconds"] = round(time.monotonic() - started, 1)
    summary["completed_at"] = datetime.now(timezone.utc).isoformat()
    (out_dir / "_manifest.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target")
    parser.add_argument("--role", choices=["agent", "jenkins_master", "all"], default="all")
    parser.add_argument("--skip-existing", action="store_true")
    args = parser.parse_args()

    doc = load_targets()
    todo: list[tuple[dict[str, Any], str]] = []
    if args.role in ("all", "agent"):
        for t in doc.get("agent", []):
            todo.append((t, "agent"))
    if args.role in ("all", "jenkins_master"):
        for t in doc.get("jenkins_master", []):
            todo.append((t, "jenkins_master"))

    if args.target:
        todo = [(t, r) for t, r in todo if t["name"] == args.target]

    OUTPUT_BASE.mkdir(parents=True, exist_ok=True)
    print(f"agent/master gather — {len(todo)} target(s)")

    results = []
    for t, role in todo:
        try:
            results.append(gather_one(t, role, args.skip_existing))
        except Exception as e:
            results.append({"target": t["name"], "error": str(e)})

    print(f"\n{'='*60}\n  TOTAL\n{'='*60}")
    for r in results:
        if "error" in r:
            print(f"  ERROR  {r['target']}: {r['error']}")
        else:
            print(f"  {r['target']:30s} cmds={len(r.get('commands',[])):3d} err={len(r.get('errors',[])):2d} elapsed={r.get('elapsed_seconds',0):.0f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
