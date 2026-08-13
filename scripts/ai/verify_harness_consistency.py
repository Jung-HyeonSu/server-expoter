#!/usr/bin/env python3
"""하네스 일관성 검증 — rules ↔ skills ↔ agents ↔ policy 참조 정합.

각 rule/skill/agent 본문에서 다른 rule/skill/agent를 참조할 때
실제 존재하는 파일인지 grep + 파일 존재 검증.

또한 server-exporter 어휘 whitelist 적용 — clovirone 잔재 (Java/Spring/MyBatis/...) 검출.

추가 게이트 (cycle-005, DRIFT-005 옵션 (2)):
- redfish-gather/library/redfish_gather.py의 _BUILTIN_VENDOR_MAP ↔
  common/vars/vendor_aliases.yml 정규화 동기화 검사 (advisory)

Usage:
    python scripts/ai/verify_harness_consistency.py [--strict]

Exit codes:
    0 = 통과
    1 = 실행 에러
    2 = 일관성 위반 발견 (rule reference 위반 + --strict 잔재 어휘)
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import List, Set, Tuple

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


# clovirone 잔재 어휘 (server-exporter 본문에 등장하면 안 됨)
FORBIDDEN_WORDS = [
    "MyBatis",
    "Spring Boot",
    "Spring Bean",
    "Freemarker",
    "FTL",
    "Vue.js",
    "jQuery",
    "Gradle",
    "MariaDB",
    "Flyway",
    "Spock",
    "Playwright",
    "Bitbucket Pipelines",
    "clovircm-domain",
    "clovircm-web",
    "plugin-posco",
    "plugin-smilegate",
    "plugin-sdk",
    "sk-hynix-dev",
    "sk-hynix-claude",
    "BillingCalculator",
]

# 경로 모양 참조 — 이것만 보던 것이 이 검증기의 사각지대였다.
RULE_REF_RE = re.compile(r"\.claude/rules/(\d{2}-[a-z0-9-]+)\.md")
SKILL_REF_RE = re.compile(r"\.claude/skills/([a-z0-9-]+)/")
AGENT_REF_RE = re.compile(r"\.claude/agents/([a-z0-9-]+)\.md")
POLICY_REF_RE = re.compile(r"\.claude/policy/([a-z0-9-]+\.yaml)")

# ── 산문 참조 (2026-08-13 추가) ────────────────────────────────────────────
# 하네스는 서로를 경로가 아니라 **이름**으로 부른다. 경로 모양만 검사하니
# `rule 60`(파일 없음)·`implement-safe-change`(스킬 없음)·`CLAUDE.md Step 6`(절 없음)·
# `docs/contract/03-fields.md`(이동됨) 이 전부 통과했고, 그러면서 "모든 참조 정합 확인"을 찍었다.
# 초록불에 정보가 없으면 게이트가 아니라 장식이다.
BARE_RULE_RE = re.compile(r"(?<![\w/-])rule\s+(\d{2})(?![\d\w-])", re.IGNORECASE)
# `- skill: a, b` / `- agent: x` 같은 관계 선언 줄에서 백틱 이름을 뽑는다.
DECL_LINE_RE = re.compile(r"^\s*[-*]?\s*(skills?|agents?)\s*:\s*(.+)$", re.IGNORECASE)
BACKTICK_NAME_RE = re.compile(r"`([a-z][a-z0-9-]{2,})`")
# `CLAUDE.md Step 6` / `` `CLAUDE.md` §11 `` — 사이에 백틱이 끼는 표기가 흔하다
CLAUDE_SEC_RE = re.compile(r"CLAUDE\.md`?\s*(?:§|절)\s*(\d{1,2})")
CLAUDE_STEP_RE = re.compile(r"CLAUDE\.md`?\s*Step\s*\d{1,2}")
# 옛 번호 문서 약칭 — 2026-08-13 구조 재편으로 더 이상 유효하지 않다.
DOCS_SHORTHAND_RE = re.compile(r"(?<![\w/])docs/(\d{2})(?![\d\w])")


def _scan_file(path: Path) -> Tuple[List[str], List[str], List[str], List[str], List[str]]:
    """단일 파일에서 참조 + 잔재 어휘 추출."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return [], [], [], [], []

    rule_refs = RULE_REF_RE.findall(text)
    skill_refs = SKILL_REF_RE.findall(text)
    agent_refs = AGENT_REF_RE.findall(text)
    policy_refs = POLICY_REF_RE.findall(text)

    forbidden = []
    # 의도적 인용/명시 표현 — false positive 방지
    allow_markers = (
        "clovirone-base", "clovirone", "출처", "변환", "잔재", "금지 패턴",
        "Forbidden", "사용 안 함", "동등 역할", "동일 정신", "대신", "→",
        "(과거)", "관찰된", "이전", "deprecate", "polyfill",
        "와 달리", "에 대응", "DBA", "etc",
    )
    for word in FORBIDDEN_WORDS:
        if word in text:
            for line in text.splitlines():
                if word in line and not any(marker in line for marker in allow_markers):
                    forbidden.append(f"{word}: {line.strip()[:80]}")
                    break

    return rule_refs, skill_refs, agent_refs, policy_refs, forbidden


