#!/usr/bin/env python3
"""Round 7: Conditional 필드 8개 live raw 수집 — 4 baseline + 1 supplemental

실행 방법:
  python3 conditional_review.py --config /path/to/targets.json
  python3 conditional_review.py --config /path/to/targets.json --output /path/to/results.json

targets.json 형식 (gitignored, tests/scripts/targets.sample.json 참조):
  [
    {"label": "Lenovo", "ip": "10.50.11.232", "user": "YOUR_USER", "password": "YOUR_PASSWORD", "group": "baseline"},
    ...
  ]

Credential은 스크립트에 포함하지 않음.
targets.json은 repo에 tracked하지 않음 (gitignored).
"""
import argparse
import json
import sys
import urllib.request
import ssl
import base64
import datetime


def parse_args():
    parser = argparse.ArgumentParser(description="Round 7: Conditional field live raw collector")
    parser.add_argument("--config", required=True,
                        help="Path to targets JSON file (contains BMC IP/credential)")
    parser.add_argument("--output", default=None,
                        help="Path to save raw JSON results (default: stdout only)")
    return parser.parse_args()


def load_targets(config_path):
    with open(config_path, "r", encoding="utf-8") as f:
        targets = json.load(f)
    # Validate required fields
    for t in targets:
        for key in ("label", "ip", "user", "password", "group"):
            if key not in t:
                print(f"ERROR: target missing '{key}': {t}", file=sys.stderr)
                sys.exit(1)
        if t["group"] not in ("baseline", "supplemental"):
            print(f"ERROR: invalid group '{t['group']}' for {t['label']}", file=sys.stderr)
            sys.exit(1)
    return targets


