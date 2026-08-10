#!/usr/bin/env python3
"""envelope_change_check — envelope 13 필드 / data.* 신규 키 추가 검출.

cycle 2026-05-01 신규. rule 13 R5 + rule 96 R1-B 자동 검증 hook.

호출자 시스템 (Jenkins downstream / 모니터링) 이 envelope shape 가정으로
파싱하므로, 호환성 cycle 에서의 신규 키 추가는 호출자 영향. 본 hook 은
PostToolUse Edit / Write 또는 pre-commit 시점에 envelope-touching 파일
변경을 감지해 advisory 보고.

검출 대상 (envelope 정본):
- common/tasks/normalize/build_output.yml  — envelope 13 필드 작성 정본
- common/tasks/normalize/build_*.yml       — 빌더
- callback_plugins/json_only.py            — stdout callback
- schema/sections.yml                       — 섹션 list
- schema/field_dictionary.yml               — 필드 정의
- schema/baseline_v1/**.json                — vendor baseline

검출 패턴:
1. envelope top-level 13 필드 변경 (target_type/collection_method/ip/hostname/
   vendor/status/sections/data/diagnosis/meta/correlation/errors/schema_version)
2. diagnosis.details / diagnosis.* 신규 sub-key
3. data.<section>.* 신규 field

advisory 모드 (exit 0). 발견 시 stderr 경고 + docs/ai/incoming-review/ 보고.

Self-test:
    python scripts/ai/hooks/envelope_change_check.py --self-test

Pre-commit 활성화:
    bash scripts/ai/hooks/install-git-hooks.sh
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

ENVELOPE_FIELDS_FROZEN: frozenset[str] = frozenset({
    "target_type", "collection_method", "ip", "hostname", "vendor",
    "status", "sections", "diagnosis", "meta", "correlation",
    "errors", "data", "schema_version",
})

ENVELOPE_TOUCHING_PATHS = (
    "common/tasks/normalize/build_output.yml",
    "common/tasks/normalize/build_",
    "callback_plugins/json_only.py",
    "schema/sections.yml",
    "schema/field_dictionary.yml",
    "schema/baseline_v1/",
    "schema/examples/",
)

DIAGNOSIS_SUBKEY_RE = re.compile(r"diagnosis\.(\w+)")
DATA_FIELD_RE = re.compile(r"data\.(\w+)\.(\w+)")


def get_changed_files() -> list[str]:
    """git status (staged + unstaged) — pre-commit / post-edit advisory."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]
    except (FileNotFoundError, subprocess.SubprocessError):
        return []


def is_envelope_touching(path: str) -> bool:
    """envelope 정본에 영향을 주는 파일인지 advisory 판정."""
    return any(path.startswith(p) or p in path for p in ENVELOPE_TOUCHING_PATHS)


def extract_top_level_keys(text: str) -> set[str]:
    """JSON / YAML 안의 envelope top-level 키 후보 추출 (regex 휴리스틱)."""
    keys: set[str] = set()
    for line in text.splitlines():
        m = re.match(r'^\s*[\'"]?(\w+)[\'"]?\s*[:=]', line)
        if m:
            keys.add(m.group(1))
    return keys


def scan_envelope_changes(changed_files: list[str]) -> list[dict[str, str]]:
    """envelope 변경 후보 검출. advisory 결과 list 반환."""
    findings: list[dict[str, str]] = []
    for f in changed_files:
        if not is_envelope_touching(f):
            continue
        full = REPO_ROOT / f
        if not full.is_file():
            continue
        try:
            text = full.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        if "build_output.yml" in f:
            present = extract_top_level_keys(text)
            unknown = present - ENVELOPE_FIELDS_FROZEN - {"name", "set_fact",
                                                          "block", "when", "vars"}
            for k in sorted(unknown):
                if len(k) > 3 and not k.startswith("_"):
                    findings.append({
                        "file": f,
                        "category": "envelope_top_level_unknown",
                        "key": k,
                        "advisory": "envelope 13 필드 외 top-level 키 의심",
                    })

        for m in DIAGNOSIS_SUBKEY_RE.finditer(text):
            sub = m.group(1)
            if sub not in {"precheck", "details", "failure_stage",
                           "failure_code", "failure_reason",
                           "gather_mode", "auth"}:
                findings.append({
                    "file": f,
                    "category": "diagnosis_subkey",
                    "key": f"diagnosis.{sub}",
                    "advisory": "diagnosis 신 sub-key — 호환성 외 영역 의심",
                })

        for m in DATA_FIELD_RE.finditer(text):
            section, field = m.group(1), m.group(2)
            if section in {"power", "memory", "cpu", "storage", "network",
                           "system", "hardware", "bmc", "firmware", "users"}:
                if field in {"thermal_score", "health_score", "predicted_failure"}:
                    findings.append({
                        "file": f,
                        "category": "data_new_field",
                        "key": f"data.{section}.{field}",
                        "advisory": "data 신 field — schema 확장 (호환성 외)",
                    })

    return findings


