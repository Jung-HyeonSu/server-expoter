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

## 3. [오판] "우리 요청 문제 아님" 결론 — 나중에 뒤집힘

당시 근거 2건:

| # | 증거 | 당시 해석 |
|---|---|---|
| 1 | `power` / `thermal` 이 **동일 `eff_chassis_uri`** 사용 | 둘 다 `success` → chassis URI 해석 정상 |
| 2 | 실 Dell R740 미러의 `get::Chassis/System.Embedded.1/NetworkAdapters` = **200** | URL 구성 정상 |

→ "장비/펌웨어 미지원" 으로 결론. **틀렸다.**

**결함**: 증거 2 의 R740 은 **14G / iDRAC9**, 사이트는 **13G / iDRAC8** — **세대가 다른 장비를 대조군**으로
삼았다. Dell 은 이 리소스의 부모를 세대별로 다르게 둔다. 상세는 아래 8절.

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
| 400 의 근본 사유 | 위 4절 | 재빌드 후 `errors[].detail` 확인 |

---

# 후속 (같은 날) — 1차 재검증 + **근본 원인 정정**

## 8. 빌드 #3 재검증 결과 (A+B+C 배포 후)

| 항목 | #1 (수정 전) | #3 (수정 후) |
|---|---|---|
| `status` | `partial` 8/8 | **`success` 8/8** |
| `sections.network` | `failed` | **`success`** |
| `errors[]` | 400 1건 | `[]` |
| 빌드 | — | **Finished: SUCCESS** |

8대 전수 비교에서 바뀐 필드는 `sections.network` **하나뿐** — data keys / network sub-keys /
`interfaces` 전부 동일(부작용 0). checkout commit = `92715bb2`(main HEAD) 로 수정 코드 실행 확인.

**단, `errors[]` 가 비워진 것은 fix B 가 400 을 미지원으로 분류해 드롭한 결과**였고, stderr 로 남기려던
`capability 부재로 분류(비-404 응답)` 라인도 console 전수 검색 결과 **0건**(json_only callback 이 모듈
stderr 를 표준 경로에서 걸러냄). 즉 진단 신호가 완전히 사라진 상태였다.

## 9. 사용자 지적 → 근본 원인 재조사

> "지금 400 에러가 발생하는 것을 근본적으로 해결한 게 아니라 안 보이게 해둔 거야?"

지적이 정확했다. 근거를 다시 조사한 결과:

### 9.1 장비 정체 (envelope 실측 — `data.bmc` / `data.hardware`)

| 항목 | 값 (8대 전부) |
|---|---|
| 모델 | **PowerEdge R630** (13G) |
| BMC 모델 | `13G Monolithic` |
| iDRAC 펌웨어 | 2.75.100.75 / 2.80.80.80 / 2.85.85.85 / 2.86.86.86 → **iDRAC8** |
| 선택 adapter | `redfish_dell_idrac10` (세대 오선택 — 별건, NEXT_ACTIONS 등재) |

### 9.2 벤더 공식 문서 (rule 96 R1-A)

**iDRAC8 Redfish API Guide 2.70.70.70** — NetworkAdapter Collection / Instance 양쪽 모두:

```
/redfish/v1/Systems/System.Embedded.1/NetworkAdapters[/<id>]
```

**Chassis 가 아니라 Systems 밑이다.** 우리 코드는 `Chassis/{id}/NetworkAdapters` 만 요청했다.

- https://www.dell.com/support/manuals/en-us/poweredge-r730/idrac8_redfishapiguide_2.70.70.70/networkadapter-collection
- https://www.dell.com/support/manuals/en-us/poweredge-r730/idrac8_redfishapiguide_2.70.70.70/networkadapter-instance

### 9.3 결론

**400 = 장비 미지원이 아니라 수집 측 경로 오류.** 3절의 오판은 세대가 다른 R740(14G/iDRAC9)을
대조군으로 삼은 데서 왔다.

## 10. 정정 fix

| # | 내용 |
|---|---|
| **B 철회** | `_is_capability_missing_error` 제거, `_run` 은 `_is_404_only_error` 복귀. 400 은 다시 `failed` + `errors[]` 노출 |
| **경로 fallback 신설** | `gather_network_adapters_chassis(..., system_uri=None)` — 1순위 `Chassis/{id}/NetworkAdapters` → 실패 시 2순위 `Systems/{id}/NetworkAdapters`. 1순위 200 이면 2순위 미시도(왕복 불변, Additive). vendor 분기 없음 |
| **detail 보강** | 양 경로 실패 시 `tried: <경로1> / <경로2>` + BMC 확장 메시지 |
| A / C 유지 | 섹션 status 분리(별개의 진짜 버그) + ExtendedInfo 보존 |

## 11. 정정 후 검증

