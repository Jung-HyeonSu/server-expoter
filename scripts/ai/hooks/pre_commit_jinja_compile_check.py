#!/usr/bin/env python3
"""pre-commit hook — inline Jinja2 템플릿 컴파일 검사 (set_fact 파싱 크래시 차단).

기존 post_edit_jinja_check.py 는 정규식 짝 검사(`{{`/`{%`/if/endif)만 한다.
그래서 **표현식 블록 안에 인라인 주석 `{# #}` 를 넣은 버그를 못 잡는다**:

    {%- set _ = out.append({
      'device':  _dev_path,
      {# 설명 #}            <-- Jinja2 는 {% %} 표현식 안 {# #} 를 허용 안 함
      'model':   ...,
    }) -%}

→ Ansible 런타임에서 `finalization of task args for ansible.builtin.set_fact failed
   ... syntax error in template ... unexpected char '#' at NNN` 으로 죽는다.

본 hook 은 staged YAML/.j2 의 모든 인라인 Jinja2 템플릿을 **실제 jinja2 파서로 컴파일**해
TemplateSyntaxError 를 잡는다 (위 버그 + 닫히지 않은 태그 + 잘못된 식 전부 커버).

직전 사고 (2026-06-12):
- os-gather/tasks/linux/gather_storage.yml  (_l_norm_physical_disks / _raw)
- os-gather/tasks/windows/gather_network.yml (_w_norm_interfaces)
  → dict 리터럴 내부 `{# Round 16 ... #}` 3곳. raw fallback 평가 시 크래시.

검사 알고리즘:
1. git diff --cached --name-only 로 staged YAML/.j2 파일 list (server-exporter 영역만)
2. YAML 은 yaml.compose_all 로 노드 + 파일 라인 번호 유지하며 scalar 순회
3. 각 scalar 값에 Jinja 마커(`{{`/`{%`/`{#`) 있으면 jinja2.Environment().parse()
4. .j2 파일은 전체를 1개 템플릿으로 컴파일
5. TemplateSyntaxError → 파일 라인 번호와 함께 보고

Exit codes:
    0 — 통과 / advisory 경고 (commit 허용) / jinja2·yaml 미설치 (graceful skip)
    1 — JINJA_COMPILE_BLOCKING=1 또는 --blocking 명시 시 위반 발견

비활성화 환경변수:
    JINJA_COMPILE_SKIP=1      — 본 hook skip
    JINJA_COMPILE_BLOCKING=1  — advisory → blocking 격상

Usage:
    pre-commit hook 자동 호출. 수동:
        python scripts/ai/hooks/pre_commit_jinja_compile_check.py
        python scripts/ai/hooks/pre_commit_jinja_compile_check.py --all        # 전 저장소 스캔
        python scripts/ai/hooks/pre_commit_jinja_compile_check.py --self-test
"""
from __future__ import annotations

import argparse
import glob
import os
import subprocess
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# jinja2 / yaml 미설치 환경에서도 commit 을 막지 않도록 graceful import
try:
    import jinja2  # type: ignore
    import yaml  # type: ignore
    _DEPS_OK = True
except ImportError:  # pragma: no cover - 환경 의존
    _DEPS_OK = False


# YAML 스캔 대상 디렉터리 (다른 영역 false positive 차단). regex hook 과 동일 정책.
TARGET_DIRS: tuple[str, ...] = (
    "os-gather/",
    "esxi-gather/",
    "redfish-gather/",
    "common/",
    "adapters/",
    "callback_plugins/",
    "filter_plugins/",
    "lookup_plugins/",
)

_JINJA_MARKERS = ("{{", "{%", "{#")


def _has_jinja(text: str) -> bool:
    return any(m in text for m in _JINJA_MARKERS)


def _normalize(p: str) -> str:
    return p.replace("\\", "/").strip()


