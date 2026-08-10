#!/usr/bin/env python3
"""Notification 이벤트 로깅.

Claude Code가 사용자에게 알림 (예: 권한 요청)을 보낼 때 발생.
.claude/.cache/notification-log.jsonl에 append.

Usage:
    python scripts/ai/hooks/notification_log.py (stdin payload)
"""

import json
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[3]
LOG_PATH = REPO_ROOT / ".claude" / ".cache" / "notification-log.jsonl"


def main() -> int:
    if sys.stdin.isatty():
        return 0
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return 0
        payload = json.loads(raw)
    except (json.JSONDecodeError, AttributeError):
        return 0

    record = {
        "ts": time.time(),
        "event": payload.get("hook_event_name", "Notification"),
        "message": payload.get("message", "")[:200],
    }

    try:
        LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError:
        pass

    return 0


if __name__ == "__main__":
    sys.exit(main())
