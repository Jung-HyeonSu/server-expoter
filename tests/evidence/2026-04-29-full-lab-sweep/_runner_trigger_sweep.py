"""Trigger hshwang-gather Jenkins job for 3 channels (sequential), poll, capture.

Output per channel:
  _build_<channel>.json   — build metadata
  _console_<channel>.txt  — console log
  _stdout_json_<channel>.txt — extracted JSON envelope blocks
"""
import json
import time
import re
import paramiko
from pathlib import Path

MASTER = "10.100.64.152"
SSH_USER = "cloviradmin"
SSH_PASS = __import__("os").environ["LAB_SSH_PASS"]
JK_URL = "http://localhost:8080"
JK_USER = "cloviradmin"
JK_PASS = __import__("os").environ["LAB_SSH_PASS"]
JOB = "hshwang-gather"
LOC = "ic"

OUT = Path("tests/evidence/2026-04-29-full-lab-sweep")
INV = json.loads((OUT / "_inventory.json").read_text(encoding="utf-8"))


def build_inventory_json(channel: str) -> str:
    """Build inventory_json string per channel."""
    if channel == "redfish":
        items = [{"bmc_ip": h["ip"], "vendor": h["vendor"]} for h in INV["redfish"]["hosts"]]
    elif channel == "os":
        items = [{"service_ip": h["ip"]} for h in INV["os"]["hosts"]]
    elif channel == "esxi":
        items = [{"service_ip": h["ip"]} for h in INV["esxi"]["hosts"]]
    else:
        raise ValueError(channel)
    return json.dumps(items)


def ssh_exec(cmd: str, timeout: int = 30):
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(MASTER, username=SSH_USER, password=SSH_PASS, timeout=15)
    stdin, stdout, stderr = c.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace")
    err = stderr.read().decode("utf-8", errors="replace")
    rc = stdout.channel.recv_exit_status()
    c.close()
    return out, err, rc


def get_crumb():
    out, _, rc = ssh_exec(
        f"curl -sS -m 10 -u '{JK_USER}:{JK_PASS}' -c /tmp/jcookie.txt "
        f"'{JK_URL}/crumbIssuer/api/json'"
    )
    data = json.loads(out)
    return data["crumb"], data["crumbRequestField"]


def get_next_build_number():
    out, _, rc = ssh_exec(
        f"curl -sS -m 10 -u '{JK_USER}:{JK_PASS}' "
        f"'{JK_URL}/job/{JOB}/api/json?tree=nextBuildNumber'"
    )
    return json.loads(out)["nextBuildNumber"]


def trigger_build(channel: str, inv_json: str):
    crumb, crumb_field = get_crumb()
    expected_build = get_next_build_number()
    # Use buildWithParameters via POST form-data
    # We POST the params as form fields. Use temp file for inventory_json (long)
    inv_file = f"/tmp/inv_{channel}.json"
    # Write file via SSH
    write_cmd = f"cat > {inv_file} <<'INVEOF'\n{inv_json}\nINVEOF"
    ssh_exec(write_cmd)

    # Trigger
    trig = (
        f"curl -sS -m 30 -u '{JK_USER}:{JK_PASS}' "
        f"-b /tmp/jcookie.txt "
        f"-H '{crumb_field}: {crumb}' "
        f"-X POST '{JK_URL}/job/{JOB}/buildWithParameters' "
        f"--data-urlencode 'loc={LOC}' "
        f"--data-urlencode 'target_type={channel}' "
        f"--data-urlencode inventory_json@{inv_file} "
        f"-w 'HTTP:%{{http_code}} LOC:%{{redirect_url}}\\n'"
    )
    out, err, rc = ssh_exec(trig)
    print(f"[{channel}] trigger rc={rc} out={out[:300]}")
    return expected_build


def wait_for_build(channel: str, build_num: int, max_wait_sec: int = 1800):
    """Poll build status until it completes (result != null)."""
    print(f"[{channel}] waiting for #{build_num} (max {max_wait_sec}s)...")
    start = time.time()
    while time.time() - start < max_wait_sec:
        out, _, rc = ssh_exec(
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
            print(f"[{channel}] still building ({elapsed}s elapsed)...")
            time.sleep(20)
            continue
        if data.get("result"):
            print(f"[{channel}] DONE #{build_num} result={data['result']} duration={data['duration']/1000:.1f}s")
            return data
        time.sleep(20)
    raise TimeoutError(f"[{channel}] build #{build_num} timed out after {max_wait_sec}s")


def fetch_console(channel: str, build_num: int):
    """Fetch full console log."""
    cmd = (
        f"curl -sS -m 30 -u '{JK_USER}:{JK_PASS}' "
        f"'{JK_URL}/job/{JOB}/{build_num}/consoleText'"
    )
    out, _, _ = ssh_exec(cmd, timeout=60)
    cpath = OUT / f"_console_{channel}.txt"
    cpath.write_text(out, encoding="utf-8")
    print(f"[{channel}] wrote {cpath} ({len(out)} bytes)")
    return out


def main():
    summary = {"channels": {}}
    # Check job is not already building
    out, _, _ = ssh_exec(
        f"curl -sS -m 10 -u '{JK_USER}:{JK_PASS}' "
        f"'{JK_URL}/job/{JOB}/api/json?tree=lastBuild%5Bnumber,building%5D'"
    )
    lb = json.loads(out)
    print(f"Job {JOB} lastBuild = {lb}")
    if lb.get("lastBuild", {}).get("building"):
        print("WARN: job already building. Will queue.")

    for channel in ["redfish", "os", "esxi"]:
        inv = build_inventory_json(channel)
        print(f"\n=== {channel} ({len(json.loads(inv))} hosts) ===")
        bnum = trigger_build(channel, inv)
        # Slight wait for queue → build
        time.sleep(20)
        # If queued behind another, build_num may shift; refetch via lastBuild after a moment
        # We'll retry to find our build
        actual_build = None
        for _ in range(20):
            out, _, _ = ssh_exec(
                f"curl -sS -m 10 -u '{JK_USER}:{JK_PASS}' "
                f"'{JK_URL}/job/{JOB}/{bnum}/api/json?tree=number'"
            )
            try:
                d = json.loads(out)
                if d.get("number") == bnum:
                    actual_build = bnum
                    break
            except Exception:
                pass
            time.sleep(10)
        if actual_build is None:
            print(f"[{channel}] could not locate build #{bnum} — fallback to lastBuild after queue")
            actual_build = bnum
        try:
            data = wait_for_build(channel, actual_build, max_wait_sec=1800)
            summary["channels"][channel] = {"build": actual_build, "result": data.get("result"), "duration_sec": data.get("duration", 0) / 1000}
            fetch_console(channel, actual_build)
        except TimeoutError as e:
            print(str(e))
            summary["channels"][channel] = {"build": actual_build, "result": "TIMEOUT", "error": str(e)}

    summary_path = OUT / "_sweep_summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWROTE {summary_path}")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
