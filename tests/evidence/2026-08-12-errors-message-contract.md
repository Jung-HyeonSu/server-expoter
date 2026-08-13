# errors[].message 계약 개선 — 변경·검증 기록 (2026-08-12)

- 대상 브랜치: `main`
- 입력 문서: 에러 메시지 전수조사(정리됨) (조사 전용, 코드 변경 0)
- 성격: 조사 결과를 **현재 코드로 재검증**한 뒤 실제 수정 + 계약 테스트 신설
- 실장비 검증: **하지 않음** (아래 §5 참조)

---

## 1. 최종 Message 구조 (확정)

| 계층 | 무엇 | 어디에 저장 | 정본 |
|---|---|---|---|
| A. 전체 실패 | `status=failed` 대표 사유 | `diagnosis.failure_reason` == `errors[0].message` | `common/vars/failure_reasons.yml` (6문장) |
| B. 섹션 부분 실패 | `status=partial` / `success` 의 섹션 오류 | `errors[N].message` (섹션 의미 유지) | `common/vars/section_messages.yml` + 각 채널 태스크 |
| C. 기술 Evidence | 포트 / HTTP status / URI / 예외 / rc / stderr / 태스크명 | `errors[N].detail` (string \| null) | 생성 지점 |
| D. 성공한 fallback | SimpleStorage·SmartStorage fallback 성공, realm vendor 식별 성공, 절단 사실 | `diagnosis.details.notices` — **errors 아님** | `redfish_gather.notices()` |
| E. Unsupported | 미지원 optional 기능 | `sections.<name> = not_supported` — errors 없음 | 기존 경로 |

### A 계층: failure_code → 문장 (단일 매핑)

문장은 **관측된 `failure_code` 에서만** 파생된다 (`precheck_bundle.REASON_BY_FAILURE_CODE`).
종전에는 문장과 stage/code 가 서로 다른 조건으로 갈려 같은 결과를 Portal 과 대시보드가 다르게 해석했다.

| failure_code | 문장 |
|---|---|
| `DNS_RESOLUTION_FAILED` / `TCP_CONNECT_FAILED` | 대상 IP에서 응답을 확인할 수 없습니다. IP 사용 여부와 네트워크 상태를 확인하세요. |
| `TCP_CONNECTION_REFUSED` | 대상 IP의 관리 포트에 연결할 수 없습니다. 방화벽과 관리 서비스 상태를 확인하세요. |
| `PROTOCOL_CHECK_FAILED` | 관리 포트에는 연결됐지만 서버 정보 수집에 필요한 응답을 확인할 수 없습니다. 관리 서비스 설정과 상태를 확인하세요. |
| `AUTH_PROBE_FAILED` | 대상에 접속할 수 없습니다. 자격증명과 계정 권한을 확인하세요. |
| `GATHER_FAILED` | 대상 접속은 확인됐지만 정보 수집에 실패했습니다. 대상 상태와 수집 로그를 확인하세요. |
| `OUTPUT_BUILD_FAILED` | 수집 결과를 생성하지 못했습니다. 실행 로그를 확인하세요. |

---

## 2. P0 항목별 결과

### P0-1 / C1 / C4 — Redfish rescue 4필드 자기모순

- **문제**: 같은 `set_fact` 안에서 `failure_stage` / `failure_code` / `auth_success` 는
  `(rejected and not collected)` 로, `failure_reason` 만 `collected` 로 갈렸다. 입력이 둘이라
  `rejected=false, collected=false` 일 때 `stage=gather` + `GATHER_FAILED` 인데 문장은
  자격증명을 지목했다. 게다가 `_rf_collect_ok` 는 인증 판정이 아니라 **전체 수집 결과**여서
  인증이 200 으로 통과해도 시리얼 확정 실패 하나로 자격증명 문장이 나갔다 (os/esxi 는 자격 probe
  전용 관측을 쓴다 — 채널 간 근거 불일치).
