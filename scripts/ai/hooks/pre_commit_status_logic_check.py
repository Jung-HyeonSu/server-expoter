#!/usr/bin/env python3
"""pre-commit hook — rule 13 R8 status 로직 변경 시 시나리오 매트릭스 검증.

rule 13 R8 정본 3종 변경 시 4 시나리오 매트릭스 (A/B/C/D) 동반 갱신 의무.

정본 3종:
- common/tasks/normalize/build_status.yml (판정 로직 정본)
- common/tasks/normalize/build_sections.yml (섹션 status 입력)
- common/tasks/normalize/build_errors.yml (errors[] 분리 영역)

동반 갱신 4 곳:
- common/tasks/normalize/build_status.yml 본문 주석 (4 시나리오 매트릭스 정본)
- docs/reference/decision-log.md (M-A2 / 2026-05-06 결정 trace)
- docs/contract/03-fields.md (호출자 reference)
- tests/ status mock fixture (시나리오 B 재현)

Blocking (exit 1) — cycle 2026-05-11 격상.
이전 cycle 2026-05-06-post 도입 시 advisory (exit 0). 5 cycle 운영 false-positive 0
확인 후 cycle 2026-05-11 advisory hook 격상 (2/4) 단계적 격상에서 blocking 격상.

정본 3종 staged + 동반 4 곳 일부 미staged 시 commit 차단.

비활성화 환경변수:
    STATUS_LOGIC_SKIP=1            — 본 hook skip
    STATUS_LOGIC_SKIP_COSMETIC=1   — cosmetic only commit (rule 13 R8 Allowed)

Usage:
    pre-commit hook 자동 호출. 수동:
    python scripts/ai/hooks/pre_commit_status_logic_check.py
    python scripts/ai/hooks/pre_commit_status_logic_check.py --self-test

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
    "common/tasks/normalize/build_status.yml",
    "common/tasks/normalize/build_sections.yml",
    "common/tasks/normalize/build_errors.yml",
)

COMPANION_PATHS: tuple[str, ...] = (
    "docs/reference/decision-log.md",
    "docs/contract/03-fields.md",
)

TESTS_PREFIX = "tests/"
TESTS_STATUS_HINTS: tuple[str, ...] = ("status", "scenario")


def _normalize(p: str) -> str:
    return p.replace("\\", "/").strip()


def _has_status_test(files: set[str]) -> bool:
    """tests/ 안에 status / scenario hint 가 있는 파일 staged 여부."""
    for f in files:
        if not f.startswith(TESTS_PREFIX):
            continue
        low = f.lower()
        if any(h in low for h in TESTS_STATUS_HINTS):
            return True
    return False


def detect_violation(staged_files: list[str]) -> tuple[list[str], list[str]]:
    """staged 파일 목록에서 rule 13 R8 위반 검출.

    Returns: (변경된 정본 파일, 누락된 동반 갱신 위치)
        - 정본 변경 없음 → ([], []) 통과
        - 동반 4 곳 모두 변경됨 → (정본, []) 통과
        - 일부 누락 → (정본, 누락 list)
    """
    files = {_normalize(f) for f in staged_files if f}
    changed_canonical = [f for f in CANONICAL_FILES if f in files]
    if not changed_canonical:
        return [], []

    missing: list[str] = []
    for companion in COMPANION_PATHS:
        if companion not in files:
            missing.append(companion)
    if not _has_status_test(files):
        missing.append(f"{TESTS_PREFIX}*status* 또는 *scenario* mock fixture")

    return changed_canonical, missing


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
    cases: list[tuple[str, list[str], tuple[list[str], list[str]]]] = [
        (
            "정본 1개만 변경 + 동반 0 → 위반 (정본 1, 누락 3)",
            ["common/tasks/normalize/build_status.yml"],
            (
                ["common/tasks/normalize/build_status.yml"],
                ["docs/reference/decision-log.md", "docs/contract/03-fields.md",
                 "tests/*status* 또는 *scenario* mock fixture"],
            ),
        ),
        (
            "정본 + 동반 4종 모두 → 통과",
            [
                "common/tasks/normalize/build_status.yml",
                "docs/reference/decision-log.md",
                "docs/contract/03-fields.md",
                "tests/test_status_scenarios.py",
            ],
            (["common/tasks/normalize/build_status.yml"], []),
        ),
        (
            "정본 외 변경 → 통과",
            ["adapters/redfish/dell_idrac9.yml"],
            ([], []),
        ),
        (
            "빈 staged → 통과",
            [],
            ([], []),
        ),
        (
            "Windows path separator 정규화",
            ["common\\tasks\\normalize\\build_errors.yml"],
            (
                ["common/tasks/normalize/build_errors.yml"],
                ["docs/reference/decision-log.md", "docs/contract/03-fields.md",
                 "tests/*status* 또는 *scenario* mock fixture"],
            ),
        ),
        (
            "정본 3종 + 동반 일부 (`docs/reference/decision-log.md` 누락) + tests scenario hint",
            [
                "common/tasks/normalize/build_status.yml",
                "common/tasks/normalize/build_sections.yml",
                "common/tasks/normalize/build_errors.yml",
                "docs/contract/03-fields.md",
                "tests/test_scenario_b.py",
            ],
            (
                [
                    "common/tasks/normalize/build_status.yml",
                    "common/tasks/normalize/build_sections.yml",
                    "common/tasks/normalize/build_errors.yml",
                ],
                ["docs/reference/decision-log.md"],
            ),
        ),
        (
            "tests 안에 status/scenario hint 없는 파일 → 회귀 누락",
            [
                "common/tasks/normalize/build_status.yml",
                "docs/reference/decision-log.md",
                "docs/contract/03-fields.md",
                "tests/test_unrelated.py",
            ],
            (
                ["common/tasks/normalize/build_status.yml"],
                ["tests/*status* 또는 *scenario* mock fixture"],
            ),
        ),
    ]
    all_pass = True
    for label, staged, expected in cases:
        result = detect_violation(staged)
        canonical, missing = result
        exp_canonical, exp_missing = expected
        ok = (sorted(canonical) == sorted(exp_canonical)
              and sorted(missing) == sorted(exp_missing))
        print(f"{'PASS' if ok else 'FAIL'}: {label}")
        if not ok:
            all_pass = False
            print(f"  expected: canonical={exp_canonical}, missing={exp_missing}")
            print(f"  actual  : canonical={canonical}, missing={missing}")
    return 0 if all_pass else 1


def main() -> int:
    parser = argparse.ArgumentParser(description="rule 13 R8 status 로직 시나리오 매트릭스 검증")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    if os.environ.get("STATUS_LOGIC_SKIP") == "1":
        return 0
    if os.environ.get("STATUS_LOGIC_SKIP_COSMETIC") == "1":
        return 0

    repo_root = Path(".").resolve()
    staged = _staged_files(repo_root)
    if not staged:
        return 0

    canonical, missing = detect_violation(staged)
    if not canonical or not missing:
        return 0

    print(
        "[status logic] rule 13 R8 위반 — 정본 변경 + 동반 매트릭스 미갱신 (BLOCKING — cycle 2026-05-11 격상):",
        file=sys.stderr,
    )
    print("  정본 변경:", file=sys.stderr)
    for f in canonical:
        print(f"    - {f}", file=sys.stderr)
    print("  동반 갱신 누락:", file=sys.stderr)
    for f in missing:
        print(f"    - {f}", file=sys.stderr)
    print(
        "\n  → status 로직 정본 변경 시 4 시나리오 매트릭스 동반 갱신 의무 (rule 13 R8).",
        file=sys.stderr,
    )
    print(
        "  → cosmetic only (주석/들여쓰기 — 4 시나리오 결과 변경 없음) 시:",
        file=sys.stderr,
    )
    print(
        "       STATUS_LOGIC_SKIP_COSMETIC=1 git commit ...",
        file=sys.stderr,
    )
    print("  → 강제 skip: STATUS_LOGIC_SKIP=1 git commit ...", file=sys.stderr)

    return 1


if __name__ == "__main__":
    sys.exit(main())