def make_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def redfish_get(ip, path, user, pw, ssl_ctx):
    creds = base64.b64encode((user + ":" + pw).encode()).decode()
    req = urllib.request.Request(
        "https://" + ip + path,
        headers={"Authorization": "Basic " + creds, "Accept": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req, context=ssl_ctx, timeout=15)
        return json.loads(resp.read())
    except Exception:
        return {}


def safe_get(d, *keys):
    """Nested dict/list safe accessor."""
    for k in keys:
        if d is None:
            return None
        if isinstance(k, int):
            if isinstance(d, list) and k < len(d):
                d = d[k]
            else:
                return None
        elif isinstance(d, dict):
            d = d.get(k)
        else:
            return None
    return d


def collect_raw(targets, ssl_ctx):
    """Collect raw Redfish data from all targets."""
    raw = {}
    for t in targets:
        label, ip, user, pw = t["label"], t["ip"], t["user"], t["password"]
        r = {}

        root = redfish_get(ip, "/redfish/v1/", user, pw, ssl_ctx)

        # System
        sys_uri = safe_get(root, "Systems", "@odata.id") or ""
        sys_coll = redfish_get(ip, sys_uri, user, pw, ssl_ctx) if sys_uri else {}
        sys_member = safe_get(sys_coll, "Members", 0, "@odata.id") or ""
        r["system"] = redfish_get(ip, sys_member, user, pw, ssl_ctx) if sys_member else {}

        # Processor
        proc_uri = safe_get(r["system"], "Processors", "@odata.id") or ""
        if proc_uri:
            proc_coll = redfish_get(ip, proc_uri, user, pw, ssl_ctx)
            p0_uri = safe_get(proc_coll, "Members", 0, "@odata.id") or ""
            r["proc"] = redfish_get(ip, p0_uri, user, pw, ssl_ctx) if p0_uri else {}

        # Power (via Chassis)
        ch_uri = safe_get(root, "Chassis", "@odata.id") or ""
        ch_coll = redfish_get(ip, ch_uri, user, pw, ssl_ctx) if ch_uri else {}
        ch_member = safe_get(ch_coll, "Members", 0, "@odata.id") or ""
        ch_d = redfish_get(ip, ch_member, user, pw, ssl_ctx) if ch_member else {}
        power_uri = safe_get(ch_d, "Power", "@odata.id") or ""
        r["power"] = redfish_get(ip, power_uri, user, pw, ssl_ctx) if power_uri else {}

        # NIC
        nic_uri = safe_get(r["system"], "EthernetInterfaces", "@odata.id") or ""
        if nic_uri:
            nic_coll = redfish_get(ip, nic_uri, user, pw, ssl_ctx)
            n0_uri = safe_get(nic_coll, "Members", 0, "@odata.id") or ""
            r["nic"] = redfish_get(ip, n0_uri, user, pw, ssl_ctx) if n0_uri else {}

        raw[label] = r
        print("Collected:", label, f"[{t['group']}]", file=sys.stderr)

    return raw


def extract_field(raw_entry, field_name):
    """Extract a single conditional field value from raw data."""
    power = raw_entry.get("power", {})
    pc_list = power.get("PowerControl", [])
    pc0 = pc_list[0] if isinstance(pc_list, list) and pc_list else {}
    psu_list = power.get("PowerSupplies", [])
    psu0 = psu_list[0] if isinstance(psu_list, list) and psu_list else {}

    extractors = {
        "PowerConsumedWatts": lambda: {
            "value": pc0.get("PowerConsumedWatts") if pc0 else None,
            "PC_count": len(pc_list) if isinstance(pc_list, list) else 0,
            "Name": pc0.get("Name") if pc0 else None,
            "PhysicalContext": pc0.get("PhysicalContext") if pc0 else None,
        },
        "PowerCapacityWatts": lambda: {
            "value": pc0.get("PowerCapacityWatts") if pc0 else None,
        },
        "PowerMetrics.Avg": lambda: {
            "value": safe_get(pc0, "PowerMetrics", "AverageConsumedWatts"),
        },
        "PowerMetrics.Min": lambda: {
            "value": safe_get(pc0, "PowerMetrics", "MinConsumedWatts"),
        },
        "PowerMetrics.Max": lambda: {
            "value": safe_get(pc0, "PowerMetrics", "MaxConsumedWatts"),
        },
        "PowerMetrics.IntervalInMin": lambda: {
            "value": safe_get(pc0, "PowerMetrics", "IntervalInMin"),
        },
        "Proc.MaxSpeedMHz": lambda: {
            "value": raw_entry.get("proc", {}).get("MaxSpeedMHz"),
            "model": str(raw_entry.get("proc", {}).get("Model", ""))[:35],
        },
        "System.SKU": lambda: {
            "value": raw_entry.get("system", {}).get("SKU"),
        },
        "PSU.Health": lambda: {
            "value": safe_get(psu0, "Status", "Health") if psu0 else None,
            "PSU_count": len(psu_list) if isinstance(psu_list, list) else 0,
        },
        "NIC.LinkStatus": lambda: {
            "value": raw_entry.get("nic", {}).get("LinkStatus"),
            "SpeedMbps": raw_entry.get("nic", {}).get("SpeedMbps"),
        },
    }

    extractor = extractors.get(field_name)
    return extractor() if extractor else {"value": None}


CONDITIONAL_FIELDS = [
    "PowerConsumedWatts",
    "PowerCapacityWatts",
    "PowerMetrics.Avg",
    "PowerMetrics.Min",
    "PowerMetrics.Max",
    "PowerMetrics.IntervalInMin",
    "Proc.MaxSpeedMHz",
    "System.SKU",
    "PSU.Health",
    "NIC.LinkStatus",
]

FIELD_ENDPOINTS = {
    "PowerConsumedWatts": "Chassis/{ch}/Power → PowerControl[0]",
    "PowerCapacityWatts": "Chassis/{ch}/Power → PowerControl[0]",
    "PowerMetrics.Avg": "Chassis/{ch}/Power → PowerControl[0].PowerMetrics",
    "PowerMetrics.Min": "Chassis/{ch}/Power → PowerControl[0].PowerMetrics",
    "PowerMetrics.Max": "Chassis/{ch}/Power → PowerControl[0].PowerMetrics",
    "PowerMetrics.IntervalInMin": "Chassis/{ch}/Power → PowerControl[0].PowerMetrics",
    "Proc.MaxSpeedMHz": "Systems/{sys}/Processors/{id}",
    "System.SKU": "Systems/{sys}",
    "PSU.Health": "Chassis/{ch}/Power → PowerSupplies[0].Status",
    "NIC.LinkStatus": "Systems/{sys}/EthernetInterfaces/{id}",
}


def print_table_a():
    """TABLE A: Endpoint Inventory (static reference)."""
    print()
    print("=" * 120)
    print("TABLE A: ENDPOINT INVENTORY — Conditional Fields")
    print("=" * 120)
    print()
    print("| Field | Endpoint | Description |")
    print("|---|---|---|")
    descs = {
        "PowerConsumedWatts": "System-level current power draw",
        "PowerCapacityWatts": "System-level power capacity",
        "PowerMetrics.Avg": "Average consumed watts over interval",
        "PowerMetrics.Min": "Minimum consumed watts over interval",
        "PowerMetrics.Max": "Maximum consumed watts over interval",
        "PowerMetrics.IntervalInMin": "Aggregation window in minutes",
        "Proc.MaxSpeedMHz": "Maximum processor clock speed",
        "System.SKU": "Product identifier / SKU",
        "PSU.Health": "Power supply unit health status",
        "NIC.LinkStatus": "Network interface link state",
    }
    for f in CONDITIONAL_FIELDS:
        print(f"| {f} | {FIELD_ENDPOINTS[f]} | {descs[f]} |")


def print_table_b(raw, labels):
    """TABLE B: Raw Key Path — live values from all BMCs."""
    print()
    print("=" * 120)
    print("TABLE B: RAW KEY PATH TABLE")
    print("=" * 120)
    print()

    header = "| Field | Endpoint |" + "|".join(f" {l} " for l in labels) + "|"
    sep = "|---|---|" + "|".join("---" for _ in labels) + "|"
    print(header)
    print(sep)

    for fname in CONDITIONAL_FIELDS:
        row = f"| {fname} | {FIELD_ENDPOINTS[fname]} |"
        for label in labels:
            result = extract_field(raw.get(label, {}), fname)
            val = result.get("value")
            val_str = repr(val) if val is not None else "null"
            if isinstance(val, str) and len(val) > 15:
                val_str = "'" + val[:12] + "..'"
            extra = ""
            if result.get("PhysicalContext"):
                extra = f" (Ctx:{result['PhysicalContext']})"
            elif result.get("model"):
                extra = f" ({result['model'][:20]})"
            row += f" {val_str}{extra} |"
        print(row)


def print_table_c():
    """TABLE C: Raw→Normalize→Output Mapping (static reference)."""
    print()
    print("=" * 120)
    print("TABLE C: RAW → NORMALIZE → OUTPUT MAPPING")
    print("=" * 120)
    print()
    print("| Field | Raw Key Path | Output Field |")
    print("|---|---|---|")
    mappings = [
        ("PowerConsumedWatts", "PowerControl[0].PowerConsumedWatts", "data.power.power_control.power_consumed_watts"),
        ("PowerCapacityWatts", "PowerControl[0].PowerCapacityWatts", "data.power.power_control.power_capacity_watts"),
        ("PowerMetrics.Avg", "PowerControl[0].PowerMetrics.AverageConsumedWatts", "data.power.power_control.avg_consumed_watts"),
        ("PowerMetrics.Min", "PowerControl[0].PowerMetrics.MinConsumedWatts", "data.power.power_control.min_consumed_watts"),
        ("PowerMetrics.Max", "PowerControl[0].PowerMetrics.MaxConsumedWatts", "data.power.power_control.max_consumed_watts"),
        ("PowerMetrics.IntervalInMin", "PowerControl[0].PowerMetrics.IntervalInMin", "data.power.power_control.interval_in_min"),
        ("Proc.MaxSpeedMHz", "Processors/{id}.MaxSpeedMHz", "data.cpu.max_speed_mhz"),
        ("System.SKU", "Systems/{id}.SKU", "data.hardware.sku"),
        ("PSU.Health", "PowerSupplies[n].Status.Health", "data.power.power_supplies[].health"),
        ("NIC.LinkStatus", "EthernetInterfaces/{id}.LinkStatus", "data.network.interfaces[].link_status"),
    ]
    for fname, raw_path, output_path in mappings:
        print(f"| {fname} | {raw_path} | {output_path} |")


def print_table_d(raw, labels):
    """TABLE D: Semantic Equivalence Judgment."""
    print()
    print("=" * 120)
    print("TABLE D: SEMANTIC EQUIVALENCE JUDGMENT")
    print("=" * 120)
    print()

    for fname in CONDITIONAL_FIELDS:
        print(f"--- {fname} ---")
        all_vals = {}
        for label in labels:
            result = extract_field(raw.get(label, {}), fname)
            all_vals[label] = result
            val = result.get("value")
            line = f"  {label:<12}: value={val!r} type={type(val).__name__}"
            for k, v in result.items():
                if k not in ("value", "type"):
                    line += f" {k}={v!r}"
            print(line)

        values = [all_vals[l].get("value") for l in labels]
        non_null = [v for v in values if v is not None]
        null_count = values.count(None)
        types = set(type(v).__name__ for v in non_null)
        print(f"  → non_null: {len(non_null)}/5, null: {null_count}, types: {types}")
        print()


def main():
    args = parse_args()
    targets = load_targets(args.config)
    ssl_ctx = make_ssl_context()

    timestamp = datetime.datetime.now().isoformat()
    labels = [t["label"] for t in targets]

    print("ROUND 7: Conditional Field Review")
    print(f"Timestamp: {timestamp}")
    print(f"Targets: {len(targets)} ({', '.join(labels)})")
    print("=" * 120)

    raw = collect_raw(targets, ssl_ctx)

    print_table_a()
    print_table_b(raw, labels)
    print_table_c()
    print_table_d(raw, labels)

    # Save structured results if --output specified
    if args.output:
        output_data = {
            "timestamp": timestamp,
            "targets": [{"label": t["label"], "ip": t["ip"], "group": t["group"]} for t in targets],
            "fields": {},
        }
        for fname in CONDITIONAL_FIELDS:
            output_data["fields"][fname] = {}
            for label in labels:
                output_data["fields"][fname][label] = extract_field(raw.get(label, {}), fname)

        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)
        print(f"\nResults saved to: {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