- **수정**: `redfish-gather/site.yml` rescue 에 `_rf_auth_outcome` (passed / rejected / unknown)
  판정을 추가하고 4필드를 **그 하나에서만** 파생.
  `passed` = 수집 성공했거나 `_rf_auth_observations` 중 첫 인증 응답이 2xx/3xx (새 요청 0 — 계정 잠금 위험 불변).
- **검증**: `tests/e2e/test_failure_code_contract.py::test_case10_redfish_rescue_derives_all_fields_from_auth_outcome` (5 케이스),
  `::test_case10_redfish_never_blames_credentials_after_auth_passed`.

### P0-2 / H12 — `status=failed` 인데 `failure_reason=null`

- **문제**: `build_sections` 의 미분류 → failed 분기, 또는 supported 0건 / success 0건이면
  `_out_status='failed'` 가 되는데, 이 경로는 rescue 가 아니라 **정상 `build_output`** 을 지나
  성공 경로 diagnosis(failure_* 전부 null)가 그대로 실렸다.
- **수정**: `common/tasks/normalize/build_output.yml` 에 `ensure failed diagnosis` 태스크 신설
  (3채널 최종 조립이 이 파일 하나로 수렴하므로 site.yml 4곳에 복제하지 않는다).
- **검증**: `tests/e2e/test_errors_message_contract.py::test_normal_path_failed_status_gets_failure_fields` 외 4건.

### P0-3 / C5 / N12 / N13 / N32 / N36 — 섹션 failed 인데 errors 가 빈 배열

- **수정**: 섹션 failed 판정 조건과 errors 생성 조건을 **같은 변수 하나**로 묶었다
  (`_l_net_raw_ok` / `_l_sys_ok` / ESXi `_e_ds_ok` 우선순위 분기).
  ESXi `esxi_disks` 는 단일 try 가 세 빌더를 삼키던 구조를 파트별로 분리해
  `connect_ok` / `failed_parts` / `part_errors` 를 **추가만** 하고, `collect_disks.yml` 이 이를 배선.
  죽어 있던 `_e_dns_ok` / `_e_config_ok` 도 소비 — 단 **성공한 fallback(config 기반 DNS)은 error 로 만들지 않는다**.
- **검증**: `tests/unit/test_esxi_section_errors.py` (43건), OS 는 렌더 검증 + 기존 회귀.

### P0-4 / C6 — 자격 후보 0건 오분류

- **문제**: accounts 가 0건이면 `try_credentials` 의 iterate 가 통째로 skip 되어
  `_e_auth_ok` / `_os_auth_ok` 가 "관측한 적 없음" 인데도 false 로 남았다. 그 상태의 실패는
  `stage=auth` + 4번 문장으로 라벨링됐고, ESXi 는 같은 errors 원소의 detail 이
  "인증과 네트워크는 정상" 이라고 말해 정면 모순이었다.
- **수정**:
  - ESXi: 판정을 `_e_auth_ok or _e_facts_ok` 로 넓혔다 (facts 반환은 인증 통과의 직접 관측).
    rescue diagnosis 에 `details.auth`(시도 후보 수)를 실어 "후보 0건" 과 "후보 N건 전멸" 을 구분 가능하게 했다.
  - OS: `_os_auth_ok or (_all_sec_collected|length > 0)` — 섹션을 하나라도 수집했다는 것은
    원격 접속·인증이 통과했다는 관측이다.
  - ESXi `abort if facts failed` 의 "인증과 네트워크는 정상이나" 라는 **관측하지 않은 단정**을 제거.

### P0-5 / H3 — `TCP_CONNECTION_REFUSED` 인데 1번 문장

- **문제**: 문장이 존재하지 않는 presence 판정(`ip_in_use`)에 걸려 있었다. `ip_in_use` 를 set 하는
  코드가 저장소에 0건이라 RST 를 실제로 관측해 code 를 REFUSED 로 확정하고도 사용자에게는
  "IP 사용 여부를 확인하세요" 가 나갔다.
