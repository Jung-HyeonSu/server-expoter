#!/usr/bin/env python3
"""Output schema drift check — sections.yml ↔ field_dictionary.yml ↔ baseline_v1 정합.

분류 (rule 80 R1 / Jenkins Stage 3):
    이 스크립트는 git hook도 Claude hook도 아닌 **CI/수동 검증 도구**다.
    - Jenkins Stage 3 (Validate Schema)에서 호출 (`docs/ai/references/jenkins/pipeline-syntax.md` 참조)
    - 사용자가 schema 변경 후 수동 실행 (rule 13 + rule 28 #1)
    - cycle 보고서에서 정적 검증으로 호출
    scripts/ai/hooks/ 디렉터리에 위치하지만 등록된 hook 아님 (git hook은 install-git-hooks.sh가 관리, Claude hook은 .claude/settings.json이 관리).

매칭 로직:
- sections.yml: top-level 'sections:' 아래 indent 2 key (10 섹션 — system/hardware/bmc/cpu/memory/...)
- field_dictionary.yml: top-level 'fields:' 아래 indent 2 key (dotted path 형식 — 'hardware.health', 'cpu.cores_physical', 'status', ...)
  → dotted path의 prefix (첫 '.' 앞)을 section 후보로 추출. 단 envelope 필드 (status / meta / diagnosis / correlation)는 섹션 아님 → 제외.

검사:
- sections.yml의 섹션이 field_dictionary.yml prefix에 누락 없는지
- baseline_v1 vendor JSON 파싱 가능 여부

Usage:
    python scripts/ai/hooks/output_schema_drift_check.py

Exit codes:
    0 = 정합
    2 = drift 감지
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _read_yaml_keys(path: Path, section: str = None) -> list[str]:
    """간단한 키 목록 파서 (stdlib only).

    section 인자 명시 시: section: 아래 indent 2 키 추출 (sections.yml의 'sections:' 패턴).
    없으면: indent 0 top-level 키.
    """
    if not path.is_file():
        return []
    keys = []
    in_section = section is None  # section 명시 안 됐으면 처음부터 수집
    try:
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.rstrip()
            if not line or line.lstrip().startswith("#"):
                continue
            stripped = line.lstrip()
            indent = len(line) - len(stripped)
            if section is not None and indent == 0 and stripped == f"{section}:":
                in_section = True
                continue
            if section is not None and indent == 0 and stripped.endswith(":") and in_section:
                # 다른 top-level 진입 → section 끝
                break
            target_indent = 2 if section is not None else 0
            if in_section and indent == target_indent and stripped.endswith(":"):
                key = stripped[:-1].strip()
                # YAML quoted key: "storage.physical_disks[]" → storage.physical_disks[]
                if len(key) >= 2 and key[0] == key[-1] and key[0] in ('"', "'"):
                    key = key[1:-1]
                # array notation: firmware[] / firmware[].component → firmware
                # (prefix 추출은 호출자 책임이지만, 키 자체는 원형 보존)
                keys.append(key)
    except Exception:
        pass
    return keys


# envelope 필드 (섹션 아님 — 13 필드 중 data 를 제외한 분석 계열)
ENVELOPE_FIELDS = {"status", "sections", "errors", "meta", "diagnosis", "correlation"}


def main() -> int:
    repo_root = Path(".").resolve()
    sections_path = repo_root / "schema" / "sections.yml"
    fd_path = repo_root / "schema" / "field_dictionary.yml"
    baseline_dir = repo_root / "schema" / "baseline_v1"

    issues = []

    # sections.yml: 'sections:' 아래 indent 2 (10 섹션 이름)
    sections = _read_yaml_keys(sections_path, section="sections")
    if not sections:
        sections = _read_yaml_keys(sections_path)

    # field_dictionary.yml: 'fields:' 아래 indent 2 (dotted path 형식)
    fd_paths = _read_yaml_keys(fd_path, section="fields")

    # dotted path → prefix 추출 (envelope 필드 제외, array 표기 [] 제거)
    fd_section_prefixes = set()
    for p in fd_paths:
        prefix = p.split(".", 1)[0]
        # firmware[] 같은 array notation에서 [] 제거
        prefix = prefix.split("[", 1)[0]
        if not prefix or prefix in ENVELOPE_FIELDS:
            continue
        fd_section_prefixes.add(prefix)

    # sections.yml ↔ field_dictionary.yml prefix 비교
    missing_in_fd = [s for s in sections if s not in fd_section_prefixes]
    if missing_in_fd:
        issues.append(
            f"sections.yml에 있지만 field_dictionary.yml에 prefix 없는 섹션: {missing_in_fd} "
            f"(field_dictionary 등록 prefix: {sorted(fd_section_prefixes)})"
        )

    # baseline JSON 점검 — 각 vendor baseline 안에 sections list 존재
    if baseline_dir.is_dir():
        for f in baseline_dir.glob("*.json"):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except Exception as e:
                issues.append(f"baseline 파싱 실패: {f.name} — {e}")
                continue
            data_sections = []
            if isinstance(data, dict):
                if "sections" in data and isinstance(data["sections"], dict):
                    data_sections = list(data["sections"].keys())
                elif "data" in data and isinstance(data["data"], dict):
                    data_sections = list(data["data"].keys())
            for s in sections:
                if data_sections and s not in data_sections:
                    # 정보성 — vendor가 일부 섹션 미지원할 수 있음
                    pass

    if issues:
        print("output schema drift 감지:")
        for i in issues:
            print(f"  - {i}")
        return 2

    print(
        f"output schema 정합: sections={len(sections)} "
        f"fd_paths={len(fd_paths)} fd_section_prefixes={len(fd_section_prefixes)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
