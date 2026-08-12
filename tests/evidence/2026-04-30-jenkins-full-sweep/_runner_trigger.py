"""Trigger hshwang-gather Jenkins job from master 10.100.64.152.

Coverage: 3 channels (os/esxi/redfish) — all reachable hosts.
Outputs:
  _build_<channel>.json   — build metadata
  _console_<channel>.txt  — last 5000 lines console log
  _envelope_<channel>.jsonl — extracted JSON envelopes
"""
from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path

import paramiko

if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

MASTER = "10.100.64.152"
SSH_USER = "cloviradmin"
SSH_PASS = os.environ.get("LAB_SSH_PASS", "__REDACTED__")
JK_URL = "http://localhost:8080"
JK_USER = "cloviradmin"
JK_PASS = SSH_PASS
JOB = "hshwang-gather"
LOC = "ich"

OUT = Path("tests/evidence/2026-04-30-jenkins-full-sweep")
OUT.mkdir(parents=True, exist_ok=True)

INVENTORY = {
    "redfish": [
        {"bmc_ip": "10.100.15.27"},
        {"bmc_ip": "10.100.15.28"},
        {"bmc_ip": "10.100.15.31"},
        {"bmc_ip": "10.100.15.33"},
        {"bmc_ip": "10.100.15.34"},
        {"bmc_ip": "10.50.11.231"},
        {"bmc_ip": "10.50.11.232"},
        {"bmc_ip": "10.100.15.2"},
        {"bmc_ip": "10.50.11.162"},
    ],
    "os": [
        {"service_ip": "10.100.64.96"},
        {"service_ip": "10.100.64.135"},
        {"service_ip": "10.100.64.161"},
        {"service_ip": "10.100.64.163"},
        {"service_ip": "10.100.64.165"},
        {"service_ip": "10.100.64.167"},
        {"service_ip": "10.100.64.169"},
    ],
    "esxi": [
        {"service_ip": "10.100.64.1"},
        {"service_ip": "10.100.64.2"},
        {"service_ip": "10.100.64.3"},
    ],
}


def _client() -> paramiko.SSHClient:
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(
        MASTER,
        username=SSH_USER,
        password=SSH_PASS,
        timeout=15,
        allow_agent=False,
        look_for_keys=False,
    )
    return c


def ssh_exec(cmd: str, timeout: int = 60) -> tuple[str, str, int]:
    c = _client()
    try:
        si, so, se = c.exec_command(cmd, timeout=timeout)
        out = so.read().decode("utf-8", errors="replace")
        err = se.read().decode("utf-8", errors="replace")
        rc = so.channel.recv_exit_status()
        return out, err, rc
    finally:
        c.close()


def get_crumb() -> tuple[str, str]:
    out, _, _ = ssh_exec(
        f"curl -sS -m 10 -u '{JK_USER}:{JK_PASS}' -c /tmp/jcookie.txt "
        f"'{JK_URL}/crumbIssuer/api/json'"
    )
    data = json.loads(out)
    return data["crumb"], data["crumbRequestField"]


def get_next_build_number() -> int:
    out, _, _ = ssh_exec(
        f"curl -sS -m 10 -u '{JK_USER}:{JK_PASS}' "
        f"'{JK_URL}/job/{JOB}/api/json?tree=nextBuildNumber'"
    )
    return json.loads(out)["nextBuildNumber"]


def trigger_build(channel: str) -> int:
    crumb, crumb_field = get_crumb()
    expected = get_next_build_number()
    inv_json = json.dumps(INVENTORY[channel])
    inv_file = f"/tmp/inv_{channel}.json"
    write_cmd = f"cat > {inv_file} <<'INVEOF'\n{inv_json}\nINVEOF"
    ssh_exec(write_cmd)

    trig = (
        f"curl -sS -m 30 -u '{JK_USER}:{JK_PASS}' "
        f"-b /tmp/jcookie.txt "
        f"-H '{crumb_field}: {crumb}' "
        f"-X POST '{JK_URL}/job/{JOB}/buildWithParameters' "
        f"--data-urlencode 'loc={LOC}' "
        f"--data-urlencode 'target_type={channel}' "
        f"--data-urlencode inventory_json@{inv_file} "
        f"-w 'HTTP:%{{http_code}}\\n'"
    )
    out, err, rc = ssh_exec(trig)
    print(f"[{channel}] triggered (expect #{expected}) rc={rc} resp={out[-100:].strip()}")
    return expected


def wait_for_build(channel: str, build_num: int, max_wait: int = 1800) -> dict:
    print(f"[{channel}] waiting for #{build_num} (max {max_wait}s)...")
    start = time.time()
    while time.time() - start < max_wait:
        out, _, _ = ssh_exec(
            f"curl -sS -m 10 -u '{JK_USER}:{JK_PASS}' "
            f"'{JK_URL}/job/{JOB}/{build_num}/api/json?tree=number,result,building,duration,timestamp'"
        )
        try:
            data = json.loads(out)
        except Exception:
            time.sleep(15)
            continue
        if data.get("building"):
            elapsed = int(time.time() - start)
            print(f"[{channel}] #{build_num} building ({elapsed}s)...")
            time.sleep(20)
            continue
        if data.get("result"):
            print(f"[{channel}] DONE #{build_num} result={data['result']} duration={data['duration']/1000:.1f}s")
            return data
        time.sleep(15)
    raise TimeoutError(f"[{channel}] build #{build_num} timed out")


def fetch_console(channel: str, build_num: int) -> str:
    out, _, _ = ssh_exec(
        f"curl -sS -m 30 -u '{JK_USER}:{JK_PASS}' "
        f"'{JK_URL}/job/{JOB}/{build_num}/consoleText'",
        timeout=120,
    )
    return out


def extract_envelopes(console: str) -> list[dict]:
    envelopes = []
    for line in console.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        if '"target_type"' not in line:
            continue
        try:
            d = json.loads(line)
            if "target_type" in d and "ip" in d:
                envelopes.append(d)
        except Exception:
            continue
    return envelopes


def main() -> int:
    summary = {"channels": {}}

    for channel in ("os", "esxi", "redfish"):
        print(f"\n{'='*60}\n=== Channel: {channel} ===\n{'='*60}")
        try:
            build_num = trigger_build(channel)
            time.sleep(5)
            meta = wait_for_build(channel, build_num)
            (OUT / f"_build_{channel}.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
            console = fetch_console(channel, build_num)
            (OUT / f"_console_{channel}.txt").write_text(console[-300_000:], encoding="utf-8")
            envelopes = extract_envelopes(console)
            with open(OUT / f"_envelope_{channel}.jsonl", "w", encoding="utf-8") as f:
                for e in envelopes:
                    f.write(json.dumps(e, ensure_ascii=False) + "\n")
            ok = sum(1 for e in envelopes if e.get("status") == "success")
            partial = sum(1 for e in envelopes if e.get("status") == "partial")
            failed = sum(1 for e in envelopes if e.get("status") == "failed")
            summary["channels"][channel] = {
                "build_number": build_num,
                "result": meta.get("result"),
                "duration_sec": meta.get("duration", 0) / 1000,
                "envelope_count": len(envelopes),
                "success": ok,
                "partial": partial,
                "failed": failed,
            }
            print(f"[{channel}] envelopes={len(envelopes)} success={ok} partial={partial} failed={failed}")
        except Exception as e:
            print(f"[{channel}] ERROR: {e}")
            summary["channels"][channel] = {"error": str(e)}

    (OUT / "_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print("\n" + json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