- **수정**: `reason_for_connect_failure(ip_in_use)` 를 제거하고 `reason_for_failure_code(code)` 로 교체.
  2번 문장을 "대상 IP의 관리 포트에 연결할 수 없습니다. 방화벽과 관리 서비스 상태를 확인하세요." 로 변경
  (presence 를 주장하지 않는다). **ICMP / IPAM / ARP presence 기능은 만들지 않았다.**
- **검증**: `test_failure_code_maps_to_exactly_one_sentence` (7 코드),
  `test_no_ip_presence_probe_is_implemented`, `test_os_portfail_reason_matches_observation`.

### P0-6 / C3 — Redfish 표준 계정 처리 오류 소실

- **문제**: `account_service.yml` 에 `errors` 라는 문자열이 **0건**이었다. 모듈이 25개 지점에서
  채우는 사유(중복 슬롯 / 계정 잠금 / 계정 비활성 / PATCH 실패 / password sync 후 재인증 실패 /
  DELETE+POST 실패 / 빈 슬롯 없음 / AccountService 미지원 …)가 전부 버려졌다.
  **계정 잠금은 재시도할수록 악화되는데 사용자는 "자격증명 확인" 만 안내받았다.**
- **수정**: `account_service.yml` 이 fragment 5변수 규칙대로 errors 를 배선.
  - 성공 필터: `recovered=true` 이고 `verification in [verified, none]` 이면 **emit 안 함**
    (모듈 errors 에는 `...retry 성공` 같은 성공 진행 노트가 섞여 있다).
  - message 는 Ansible 계층에서 새로 쓴다 (action/method 로 3분기). 모듈 원문 25건은 **detail 로만**.
    모듈 문자열은 건드리지 않았다 — 단위 테스트 6파일이 message 부분문자열을 assert 하고,
    `_is_404_only_error` 가 message 의 HTTP status 로 unsupported 를 분류하기 때문이다.
  - `role=primary` 후보가 아예 없는 경로(NEW-6)도 errors 1건을 남긴다.
  - Standard Account username 하드코딩 없음 재확인 (`infraops` 는 주석/테스트에만 존재).

### P0-7 / H11 — 성공한 fallback 이 status 를 partial 로 강등

- **문제**: `SimpleStorage` / `SmartStorage` fallback 으로 **데이터를 정상 수집했는데도**
  errors 에 항목이 생겨 `_make_section_runner` 의 `if errs: failed.append(section)` 때문에
  섹션이 failed → overall status 가 partial 로 강등됐다. HPE iLO4 등 구세대 BMC 는 매 수집마다 partial.
  또 vendor fallback 성공 시 **사용자 문구 부분일치**로 앞선 error 를 지우는 코드가 있어
  문구를 다듬는 순간 분류가 깨지는 구조였다.
- **수정**: `redfish_gather.py` 에 `_notice()` / `notices()` 신설 → 성공 fallback 은 errors 가 아니라
  notices 로. site.yml 이 `diagnosis.details.notices` 에 싣는다 (envelope 13 top-level 불변).
  문구 기반 제어는 내부 `code=_CODE_VENDOR_UNRESOLVED` 로 교체.
  `_capped` 는 `errors=None` 호출부(power TelemetryService / thermal Sensors)에서 절단 사실이
  아무 데도 안 남던 silent 절단(M6)을 notices 로 보완.
- **실측 근거**: `tests/fixtures/redfish/dmtf_rackmount1` 오프라인 재생 결과가
  `partial → success` 로 바뀌고 `failed_sections: ['storage'] → []`, `collected` 에 storage 추가,
  `error_count: 2 → 1`. golden 재생성 (`expected_output.json`).

---

## 3. 그 밖의 수정

