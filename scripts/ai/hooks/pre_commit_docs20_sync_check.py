#!/usr/bin/env python3
"""pre-commit hook — rule 13 R7 `docs/contract/03-fields.md` 동기화 검증.

rule 13 R7 정본 4종 변경 시 docs/contract/03-fields.md 동기화 갱신 의무.

정본 4종:
- common/tasks/normalize/build_output.yml (envelope 13 필드)
- schema/sections.yml (섹션 정의)
- schema/field_dictionary.yml (Must/Nice/Skip 분류)
- common/tasks/normalize/build_status.yml (status 판정 규칙)

Blocking (exit 1) — cycle 2026-05-11 격상.
이전 cycle 2026-05-06 도입 시 advisory (exit 0). 5 cycle 운영 false-positive 0
확인 후 cycle 2026-05-11 harness-cycle 에서 blocking 격상.

정본 4종 staged + `docs/contract/03-fields.md` 미staged 시 commit 차단.

비활성화 환경변수:
    DOCS20_SYNC_SKIP=1            — 본 hook skip
    DOCS20_SYNC_SKIP_COSMETIC=1   — cosmetic only commit (rule 13 R7 Allowed)

Usage:
    pre-commit hook 자동 호출. 수동:
    python scripts/ai/hooks/pre_commit_docs20_sync_check.py
    python scripts/ai/hooks/pre_commit_docs20_sync_check.py --self-test

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


CANONICAL_FILES: tuple[str, ...] = (
    "common/tasks/normalize/build_output.yml",
    "common/tasks/normalize/build_status.yml",
    "schema/sections.yml",
    "schema/field_dictionary.yml",
)

DOCS20_PATH = "docs/contract/03-fields.md"


def _normalize(p: str) -> str:
    return p.replace("\\", "/").strip()


def detect_violation(staged_files: list[str]) -> list[str]:
    """staged 파일 목록에서 rule 13 R7 위반 (정본 변경 + `docs/contract/03-fields.md` 미변경) 검출.

    Returns: 위반한 정본 파일 목록 (없으면 빈 리스트).
    """
    files = {_normalize(f) for f in staged_files if f}
    changed_canonical = [f for f in CANONICAL_FILES if f in files]
    if not changed_canonical:
        return []
    if DOCS20_PATH in files:
        return []
    return changed_canonical


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


def self_test() -> int:
    cases: list[tuple[str, list[str], list[str]]] = [
        (
            "정본 1개만 변경 + `docs/contract/03-fields.md` 미변경 → 위반 1건",
            ["common/tasks/normalize/build_output.yml"],
            ["common/tasks/normalize/build_output.yml"],
        ),
        (
            "정본 2개 변경 + `docs/contract/03-fields.md` 변경 → 통과",
            [
                "schema/sections.yml",
                "schema/field_dictionary.yml",
                "docs/contract/03-fields.md",
            ],
            [],
        ),
        (
            "정본 외 변경 → 통과",
            ["adapters/redfish/dell_idrac9.yml"],
            [],
        ),
        (
            "빈 staged → 통과",
            [],
            [],
        ),
        (
            "Windows path separator 정규화",
            ["common\\tasks\\normalize\\build_status.yml"],
            ["common/tasks/normalize/build_status.yml"],
        ),
        (
            "정본 4종 모두 변경 + `docs/contract/03-fields.md` 미변경 → 위반 4건",
            list(CANONICAL_FILES),
            list(CANONICAL_FILES),
        ),
    ]
    all_pass = True
    for label, staged, expected in cases:
        violations = detect_violation(staged)
        ok = sorted(violations) == sorted(expected)
        print(f"{'PASS' if ok else 'FAIL'}: {label} → {violations}")
        if not ok:
            all_pass = False
            print(f"  expected: {expected}")
    return 0 if all_pass else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="rule 13 R7 `docs/contract/03-fields.md` 동기화 검증")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if os.environ.get("DOCS20_SYNC_SKIP") == "1":
        return 0
    if os.environ.get("DOCS20_SYNC_SKIP_COSMETIC") == "1":
        return 0

    repo_root = Path(".").resolve()
    staged = _staged_files(repo_root)
    if not staged:
        return 0

    violations = detect_violation(staged)
    if not violations:
        return 0

    print(
        "[`docs/contract/03-fields.md` sync] rule 13 R7 위반 — 정본 변경 + `docs/contract/03-fields.md` 미동기화 (BLOCKING — cycle 2026-05-11 격상):",
        file=sys.stderr,
    )
    for f in violations:
        print(f"  - {f}", file=sys.stderr)
    print(
        f"\n  → 정본 변경 시 {DOCS20_PATH} 동기화 갱신 의무 (rule 13 R7).",
        file=sys.stderr,
    )
    print(
        "  → cosmetic only (주석/들여쓰기) 시 commit 메시지 명시 후 skip:",
        file=sys.stderr,
    )
    print(
        "       DOCS20_SYNC_SKIP_COSMETIC=1 git commit ...",
        file=sys.stderr,
    )
    print("  → 강제 skip: DOCS20_SYNC_SKIP=1 git commit ...", file=sys.stderr)

    return 1


if __name__ == "__main__":
    sys.exit(main())