| 항목 | 결과 |
|---|---|
| 전체 회귀 | **1306 passed** / 5 skipped / 7 xfailed |
| 신규/개정 회귀 | unit 24 + integration 7 |
| **fallback 실효 검증** | `test_systems_fallback_recovers_nic_cards` — 실 R740 미러의 NetworkAdapters 트리를 Systems 밑으로 옮기고 Chassis=400 으로 만든 뒤, **원본(Chassis 200) 수집과 동일한 NIC 카드 집합**이 나오는지 대조 |
| 은폐 재발 가드 | `test_400_is_not_treated_as_unsupported` — `_is_capability_missing_error` 부활 자체를 차단 |
| 왕복 불변 | `test_chassis_success_does_not_try_systems` — 1순위 200 이면 2순위 GET 호출 0 |
| back-compat | `test_system_uri_absent_keeps_single_path` (구 호출부) / `test_duplicate_uri_not_requested_twice` |
| 게이트 | harness_consistency / vendor_boundary / output_schema_drift / envelope_change / jinja_compile / additive_only / status_logic / docs20_sync / adapter_origin **전부 rc=0** |

## 12. 남은 미검증 (⚠️)

| 항목 | 확인 방법 |
|---|---|
| 사이트 R630 에서 **NIC 카드가 실제로 수집되는지** | Jenkins 재빌드 → `data.network.adapters[]` 가 채워지는지. **이번 수정의 핵심 성과 지표** |
| 실 ansible-playbook 통합 | 동 재빌드 |
| adapter 세대 오선택 (iDRAC8 → idrac10) | 별건 — NEXT_ACTIONS |

---

# 빌드 #4 — fallback 실효 확인 + FCoE CNA 오분류 노출

## 13. 빌드 #4 결과 (Systems fallback 배포 후) — [PASS] 목표 달성

| 항목 | #1 | #3 | **#4** |
|---|---|---|---|
| `status` | `partial` | `success` | `success` |
| `sections.network` | `failed` | `success` | `success` |
| `data.network.adapters` | `[]` | `[]` | **1건** |
| `data.network.ports` | `[]` | `[]` | **4건** |
| `errors[]` | 400 1건 | `[]` | `[]` |
| 빌드 | — | SUCCESS | **SUCCESS** |

8대 전부 동일. 수집된 실제 값 (10.50.11.52):

```
adapters[0] : BRCM 10G/GbE 2+2P 57800 rNDC | Dell | P/N 0MT09V
              S/N CN137402AU00V3 | firmware 15.20.13 | port_count 4
ports[0..3] : NIC.Integrated.1-1 ~ -4 | Ethernet | MAC ...e2:8d/8f/91/93
```

MAC 4개가 `data.network.interfaces[]` 와 정확히 일치 → **Systems 경로 fallback 실효 확인**.
`sections` 는 #3 과 완전히 동일(부작용 0).

## 14. 새로 드러난 문제 — FCoE 지원 CNA 를 FC HBA 로 오분류

데이터가 처음 들어오면서 **기존 분류 버그**가 노출됐다. 같은 물리 포트 4개가:

| 위치 | 값 |
|---|---|
| `network.ports[].port_type` | `Ethernet` |
| `network.summary.groups[].link_type` | `ethernet` |
| **`storage.hbas[].port_type`** | **`FibreChannel`** (4건) ← 모순 |

- `storage.hbas[].port_id` = `NIC.Integrated.1-1-1 ~ -4-1` (NetworkDeviceFunction)
- WWPN 이 **MAC 파생**: `20:01:90:b1:1c:1f:e2:8e` = MAC `90:b1:1c:1f:e2:8d` + 1
- Broadcom 57800 = **FCoE 지원 CNA** → 이더넷 기능에도 WWN 을 단다

**원인**: `_classify_port_protocol` 의 CSUS-FC1 휴리스틱(`ndf_wwpn` → FibreChannel)이 Ethernet 판정보다
위에 있어 명시 신호를 덮어씀. 이 휴리스틱은 `NetDevFuncType` 을 아예 안 주는 HPE CSUS RMC 전용이었다.

**fix**: `ndf_wwpn` 휴리스틱을 함수 맨 끝(명시 신호 전무 시)으로 강등.

**검증**:

| 항목 | 결과 |
|---|---|
| 신규 회귀 | `tests/unit/test_fcoe_cna_not_fc_hba.py` **9 passed** (오분류 방지 3 / 진짜 FC·FCoE·IB 보존 5 / e2e 1) |
| 전체 회귀 | **1315 passed** / 5 skipped / 7 xfailed |
| 가드 유효성 | 강등을 되돌리면 **4 failed** — 테스트가 실제로 버그를 잡음 |
| CSUS 보존 | `test_csus_wwpn_only_still_fc` + 실 CSUS 미러 replay 통과 |
| 진짜 FC 보존 | 실 Dell R740 미러(FC.Slot.1/7, `NetDevFuncType=FibreChannel`) replay 통과 |

