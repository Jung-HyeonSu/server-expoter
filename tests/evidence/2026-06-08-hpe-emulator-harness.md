# HPE iLO 에뮬레이터 오프라인 회귀 하네스 — 검증 증거

- **일자**: 2026-06-08
- **작업자**: AI (Claude Code) — 사용자 승인 plan 기반
- **요청 (사용자)**: HPE 공식 iLO Redfish 에뮬레이터를 "웹 소스 MOCK 보다 한 단계 위인
  고품질 테스트 타깃" 으로 도입해 프로젝트를 더 견고하게.
- **branch**: `main`

## 무엇을 했나 (WHAT)

HPE 공식 iLO Redfish Interface Emulator (BSD-3-Clause, v1.7.0) 를 이 PC 의 Docker 로
띄워 `redfish_gather.py` gather 흐름을 1 회 구동, 모든 GET 요청/응답을 record 하고
모듈 산출을 golden 으로 snapshot. 이후 **에뮬레이터 없이 오프라인**으로 record 를
재생해 파싱/정규화 엔진을 결정적으로 회귀 검증하는 하네스를 추가.

## 왜 (WHY)

lab 부재 — 실측 HPE 장비 1 대뿐 (DL380 Gen11, iLO6 v1.73). iLO5(Gen10 Plus)·Gen12·
HBA/FC 스토리지 경로는 실장비 검증 0. 에뮬레이터로 이 코드 경로들에 오프라인 회귀
안전망을 걸어 코드 회귀를 자동 검출.

## 정직한 경계 (rule 21 R1 / rule 25 R7-B)

- **에뮬레이터 != 실장비.** 본 산출물(fixture/golden)은 `schema/baseline_v1/` 실측
  baseline 으로 **승격하지 않는다.** 전부 `tests/fixtures/redfish/hpe_emulator_*` 아래
  "emulator-derived" 라벨.
- 에뮬레이터는 **CSUS 3200 / Superdome Flex mockup 부재** → 그 갭은 못 메움
  (LAB_PENDING_MATRIX 의 실장비 PENDING 유지).

## 캡처 결과 (5 BMC type — 모두 vendor=hpe / status=success / 9 섹션)

| fixture | mockup | 세대 | manager_fw | recording paths |
|---|---|---|---|---|
| `hpe_emulator_dl360` | DL360 | iLO5 | iLO 5 v3.11 | 94 |
| `hpe_emulator_dl365_gen10plus` | DL365_Gen10Plus | iLO5 (HBA) | iLO 5 v3.14 | 97 |
| `hpe_emulator_dl325_gen10plus_fc` | DL325_Gen10Plus_FC | iLO5 (FC HBA) | iLO 5 v2.46 | 71 |
| `hpe_emulator_dl380a` | DL380a | iLO6 (Gen11) | iLO 6 v1.66 | 106 |
| `hpe_emulator_dl380a_gen12` | DL380a_Gen12 | Gen12 | 1.13.01 (iLO7) | 147 |

각 디렉터리: `recording.json`(replay 입력) + `expected_output.json`(golden) + `README.md`(출처).

### 제외: DL360_Gen12

에뮬레이터 **자체 버그** — `api_emulator/loader.py:740 randomize()` 에서 WWN
`KeyError: '1'` 로 startup crash (DL360_Gen12 mockup 한정). 우리 코드 무관. 캡처 제외.

## 검증 ([OK] 확인층)

- [OK] **에뮬레이터 기동 확인**: `curl -k https://127.0.0.1:443/redfish/v1/` →
  `Vendor: HPE`, `Oem keys: ['Hpe']`, Systems/Managers 링크 노출.
- [OK] **골든 품질**: DL380a 산출 — `processors[0].model = INTEL(R) XEON(R) GOLD 6530`,
  `memory.slots` RDIMM 32768MB ECC, `storage.controllers`+`volumes`, `bmc.firmware_version
  = iLO 6 v1.66`, `probe_facts {firmware_hint:1.66, manager_type:iLO 6}`.
- [OK] **오프라인 보장**: 에뮬레이터 컨테이너 중지(`docker rm -f`) 후
  `pytest tests/integration/test_hpe_emulator_replay.py` → **26 passed, 1 skipped**
  (live 스모크는 SE_EMULATOR_LIVE 미설정으로 skip). 네트워크 호출 0.
- [OK] **전체 회귀 무영향**: `pytest tests/ --ignore=tests/e2e_browser` →
  **797 passed, 1 skipped** (10.3s). 기존 771 → +26 신규.
- [OK] **py_compile**: 신규 4 파일 (emulator_harness/capture_emulator/test_hpe_emulator_replay/conftest) PASS.

