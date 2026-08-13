#!/usr/bin/env python3
"""post-commit hook — rule 28 #12 호환성 매트릭스 advisory.

adapter capabilities 변경 시 docs/reference/compatibility-matrix.md 갱신 권장.

Advisory (exit 0): adapter 변경 + docs/22 미갱신 시 경고.

비활성화 환경변수:
    COMPAT_MATRIX_CHECK_SKIP=1  — 본 hook skip

Usage:
    post-commit hook 자동 호출. 수동:
    python scripts/ai/hooks/post_commit_compatibility_matrix_check.py
    python scripts/ai/hooks/post_commit_compatibility_matrix_check.py --self-test

Exit codes:
    0 = 통과 (advisory)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


ADAPTER_PREFIX = "adapters/redfish/"
DOCS22_PATH = "docs/reference/compatibility-matrix.md"


def _normalize(p: str) -> str:
    return p.replace("\\", "/").strip()


def detect_advisory(committed_files: list[str]) -> tuple[list[str], bool]:
    """commit 파일 목록에서 adapter 변경 + docs/22 미갱신 검출.

    Returns: (변경된 adapter 파일 list, docs/22 갱신 여부)
    """
    files = [_normalize(f) for f in committed_files if f]
    adapter_files = [f for f in files if f.startswith(ADAPTER_PREFIX) and f.endswith(".yml")]
    if any("generic" in f.lower() for f in adapter_files):
        adapter_files = [f for f in adapter_files if "generic" not in f.lower()]
    docs22_changed = DOCS22_PATH in files
    return adapter_files, docs22_changed


def _last_commit_files(repo_root: Path) -> list[str]:
    try:
        r = subprocess.run(
            ["git", "show", "--name-only", "--format=", "HEAD"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=5,
            encoding="utf-8", errors="replace",
        )
    except Exception:
        return []
    return [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]


def self_test() -> int:
    cases: list[tuple[str, list[str], tuple[list[str], bool]]] = [
        (
            "adapter 1개 변경 + docs/22 미변경 → advisory (1 adapter, no docs22)",
            ["adapters/redfish/dell_idrac9.yml"],
            (["adapters/redfish/dell_idrac9.yml"], False),
        ),
        (
            "adapter 변경 + docs/22 변경 → 통과",
            ["adapters/redfish/dell_idrac9.yml", "docs/reference/compatibility-matrix.md"],
            (["adapters/redfish/dell_idrac9.yml"], True),
        ),
        (
            "generic adapter 만 변경 → 제외",
            ["adapters/redfish/redfish_generic.yml"],
            ([], False),
        ),
        (
            "adapter 외 변경 → 통과",
            ["docs/reference/decision-log.md"],
            ([], False),
        ),
        (
            "Windows path separator 정규화",
            ["adapters\\redfish\\hpe_ilo6.yml"],
            (["adapters/redfish/hpe_ilo6.yml"], False),
        ),
        (
            "다중 adapter 변경 + docs/22 변경 → 통과",
            [
                "adapters/redfish/dell_idrac9.yml",
                "adapters/redfish/hpe_ilo6.yml",
                "docs/reference/compatibility-matrix.md",
            ],
            (
                ["adapters/redfish/dell_idrac9.yml", "adapters/redfish/hpe_ilo6.yml"],
                True,
            ),
        ),
    ]
    all_pass = True
    for label, files, expected in cases:
        actual = detect_advisory(files)
        ok = (sorted(actual[0]) == sorted(expected[0]) and actual[1] == expected[1])
        print(f"{'PASS' if ok else 'FAIL'}: {label} → {actual}")
        if not ok:
            all_pass = False
            print(f"  expected: {expected}")
    return 0 if all_pass else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="rule 28 #12 호환성 매트릭스 advisory")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if os.environ.get("COMPAT_MATRIX_CHECK_SKIP") == "1":
        return 0

    repo_root = Path(".").resolve()
    files = _last_commit_files(repo_root)
    if not files:
        return 0

    adapter_files, docs22_changed = detect_advisory(files)
    if not adapter_files or docs22_changed:
        return 0

    print(
        "[compat-matrix] rule 28 #12 advisory — adapter capabilities 변경 + docs/22 미갱신:",
        file=sys.stderr,
    )
    for f in adapter_files:
        print(f"  - {f}", file=sys.stderr)
    print(
        f"\n  → adapter capabilities 변경 시 {DOCS22_PATH} 갱신 권장 (rule 28 #12).",
        file=sys.stderr,
    )
    print(
        "  → 자동 측정: python scripts/ai/measure_compatibility_matrix.py",
        file=sys.stderr,
    )
    print("  → 강제 skip: COMPAT_MATRIX_CHECK_SKIP=1", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