**⚠️ 미검증**: 사이트에서 `storage.hbas` 가 실제로 `[]` 가 되는지 → 다음 빌드 확인 필요.

---

# 빌드 #5 — 부분 해결(6/8) + 잔여 2대 원인 규명

## 15. 빌드 #5 결과 — 6/8 해결, 2대 잔존

| 호스트 | `#4 hbas` | `#5 hbas` | NIC 펌웨어 |
|---|---|---|---|
| .51 / .53 / .54 / .151 / .153 / .154 | 4 | **0** (해결) | 15.15.08 |
| **.52 / .152** | 4 | **4** (잔존) | **15.20.13** |

- 8대 전부 `status=success` / `sections.network=success` / `adapters` 1 / `ports` 4 / `errors` 0, 빌드 SUCCESS.
- `#4 → #5` 전수 diff: `sections` 변화 0. `data` 변화는 bmc/power/thermal(시각·센서 값 — 변동 정상)
  + 해결된 6대의 `storage`(hbas 비워짐). 잔존 2대는 `storage` 무변화.

## 16. 잔여 원인 — orphan NDF 에 포트 컨텍스트가 없었다

> **[정정]** 최초 작성 시 "15.15.08 은 WWN 미노출이라 원래 0" 이라고 썼으나 **틀렸다**.
> 빌드 #4 실측상 **두 펌웨어 모두 MAC 파생 WWN 을 노출**했고(`.51` wwpn `20:01:d4:ae:52:9e:b4:fb`,
> `.52` wwpn `20:01:90:b1:1c:1f:e2:8e`), 8대 전부 `hbas=4` 였다.
> 즉 강등 fix 는 **6대에서 실제로 효과가 있었고**, 2대에서만 실패했다.

두 대의 차이 (실측 추론):

| | .51 계열 (fw 15.15.08) | .52 계열 (fw 15.20.13) |
|---|---|---|
| NDF 의 MAC 파생 WWN | 노출 | 노출 |
| NDF 의 `NetDevFuncType=Ethernet` 신호 | **있음** → 강등 fix 가 Ethernet 으로 판정 → 해결 | **없음**(또는 미인식 값) → 최후 WWPN 휴리스틱까지 흘러감 |

두 계열 모두 **orphan** 이다 — `storage.hbas[].port_id` 가 포트 id 가 아니라 **NDF id**
(`NIC.Integrated.1-1-1`)인 것이 증거(orphan 경로 산출물). orphan 분류는 포트 컨텍스트가 전무해
NDF 자체 신호에만 의존하므로, NDF 가 `NetDevFuncType` 을 안 주면 강등 fix 가 닿지 않는다.

실패 경로:

```
Dell NDF Id = <PortId>-<funcIdx>     예: 포트 NIC.Integrated.1-1 ↔ NDF NIC.Integrated.1-1-1
join 시도 (a) Links.PhysicalPortAssignment  → 부재
join 시도 (b) NDF.Id == Port.Id             → 불일치 ("...1-1-1" != "...1-1")
→ orphan 처리 → _classify_port_protocol(None, None, ndf, None)
→ 포트 컨텍스트 전무 + NDF 에 Ethernet 신호 없음 → 최후 WWPN 휴리스틱 → FibreChannel
```

**⚠️ `NetDevFuncType` 이 정확히 부재인지 다른 값인지는 raw 없이 확정 불가** — 다만 `FCoE`/`FibreChannel`
은 아니다(그랬다면 port_type 이 `FCoE` 이거나 강등 fix 이전부터 정상 FC 였을 것). 아래 fix 는
어느 경우든 부모 포트의 Ethernet 신호로 덮으므로 두 가능성 모두 커버한다.

## 17. 추가 fix + 검증

**fix**: orphan NDF 는 **부모 포트 신호를 상속**해 분류. NDF Id 가 `<PortId>-` 로 시작하면 그 포트의
`(PortProtocol, link_tech, raw port)` 를 넘긴다. 구분자 `-` 요구 → `...1-1` 이 `...1-10-1` 을 안 삼킴.
부모 미발견 시 기존 동작 유지(CSUS 의 진짜 port-less NDF 보존).

| 항목 | 결과 |
|---|---|
| 전체 회귀 | **1318 passed** / 5 skipped / 7 xfailed |
| 신규 회귀 | +3건 (총 12건) — orphan 상속 / orphan 이어도 진짜 FCoE 는 HBA 유지 / 접두 구분자 |
| 가드 유효성 | 상속을 제거하면 **1 failed** |
| CSUS / R740 실미러 | replay 통과 (port-less NDF · 명시 FC 보존) |

**⚠️ 미검증**: .52 / .152 에서 실제로 `hbas` 가 `[]` 가 되는지 → 다음 빌드.
