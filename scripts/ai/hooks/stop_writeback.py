#!/usr/bin/env python3
"""Stop hook — 세션 종료 시 docs/ai/CURRENT_STATE.md 갱신 권고.

세션이 어떻게 끝났는지(완료 / 미완)와 무관하게 작업 산출물 안내만.

Usage:
    python scripts/ai/hooks/stop_writeback.py
"""

import json
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[3]


def _read_payload() -> dict | None:
    if sys.stdin.isatty():
        return None
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return None
        return json.loads(raw)
    except (json.JSONDecodeError, AttributeError):
        return None


def main() -> int:
    payload = _read_payload()
    repo_root = REPO_ROOT

    # git status 요약 (변경된 파일이 있으면 알림)
    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            changed = len([ln for ln in r.stdout.splitlines() if ln.strip()])
            print(f"\n[세션 종료] 변경된 파일 {changed}건. "
                  "docs/ai/CURRENT_STATE.md 갱신 권장.")
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
