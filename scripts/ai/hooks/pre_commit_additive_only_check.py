#!/usr/bin/env python3
"""pre-commit hook — rule 92 R2 / rule 96 R1-B Additive only 검증.

호환성 cycle (사용자 사이트 사고 fallback 도입) 시 envelope shape 변경 / 기존 path
삭제 / 리네임 차단. 기존 path 유지 + 새 fallback path 추가만 허용.

검증 대상:
- common/tasks/normalize/build_*.yml — envelope 정본
- schema/sections.yml — 섹션 정의
- schema/field_dictionary.yml — Must/Nice/Skip

Blocking (exit 1) — cycle 2026-05-11 격상.
이전 cycle 2026-05-06-post 도입 시 advisory (exit 0). 5 cycle 운영 false-positive 0
확인 후 cycle 2026-05-11 advisory hook 격상 (3/4) 단계적 격상에서 blocking 격상.

envelope/schema 정본 삭제 line 감지 시 commit 차단. 호환성 cycle 외 영역 변경은
별도 cycle 권장 (escape hatch ADDITIVE_SKIP_NEW_CYCLE=1).

비활성화 환경변수:
    ADDITIVE_SKIP=1            — 본 hook skip
    ADDITIVE_SKIP_NEW_CYCLE=1  — 새 cycle (호환성 외 — schema 확장 / 새 vendor) 명시 시

Usage:
    pre-commit hook 자동 호출. 수동:
    python scripts/ai/hooks/pre_commit_additive_only_check.py
    python scripts/ai/hooks/pre_commit_additive_only_check.py --self-test

Exit codes:
    0 = 통과
    1 = 위반 (BLOCKING — cycle 2026-05-11 격상)
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


WATCHED_PATHS: tuple[str, ...] = (
    "common/tasks/normalize/build_output.yml",
    "common/tasks/normalize/build_status.yml",
    "common/tasks/normalize/build_sections.yml",
    "common/tasks/normalize/build_errors.yml",
    "common/tasks/normalize/build_meta.yml",
    "common/tasks/normalize/build_correlation.yml",
    "schema/sections.yml",
    "schema/field_dictionary.yml",
)


def _normalize(p: str) -> str:
    return p.replace("\\", "/").strip()


def detect_deletions(diff_output: str) -> tuple[int, int]:
    """git diff --cached 출력에서 삭제 / 추가 line 카운트.

    Returns: (deletion_count, addition_count) — diff header `---` / `+++` 제외.
    """
    deletions = 0
    additions = 0
    for line in diff_output.splitlines():
        if line.startswith("---") or line.startswith("+++"):
            continue
        if line.startswith("-") and not line.startswith("--"):
            deletions += 1
        elif line.startswith("+") and not line.startswith("++"):
            additions += 1
    return deletions, additions


def _staged_files(repo_root: Path) -> list[str]:
    try:
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=5,
            encoding="utf-8", errors="replace",
        )
    except Exception:
        return []
    return [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]


def _file_diff(repo_root: Path, path: str) -> str:
    try:
        r = subprocess.run(
            ["git", "diff", "--cached", "--", path],
            capture_output=True, text=True, cwd=str(repo_root), timeout=5,
            encoding="utf-8", errors="replace",
        )
        return r.stdout or ""
    except Exception:
        return ""


def self_test() -> int:
    cases: list[tuple[str, str, tuple[int, int]]] = [
        (
            "추가만 (Additive)",
            "+    new_path: '/redfish/v1/...'\n+    fallback: true",
            (0, 2),
        ),
        (
            "삭제 + 추가 (의심)",
            "-    old_path: '/old'\n+    new_path: '/new'",
            (1, 1),
        ),
        (
            "삭제만 (위반)",
            "-    deprecated: true\n-    old_field: 1",
            (2, 0),
        ),
        (
            "diff header line 무시",
            "--- a/file.yml\n+++ b/file.yml\n+    new_line",
            (0, 1),
        ),
        (
            "multi-line 삭제 + 추가",
            ("-    a: 1\n-    b: 2\n-    c: 3\n"
             "+    a: 1\n+    b: 2\n+    c: 3\n+    d: 4"),
            (3, 4),
        ),
    ]
    all_pass = True
    for label, diff, expected in cases:
        actual = detect_deletions(diff)
        ok = actual == expected
        print(f"{'PASS' if ok else 'FAIL'}: {label} → {actual}")
        if not ok:
            all_pass = False
            print(f"  expected: {expected}")
    return 0 if all_pass else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="rule 92 R2 / rule 96 R1-B Additive 검증")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if os.environ.get("ADDITIVE_SKIP") == "1":
        return 0
    if os.environ.get("ADDITIVE_SKIP_NEW_CYCLE") == "1":
        return 0

    repo_root = Path(".").resolve()
    staged = _staged_files(repo_root)
    if not staged:
        return 0

    files_norm = [_normalize(f) for f in staged]
    watched = [f for f in files_norm if f in WATCHED_PATHS]
    if not watched:
        return 0

    violations: list[tuple[str, int, int]] = []
    for f in watched:
        diff = _file_diff(repo_root, f)
        if not diff:
            continue
        deletions, additions = detect_deletions(diff)
        if deletions > 0:
            violations.append((f, deletions, additions))

    if not violations:
        return 0

    print(
        "[additive only] rule 92 R2 / rule 96 R1-B 위반 — envelope/schema 정본 삭제 line 감지 (BLOCKING — cycle 2026-05-11 격상):",
        file=sys.stderr,
    )
    for f, dels, adds in violations:
        print(f"  - {f}: -{dels} / +{adds}", file=sys.stderr)
    print(
        "\n  → 호환성 cycle 은 Additive only — 기존 path 유지 + 새 fallback path 추가만.",
        file=sys.stderr,
    )
    print(
        "  → 새 cycle (호환성 외 — schema 확장 / 새 vendor) 명시 skip:",
        file=sys.stderr,
    )
    print("       ADDITIVE_SKIP_NEW_CYCLE=1 git commit ...", file=sys.stderr)
    print("  → 강제 skip: ADDITIVE_SKIP=1 git commit ...", file=sys.stderr)

    return 1


if __name__ == "__main__":
    sys.exit(main())