def write_advisory_report(findings: list[dict[str, str]]) -> Path | None:
    """findings 발견 시 docs/ai/incoming-review/ 보고서 생성."""
    if not findings:
        return None
    out_dir = REPO_ROOT / "docs/ai/incoming-review"
    out_dir.mkdir(parents=True, exist_ok=True)
    today = date.today().isoformat()
    out = out_dir / f"{today}-envelope-change-advisory.md"
    lines = [
        f"# envelope 변경 advisory — {today}",
        "",
        "> rule 13 R5 / rule 96 R1-B 자동 검출. 호환성 cycle 외 영역 의심 시 사용자 결정 필요.",
        "",
        f"## 발견 ({len(findings)} 건)",
        "",
    ]
    for f in findings:
        lines.append(f"- **{f['category']}** — `{f['key']}` (`{f['file']}`)")
        lines.append(f"  - {f['advisory']}")
    lines.append("")
    lines.append("## 결정 필요")
    lines.append("- 호환성 fallback (Additive)? → OK, sources origin 추가")
    lines.append("- 새 데이터 / 새 섹션? → 별도 cycle + schema 변경 승인 (rule 92 R5)")
    out.write_text("\n".join(lines), encoding="utf-8")
    return out


def self_test() -> int:
    """self-test mode — 합성 input 으로 검출 흐름 검증."""
    print("[envelope_change_check] self-test 시작", file=sys.stderr)
    sample_yaml = """\
- name: build envelope
  set_fact:
    target_type: redfish
    diagnosis_thermal: ref to diagnosis.thermal_score
    data_field: data.power.thermal_score is suspicious
"""
    diag_findings = [
        m.group(1) for m in DIAGNOSIS_SUBKEY_RE.finditer(sample_yaml)
        if m.group(1) not in {"precheck", "details", "failure_stage",
                              "failure_code", "failure_reason",
                              "gather_mode", "auth"}
    ]
    data_findings = [
        (m.group(1), m.group(2)) for m in DATA_FIELD_RE.finditer(sample_yaml)
        if m.group(2) in {"thermal_score", "health_score", "predicted_failure"}
    ]

    if diag_findings and data_findings:
        print("[envelope_change_check] self-test PASS — 패턴 검출 동작 "
              f"(diag={diag_findings}, data={data_findings})",
              file=sys.stderr)
        return 0
    print(f"[envelope_change_check] self-test FAIL — diag={diag_findings} "
          f"data={data_findings}", file=sys.stderr)
    return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="envelope change advisory")
    parser.add_argument("--self-test", action="store_true",
                        help="self-test mode (no git)")
    parser.add_argument("--strict", action="store_true",
                        help="findings 발견 시 exit 1 (default advisory)")
    args = parser.parse_args()

    if args.self_test:
        return self_test()

    changed = get_changed_files()
    if not changed:
        return 0

    findings = scan_envelope_changes(changed)
    if not findings:
        return 0

    print(f"[envelope_change_check] advisory: {len(findings)} 건 envelope "
          "변경 후보", file=sys.stderr)
    for f in findings[:5]:
        print(f"  - {f['category']}: {f['key']} ({f['file']})", file=sys.stderr)
    out = write_advisory_report(findings)
    if out:
        rel = out.relative_to(REPO_ROOT)
        print(f"[envelope_change_check] 보고서: {rel}", file=sys.stderr)

    return 1 if args.strict else 0


if __name__ == "__main__":
    sys.exit(main())