def _scan_prose_refs(
    path: Path,
    rule_nums: Set[str],
    skills: Set[str],
    agents: Set[str],
    claude_sections: Set[str],
) -> List[str]:
    """이름으로 부르는 참조가 실제로 존재하는지 본다."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return []

    found: List[str] = []
    for lineno, line in enumerate(text.splitlines(), 1):
        # 폐지 사실을 서술하는 줄은 대상이 아니다 (tombstone 은 정보다)
        tombstone = any(k in line for k in ("해제", "제거됨", "삭제됨", "존재하지 않", "폐지", "정리됨"))

        for num in BARE_RULE_RE.findall(line):
            if num not in rule_nums and not tombstone:
                found.append(f"{path.name}:{lineno}: 없는 rule 참조 — rule {num}")

        m = DECL_LINE_RE.match(line)
        if m:
            kind = m.group(1).lower().rstrip("s")
            for name in BACKTICK_NAME_RE.findall(m.group(2)):
                if kind == "skill" and name not in skills and not tombstone:
                    found.append(f"{path.name}:{lineno}: 없는 skill 참조 — {name}")
                if kind == "agent" and name not in agents and not tombstone:
                    found.append(f"{path.name}:{lineno}: 없는 agent 참조 — {name}")

        # CLAUDE.md 에는 "Step" 이라는 표제가 없다. 절 번호(`## N.`)뿐이다.
        # 번호가 우연히 맞아도 가리키는 내용이 다르므로 표기 자체를 위반으로 본다.
        if CLAUDE_STEP_RE.search(line):
            found.append(f"{path.name}:{lineno}: CLAUDE.md 에 Step 표제 없음 — 절 번호(§N)로 적어야 한다")
        for sec in CLAUDE_SEC_RE.findall(line):
            if sec not in claude_sections:
                found.append(f"{path.name}:{lineno}: CLAUDE.md 에 없는 절 — §{sec}")

        for num in DOCS_SHORTHAND_RE.findall(line):
            if not tombstone:
                found.append(f"{path.name}:{lineno}: 옛 문서 번호 약칭 — docs/{num} (구조 재편됨)")

    return found


def main() -> int:
    parser = argparse.ArgumentParser(description="하네스 일관성 검증")
    parser.add_argument(
        "--no-forbidden-check",
        action="store_true",
        help="잔재 어휘 검사 비활성화 (default: 활성화 — rule 00 약속)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="(deprecated) 잔재 어휘 검사는 default. 호환성 위해 유지.",
    )
    parser.add_argument("--repo-root", default=".")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    claude_dir = repo_root / ".claude"

    if not claude_dir.is_dir():
        print(f".claude/ 없음: {claude_dir}", file=sys.stderr)
        return 1

    # 존재하는 rule/skill/agent/policy 카탈로그
    existing_rules: Set[str] = {
        f.stem for f in (claude_dir / "rules").glob("*.md")
    } if (claude_dir / "rules").is_dir() else set()
    existing_skills: Set[str] = {
        d.name for d in (claude_dir / "skills").iterdir() if d.is_dir()
    } if (claude_dir / "skills").is_dir() else set()
    existing_agents: Set[str] = {
        f.stem for f in (claude_dir / "agents").glob("*.md")
    } if (claude_dir / "agents").is_dir() else set()
    existing_policies: Set[str] = {
        f.name for f in (claude_dir / "policy").glob("*.yaml")
    } if (claude_dir / "policy").is_dir() else set()

    issues: List[str] = []
    forbidden_total: List[str] = []

    # SKILL.md frontmatter name ↔ 폴더명 일치 검사 (NEXT_ACTIONS P2 — 2026-04-27 추가)
    skill_name_re = re.compile(r"^name:\s*(.+?)\s*$", re.MULTILINE)
    for skill_dir in (claude_dir / "skills").iterdir() if (claude_dir / "skills").is_dir() else []:
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.is_file():
            issues.append(f".claude/skills/{skill_dir.name}/SKILL.md: 누락")
            continue
        try:
            text = skill_md.read_text(encoding="utf-8")
        except Exception:
            continue
        m = skill_name_re.search(text)
        if not m:
            issues.append(f".claude/skills/{skill_dir.name}/SKILL.md: frontmatter 'name' 누락")
        elif m.group(1).strip().strip('"').strip("'") != skill_dir.name:
            issues.append(
                f".claude/skills/{skill_dir.name}/SKILL.md: name '{m.group(1).strip()}' "
                f"↔ 폴더 '{skill_dir.name}' 불일치"
            )

    # 산문 참조 검사용 카탈로그
    rule_nums: Set[str] = {r.split("-", 1)[0] for r in existing_rules}
    claude_md = repo_root / "CLAUDE.md"
    claude_sections: Set[str] = set()
    if claude_md.is_file():
        claude_sections = set(
            re.findall(r"^##\s*(\d{1,2})\.", claude_md.read_text(encoding="utf-8"), re.MULTILINE)
        )

    for path in list(claude_dir.rglob("*.md")) + ([claude_md] if claude_md.is_file() else []):
        issues.extend(
            _scan_prose_refs(path, rule_nums, existing_skills, existing_agents, claude_sections)
        )

    for path in claude_dir.rglob("*.md"):
        rule_refs, skill_refs, agent_refs, policy_refs, forbidden = _scan_file(path)
        rel = path.relative_to(repo_root).as_posix()

        for r in rule_refs:
            if r not in existing_rules:
                issues.append(f"{rel}: 존재하지 않는 rule 참조 — {r}")
        for s in skill_refs:
            if s not in existing_skills:
                issues.append(f"{rel}: 존재하지 않는 skill 참조 — {s}")
        for a in agent_refs:
            if a not in existing_agents:
                issues.append(f"{rel}: 존재하지 않는 agent 참조 — {a}")
        for p in policy_refs:
            if p not in existing_policies:
                issues.append(f"{rel}: 존재하지 않는 policy 참조 — {p}")

        for fw in forbidden:
            forbidden_total.append(f"{rel}: {fw}")

    # ── vendor alias 동기화 검사 (cycle-005 게이트 — DRIFT-005 옵션 (2)) ─────────
    vendor_alias_drift: List[str] = _check_vendor_alias_sync(repo_root)

    print("=== 하네스 일관성 검증 ===")
    print(f"rules: {len(existing_rules)}, skills: {len(existing_skills)}, "
          f"agents: {len(existing_agents)}, policies: {len(existing_policies)}")

    if issues:
        print(f"\n참조 위반: {len(issues)}건")
        for i in issues[:50]:
            print(f"  - {i}")
        if len(issues) > 50:
            print(f"  ... ({len(issues) - 50}건 추가)")

    if forbidden_total:
        print(f"\nclovirone 잔재 어휘: {len(forbidden_total)}건")
        for f in forbidden_total[:20]:
            print(f"  - {f}")
        if len(forbidden_total) > 20:
            print(f"  ... ({len(forbidden_total) - 20}건 추가)")

    if vendor_alias_drift:
        print(f"\n[advisory] vendor alias 동기화 drift: {len(vendor_alias_drift)}건")
        for d in vendor_alias_drift:
            print(f"  - {d}")
        print("  → redfish_gather.py _BUILTIN_VENDOR_MAP과 vendor_aliases.yml 동기화 확인")

    forbidden_check_active = not args.no_forbidden_check
    if issues or (forbidden_check_active and forbidden_total):
        return 2

    print("\n통과: 모든 참조 정합 확인")
    return 0


# ── vendor alias 동기화 검사 ─────────────────────────────────────────────────

def _check_vendor_alias_sync(repo_root: Path) -> List[str]:
    """redfish_gather.py _BUILTIN_VENDOR_MAP ↔ vendor_aliases.yml 동기화 (lower-strip 비교)."""
    py_path = repo_root / "redfish-gather" / "library" / "redfish_gather.py"
    yml_path = repo_root / "common" / "vars" / "vendor_aliases.yml"
    if not py_path.is_file() or not yml_path.is_file():
        return []

    py_alias_map = _extract_python_vendor_map(py_path)
    yml_alias_map = _extract_yaml_vendor_aliases(yml_path)

    drift: List[str] = []
    all_canon = set(py_alias_map.keys()) | set(yml_alias_map.keys())
    for canon in sorted(all_canon):
        py_set = py_alias_map.get(canon, set())
        yml_set = yml_alias_map.get(canon, set())
        only_py = py_set - yml_set
        only_yml = yml_set - py_set
        if only_py:
            drift.append(f"vendor '{canon}': Python에만 있음 — {sorted(only_py)}")
        if only_yml:
            drift.append(f"vendor '{canon}': YAML에만 있음 — {sorted(only_yml)}")
    return drift


def _extract_python_vendor_map(path: Path) -> dict:
    """_BUILTIN_VENDOR_MAP dict literal에서 alias → canonical 매핑 추출 (canonical 별 set)."""
    try:
        text = path.read_text(encoding="utf-8")
    except Exception:
        return {}
    # _BUILTIN_VENDOR_MAP / _FALLBACK_VENDOR_MAP = { ... } 블록 추출
    m = re.search(r"_(?:BUILTIN|FALLBACK)_VENDOR_MAP\s*=\s*\{(.*?)\n\}", text, re.DOTALL)
    if not m:
        return {}
    body = m.group(1)
    # 'alias': 'canonical', 패턴 매칭 (loose)
    pair_re = re.compile(r"'([^']+)'\s*:\s*'([^']+)'")
    result: dict = {}
    for alias, canon in pair_re.findall(body):
        result.setdefault(canon.strip().lower(), set()).add(alias.strip().lower())
    return result


def _extract_yaml_vendor_aliases(path: Path) -> dict:
    """vendor_aliases.yml에서 canonical → alias set 추출 (간단 indent parser)."""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except Exception:
        return {}
    in_section = False
    current_canon: str = ""
    result: dict = {}
    for raw in lines:
        line = raw.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        stripped = line.lstrip()
        indent = len(line) - len(stripped)
        if indent == 0 and stripped == "vendor_aliases:":
            in_section = True
            continue
        if not in_section:
            continue
        if indent == 2 and stripped.endswith(":"):
            current_canon = stripped[:-1].strip().lower()
            result.setdefault(current_canon, set())
        elif indent >= 4 and stripped.startswith("-"):
            alias = stripped[1:].strip().strip('"').strip("'").lower()
            if current_canon:
                result.setdefault(current_canon, set()).add(alias)
    return result


if __name__ == "__main__":
    sys.exit(main())
