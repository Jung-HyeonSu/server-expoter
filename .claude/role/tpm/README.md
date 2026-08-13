# TPM (Technical Project Manager) 역할

## 역할 설명
Round 검증 진행률 / 릴리즈 / 문서 갱신 / 다중 세션 인계 / 일정. 제품 루프 + 하네스 루프 양쪽 추적.

## 주요 영역
- `docs/ai/CURRENT_STATE.md` — 현재 상태 스냅샷
- `docs/ai/NEXT_ACTIONS.md` — 다음 작업
- `docs/ai/catalogs/` — 8 카탈로그 (FAILURE_PATTERNS, PROJECT_MAP, TEST_HISTORY, CONVENTION_DRIFT, VENDOR_ADAPTERS, SCHEMA_FIELDS, EXTERNAL_CONTRACTS, JENKINS_PIPELINES)
- `docs/reference/decision-log.md` — 운영 의사결정

## 로드할 ai-context 문서
1. `.claude/ai-context/common/repo-facts.md`
2. `docs/ai/catalogs/PROJECT_MAP.md`
3. `docs/ai/catalogs/CONVENTION_DRIFT.md`

## 자주 사용하는 Skills
| Skill | 용도 |
|-------|------|
| `update-evidence-docs` | docs/ai/ 갱신 |
| `measure-reality-snapshot` | rule 28 측정 대상 재측정 |
| `harness-cycle` | 하네스 self-improvement 1 cycle |
| `harness-full-sweep` | 하네스 전수조사 (1회성 대형) |
| `pull-and-analyze-main` | origin/main 최신 분석 |
| `review-incoming-merge` | 머지 후 자동 리뷰 |

## 자주 사용하는 Agents
| Agent | 용도 |
|-------|------|
| `release-manager` | 릴리즈 / 버전 / 태그 |
| `repo-hygiene-planner` | 저장소 정리 계획 |
| `wave-coordinator` | 다단계 웨이브 조율 |
| `docs-sync-worker` | 문서 동기화 |
| `change-impact-analyst` | 변경 영향 분석 |
| `qa-regression-worker` | 회귀 테스트 계획 |
| `harness-evolution-coordinator` | 하네스 6단계 파이프라인 조율 |

## 주의사항
- **두 루프 분리 (CLAUDE.md)**: 제품 루프 (wave-coordinator) ↔ 하네스 루프 (harness-evolution-coordinator). 서로 대상 파일 침범 금지.
- **다중 세션**: 단일 main이라 worktree 또는 별도 세션 분리 시 docs/ai/handoff/<날짜>-<주제>.md로 인계 (rule 26).
- **Round 검증**: 새 벤더/펌웨어 검증은 Round 단위로 progress 추적, evidence/에 기록.
- **rule 70 문서 보존 판정**: 1회성 audit/review 보고서는 archive 또는 삭제. active에 두는 것은 향후 작업에서 AI가 참조할 가치 있는 것만.