def _iter_scalar_nodes(node):
    """yaml.compose_all 노드 트리 순회 → (value, file_line) yield.

    ScalarNode.start_mark.line 은 0-based → +1 해서 1-based 파일 라인.
    """
    # 지연 import 가드: _DEPS_OK 가 False 면 호출 안 됨
    if isinstance(node, yaml.ScalarNode):
        if isinstance(node.value, str):
            yield node.value, node.start_mark.line + 1
    elif isinstance(node, yaml.MappingNode):
        for key_node, val_node in node.value:
            yield from _iter_scalar_nodes(key_node)
            yield from _iter_scalar_nodes(val_node)
    elif isinstance(node, yaml.SequenceNode):
        for child in node.value:
            yield from _iter_scalar_nodes(child)


def check_yaml_text(text: str) -> list[tuple[int, int, str, str]]:
    """YAML 본문 → Jinja2 컴파일 실패 [(file_line, jinja_lineno, msg, snippet)].

    yaml.compose_all 로 파일 라인 번호를 유지한다. YAML 자체가 깨졌으면
    (별도 게이트 영역) 빈 list (본 hook 책임 아님).
    """
    env = jinja2.Environment()
    findings: list[tuple[int, int, str, str]] = []
    try:
        roots = list(yaml.compose_all(text, Loader=yaml.SafeLoader))
    except yaml.YAMLError:
        return findings  # YAML 파싱 불가 — 본 hook 범위 밖

    for root in roots:
        if root is None:
            continue
        for value, file_line in _iter_scalar_nodes(root):
            if not _has_jinja(value):
                continue
            try:
                env.parse(value)
            except jinja2.TemplateSyntaxError as e:
                jlineno = e.lineno or 1
                snippet = value.strip().splitlines()[0] if value.strip() else ""
                findings.append((file_line, jlineno, str(e), snippet))
    return findings


def check_j2_text(text: str) -> list[tuple[int, int, str, str]]:
    """.j2 파일 본문(전체가 1개 템플릿) → 컴파일 실패 list."""
    env = jinja2.Environment()
    try:
        env.parse(text)
    except jinja2.TemplateSyntaxError as e:
        jlineno = e.lineno or 1
        lines = text.splitlines()
        snippet = lines[jlineno - 1].strip() if 0 < jlineno <= len(lines) else ""
        return [(jlineno, jlineno, str(e), snippet)]
    return []


def check_file(abs_path: Path) -> list[tuple[int, int, str, str]]:
    try:
        text = abs_path.read_text(encoding="utf-8", errors="replace")
    except (OSError, UnicodeDecodeError):
        return []
    suffix = abs_path.suffix.lower()
    if suffix == ".j2":
        return check_j2_text(text)
    if suffix in (".yml", ".yaml"):
        return check_yaml_text(text)
    return []


def _staged_files(repo_root: Path) -> list[str]:
    try:
        r = subprocess.run(
            ["git", "diff", "--cached", "--name-only"],
            capture_output=True, text=True, cwd=str(repo_root), timeout=5,
            encoding="utf-8", errors="replace",
        )
    except (OSError, subprocess.SubprocessError):
        return []
    files: list[str] = []
    for ln in (r.stdout or "").splitlines():
        path = _normalize(ln)
        if not path:
            continue
        if not (path.endswith(".yml") or path.endswith(".yaml") or path.endswith(".j2")):
            continue
        if not any(path.startswith(d) for d in TARGET_DIRS):
            continue
        files.append(path)
    return files


def _all_files(repo_root: Path) -> list[str]:
    files: list[str] = []
    for pat in ("**/*.yml", "**/*.yaml", "**/*.j2"):
        for fp in glob.glob(str(repo_root / pat), recursive=True):
            rel = _normalize(os.path.relpath(fp, repo_root))
            if rel.startswith(".git/"):
                continue
            if not any(rel.startswith(d) for d in TARGET_DIRS):
                continue
            files.append(rel)
    return sorted(set(files))


