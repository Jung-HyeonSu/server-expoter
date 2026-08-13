#!/usr/bin/env python3
"""scripts/ai/measure_compatibility_matrix.py — rule 28 #12 매트릭스 자동 측정.

vendor × generation × section 호환성 매트릭스를 adapter YAML 의 capabilities 에서
자동 추출. baseline JSON 존재 여부로 OK / OK★ 격상.

호출 시점:
- TTL 14일 만료 시 (rule 28 #12)
- adapter capabilities 변경 후
- 새 vendor 추가 후
- 펌웨어 업그레이드 후

비활성화 환경변수:
    COMPAT_MATRIX_SKIP=1  — 본 측정 skip

Usage:
    python scripts/ai/measure_compatibility_matrix.py
    python scripts/ai/measure_compatibility_matrix.py --self-test
    python scripts/ai/measure_compatibility_matrix.py --output docs/reference/compatibility-matrix.md
"""

from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None  # 본 script 에서는 stdlib only YAML 파싱 fallback


REDFISH_SECTIONS: tuple[str, ...] = (
    "system", "hardware", "bmc", "cpu", "memory",
    "storage", "network", "firmware", "users", "power",
)


def _parse_yaml(text: str) -> dict[str, Any]:
    if yaml is None:
        return _stdlib_yaml_parse(text)
    try:
        return yaml.safe_load(text) or {}
    except Exception:
        return {}


def _stdlib_yaml_parse(text: str) -> dict[str, Any]:
    """매우 단순한 YAML subset 파서 — adapter YAML의 capabilities/sections_supported 만 추출.

    adapter YAML 의 다음 패턴만 처리:
        capabilities:
          sections_supported:
            - system
            - cpu
            ...
    """
    result: dict[str, Any] = {"capabilities": {}, "match": {}, "metadata": {}}
    lines = text.splitlines()
    in_capabilities = False
    in_sections = False
    sections: list[str] = []
    for line in lines:
        stripped = line.rstrip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("capabilities:"):
            in_capabilities = True
            in_sections = False
            continue
        if in_capabilities and stripped.startswith("  sections_supported:"):
            in_sections = True
            continue
        if in_sections and stripped.startswith("    - "):
            section = stripped[6:].strip().strip("'\"")
            if section:
                sections.append(section)
            continue
        if in_sections and not stripped.startswith("  "):
            in_sections = False
        if in_capabilities and not (stripped.startswith("  ") or stripped.startswith("\t")):
            in_capabilities = False
            in_sections = False
    if sections:
        result["capabilities"]["sections_supported"] = sections
    return result


def _detect_vendor_generation(filename: str) -> tuple[str, str]:
    """파일명에서 vendor / generation 추출. 예: dell_idrac9.yml → (dell, idrac9)."""
    name = filename.replace(".yml", "").replace(".yaml", "")
    parts = name.split("_", 1)
    if len(parts) == 1:
        return (parts[0], "default")
    return (parts[0], parts[1])


def measure_matrix(adapters_dir: Path, baseline_dir: Path) -> dict[str, dict[str, dict[str, str]]]:
    """adapters/redfish/*.yml + schema/baseline_v1/*.json 으로 매트릭스 측정.

    Returns: {vendor: {generation: {section: 기호}}}
    """
    matrix: dict[str, dict[str, dict[str, str]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(lambda: "?")))

    if not adapters_dir.exists():
        return dict(matrix)

    baseline_vendors: set[str] = set()
    if baseline_dir.exists():
        for fp in baseline_dir.glob("*_baseline.json"):
            baseline_vendors.add(fp.stem.replace("_baseline", "").split("_")[0])

    for fp in sorted(adapters_dir.glob("*.yml")):
        if "generic" in fp.stem.lower():
            continue
        vendor, generation = _detect_vendor_generation(fp.name)
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        data = _parse_yaml(text)
        caps = (data.get("capabilities") or {}) if isinstance(data, dict) else {}
        sections = caps.get("sections_supported") if isinstance(caps, dict) else None
        if not isinstance(sections, list):
            sections = []
        for section in REDFISH_SECTIONS:
            if section == "users":
                matrix[vendor][generation][section] = "N/A"
                continue
            if section in sections:
                if vendor in baseline_vendors:
                    matrix[vendor][generation][section] = "OK"
                else:
                    matrix[vendor][generation][section] = "OK★"
            else:
                matrix[vendor][generation][section] = "GAP"
    return dict(matrix)


