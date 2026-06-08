#!/usr/bin/env python3
"""PROJECT_MAP fingerprint drift 체크.

`.claude/policy/project-map-fingerprint.yaml`에 baseline 디렉터리별 SHA-1을 기록.
실제 저장소와 비교하여 drift 감지.

fingerprint는 **git 추적 파일의 경로 집합(정렬된 파일 목록)** 을 해싱한다. 따라서:
- 줄바꿈(LF/CRLF, autocrlf) 차이에 영향받지 않음 — 파일 내용을 보지 않음
- `__pycache__/*.pyc`, untracked 로컬 파일에 영향받지 않음 — git 추적 파일만 대상
- 파일 내용 편집에도 반응하지 않음 — PROJECT_MAP 은 구조 문서이므로 내용 변경 시 갱신 불요
- **구조 변경만 추적** — 파일/디렉터리 추가·삭제·이름변경 (rule 28 R1 #2 목적과 정합)

git 사용 불가 환경에서는 디스크 rglob 경로 fallback.

Exit codes:
    0 = 일치 (drift 없음)
    2 = drift 감지
    3 = baseline 없음
    1 = 실행 에러

Usage:
    python scripts/ai/check_project_map_drift.py [--update]
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple


WATCHED_DIRS = [
    "os-gather",
    "esxi-gather",
    "redfish-gather",
    "common",
    "adapters",
    "schema",
    "callback_plugins",
    "filter_plugins",
    "lookup_plugins",
    "module_utils",
    "tests",
]


def _git_ls_files_staged(repo_root: Path, subdir: str) -> Optional[List[Tuple[str, str]]]:
    """git index의 <subdir> 추적 파일을 (경로, blob OID) list로 반환.

    git 사용 불가(미설치 / 비 git 디렉터리) 시 None.
    """
    try:
        proc = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "-s", "--", subdir],
            capture_output=True,
            text=True,
            check=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
    entries: List[Tuple[str, str]] = []
    for line in proc.stdout.splitlines():
        # 형식: "<mode> <oid> <stage>\t<path>"
        if "\t" not in line:
            continue
        meta, path = line.split("\t", 1)
        parts = meta.split()
        if len(parts) >= 2:
            entries.append((path, parts[1]))
    return entries


def _fingerprint_dir_disk(d: Path) -> str:
    """fallback: 디스크 rglob 경로 집합 기반 (git 불가 환경).

    내용/크기를 보지 않고 파일 경로만 해싱 (구조 변경만 추적). 단 git 부재라
    __pycache__/untracked 도 포함될 수 있어 git 경로보다 noise 여지 있음 (degraded).
    """
    if not d.is_dir():
        return "missing"
    h = hashlib.sha1()
    for f in sorted(d.rglob("*")):
        if f.is_file():
            try:
                h.update(f"{f.relative_to(d).as_posix()}\n".encode("utf-8"))
            except Exception:
                pass
    return h.hexdigest()[:12]


def fingerprint_dir(repo_root: Path, subdir: str) -> str:
    """디렉터리의 git 추적 파일 경로 집합을 SHA-1로 해싱 (구조 변경만 추적).

    경로 목록만 해싱하므로 줄바꿈(CRLF/LF) 차이, __pycache__/.pyc, untracked
    로컬 파일, **파일 내용 편집** 에 영향받지 않는다 — 파일/디렉터리 추가·삭제·
    이름변경에만 반응. git 사용 불가 시 디스크 rglob 경로 fallback.
    """
    entries = _git_ls_files_staged(repo_root, subdir)
    if entries is None:
        return _fingerprint_dir_disk(repo_root / subdir)
    if not entries and not (repo_root / subdir).is_dir():
        return "missing"
    h = hashlib.sha1()
    for path, _oid in sorted(entries):
        h.update(f"{path}\n".encode("utf-8"))
    return h.hexdigest()[:12]


def _parse_fingerprint_yaml(yaml_text: str) -> Dict[str, str]:
    """간단한 키:값 YAML 파서 (stdlib only)."""
    out: Dict[str, str] = {}
    for line in yaml_text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _format_fingerprint_yaml(fp: Dict[str, str]) -> str:
    """fingerprint dict를 YAML로 직렬화."""
    lines = ["# PROJECT_MAP fingerprint — 디렉터리별 SHA-1 (앞 12자)",
             "# scripts/ai/check_project_map_drift.py --update 로 갱신",
             ""]
    for k in sorted(fp.keys()):
        lines.append(f"{k}: {fp[k]}")
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="PROJECT_MAP drift check")
    parser.add_argument("--update", action="store_true", help="baseline 갱신")
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    fp_path = repo_root / ".claude" / "policy" / "project-map-fingerprint.yaml"

    current = {d: fingerprint_dir(repo_root, d) for d in WATCHED_DIRS}

    if args.update:
        fp_path.parent.mkdir(parents=True, exist_ok=True)
        fp_path.write_text(_format_fingerprint_yaml(current), encoding="utf-8")
        print(f"baseline 갱신: {fp_path}")
        return 0

    if not fp_path.is_file():
        print(f"baseline 없음: {fp_path}")
        print("→ python scripts/ai/check_project_map_drift.py --update 실행 권장")
        return 3

    baseline = _parse_fingerprint_yaml(fp_path.read_text(encoding="utf-8"))

    drifted = []
    for d, h in current.items():
        if baseline.get(d) and baseline[d] != h:
            drifted.append((d, baseline[d], h))
        elif d not in baseline:
            drifted.append((d, "(미등록)", h))

    if drifted:
        print(f"drift 감지: {len(drifted)}건")
        for d, old, new in drifted:
            print(f"  - {d}: {old} → {new}")
        return 2

    print("PROJECT_MAP fingerprint 일치")
    return 0


if __name__ == "__main__":
    sys.exit(main())
