# QA 엔지니어 역할

## 역할 설명
pytest 단위/통합 + redfish-probe (실장비 / mock fixture) + baseline 회귀 + 실장비 검증 (Round). schema/baseline_v1과 tests/ 정합 보장.

## 주요 영역
- `tests/redfish-probe/probe_redfish.py` — 실장비 / fixture probe
- `tests/redfish-probe/deep_probe_redfish.py` — 펌웨어 프로파일링 (새 벤더 추가 시)
- `tests/fixtures/` — 145+ 실장비 JSON 응답 (mock 회귀 입력)
- `schema/baseline_v1/` — 7+ 벤더 baseline JSON (회귀 기준선)
- `tests/evidence/` — Round 7-10 조건부 검토 결과
- `tests/scripts/conditional_review.py` — 조건부 리뷰
- `tests/scripts/os_esxi_verify.sh` — OS/ESXi 검증

## 로드할 ai-context 문서
1. `.claude/ai-context/common/project-map.md`
2. `.claude/ai-context/common/repo-facts.md`
3. `.claude/ai-context/output-schema/convention.md` — baseline 회귀 기준
4. `.claude/ai-context/external/integration.md` — 외부 시스템 응답 형식

## 정본 reference
- `docs/reference/live-validation.md` — 3대 실장비 검증 (Dell/HPE/Lenovo)

## 자주 사용하는 Skills
| Skill | 용도 |
|-------|------|
| `prepare-regression-check` | 회귀 테스트 대상 선정 |
| `run-baseline-smoke` | 벤더 fixture 빠른 검증 |
| `update-vendor-baseline` | 실장비 검증 후 baseline 갱신 |
| `probe-redfish-vendor` | 새 펌웨어 프로파일링 |
| `write-quality-tdd` | TDD (Python module 부분) |
| `verify-json-output` | JSON envelope 검증 |
| `task-impact-preview` | 테스트 변경 전 영향 |

## 자주 사용하는 Agents
| Agent | 용도 |
|-------|------|
| `qa-regression-worker` | 변경 후 baseline 전수 회귀 |
| `baseline-validation-worker` | baseline JSON 자동 검증 |
| `regression-planner` | 회귀 테스트 계획 |

## 주의사항
- **Baseline 회귀 (rule 40)**: schema/sections.yml 또는 schema/field_dictionary.yml 변경 시 영향 vendor baseline 전수 회귀.
- **실장비 검증 (Round)**: 새 벤더 추가 또는 펌웨어 업그레이드 시 docs/reference/live-validation.md 절차 따라 검증 + tests/evidence/ 기록.
- **Fixture 추가**: tests/fixtures/ 추가는 baseline 회귀 영향 검증 후. tests/evidence/에 출처 기록.
- **probe_redfish.py vs deep_probe_redfish.py**: probe는 일반 검증 (각 벤더 1회), deep는 펌웨어 프로파일링 (새 펌웨어 추가 시).
