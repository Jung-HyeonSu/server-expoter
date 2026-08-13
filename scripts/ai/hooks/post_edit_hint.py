#!/usr/bin/env python3
"""편집 후 힌트 — server-exporter 도메인 매핑.

파일 편집 후 관련 문서/테스트 제안.

Usage:
    python scripts/ai/hooks/post_edit_hint.py <file_path> [--json]
"""

import argparse
import json
import re
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

REPO_ROOT = Path(__file__).resolve().parents[3]


# server-exporter 도메인 힌트 규칙
HINT_RULES = [
    # 3-channel gather 코드
    (r"os-gather/.*\.yml$", "test",
     "OS gather 변경 → tests/redfish-probe + 실장비 검증 권장"),
    (r"os-gather/.*\.yml$", "doc",
     "GUIDE_FOR_AI.md Fragment 철학 / docs/develop/01-gather-structure.md 확인"),
    (r"esxi-gather/.*\.yml$", "test",
     "ESXi gather 변경 → community.vmware 의존성 + ESXi 실장비 검증"),
    (r"redfish-gather/.*\.yml$", "test",
     "Redfish gather 변경 → tests/redfish-probe + 벤더별 baseline 회귀"),
    (r"redfish-gather/library/.*\.py$", "test",
     "Redfish 라이브러리 변경 → ServiceRoot/Chassis/Systems/Storage/Volumes 회귀 검증"),
    (r"common/library/.*\.py$", "test",
     "공통 라이브러리 (precheck_bundle 등) 변경 → 4단계 진단 회귀"),

    # 어댑터
    (r"adapters/.*\.yml$", "test",
     "Adapter YAML 변경 → score-adapter-match 디버깅 + 해당 벤더 baseline"),
    (r"adapters/.*\.yml$", "doc",
     "docs/develop/03-adapter-system.md / .claude/ai-context/vendors/ 갱신 검토"),

    # 출력 schema
    (r"schema/sections\.yml$", "doc",
     "출력 섹션 정의 변경 → field_dictionary.yml + baseline_v1 동반 갱신 (rule 13)"),
    (r"schema/field_dictionary\.yml$", "doc",
     "필드 사전 변경 → baseline_v1 회귀 + sections.yml 정합 (rule 13)"),
    (r"schema/baseline_v1/.*\.json$", "test",
     "Baseline 변경 → 실장비 검증 후 evidence/ 갱신 (rule 40)"),
    (r"common/tasks/normalize/.*\.yml$", "test",
     "Fragment 정규화 변경 → fragment 침범 검증 (rule 22) + 3-channel 회귀"),
    (r"callback_plugins/json_only\.py$", "doc",
     "JSON envelope callback 변경 → 출력 스키마 호환성 + 호출자 통보"),

    # Jenkins
    (r"^Jenkinsfile($|_)", "doc",
     "Jenkins 파이프라인 변경 → docs/operate/04-pipeline-runtime.md / 4-Stage 검증 통과"),

    # Vault
    (r"^vault/", "doc",
     "Vault 변경 → 읽기 전용. 회전은 rotate-vault skill 사용"),

    # 테스트
    (r"tests/redfish-probe/.*\.py$", "test",
     "probe 변경 → 실장비 1대 이상에서 재실행 검증"),
    (r"tests/fixtures/.*\.json$", "doc",
     "Fixture 추가/변경 → baseline 회귀 영향 + tests/evidence/ 기록"),
    (r"tests/baseline_v1/.*\.json$", "test",
     "Baseline 회귀 기준선 변경 → 영향 벤더 전수 검증"),

    # 하네스
    (r"^\.claude/rules/", "doc",
     "rule 변경 → verify_harness_consistency.py 통과 + ADR 검토"),
    (r"^\.claude/skills/.*SKILL\.md$", "doc",
     "skill 변경 → description 1024자 + 트리거 정확성"),
    (r"^\.claude/agents/.*\.md$", "doc",
     "agent 변경 → 도구 권한 / model / description 검증"),

    # 전체 공통
    (r"\.(yml|yaml|py|md)$", "doc",
     "docs/ai/CURRENT_STATE.md 업데이트 권장"),
]


def generate_hints(file_path: str, repo_root: Path) -> dict:
    try:
        abs_path = Path(file_path).resolve()
        if abs_path.is_relative_to(repo_root):
            rel_path = str(abs_path.relative_to(repo_root)).replace("\\", "/")
        else:
            rel_path = file_path.replace("\\", "/")
    except (ValueError, TypeError):
        rel_path = file_path.replace("\\", "/")

    name = Path(file_path).stem
    parts = rel_path.split("/")
    module = parts[0] if len(parts) > 1 else "(root)"

    doc_hints, test_hints = [], []
    for pattern, hint_type, message in HINT_RULES:
        if re.search(pattern, rel_path):
            (doc_hints if hint_type == "doc" else test_hints).append(message)

    doc_hints = list(dict.fromkeys(doc_hints))
    test_hints = list(dict.fromkeys(test_hints))

    return {
        "file": file_path,
        "relative_path": rel_path,
        "module": module,
        "name": name,
        "doc_hints": doc_hints,
        "test_hints": test_hints,
        "total_hints": len(doc_hints) + len(test_hints),
    }


def _read_file_path_from_stdin() -> str | None:
    if sys.stdin.isatty():
        return None
    try:
        raw = sys.stdin.read()
        if not raw.strip():
            return None
        payload = json.loads(raw)
        return payload.get("tool_input", {}).get("file_path")
    except (json.JSONDecodeError, AttributeError):
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description="편집 후 힌트")
    parser.add_argument("file_path", nargs="?", default=None)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    args = parser.parse_args()

    file_path = args.file_path or _read_file_path_from_stdin()
    if not file_path:
        return 0

    repo_root = Path(args.repo_root).resolve()

    try:
        result = generate_hints(file_path, repo_root)
    except Exception as e:
        print(f"오류: {e}", file=sys.stderr)
        return 1

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        if result["total_hints"] == 0:
            return 0  # 조용히 종료
        print(f"'{result['name']}' 편집 후 힌트 ({result['total_hints']}건):")
        if result["doc_hints"]:
            print("\n  [문서]")
            for h in result["doc_hints"]:
                print(f"    - {h}")
        if result["test_hints"]:
            print("\n  [테스트]")
            for h in result["test_hints"]:
                print(f"    - {h}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
