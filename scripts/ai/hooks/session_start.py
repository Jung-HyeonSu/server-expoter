#!/usr/bin/env python3
"""세션 시작 훅 — server-exporter 컨텍스트 + 구조 + 저장소 팩트.

scripts/ai/{detect_session_context,validate_claude_structure,collect_repo_facts}.py를
모듈로 import해 단일 프로세스에서 처리. repo_facts는 TTL 캐시.

Usage:
    python scripts/ai/hooks/session_start.py [--json] [--repo-root .]

Exit codes:
    0 = 항상 (세션 차단 방지)
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SCRIPT_DIR))

from detect_session_context import detect_context, get_current_branch  # noqa: E402
from validate_claude_structure import validate_structure  # noqa: E402
from collect_repo_facts import collect_facts  # noqa: E402

CACHE_DIR = Path(".claude") / ".cache"
CACHE_FILE = CACHE_DIR / "repo_facts.json"
CACHE_TTL_SECONDS = 3600


def _git_head_short(repo_root: Path) -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=5,
        )
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def _load_cached_facts(repo_root: Path) -> dict | None:
    cache_path = repo_root / CACHE_FILE
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    ts = data.get("_cached_at", 0)
    head = data.get("_cached_head", "")
    current_head = _git_head_short(repo_root)
    if time.time() - ts > CACHE_TTL_SECONDS:
        return None
    if head and current_head and head != current_head:
        return None
    return data.get("facts")


def _save_cached_facts(repo_root: Path, facts: dict) -> None:
    cache_path = repo_root / CACHE_FILE
    try:
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "_cached_at": time.time(),
            "_cached_head": _git_head_short(repo_root),
            "facts": facts,
        }
        cache_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    except OSError:
        pass


def _safe_call(fn, *args, default_error: str = "execution failed") -> dict:
    try:
        return fn(*args)
    except Exception as exc:
        return {"error": f"{default_error}: {exc}"}


def main() -> int:
    parser = argparse.ArgumentParser(description="세션 시작 컨텍스트/구조/팩트 수집")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--no-cache", action="store_true")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()

    try:
        branch = get_current_branch(repo_root)
        context = detect_context(branch)
    except Exception as exc:
        context = {"error": str(exc), "branch": "unknown"}

    structure = _safe_call(validate_structure, repo_root / ".claude",
                           default_error="structure validation failed")

    facts = None if args.no_cache else _load_cached_facts(repo_root)
    if facts is None:
        facts = _safe_call(collect_facts, repo_root, default_error="facts collection failed")
        if "error" not in facts:
            _save_cached_facts(repo_root, facts)

    has_issues = bool(context.get("error")) or bool(structure.get("issues"))

    summary = {
        "context": context,
        "structure": structure,
        "facts": {
            "channels_active": sum(facts.get("channels", {}).values()) if isinstance(facts.get("channels"), dict) else "?",
            "vendor_count": facts.get("vendor_count", "?"),
            "adapter_files": facts.get("adapter_files", "?"),
            "python_files": facts.get("python_files", "?"),
            "pytest_files": facts.get("pytest_files", "?"),
            "fixture_files": facts.get("fixture_files", "?"),
            "baseline_files": facts.get("baseline_files", "?"),
            "python_version": facts.get("python_version", "?"),
            "ansible_version": facts.get("ansible_version", "?"),
        },
        "status": "warning" if has_issues else "ready",
    }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        ctx = context
        if ctx.get("detected"):
            print(f"server-exporter — {ctx.get('purpose', '?')} (브랜치: {ctx.get('branch', '?')})")
        else:
            branch_name = ctx.get("branch", "unknown")
            print(f"브랜치 '{branch_name}'에서 컨텍스트 자동 감지 불가.")

        f = summary["facts"]
        print(f"\nPython {f['python_version']} / Ansible {f['ansible_version']}")
        print(f"3-channel: {f['channels_active']}개 / 벤더 어댑터 {f['adapter_files']}개 (벤더 {f['vendor_count']}종)")
        print(f"Python 파일: {f['python_files']}개 / pytest: {f['pytest_files']}개 / "
              f"Fixture: {f['fixture_files']}개 / Baseline: {f['baseline_files']}개")

        if structure.get("passed"):
            print("\n.claude/ 구조: OK")
        else:
            issues = structure.get("issues", [])
            print(f"\n.claude/ 구조: 이슈 {len(issues)}건")
            for issue in issues[:10]:
                print(f"  - {issue}")

        # PROJECT_MAP drift
        drift_script = repo_root / "scripts" / "ai" / "check_project_map_drift.py"
        if drift_script.exists():
            try:
                result = subprocess.run(
                    [sys.executable, str(drift_script)],
                    capture_output=True, text=True, timeout=10,
                    encoding="utf-8", errors="replace",
                )
                if result.returncode == 2:
                    print("\n[WARN] PROJECT_MAP drift 감지")
                    for line in (result.stdout or "").splitlines()[:5]:
                        if line.strip():
                            print(f"  {line}")
                    print("  → docs/ai/catalogs/PROJECT_MAP.md 갱신 검토 권장")
                elif result.returncode == 3:
                    print("\n[INFO] PROJECT_MAP fingerprint baseline 없음")
                    print("  → python scripts/ai/check_project_map_drift.py --update 실행 권장")
            except Exception:
                pass

        # 브랜치 갭 (feature/* 등에서만)
        gap_script = repo_root / "scripts" / "ai" / "check_gap_against_main.py"
        branch_name = ctx.get("branch", "") if isinstance(ctx, dict) else ""
        if gap_script.exists() and branch_name and branch_name not in ("main", "master"):
            try:
                result = subprocess.run(
                    [sys.executable, str(gap_script), "--no-fetch"],
                    capture_output=True, text=True, timeout=10,
                    encoding="utf-8", errors="replace",
                )
                if result.returncode == 0 and result.stdout:
                    lines = [ln for ln in result.stdout.splitlines() if ln.strip()]
                    if any("ahead" in ln or "behind" in ln for ln in lines[:5]):
                        print("")
                        for ln in lines[:8]:
                            print(ln)
            except Exception:
                pass

        if has_issues:
            print("\n세션 시작 시 경고 사항이 있습니다.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
