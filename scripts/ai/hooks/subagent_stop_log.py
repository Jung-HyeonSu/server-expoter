#!/usr/bin/env python3
"""SubagentStop 이벤트 로깅 — Agent 종료 시 결과 요약을 .claude/.cache/agent-log.jsonl에 append.

향후 self-improvement loop가 이 로그로부터 agent 활용 패턴 분석.

Usage:
    python scripts/ai/hooks/subagent_stop_log.py (stdin으로 SubagentStop payload 수신)
"""

import json
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[3]
LOG_PATH = REPO_ROOT / ".claude" / ".cache" / "agent-log.jsonl"


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
        "event": payload.get("hook_event_name", "SubagentStop"),
        "subagent_type": payload.get("subagent_type", "?"),
        "stop_reason": payload.get("stop_reason", "?"),
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
