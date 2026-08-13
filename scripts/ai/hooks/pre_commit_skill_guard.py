#!/usr/bin/env python3
"""pre-commit hook — skill 변경 시 SKILL.md 형식 검증.

staged 파일 중 .claude/skills/*/SKILL.md 가 있으면 frontmatter 형식 검증.
형식 위반 시 commit 차단.

Usage:
    pre-commit hook 자동 호출. 수동:
    python scripts/ai/hooks/pre_commit_skill_guard.py

Exit codes:
    0 = 통과
    2 = 형식 위반 (commit 차단)
"""

import os
import re
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


def _check_skill_md(path: Path) -> list[str]:
    issues = []
    if not path.is_file():
        return ["파일 없음"]
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as e:
        return [f"읽기 실패: {e}"]

    fm_match = FRONTMATTER_RE.match(text)
    if not fm_match:
        issues.append("frontmatter 누락")
        return issues

    fm: dict = {}
    for line in fm_match.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fm[k.strip()] = v.strip().strip('"').strip("'")

    if not fm.get("name"):
        issues.append("frontmatter `name` 누락")
    elif fm.get("name") != path.parent.name:
        issues.append(f"name '{fm.get('name')}' ↔ 폴더 '{path.parent.name}' 불일치")

    desc = fm.get("description", "")
    if not desc:
        issues.append("frontmatter `description` 누락")
    elif len(desc) > 1024:
        issues.append(f"description 1024자 초과 ({len(desc)}자)")

    return issues


def main() -> int:
    if os.environ.get("SKILL_GUARD_SKIP") == "1":
        return 0

    repo_root = Path(".").resolve()
    try:
        # 2026-08-13: --diff-filter=d 필수. 이 옵션이 없으면 삭제된 SKILL.md 도 목록에
        #   들어와 _check_skill_md 가 "파일 없음"을 위반으로 보고하고 commit 을 막는다.
        #   skill 을 지우는 것은 정상 동작이므로 삭제는 형식 검증 대상이 아니다.
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-only", "--diff-filter=d"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=5,
            encoding="utf-8", errors="replace",
        )
        files = [ln.strip() for ln in (r.stdout or "").splitlines() if ln.strip()]
    except Exception:
        return 0

    skill_files = [f for f in files
                   if f.startswith(".claude/skills/") and f.endswith("/SKILL.md")]
    if not skill_files:
        return 0

    all_issues = []
    for f in skill_files:
        issues = _check_skill_md(repo_root / f)
        if issues:
            all_issues.append((f, issues))

    if all_issues:
        print("[skill guard] SKILL.md 형식 위반 — commit 차단:", file=sys.stderr)
        for f, issues in all_issues:
            print(f"  - {f}", file=sys.stderr)
            for i in issues:
                print(f"      • {i}", file=sys.stderr)
        print("\n  → 수정 후 재커밋. 의도적 skip: SKILL_GUARD_SKIP=1 git commit ...",
              file=sys.stderr)
        return 2

    return 0


if __name__ == "__main__":
    sys.exit(main())