def render_matrix(matrix: dict[str, dict[str, dict[str, str]]]) -> str:
    """matrix → markdown table."""
    lines: list[str] = []
    header = "| vendor | generation | " + " | ".join(REDFISH_SECTIONS) + " |"
    sep = "|" + "|".join(["---"] * (2 + len(REDFISH_SECTIONS))) + "|"
    lines.append(header)
    lines.append(sep)
    for vendor in sorted(matrix.keys()):
        for generation in sorted(matrix[vendor].keys()):
            cells = [matrix[vendor][generation].get(s, "?") for s in REDFISH_SECTIONS]
            row = f"| **{vendor}** | {generation} | " + " | ".join(cells) + " |"
            lines.append(row)
    return "\n".join(lines)


def count_distribution(matrix: dict[str, dict[str, dict[str, str]]]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for vendor in matrix:
        for generation in matrix[vendor]:
            for section in matrix[vendor][generation]:
                counts[matrix[vendor][generation][section]] += 1
    return dict(counts)


def self_test() -> int:
    cases: list[tuple[str, str, tuple[str, str]]] = [
        ("dell_idrac9.yml → (dell, idrac9)", "dell_idrac9.yml", ("dell", "idrac9")),
        ("hpe_ilo7.yml → (hpe, ilo7)", "hpe_ilo7.yml", ("hpe", "ilo7")),
        ("supermicro_x14.yml → (supermicro, x14)", "supermicro_x14.yml", ("supermicro", "x14")),
        ("redfish_generic.yml → (redfish, generic)", "redfish_generic.yml", ("redfish", "generic")),
        ("solo.yml → (solo, default)", "solo.yml", ("solo", "default")),
    ]
    all_pass = True
    for label, filename, expected in cases:
        actual = _detect_vendor_generation(filename)
        ok = actual == expected
        print(f"{'PASS' if ok else 'FAIL'}: {label} → {actual}")
        if not ok:
            all_pass = False
            print(f"  expected: {expected}")

    yaml_text = """
priority: 100
match:
  manufacturer: ["Dell"]
capabilities:
  sections_supported:
    - system
    - cpu
    - memory
    - power
"""
    parsed = _parse_yaml(yaml_text)
    expected_sections = ["system", "cpu", "memory", "power"]
    actual_sections = ((parsed.get("capabilities") or {}).get("sections_supported") or [])
    ok = actual_sections == expected_sections
    print(f"{'PASS' if ok else 'FAIL'}: YAML parse capabilities.sections_supported → {actual_sections}")
    if not ok:
        all_pass = False
        print(f"  expected: {expected_sections}")

    return 0 if all_pass else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="rule 28 #12 호환성 매트릭스 자동 측정")
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if os.environ.get("COMPAT_MATRIX_SKIP") == "1":
        return 0

    repo_root = Path(args.repo_root).resolve()
    adapters_dir = repo_root / "adapters" / "redfish"
    baseline_dir = repo_root / "schema" / "baseline_v1"

    if not adapters_dir.exists():
        print(f"ERROR: adapters dir not found: {adapters_dir}", file=sys.stderr)
        return 1

    matrix = measure_matrix(adapters_dir, baseline_dir)
    print(render_matrix(matrix))
    print()
    print("Distribution:")
    counts = count_distribution(matrix)
    total = sum(counts.values())
    for symbol, count in sorted(counts.items()):
        ratio = (count / total * 100) if total else 0
        print(f"  {symbol}: {count} ({ratio:.1f}%)")
    print(f"  total: {total}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