| ID | 내용 |
|---|---|
| H1 | `build_failed_output.yml` 이 `_all_errors` 를 한 번도 참조하지 않아 rescue 진입 시 누적 섹션 오류가 전부 소실되던 것 → 대표 error 를 첫 원소로 두고 의미 있는 섹션 오류를 뒤에 보존, 중복 제거 + 상한 10건 |
| H2 | `수집 결과를 생성하지 못했습니다…` 가 3채널 always 블록 8곳 + callback 1곳에 리터럴 → `_fr_output_build_failed` 로 중앙화. `build_failed_output.yml` 의 표준 밖 7번째 문장은 폐지 |
| H10 | `e.message \| default(e \| string)` 이 null/''/키부재를 못 막아 **파이썬 dict repr 이 사용자 문장 자리**에 노출되던 것 → `filter_plugins/errors_normalizer.py` 신설 |
| M5 | 정규화 Jinja 가 merge_fragment / build_errors / 테스트 3곳에 복제 → 필터 한 곳으로 통합 (멱등) |
| M12 | `errors[].detail` 타입이 string / dict / null / `''` 혼재 → **string \| null** 로 통일 (dict 는 `k=v; k=v` 평탄화) |
| M3 | `errors[].section` 이 raw 이름으로 새어나가 Portal 이 섹션별로 묶을 수 없던 것 → `processors→cpu`, `network_adapters→network`, `boot→system`, `log_services→bmc`, `multi_node.*→multi_node`, `linux_hba_ib→storage`, `system_runtime/windows_runtime→system`, `esxi_network_extended→network` |
| C2 | 모듈 기술 문자열(`Processor /redfish/v1/... 실패: 401`, `예외 발생`)이 partial/success 경로 message 로 그대로 나가던 것 → `normalize_standard.yml` 이 섹션 사용자 문장으로 치환하고 원문은 detail 로 |
| M2 | vendor OEM 3종 문장에서 관측하지 않은 추측 + `graceful degradation` 제거. 죽은 `severity: warning` 키 제거 (정규화가 3키만 남겨 **envelope 에 도달한 적이 없다**) |
| H4~H7, M1 | OS 섹션 문장의 raw stderr / 영문 enum / Ansible 용어 / 내부 필드명 제거 → detail 로 |
| H8 | ESXi datastore 이름 무제한 concat → 고정 문장 + detail(500자 상한) |
| N41/N50/N51/N52/N65 | 실패 후보의 모듈 errors 와 무인증 probe errors 가 전부 버려지던 것 → 화이트리스트(role/label/status/첫 message)만 `errors[].detail` 로 합류 (상한 3건) |
| M10/N01/N02/N20 | callback 보충 루프를 per-host try 로 격리(첫 호스트 예외가 나머지를 전부 죽이던 것), 비상 스위치 상태 stderr 고지, precheck 원본 detail 보존, `_emit_error` 를 평문으로(stdout envelope 과 키 충돌 회피) |
| H13/P5 | `schema/field_dictionary.yml` 에 `errors[]` / `.section` / `.message` / `.detail` 4항목 신설 (종전 정의 **0건**) + `docs/contract/03-fields.md` §4-1 신설 |

---

## 4. 검증 결과 (실행함)

| 검증 | 결과 |
|---|---|
| `python -m pytest tests/ -q` | **2094 passed, 10 skipped, 7 xfailed** (착수 전 baseline 1974 passed) |
| `python tests/validate_field_dictionary.py` | `RESULT: PASS` (10 checks, 8 passed, 0 failed, 79 warnings) |
| `python scripts/ai/hooks/output_schema_drift_check.py` | exit 0 — `sections=11 fd_paths=173 fd_section_prefixes=18` |
| `python scripts/ai/verify_vendor_boundary.py` | 통과 (vendor 하드코딩 0건) |
| `python scripts/ai/verify_harness_consistency.py` | 통과 |
| 저장소 전체 Python `ast.parse` | 오류 0 |
| 저장소 전체 YAML `safe_load_all` | 오류 1건 — `scripts/ai/bug_tracker/inventory_lab_linux.yml` (**이번 변경 대상 아님**, 이전부터 Jinja 포함 inventory 라 plain YAML 파싱 불가) |
| DMTF mockup 오프라인 재생 10건 | golden 일치 (rackmount1 은 위 P0-7 근거로 재생성) |