def check_repo(repo_root: Path, blocking: bool = False, scan_all: bool = False) -> int:
    if not _DEPS_OK:
        print("[INFO] jinja2/PyYAML 미설치 — Jinja2 컴파일 검사 skip (commit 허용)",
              file=sys.stderr)
        return 0

    files = _all_files(repo_root) if scan_all else _staged_files(repo_root)
    if not files:
        return 0

    total = 0
    for rel_path in files:
        abs_path = repo_root / rel_path
        if not abs_path.is_file():
            continue
        findings = check_file(abs_path)
        if not findings:
            continue
        total += len(findings)
        sev = "BLOCK" if blocking else "WARN"
        print(f"[{sev}] {rel_path} — Jinja2 템플릿 컴파일 실패 {len(findings)} 건:",
              file=sys.stderr)
        for file_line, jlineno, msg, snippet in findings:
            preview = snippet if len(snippet) <= 100 else snippet[:97] + "..."
            print(f"  L{file_line}+ (템플릿 {jlineno}행): {msg}", file=sys.stderr)
            if preview:
                print(f"      near: {preview}", file=sys.stderr)

    if total == 0:
        return 0

    print("", file=sys.stderr)
    print("[Jinja2] set_fact 등 inline 템플릿 문법 오류 = Ansible 런타임 크래시 위험.", file=sys.stderr)
    print("  흔한 원인: {%- set x = {...} -%} 같은 표현식 dict **안쪽**에 {# 주석 #} 삽입.", file=sys.stderr)
    print("  해결: 주석을 태스크 위 YAML `#` 주석으로 이동 (표현식 밖으로).", file=sys.stderr)
    print("  skip: JINJA_COMPILE_SKIP=1 (commit 단발성)", file=sys.stderr)

    return 1 if blocking else 0


def _self_test() -> int:
    if not _DEPS_OK:
        print("[SKIP] jinja2/PyYAML 미설치 — self-test 불가", file=sys.stderr)
        return 0

    cases: list[tuple[str, str, int]] = [
        (
            "bad: {# #} inside set_fact dict literal (2026-06-12 사고 패턴)",
            "- name: t\n"
            "  ansible.builtin.set_fact:\n"
            "    x: >-\n"
            "      {%- set _ = out.append({\n"
            "        'id': a,\n"
            "        {# inline comment in expr #}\n"
            "        'model': b\n"
            "      }) -%}\n"
            "      {{ out }}\n",
            1,
        ),
        (
            "good: standalone {# #} between tags",
            "- name: t\n"
            "  ansible.builtin.set_fact:\n"
            "    x: >-\n"
            "      {%- set out = [] -%}\n"
            "      {# 설명 주석은 태그 사이에서 OK #}\n"
            "      {%- set out = out + [1] -%}\n"
            "      {{ out }}\n",
            0,
        ),
        (
            "bad: unclosed expression",
            "- set_fact:\n"
            "    y: \"{{ foo | default(0) \"\n",
            1,
        ),
        (
            "good: normal multi-line set_fact dict (no inline comment)",
            "- set_fact:\n"
            "    z: >-\n"
            "      {%- set _ = out.append({\n"
            "        'a': 1,\n"
            "        'b': 2\n"
            "      }) -%}\n"
            "      {{ out }}\n",
            0,
        ),
        (
            "good: plain YAML, no jinja",
            "- name: hello\n"
            "  debug:\n"
            "    msg: world\n",
            0,
        ),
    ]
    failures = 0
    for desc, yaml_text, expected in cases:
        got = len(check_yaml_text(yaml_text))
        status = "OK " if got == expected else "FAIL"
        print(f"[{status}] {desc}: expected={expected} got={got}")
        if got != expected:
            failures += 1
    if failures:
        print(f"\n{failures} self-test case FAILED", file=sys.stderr)
        return 1
    print(f"\nself-test OK ({len(cases)}/{len(cases)})")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--self-test", action="store_true", help="hook 자체 검증")
    parser.add_argument("--all", action="store_true",
                        help="staged 대신 전 저장소 스캔 (수동 sweep)")
    parser.add_argument("--blocking", action="store_true",
                        help="advisory → blocking 격상 (JINJA_COMPILE_BLOCKING=1 동등)")
    args, _unknown = parser.parse_known_args()

    if args.self_test:
        return _self_test()

    if os.environ.get("JINJA_COMPILE_SKIP", "").strip() == "1":
        return 0

    blocking = args.blocking or os.environ.get("JINJA_COMPILE_BLOCKING", "").strip() == "1"
    repo_root = Path(__file__).resolve().parents[3]
    return check_repo(repo_root, blocking=blocking, scan_all=args.all)


if __name__ == "__main__":
    sys.exit(main())
