# ADR-2026-05-11-field-channel-declaration-refinement

## 상태
Accepted (2026-05-11)

## 컨텍스트 (Why)

사용자 명시 (2026-05-11):
> "개더링을 할때 정말로 사용하는 json 값은 뭔지 분류하고 사용안하는건 빼는게 좋지않을까?? 예를들어 redfish 개더링부분에 메모리에 visible_mb, free_mb 부분은 다른 서버들을 모두 개더링해봐도 모두 null로 떨어져는데 이런것들을 분류해서 정리하면 안되나? redfish, os, esxi 모두."
>
> "정말 개더링을 못하는 값인지? 개더링할 수 있는데 서버에서 지원을안하는건지? 또는 코드가 잘못돼서 정말값이있는데, 못들고오는건지? 분류 및 검토가필요해 계획 세워줄래?"

### 발견된 패턴

`schema/field_dictionary.yml` 의 65 entries 중 일부 field 의 `channel:` 선언이 실제 baseline 실측과 불일치:

- `memory.visible_mb` channel `[redfish, os, esxi]` 선언 → Redfish 4 baseline (dell/hpe/lenovo/cisco) 모두 null
  - 원인: Redfish API spec `Memory.v1_*.json` 에 `VisibleMiB` 필드 자체 미정의
  - help_ko 에 "Redfish 채널에서는 null" 명시는 있으나 channel 선언이 거짓

- `memory.installed_mb` channel `[redfish, os, esxi]` 선언 → ESXi baseline null
  - 원인: ESXi `ansible_host_facts` 가 `ansible_memtotal_mb` 만 제공 (DIMM slot 정보 없음)

- `system.runtime` channel `[os]` 선언 → 3 OS baseline 모두 missing, ESXi baseline 만 present
  - DRIFT-B 패턴 (실측에서 channel 선언 누락)

### 호출자 시스템 영향

호출자 시스템 (Jenkins downstream / 모니터링 / 외부 통합) 이 `field_dictionary.yml` 의 `channel:` 배열을 lookup 으로 사용:
- channel 거짓 선언 시 — 호출자가 "Redfish 에서도 visible_mb 채워질 것" 가정 → 잘못된 null 처리 로직
- channel 누락 선언 시 — 호출자가 "ESXi 에서 system.runtime 안 채워짐" 가정 → 실제 채워지는데 무시

### 측정 부재

cycle 2026-05-11 이전에는 65 entries × 8 baseline = 520 cells 의 실제 사용 실태를 측정한 정본 부재. `schema/baseline_v1/*.json` 8 파일을 사람이 매번 grep 해서 확인 — TTL 부재 / 추정 vs 실측 구분 어려움 / 다음 작업자 재현 불가.

## 결정 (What)

### 1. FIELD_USAGE_MATRIX 측정 대상 신설 (rule 28 R1 #13)

- **`.claude/policy/measurement-targets.yaml`**: `field_usage_matrix` (id: 13) 등록
  - TTL: 14일
  - 무효화 trigger: `field_dictionary.yml` 변경 / `baseline_v1/*.json` 변경 / `adapters/*/*.yml` capabilities 변경
- **`.claude/rules/28-empirical-verification-lifecycle.md`** R1 표: 12종 → **13종**

### 2. 측정 스크립트 신설 — `scripts/ai/measure_field_usage_matrix.py`

- 입력: `field_dictionary.yml` + 8 baseline JSON + adapter capabilities
- 처리: field × baseline → 4 상태 (`present` / `null` / `empty` / `not_supported` / `missing`) + 분류 1/2/3 자동 도출 + drift 검출
- 출력: `docs/ai/catalogs/FIELD_USAGE_MATRIX.md` (자동 갱신 marker 사이)

### 3. 분류 3 분류 체계

| 분류 | 의미 | 조치 |
|---|---|---|
| 1 | 외부 시스템 spec 미제공 (모든 baseline null) | channel 배열 축소 |
| 2 | 일부 vendor / 환경 미지원 (일부 baseline null) | channel 유지 + help_ko 명시 |
| 3 | 외부 시스템 제공인데 코드 잘못 (한 baseline 만 null + spec 상 제공) | 즉시 fix + rule 95 R3 회귀 |

### 4. 본 cycle channel 정밀화 (분류 1 적용)

`schema/field_dictionary.yml` 3 entries:
- `memory.installed_mb`: `[redfish, os, esxi]` → `[redfish, os]`
- `memory.visible_mb`: `[redfish, os, esxi]` → `[os, esxi]` (사용자 핵심 사례 해소)
- `system.runtime`: `[os]` → `[esxi]` (DRIFT-B 해소)

### 5. add-new-vendor skill 단계 추가

`.claude/skills/add-new-vendor/SKILL.md` 절차 10단계 (기존 9 → 10):
- 단계 8 신설: 새 vendor baseline 추가 후 `measure_field_usage_matrix.py --update-md` 실행 → DRIFT 검출 / 분류 후보 식별

