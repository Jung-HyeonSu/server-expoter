#!/usr/bin/env python3
"""SubagentStop hook — Agent self-approval 패턴 감지.

Agent가 자신이 작성한 결과를 본인이 검수/승인하는 패턴 (예: writer가 reviewer 역할까지)
관측 시 stderr 경고. .claude/.cache/self-approval-log.jsonl에 기록.

Self-approval 신호:
- Agent 결과에 "검수 완료", "승인합니다", "self-review 통과" 등 종결 표현
- 다른 reviewer agent 호출 흔적 없음

Usage:
    python scripts/ai/hooks/detect_self_approval.py (stdin SubagentStop payload)
"""

import json
import re
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[3]
LOG_PATH = REPO_ROOT / ".claude" / ".cache" / "self-approval-log.jsonl"

SELF_APPROVAL_PATTERNS = [
    re.compile(r"검수.{0,3}완료"),
    re.compile(r"self.?review\s+(통과|완료|pass)"),
    re.compile(r"승인합니다"),
    re.compile(r"approved by myself"),
    re.compile(r"본인.{0,3}검수"),
]


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

    output = payload.get("output", "") or payload.get("result", "") or ""
    output_text = output if isinstance(output, str) else json.dumps(output, ensure_ascii=False)

    matches = [p.pattern for p in SELF_APPROVAL_PATTERNS if p.search(output_text)]
    if matches:
        record = {
            "ts": time.time(),
            "subagent_type": payload.get("subagent_type", "?"),
            "matches": matches,
            "snippet": output_text[:200],
        }
        try:
            LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with LOG_PATH.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass

        print(f"[self-approval 의심] subagent='{record['subagent_type']}' "
              f"패턴={matches} — reviewer 별도 호출 권장",
              file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