### 신설 테스트

| 파일 | 건수 | 무엇을 고정하나 |
|---|---|---|
| `tests/e2e/test_section_message_contract.py` | 40 | partial/success 섹션 message 품질 (종전 게이트 **0건**), section 이름 정합, 모듈 문자열이 message 로 새지 않음, 성공 fallback ≠ error |
| `tests/unit/test_esxi_section_errors.py` | 43 | ESXi 섹션 errors 배선 + 문장 품질 |
| `tests/unit/test_errors_normalize.py` (재작성) | 17 | message 항상 non-empty string, detail string\|null, 조용한 drop 금지, 멱등, 사본 재생성 차단 |
| `tests/e2e/test_errors_message_contract.py` (추가분) | +14 | H1 보존/중복제거/상한, H12 failure_* 보장, failure_code→문장 매핑 7종, presence 미구현 고정 |

---

## 5. 검증하지 않은 것 (정직 고지)

- **실장비 / 실 Jenkins 실행 0건.** 이 환경에 `ansible-playbook` 이 없다. 모든 Ansible 검증은
  production YAML 에서 템플릿을 **추출해 Jinja 로 렌더**하는 방식이며, 실제 플레이북 실행이 아니다.
  따라서 다음은 `[WARN] 했지만 미확인` 이다:
  - `ansible-playbook --syntax-check` (3채널)
  - 실제 BMC / ESXi / OS 대상 end-to-end envelope
  - Portal 화면에 실제로 어떤 문장이 뜨는지
- **계정 write 경로(P0-6)는 dry-run 도 실행하지 않았다.** 배선의 정합성만 정적으로 확인했다.
  실제 recovery → 표준 계정 복구 시나리오는 실장비 검증이 필요하다.
- ESXi `_e_ds_result.msg` 가 모듈 실패 시 실제로 채워지는지, `esxi_disks` 파트 실패가 권한 부족
  환경에서 어떤 사유 문자열로 오는지는 실 vCenter 응답으로 한 번 봐야 확정된다.

---

## 6. 적대적 검수 (4 렌즈 병렬) 및 그 결과 고친 것

변경을 커밋하기 전에 독립 검수 4종(런타임 파손 / 정보 소실 / 계약 위반 / 비밀 노출·문구 품질)을
돌렸다. 검수자에게는 "테스트가 통과한다는 사실을 근거로 문제 없다고 말하지 마라 — 테스트가 없는
곳을 찾아라" 를 지시했다. 결과로 **내 변경이 만든 파손 2건과 pre-existing 파손 1건**을 잡았다.

| 등급 | 무엇 | 어떻게 발견됐나 | 조치 |
|---|---|---|---|
| BLOCKER | `redfish-gather/site.yml` 성공 경로 `set output meta` 의 `>-` 폴디드 스칼라 **안쪽**에 `#` 주석 3줄을 넣어 템플릿이 통째로 컴파일 불가. 그 태스크가 죽으면 rescue 로 빠져 **정상 수집한 Redfish 결과가 전부 status=failed 로 나간다** | 저장소 hook(`pre_commit_jinja_compile_check.py`)이 [WARN]/exit 0 이라 차단하지 못했고, pytest 는 이 템플릿을 렌더하지 않아 2128 passed 로도 안 잡혔다 | 주석을 표현식 밖으로 이동. **pytest 게이트 신설** — `test_every_inline_jinja_template_compiles` (실제로 주입 실험으로 검출력 확인) |
| HIGH | `_fail_errors` 가 살린 섹션 오류 중 `표준 항목은 정상 수집되었습니다` 같은 **다른 부분의 성공을 단언하는 절**이 status=failed envelope 에 섞여 Portal 한 화면에 "수집 실패" 와 "정상 수집 완료" 가 동시에 표시 | 렌즈 5(문장이 거짓을 말하는가) | 해당 절 4곳 삭제(vendor OEM 3 + site.yml OEM rescue) + `_sm_overrides` 2건 수정. 게이트 추가 — `test_section_message_never_asserts_success_of_other_parts` |
| HIGH (pre-existing) | 3채널 rescue / `build_output` / esxi·redfish 성공 경로가 `_diagnosis.details` 를 **가드 없이** 접근. ansible-core 2.19+ 는 dict 에 없는 키의 속성 접근 결과(Marker)를 테스트에 넘기면 `AnsibleUndefinedVariable` 로 죽는다 → rescue 중단 → `build_failed_output` 미실행 → 그 호스트는 실패 원인을 잃고 `OUTPUT_BUILD_FAILED` fallback 만 받는다 | 순수 jinja2 `_ChainableUndefined` 환경은 이 동작을 **재현하지 못한다**. 검수자가 실제 `ansible.template.Templar` 로 렌더해 발견 | 5곳 전부 `\| default({})` 가드 추가. **실제 Ansible 엔진 렌더 테스트 신설** — `tests/e2e/test_diagnosis_template_ansible_render.py` (22 케이스) |