## 산출물

- 하네스: `tests/integration/emulator_harness.py` (record/replay + main() gather 미러)
- 캡처: `tests/integration/capture_emulator.py` (재생성 entrypoint)
- 테스트: `tests/integration/test_hpe_emulator_replay.py` (golden + 의미 invariant + live 스모크)
- conftest: `tests/integration/conftest.py` (integration/live 마커 등록)
- fixture: `tests/fixtures/redfish/hpe_emulator_*/` (5 type × recording+golden+README)

## 회귀 메커니즘

`redfish_gather.py` 파싱이 바뀌면 `test_golden_match` 가 어떤 필드가 어떻게 변했는지
드러냄. 의도된 변경 시 에뮬레이터 재기동 후
`python tests/integration/capture_emulator.py --mockup <X> --captured <YYYY-MM-DD>` 로
golden 재생성.

## 견고화 라운드 (2026-06-08, 멀티에이전트 재검토 후)

사용자 요청으로 본 작업 전체를 37-에이전트 5차원 적대적 워크플로(하네스 충실도 / 테스트
견고성 / 규칙·문서 정합 / 주장 실측 / 견고화)로 재검증. **모든 주장(797 pass, 오프라인,
결정성, 프로덕션 코드 무변경, rule 21 준수)은 적대적 재현으로 전부 사실 확인.** 확정된
견고화/정합 갭을 다음과 같이 보강 (전부 tests/ + 문서, 프로덕션 코드 무변경):

- **hermetic 가드 (conftest autouse)**: 비-live 테스트 중 `rg.urlreq.urlopen` 을 raise 로
  차단 → "오프라인 / 네트워크 0" 불변식을 convention → enforced assertion 으로 격상.
  `_probe_realm_hint` 등 replay seam 우회 직접 urlopen 경로가 미래에 활성화되면 즉시 검출.
  가드 자체 회귀 방지 메타테스트(`test_hermetic_guard_is_active`) 추가.
- **error_count golden 편입**: `GOLDEN_KEYS` 에 `error_count` 추가 + 5 golden 에 실측값 0
  기입 → "에러 0건이 silent 하게 늘어나는" 회귀 탐지.
- **타깃 의미 assertion 보강**: memory.total_mib>0 / firmware 비어있지 않음 /
  bmc.firmware_version 추출 / FC HBA(WWPN) — FC fixture(dl325_fc + dl365) 이름 keyed
  (golden-laundering 방어). 검증자 교정 반영('iLO' 부분문자열 금지 — Gen12 미포함, FC 는 2 fixture).
- **EOL 결정화**: `.gitattributes`(`tests/fixtures/**/*.json text eol=lf`) + capture writer
  `newline="\n"` → 기여자 autocrlf 무관 golden 재생성 diff 노이즈 차단.
- **stale 수치 정정 (rule 28/70)**: CLAUDE.md / rule 00 / PROJECT_MAP 의 fixtures 380→395
  (실장비 380 + 에뮬레이터 15, rule 25 R7-B 라벨), test 48파일/445→49파일/462. PROJECT_MAP
  fingerprint `--update`.

### 견고화 후 검증 ([OK] 확인층)
- [OK] `pytest tests/integration/` → **44 passed / 4 skipped** (live 1 + FC-skip 3). 가드 self-test 통과.
- [OK] 전체 `pytest tests/ --ignore=tests/e2e_browser` → **815 passed / 4 skipped** (10.5s). 무회귀.
- [OK] py_compile 4 파일 / git add --renormalize / fingerprint drift 0.

### 검토에서 의도적으로 보류한 항목 (검증자 판정)
- **Jenkins CI 편입** (medium): Jenkinsfile 은 보호 경로(rule 80, CLAUDE.md 절대금지 #2) →
  자율 편집 금지. 사용자 승인 후 진행 (NEXT_ACTIONS 등재).
- **CURRENT_STATE/evidence [OK] 이모지** (uncertain): 전역 verification.md 가 [OK]/[WARN]/[NG] 3상태를
  강제하고 CURRENT_STATE 가 이미 [OK] 컨벤션 → 부분 치환은 파일 내부 일관성 악화. 거버넌스
  결정(ADR) 전까지 현 상태 유지.
- **main() list(set()) → sorted()** (info): 프로덕션 cosmetic 변경 + 게이트 유발 → 보류.

## 후속 (실장비 — 여전히 PENDING)

에뮬레이터는 실장비 검증을 대체 못함. iLO5/iLO6/Gen12 실장비 캡처 + baseline 은
`LAB_PENDING_MATRIX.md` 에서 계속 PENDING. lab 도입 시 7 단계 절차 유효.
