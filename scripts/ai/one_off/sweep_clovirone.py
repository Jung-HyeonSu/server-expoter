"""One-off: 2026-04-28 full-sweep — clovirone 매핑 표현 일괄 제거."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]

# (path_relative, old, new)
EDITS = [
    (".claude/skills/plan-schema-change/SKILL.md",
     "description: 새 섹션 / 새 필드 / Must↔Nice 재분류 / baseline 일괄 갱신 등 schema 변경 계획 (clovirone plan-db-change 등가). ",
     "description: 새 섹션 / 새 필드 / Must↔Nice 재분류 / baseline 일괄 갱신 등 schema 변경 계획. "),
    (".claude/skills/plan-schema-change/SKILL.md",
     "server-exporter 출력 schema 변경 계획. clovirone DB 스키마 (Flyway) 변경에 대응 — server-exporter는 `schema/sections.yml + schema/field_dictionary.yml + baseline_v1/`.",
     "server-exporter 출력 schema 변경 계획. 정본 = `schema/sections.yml + schema/field_dictionary.yml + baseline_v1/`. (server-exporter는 DB 없음 — 출력 schema가 동등 역할)"),
    (".claude/skills/review-adapter-change/SKILL.md",
     "description: adapters/{redfish,os,esxi}/*.yml 변경을 DBA 관점 (clovirone의 review-sql-change 등가)으로 리뷰. 점수 일관성 / metadata 주석 / OEM 분기 / 영향 vendor. ",
     "description: adapters/{redfish,os,esxi}/*.yml 변경을 점수 / metadata / OEM 분기 / 영향 vendor 4축으로 리뷰. "),
    (".claude/skills/review-adapter-change/SKILL.md",
     "adapter YAML 변경 전문 리뷰. clovirone DBA가 SQL/MyBatis/Flyway 리뷰하던 자리에 server-exporter는 adapter (vendor 분기 메타).",
     "adapter YAML 변경 전문 리뷰. server-exporter의 adapter는 vendor 분기 메타 정본 (점수 / capabilities / collect / normalize 4 키)."),
    (".claude/skills/investigate-ci-failure/SKILL.md",
     "server-exporter Jenkins 4-Stage 실패 분석. clovirone Bitbucket Pipelines와 달리 Jenkins multi-pipeline (3종).",
     "server-exporter Jenkins 4-Stage 실패 분석. Jenkins multi-pipeline 3종 (Jenkinsfile / Jenkinsfile_grafana / Jenkinsfile_portal) 단독 사용."),
    (".claude/skills/classify-precheck-layer/SKILL.md",
     "description: 새 검증을 어느 layer (Jenkins Stage 1 / precheck 1-4 / Stage 3 / adapter capabilities)에 배치할지 분류 (rule 27 R5). clovirone classify-validation-layer의 server-exporter 등가물. ",
     "description: 새 검증을 어느 layer (Jenkins Stage 1 / precheck 1-4 / Stage 3 / adapter capabilities)에 배치할지 분류 (rule 27 R5). "),
    (".claude/skills/classify-precheck-layer/SKILL.md",
     '사용자가 "프론트에서 막아도 돼?" 같은 질의 (server-exporter는 호출자/Stage1)',
     '"어느 단계에서 막을까?" 같은 질의 (server-exporter는 호출자/Stage1)'),
    (".claude/skills/vendor-change-impact/SKILL.md",
     "description: 코드 변경이 server-exporter의 5 vendor (Dell / HPE / Lenovo / Supermicro / Cisco)에 미치는 영향 분석. clovirone customer-change-impact의 server-exporter 등가물. ",
     "description: 코드 변경이 server-exporter의 5 vendor (Dell / HPE / Lenovo / Supermicro / Cisco)에 미치는 영향 분석. "),
    (".claude/skills/handoff-driven-implementation/SKILL.md",
     "세션 간 작업 인계받기. clovirone에서는 prototype 기반이었으나 server-exporter는 prototype 없음 → 티켓 + 명세 + ai-context 기반.",
     "세션 간 작업 인계받기. server-exporter는 prototype 없음 → 티켓 + 명세 + ai-context 기반 인계."),
    (".claude/skills/plan-feature-change/SKILL.md",
     "server-exporter 기능 변경 구현 계획. clovirone API (Spring REST) 대신 server-exporter는 callback 호출 + Jenkinsfile + 3-channel + adapter.",
     "server-exporter 기능 변경 구현 계획. server-exporter API surface = callback 호출 + Jenkinsfile + 3-channel + adapter."),
    (".claude/skills/pr-review-playbook/SKILL.md",
     "description: PR 생성 전 server-exporter 최종 체크리스트 (clovirone bitbucket-pr-review-playbook의 server-exporter 등가). ",
     "description: PR 생성 전 server-exporter 최종 체크리스트. "),
    (".claude/skills/pull-and-analyze-main/SKILL.md",
     "description: origin/main 최신 변경을 fetch하여 자동 분석 (clovirone pull-and-analyze-dev의 단일 main 단순화). ",
     "description: origin/main 최신 변경을 fetch하여 자동 분석. "),
    (".claude/skills/pull-and-analyze-main/SKILL.md",
     "server-exporter는 단일 main + feature/* 운영. clovirone 3계층 (배포 / dev / personal)에 비해 단순. main 최신 동기화 시 변경 분석.",
     "server-exporter는 단일 main + feature/* 운영 (단순 브랜치 정책). main 최신 동기화 시 변경 분석."),
    (".claude/skills/run-baseline-smoke/SKILL.md",
     "description: vendor fixture 기반 빠른 baseline 회귀 (clovirone run-ui-smoke 등가). ",
     "description: vendor fixture 기반 빠른 baseline 회귀. "),
    (".claude/skills/run-baseline-smoke/SKILL.md",
     "server-exporter baseline 회귀를 빠르게 (실장비 없이 fixture만) 실행. clovirone run-ui-smoke (5개 화면 시나리오)에 대응 — server-exporter는 5 vendor x 1 fixture.",
     "server-exporter baseline 회귀를 빠르게 (실장비 없이 fixture만) 실행. 5 vendor x 1 fixture 단위 smoke."),
    (".claude/skills/verify-adapter-boundary/SKILL.md",
     "description: common / 3-channel 코드에 vendor 이름 하드코딩 검출 (rule 12 R1). clovirone verify-plugin-boundary의 server-exporter 등가물. ",
     "description: common / 3-channel 코드에 vendor 이름 하드코딩 검출 (rule 12 R1). "),
    (".claude/skills/verify-json-output/SKILL.md",
     "description: callback_plugins/json_only.py가 출력하는 JSON envelope 6 필드 (status / sections / data / errors / meta / diagnosis) 정합 검증. UI 변경 (clovirone의 verify-ui-rendering)에 대응 — server-exporter는 UI 없음. ",
     "description: callback_plugins/json_only.py가 출력하는 JSON envelope 13 필드 정합 검증. server-exporter는 UI 없음 -> 호출자 시스템은 stdout JSON 파싱. "),
    (".claude/skills/verify-json-output/SKILL.md",
     "server-exporter 출력 envelope의 호출자 호환성 검증. clovirone verify-ui-rendering의 server-exporter 등가물 — UI 대신 JSON envelope.",
     "server-exporter 출력 envelope의 호출자 호환성 검증. UI 없음 — JSON envelope이 호출자 계약면."),
    # agents
    (".claude/agents/adapter-boundary-reviewer.md",
     "description: adapter YAML 경계 리뷰 — priority 일관성, metadata origin 주석, OEM tasks 분리. clovirone plugin-boundary-reviewer 등가. ",
     "description: adapter YAML 경계 리뷰 — priority 일관성, metadata origin 주석, OEM tasks 분리. "),
    (".claude/agents/adapter-boundary-reviewer.md",
     "리뷰어 (clovirone plugin-boundary-reviewer -> server-exporter adapter)",
     "리뷰어 (server-exporter adapter 경계 검증)"),
    (".claude/agents/adapter-boundary-reviewer.md",
     "리뷰어 (clovirone plugin-boundary-reviewer → server-exporter adapter)",
     "리뷰어 (server-exporter adapter 경계 검증)"),
    (".claude/agents/ansible-perf-investigator.md",
     "description: ansible-playbook 작업 시간 분석 / 병목 식별. clovirone query-tuning-investigator → server-exporter ansible. ",
     "description: ansible-playbook 작업 시간 분석 / 병목 식별. "),
    (".claude/agents/qa-regression-worker.md",
     "description: schema/baseline_v1/ 갱신 / 회귀 검증 자동화. clovirone chrome-ui-e2e-worker → server-exporter는 UI 없으므로 baseline 회귀로 등가. ",
     "description: schema/baseline_v1/ 갱신 / 회귀 검증 자동화. server-exporter는 UI 없음 -> baseline 회귀로 동등 역할. "),
    (".claude/agents/build-verifier.md",
     "server-exporter 정적 검증 (clovirone Gradle build → server-exporter ansible/pytest).",
     "server-exporter 정적 검증 (ansible-playbook --syntax-check + pytest + verify_*.py)."),
    (".claude/agents/ci-failure-investigator.md",
     "server-exporter Jenkins 4-Stage 실패 분석. clovirone Bitbucket Pipeline → Jenkins multi-pipeline.",
     "server-exporter Jenkins 4-Stage 실패 분석. Jenkins multi-pipeline 3종 단독 사용."),
    (".claude/agents/refactor-worker.md",
     "도메인 워커 (clovirone backend-refactor-worker → server-exporter gather)",
     "도메인 워커 (server-exporter gather refactor)"),
    (".claude/agents/refactor-worker.md",
     "도메인 워커 (clovirone scheduler-refactor-worker → server-exporter Jenkins)",
     "도메인 워커 (server-exporter Jenkinsfile refactor)"),
    (".claude/agents/refactor-worker.md",
     "도메인 워커 (clovirone frontend-refactor-worker → server-exporter output-schema)",
     "도메인 워커 (server-exporter output-schema refactor)"),
    (".claude/agents/schema-reviewer.md",
     "description: callback_plugins/json_only.py + build_*.yml 빌더 + envelope 형식 리뷰. clovirone frontend-ftl-vue-reviewer 등가. ",
     "description: callback_plugins/json_only.py + build_*.yml 빌더 + envelope 형식 리뷰. "),
    (".claude/agents/schema-reviewer.md",
     "리뷰어 (clovirone frontend-ftl-vue → server-exporter output)",
     "리뷰어 (server-exporter output envelope 검증)"),
    (".claude/agents/qa-regression-worker.md",
     "도메인 워커 (clovirone qa-regression-worker → server-exporter pytest)",
     "도메인 워커 (server-exporter pytest + baseline 회귀)"),
    (".claude/agents/schema-reviewer.md",
     "description: sections.yml ↔ field_dictionary.yml ↔ baseline_v1 정합 리뷰. clovirone mybatis-reviewer 등가. ",
     "description: sections.yml ↔ field_dictionary.yml ↔ baseline_v1 정합 리뷰. "),
    (".claude/agents/schema-reviewer.md",
     "리뷰어 (clovirone mybatis-reviewer → server-exporter schema)",
     "리뷰어 (server-exporter schema 매핑 검증)"),
    (".claude/agents/schema-migration-worker.md",
     "description: 새 섹션 / 새 필드 / Must↔Nice 재분류 마이그레이션. clovirone migration-worker (Flyway) → server-exporter schema. ",
     "description: 새 섹션 / 새 필드 / Must↔Nice 재분류 마이그레이션. "),
    (".claude/agents/schema-reviewer.md",
     "description: schema YAML 구조 리뷰 — Must/Nice/Skip 분류 적절성, 새 섹션 의도, 필드명 일관성. clovirone dba-reviewer 등가. ",
     "description: schema YAML 구조 리뷰 — Must/Nice/Skip 분류 적절성, 새 섹션 의도, 필드명 일관성. "),
    (".claude/agents/schema-reviewer.md",
     "리뷰어 (clovirone dba-reviewer → server-exporter schema)",
     "리뷰어 (server-exporter schema YAML 구조 검증)"),
    (".claude/agents/vendor-boundary-guardian.md",
     "description: gather / common 코드에 vendor 이름 (Dell/HPE/Lenovo/Supermicro/Cisco) 하드코딩 검출. clovirone customer-boundary-guardian 등가. ",
     "description: gather / common 코드에 vendor 이름 (Dell/HPE/Lenovo/Supermicro/Cisco) 하드코딩 검출. "),
    (".claude/agents/vendor-boundary-guardian.md",
     "리뷰어 (clovirone customer-boundary-guardian → server-exporter vendor)",
     "리뷰어 (server-exporter vendor 경계 가드)"),
]


def main():
    applied = 0
    miss = []
    for rel, old, new in EDITS:
        p = ROOT / rel
        if not p.exists():
            miss.append(f"missing: {rel}")
            continue
        txt = p.read_text(encoding="utf-8")
        if old in txt:
            p.write_text(txt.replace(old, new, 1), encoding="utf-8")
            applied += 1
        else:
            miss.append(f"no match: {rel}")
    print(f"applied: {applied} / {len(EDITS)}")
    for m in miss:
        print("  -", m)


if __name__ == "__main__":
    main()