그 밖에 검수에서 나와 함께 고친 것:

- Redfish 섹션 message 를 고정 문장으로 통일하면서 **같은 문장 N개가 Grid 를 채우던** 문제
  (DIMM 24개 실패 → 동일 행 24개) → `(section, message)` 로 합치고 detail 5건 + `외 N건`.
- `SimpleStorage` fallback 이 200 을 주고도 **결과가 비면** errors 가 0건이 되어 "데이터 없음" 이
  success 로 보고되던 신규 회귀 → 빈 결과일 때 error 를 남긴다.
- `_fail_errors` 중복 판정을 message 단독 → `(message, detail)` 로 좁혀 **유일한 1차 증거인
  detail 이 함께 사라지던** 문제 해소. 상한 초과 시 `표시하지 않은 오류 N건` 을 남긴다.
- `_rf_auth_outcome` 에 `not_attempted` 를 추가. 자격 요청을 **보내기 전에** 멈춘 실패
  (adapter 선택 / vault 로드 예외)를 `auth` 로 라벨링하면 CLAUDE.md §9 위반이고 사용자가
  자격증명을 헛되이 뒤진다 → `gather` / `GATHER_FAILED` / 5번 문장.
- dryrun(`-e _rf_account_service_dryrun=true`)을 계정 정리 **실패로 오탐**하던 것 제외.
- `diagnosis.details.notices` 를 rescue 경로와 `account_provision` 모드에도 실어 대칭 확보.
- `field_dictionary` 에 `diagnosis.details.notices` 추가, `errors[].section` 허용값에 채널 표시값
  5종 명시. `build_status.yml` 의 시나리오 B 참조를 line 번호 → **변수 기준**으로 교체(재-stale 차단).
- `schema/output_examples/redfish_failed.jsonc` 를 새 계약으로 갱신(M7).

**반증되어 고치지 않은 것**: 검수자가 지적한 `_fail_errors` 미검증 주장은 이미
`test_failed_envelope_*` 5건이 production 템플릿을 추출해 렌더하고 있어 사실이 아니었다.

## 7. 최종 검증 (실행함, 2026-08-12)

| 검증 | 결과 |
|---|---|
| `python -m pytest tests/ -q` | **2190 passed, 10 skipped, 7 xfailed** (착수 전 1974 passed) |
| `python tests/validate_field_dictionary.py` | `RESULT: PASS` (0 failed) |
| `python scripts/ai/hooks/output_schema_drift_check.py` | exit 0 (`sections=11 fd_paths=174 prefixes=18`) |
| `python scripts/ai/hooks/pre_commit_jinja_compile_check.py --all` | 위반 0건 |
| `python scripts/ai/verify_vendor_boundary.py` | 통과 |
| `python scripts/ai/verify_harness_consistency.py` | 통과 |
| 저장소 전체 `ast.parse` / `yaml.safe_load_all` | py 0건 / yaml 1건(`scripts/ai/bug_tracker/inventory_lab_linux.yml` — 이번 변경 대상 아님) |

