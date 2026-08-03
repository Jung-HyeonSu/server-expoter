# 2026-08-03 — NetworkAdapters HTTP 400 → sections.network 마스킹 (사이트 Dell 8대)

> 분류: 사이트 사고 조사 + fix. 관련 결정: `docs/19_decision-log.md` 2026-08-03.
> 외부 계약: `docs/ai/catalogs/EXTERNAL_CONTRACTS.md` 2026-08-03.

## 1. 관측 (사용자 제보 + 실측)

- 출처: Jenkins `http://10.100.64.153:8080/job/DAY_1/job/git/job/소연등록redfish/1/consoleText`
  (console 178,665 chars / 338 lines, envelope 8건 = line 102~109 회수).
- 대상: Dell iDRAC 8대 — 10.50.11.51 / .52 / .53 / .54 / .151 / .152 / .153 / .154.
  `RedfishVersion=1.4.0`, Product=`Integrated Dell Remote Access Controller`, adapter=`redfish_dell_idrac10`.

**8대 전부 동일**:

```
status: partial
sections.network: failed
errors: [{"section":"network_adapters",
          "message":"NetworkAdapters 미지원 또는 실패: HTTP 400: Bad Request",
          "detail":null}]
```

**그런데 data.network 는 정상** (10.50.11.52 기준):

| 키 | 값 |
|---|---|
| `interfaces` | 4건 (NIC.Integrated.1-1-1 ~ 1-4-1, MAC/speed 실값) |
| `default_gateways` | `[{ipv4, 10.50.11.254}]` |
| `summary.port_count` | 4 |
| `adapters` / `ports` | `[]` / `[]` ← 이것만 빔 |

→ **데이터는 멀쩡한데 status 만 거짓**. 다른 섹션은 전부 success(system/users 는 not_supported).

## 2. 원인 (코드 실측 — file:line)

| # | 결함 | 위치 |
|---|---|---|
| 1 | `_run()` 이 errs 있는 섹션을 `collected` + `failed` 양쪽에 등록 → 모듈이 `failed_sections=['network_adapters']` emit | `redfish-gather/library/redfish_gather.py` `_make_section_runner` |
| 2 | `_rf_proc_map` 이 `network` 와 `network_adapters` 를 같은 `network` 로 collapse | `redfish-gather/tasks/normalize_standard.yml` `_rf_proc_map` |
| 3 | `build_sections` 우선순위 `not_supported > failed > success` → 보조 실패가 항상 승리 | `common/tasks/normalize/build_sections.yml` |
| 4 | 404 만 capability 부재로 분류 (`_is_404_only_error`) → 벤더 400 은 영구 failed | 동 라이브러리 |
| 5 | 실패 시 응답 body 폐기 → `errors[].detail=null` (DSP0266 `@Message.ExtendedInfo` 소실) | `gather_network_adapters_chassis` |

`docs/ai/NEXT_ACTIONS.md` 에 **NET-SEC-MAP**(LOW, "CSUS 수정 후 미발동")으로 등재돼 있던 latent 결함이 실발동.

## 3. "우리 요청 문제 아님" 검증 (증거 2건)

| # | 증거 | 결과 |
|---|---|---|
| 1 | `power` / `thermal` 이 **동일 `eff_chassis_uri`** 사용 (`_collect_all_sections`) | 둘 다 `success` → chassis URI 해석 정상 |
| 2 | 실 Dell R740 전수 미러 `tests/fixtures/redfish/real_dell_r740/recording.json` 에 `get::Chassis/System.Embedded.1/NetworkAdapters` | **200** (NIC.Integrated.1 / NIC.Slot.2,3,5,8 / FC.Slot.1,7 수집) → URL 구성 정상 |

→ 장비/펌웨어(또는 라이선스) 차이로 결론. rule 25 R7-A-1(사용자 실측 우선).

## 4. 실장비 직접 확인 시도 — 실패 (정직 보고)

- 10.50.11.52:443 TCP 도달 확인(`Test-NetConnection` = True).
- vault `dell_fallback_2` 계정으로 ServiceRoot/System/Manager/Chassis GET 시도 → **전부 401**,
  이후 **연결 강제 종료(WinError 10054, IP 차단 추정)**.
- **즉시 중단** — BMC/AD lockout 위험(AUDIT-2026-05-29 [HIGH]). 재시도 안 함.
- 결과: **400 의 근본 사유(미구현 / 라이선스 / 기타)는 ❌ 미확정**. fix C 적용 후 다음 빌드의
  `errors[].detail` 로 확인 필요.
- 부수: 복호화한 vault 평문 사본은 검증 직후 삭제함.

## 5. 적용한 fix

| # | 내용 | 파일 |
|---|---|---|
| A | 보조(auxiliary) 섹션 개념 — `_rf_aux_sections: ['network_adapters']`, 세 status fragment(collected/failed/**unsupported**) 모두에서 제외 | `normalize_standard.yml` |
| B | `_is_capability_missing_error`(404 **or 400**) 신설, `_run` 이 사용. `_is_empty_result` AND 가드 + 비-404 분류 시 stderr 원문 기록 | `redfish_gather.py` |
| C | `_extended_info(body)` — `error.code`/`message`/`@Message.ExtendedInfo[]` 300자 축약 → `errors[].detail` | `redfish_gather.py` |

A 에서 `unsupported` 까지 제외한 게 핵심 — 안 하면 B 적용 후 `network` 가 `not_supported` 로 덮여 더 나쁜 마스킹.

## 6. 검증 결과

| 항목 | 결과 | 증거 |
|---|---|---|
| 신규 단위 회귀 | **21 passed** | `tests/unit/test_network_adapters_aux_status.py` |
| 신규 사이트 재현 회귀 | **6 passed** | `tests/integration/test_site_dell_networkadapters_400.py` (실 R740 미러의 NetworkAdapters 를 400 으로 변조 → 모듈 → normalize fragment → build_sections → build_status 전 체인 렌더) |
| 역가드 (버그 재현 확인) | PASS | `test_prefix_behavior_would_have_been_partial` — 수정 전 로직이면 `partial` 재현 |
| fix 제거 시 실패 확인 | **9 failed** | `git stash push -- redfish-gather/tasks/normalize_standard.yml` 후 재실행 → 핵심 테스트 전부 FAIL, stash pop 복원 |
| 전체 회귀 | **1302 passed / 5 skipped / 7 xfailed** | `pytest tests/ --ignore=tests/e2e_browser` |
| Python 컴파일 | OK | `python -m py_compile redfish-gather/library/redfish_gather.py` |
| YAML 파싱 | OK | `yaml.safe_load(normalize_standard.yml)` |
| baseline 영향 | 0 | 10종 전부 `sections.network=success` 유지 (변경 전후 동일) |

## 7. 미검증 (⚠️ — 이 환경 제약)

| 항목 | 사유 | 확인 방법 |
|---|---|---|
| 실 ansible-playbook 통합 | 이 환경에 `ansible-playbook` CLI 부재 (ansible **라이브러리** 2.19.9 만 존재) | Jenkins Agent 에서 redfish 파이프라인 1회 재빌드 |
| 사이트 envelope 실제 변화 | BMC 직접 접근 불가 | 같은 Job 재실행 → `status`/`sections.network` 확인 |
| 400 의 근본 사유 | 위 4절 | 재빌드 후 `errors[].detail` 또는 Jenkins console stderr 의 `capability 부재로 분류(비-404 응답)` 라인 |