### 6. `docs/contract/03-fields.md` 동기화 (rule 13 R7)

- `docs/contract/03-fields.md` memory 절: installed_mb / visible_mb / free_mb 채널 변경 반영
- 섹션 8 (참조 표): `FIELD_USAGE_MATRIX.md` 신규 catalog 링크 추가

## 결과 (Impact)

### 정합성 검증

- **rule 13 R5 envelope shape 보존**: envelope 13 필드 변경 없음 [PASS]
- **rule 13 R7 `docs/contract/03-fields.md` 동기화**: 적용 [PASS]
- **rule 92 R2 Additive only**: channel 배열은 "거짓 선언 제거" + "누락 선언 추가" (시스템 안정성). schema/baseline_v1 변경 없음 [PASS]
- **rule 92 R5 schema 변경 사용자 승인**: ExitPlanMode 가 승인 시점 [PASS]
- **rule 70 R8 ADR 의무**: rule 28 R1 표 카운트 변경 (12 → 13) + rule 본문 의미 변경 [PASS — 본 ADR]

### 회귀 검증

- pytest: **621 PASS / 0 FAIL**
- `output_schema_drift_check`: PASS (sections=10 / field_dictionary=65 / section_prefixes=16)
- `envelope_change_check`: advisory 1건 (sensitivity false-positive — envelope shape 실제 변경 없음)
- `verify_harness_consistency`: PASS

### 매트릭스 결과 변화

- 분류 1 후보: 58 cells → **13 cells** (false-positive 45 제거 — algorithm 개선)
- 분류 2 후보: 14 cells (변경 없음)
- 분류 3? 후보: 1 cell (Dell OEM 한정 — 의도된 동작)
- Drift 검출: 12 entries → **8 entries** (3 channel 정밀화 적용 결과)

### 호출자 시스템 영향

- `memory.visible_mb` × Redfish: 호출자가 Redfish 응답에서 visible_mb 채워지길 기대 안 함 (channel 선언 정합) — **사용자 핵심 의문 해소**
- `memory.installed_mb` × ESXi: 동일
- `system.runtime` × ESXi: 호출자가 ESXi 응답에서 system.runtime 채워짐 기대 (channel 추가) — DRIFT-B 해소

### NEXT_ACTIONS 등재 (cycle field-channel-refinement-followup)

- F1: `meta.duration_ms × cisco_baseline` null 갱신 (실장비 재캡처)
- F2: `cpu.summary × rhel810_raw_fallback` 빌더 추가 (별도 cycle)
- F3: Supermicro baseline 확보 (cycle 정확도 향상)
- F4: 베어메탈 Windows / ESXi baseline 확보
- F5: OS channel system.runtime 구현 (현재 ESXi 만)

## 대안 비교 (Considered)

### 대안 A: envelope drop (선택 안 함)

> 항상 null 인 필드를 envelope 에서 아예 제거 (key 자체 부재).

- **장점**: envelope 크기 축소
- **단점**:
  - rule 96 R1-B 위반 — 호환성 cycle 외 envelope shape 변경
  - 호출자 시스템 파싱 변경 유발 (key 부재 vs null 구분 의무)
  - 거짓 가정 시 KeyError 발생 위험
- **결론**: 거절 (envelope shape 보존이 호출자 안정성 우선)

### 대안 B: 진단 리포트만 (선택 안 함)

> 매트릭스 문서만 생성, field_dictionary 변경 없음.

- **장점**: 변경 최소
- **단점**:
  - field_dictionary 의 `channel:` 선언 거짓 유지 → 호출자 잘못된 가정 지속
  - 다음 cycle 에서 다시 같은 발견 / 결정 반복
- **결론**: 거절 (cycle 가치 약함)

### 대안 C: channel filtering 정밀화 + 진단 리포트 (선택)

> 매트릭스 + field_dictionary channel 정밀화.

- **장점**:
  - envelope shape 보존 (rule 13 R5)
  - field_dictionary 정합성 회복
  - 향후 cycle 의 reference 자료 (FIELD_USAGE_MATRIX.md)
  - 신규 vendor 추가 시 분류 검증 의무화 (add-new-vendor skill)
- **단점**: ADR 의무 (rule 70 R8) 발생 — 본 ADR 작성으로 충족
- **결론**: 채택

## 관련

- rule: `13-output-schema-fields` R5/R7 / `28-empirical-verification-lifecycle` R1 #13 / `70-docs-and-evidence-policy` R8 / `92-dependency-and-regression-gate` R2/R5 / `96-external-contract-integrity` R1-B
- script: `scripts/ai/measure_field_usage_matrix.py`
- catalog: `docs/ai/catalogs/FIELD_USAGE_MATRIX.md`
- skill: `add-new-vendor` (단계 10)
- plan: `~/.claude/plans/tranquil-wandering-lampson.md`
