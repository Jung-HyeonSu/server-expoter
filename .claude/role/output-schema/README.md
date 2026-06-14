# Output-Schema 엔지니어 역할

## 역할 설명
3-channel JSON 출력 스키마 관리. `sections.yml` (11 섹션) + `field_dictionary.yml` (42 Must + 74 Nice + 6 Skip = 122 entries) + `baseline_v1/` (벤더별 회귀 기준선) + `callback_plugins/json_only.py` (출력 envelope) 일관성 보장. fragment 정규화 → 표준 JSON 조립 파이프라인 (build_*.yml 5종).

## 주요 영역
- `schema/sections.yml` — 11 섹션 정의 (system, hardware, bmc, cpu, memory, storage, network, firmware, users, power, thermal)
- `schema/field_dictionary.yml` — 필드 사전 (Must 42 + Nice 74 + Skip 6 = 122 entries)
- `schema/fields/` — 섹션별 상세 필드
- `schema/baseline_v1/` — 벤더별 baseline JSON (실장비 회귀 기준선)
- `schema/examples/` — success/partial/failed 예시
- `common/tasks/normalize/` — Fragment 정규화 (init_fragments / merge_fragment / build_sections / build_status / build_errors / build_meta / build_correlation / build_output)
- `callback_plugins/json_only.py` — stdout callback (OUTPUT 태스크만 JSON 직렬화)

## 로드할 ai-context 문서
1. `.claude/ai-context/output-schema/convention.md` — schema 매핑 / build_*.yml 빌더 / JSON envelope
2. `.claude/ai-context/gather/convention.md` — 입력 fragment 형식 (gather 산출물)
3. `.claude/ai-context/common/project-map.md`
4. `.claude/ai-context/common/coding-glossary-ko.md` — sections / fields / baseline 용어

## 정본 reference
- `docs/07_normalize-flow.md` — 정규화 흐름
- `docs/09_output-examples.md` — 표준 JSON 출력 예시
- `docs/12_diagnosis-output.md` — diagnosis 구조
- `docs/16_os-esxi-mapping.md` — OS/ESXi 필드 매핑

## 자주 사용하는 Skills
| Skill | 용도 |
|-------|------|
| `task-impact-preview` | schema 변경 전 영향 미리보기 |
| `update-output-schema-evidence` | sections + field_dictionary + baseline 정합 갱신 |
| `verify-json-output` | callback_plugins/json_only.py 출력 envelope 검증 |
| `update-vendor-baseline` | 실장비 검증 후 baseline JSON 갱신 |
| `plan-schema-change` | 새 섹션/필드 추가 계획 |
| `prepare-regression-check` | baseline 전수 회귀 테스트 |
| `review-existing-code` | 4축 리뷰 |

## 자주 사용하는 Agents
| Agent | 용도 |
|-------|------|
| `output-schema-refactor-worker` | sections / field_dictionary / build_*.yml 리팩토링 |
| `schema-mapping-reviewer` | sections ↔ field_dictionary ↔ baseline 정합 |
| `output-schema-reviewer` | callback envelope / build_*.yml 빌더 리뷰 |
| `schema-reviewer` | YAML schema 구조 리뷰 |
| `schema-migration-worker` | 새 섹션 / 필드 마이그레이션 |
| `baseline-validation-worker` | baseline 회귀 자동 검증 |
| `naming-consistency-reviewer` | 필드명 일관성 (camelCase / snake_case) |

## 주의사항 (Critical)
- **schema 변경은 3종 동반 (rule 13)**: `sections.yml` + `field_dictionary.yml` + `tests/baseline_v1/{vendor}_baseline.json` 동시 갱신. 한쪽만 수정 금지.
- **Field Dictionary 39 Must**: Must 필드는 모든 vendor baseline에 존재해야 함. Nice는 vendor-specific 허용. Skip은 의도적 미수집. (실측 2026-06-14 = 42 Must / 74 Nice / 6 Skip = 122 entries)
- **JSON envelope (rule 20)**: `{status, sections, data, errors, meta, diagnosis}` 6 필드. callback_plugins/json_only.py가 OUTPUT 태스크에만 JSON 직렬화.
- **build_*.yml 빌더 5종 (common/tasks/normalize/)**: build_sections / build_status / build_errors / build_meta / build_correlation / build_output. 각 빌더가 fragment 변수를 어떻게 누적하는지 일관 패턴.
- **baseline 회귀**: schema 변경 PR은 영향 vendor 전수 회귀 검증 결과를 docs/ai/incoming-review/ 또는 evidence/에 첨부.
