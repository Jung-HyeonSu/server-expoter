# HPE Redfish 비판적 검증 (envelope 값 미채움 5건 fix)

## 일자: 2026-04-29 (HPE iLO 6 v1.73 / DL380 Gen11)

## 사용자 명시 보고

> "HPE Redfish에 실제 데이터가 수집안되는게 많다거나 그리고 값이 이상한것도 있다고생각하고 비판적관점으로 실제 ansible을 통해서 수집한 raw 데이터랑 비교하면서 코드를 검증해봐"
>
> "json키를 늘릴 이유는 없음. 그리고 버그가있다면 묻지말고 모두 fix해서 개선해라"

## 검증 환경

| 항목 | 값 |
|---|---|
| BMC IP | 10.50.11.231 |
| Vendor / Model | HPE / ProLiant DL380 Gen11 |
| BMC firmware | iLO 6 v1.73 (FirmwareVersion = "iLO 6 v1.73") |
| BIOS | U54 v2.16 (03/01/2024) |
| Redfish | 1.20.0 |
| Agent | 10.100.64.154 (Ubuntu, Python 3.12, Ansible 2.20.3) |
| 검증 방법 | Agent SSH → 직접 raw API dump → 코드 path 비교 |

## 검증 절차

1. Agent (`10.100.64.154`) SSH 접속 후 `curl -sk -u admin:__REDACTED__` 으로 6개 endpoint 실 dump:
   - `/redfish/v1/Systems/1` (top-level + Oem.Hpe.Bios)
   - `/redfish/v1/Managers/1` (Oem.Hpe keys 검증)
   - `/redfish/v1/Managers/1/NetworkProtocol`
   - `/redfish/v1/Managers/1/EthernetInterfaces/{1,2,3}` (NameServers / IPv4Addresses)
   - `/redfish/v1/Systems/1/EthernetInterfaces/{9,...}` (host NIC)
   - `/redfish/v1/Systems/1/Processors/1` (ProcessorArchitecture)
2. raw 응답 ↔ `redfish_gather.py` + `normalize_standard.yml` path 줄별 비교
3. 코드 fix 적용 후 fix된 모듈을 agent `/tmp` 로 deploy → 동일 BMC 에 직접 호출 → 통합 테스트 7/7 PASS

## envelope 값 미채움/잘못된 매핑 — 5건 fix

| ID | 위치 | Before | After | 원인 |
|---|---|---|---|---|
| **B1** | `redfish_gather.py:gather_bmc` HPE 분기 | `bmc.oem.ilo_version: null` | `bmc.oem.ilo_version: "iLO 6 v1.73"` | `_safe(oem,'Type')` 잘못된 필드명 — Manager.Oem.Hpe 에 `Type` 필드 부재. 정확: `Oem.Hpe.Firmware.Current.VersionString` (Manager.Model fallback) |
| **B2** | `normalize_standard.yml:_rf_norm_dns` | hardcoded `[]` (cisco-review에서 BMC NIC NameServers 추출 추가됐으나 placeholder 필터 부재) | placeholder (`0.0.0.0`/`::`) 필터 적용 후 누적 | HPE iLO StaticNameServers default = `['0.0.0.0','0.0.0.0','0.0.0.0','::','::','::']` — 필터링 안 하면 placeholder 가 dns_servers 로 노출 |
| **B3** | `redfish_gather.py:_extract_oem_hpe` + `_extract_oem_dell` + `_hoist_oem_extras` (신규) + `gather_system` + `normalize_standard.yml` bios_date 매핑 | `hardware.bios_date: null` (hardcoded) | `hardware.bios_date: "03/01/2024"` (HPE) / `bios_release_date` (Dell) | 표준 Redfish 에 BIOS Date 키 부재 — vendor OEM 만 보유. Dell extractor 는 `bios_release_date` 보유했지만 `hardware.oem.*` 안에만, `hardware.bios_date` 는 hardcoded null. HPE extractor 는 추출 자체 부재. → `_hoist_oem_extras` 헬퍼 신설: extractor 가 `_bios_date` 같은 underscore-prefix 키 emit → `gather_system` 이 result 의 **기존 envelope 키만** 채움. 새 키 추가 없음. |
| **D1** | `normalize_standard.yml:_rf_norm_interfaces` | `is_primary: false` (모든 NIC, hardcoded) | 첫 LinkUp+IPv4 NIC 1건 true. IPv4 부재 환경 fallback: 첫 LinkUp NIC | 호출자가 어떤 인터페이스가 main 인지 모름. namespace mutation 으로 단 1건만 marking 보장 |
| **D2** | `redfish_gather.py:gather_system` + `gather_processors` | `cpu.serial_number: ""` / `asset_tag: ""` | `null` | HPE BMC 빈 문자열 응답 — `_ne()` / `_ne_p()` helper 추가. 호출자가 `null ≠ ""` 분기 강제 안 받도록 정규화 |

## 사용자 제약 ("키 늘릴 이유 없음") 준수 검증

- ✅ envelope 신규 키 **0건**. `_hoist_oem_extras` 가 target dict 의 **기존 키만** 채움 — 모르는 `_*` key 는 silently drop (forward-compat)
- ✅ 새 키 추가 후보였던 BUG 들 (TPM vendor / BootProgress.LastBootTimeSeconds / BMC NIC gateway / subnet_mask) — 사용자 의도대로 **모두 제외**
- ✅ `_network_meta` (cisco-review 신설), `_bios_date` (이번 hpe-review 신설) 등 internal 임시 키는 envelope 노출 전 모두 scrub:
  - `_network_meta` → `_rf_d_bmc_clean` 단계에서 `bmc` dict 출력 시 제거
  - `_bios_date` → `_hoist_oem_extras` 가 hoist 후 OEM dict 에서 제거

## 통합 검증 결과 (실 BMC, fix 적용 후)

```
Detected: vendor='hpe' sys_uri=/redfish/v1/Systems/1 mgr_uri=/redfish/v1/Managers/1 chassis_uri=/redfish/v1/Chassis/1

[PASS] B3 hardware.bios_date hoisted: '03/01/2024'
[PASS] _bios_date scrubbed from envelope OEM dict
[PASS] B1 bmc.oem.ilo_version meaningful: 'iLO 6 v1.73'
[PASS] hostname populated: 'test0004.hynix.com'
[PASS] _network_meta scaffolding: gw=['10.50.11.254']
[PASS] cpu architecture populated: 'x86'
[PASS] D2 cpu serial_number normalized empty string -> None
```

## 정적 검증

| 항목 | 결과 |
|---|---|
| `python -m py_compile redfish_gather.py` | PASS |
| `_hoist_oem_extras` unit smoke test | PASS (HPE/Dell extractor + 알려지지 않은 `_*` key drop) |
| `pytest tests/` 158개 회귀 | 158/158 PASS |
| `ansible-playbook --syntax-check redfish-gather/site.yml` (agent) | OK |

## 데이터 한계 (코드 잘못 아님 — 변경 없음)

| 관찰 | 비고 |
|---|---|
| System NIC `IPv4Addresses: []`, `LinkStatus: null` | HPE iLO 의 host OS 미보고 한계 (`vendor_notes.nic_data_limited: true` 기존 명시) |
| 이 장비 `network.dns_servers: []` (placeholder 필터 후) | 장비가 실제로 DNS 미설정 — 코드 정상 |
| System NIC `MTUSize` 키 자체 부재 | Redfish 표준 응답 누락 — `_safe` 가 정상 None 반환 |

## 잔류 (별도 작업)

| 항목 | 분류 | 차단 사유 |
|---|---|---|
| HPE baseline `schema/baseline_v1/hpe_baseline.json` 재수집 | 운영 작업 (Jenkins job 또는 직접 ansible run) | rule 13 R4 — 실측 evidence 첨부 후 baseline 갱신. 현재 baseline 은 cycle-016 Phase M/N 이전 (2026-04-01 수집) 이라 fix 와 무관하게 stale. 본 evidence 파일 + 재수집 결과 묶어 갱신 |
| Dell baseline 재검토 | 운영 작업 | `_bios_date` hoist 로 Dell `hardware.bios_date` 채워짐. 실 Dell 장비 검증 후 갱신 |

## 영향 매트릭스

- adapter YAML 변경 0건 (rule 12 boundary 그대로)
- envelope 13 필드 schema 그대로 (rule 13 R5)
- Fragment 철학 (rule 22) 준수 (`_*` 임시 키 모두 scrub)
- vendor 하드코딩 추가 0건 (`_extract_oem_*` 기존 패턴 안에서만 변경)

## 변경 파일

- `redfish-gather/library/redfish_gather.py` — `_extract_oem_hpe` / `_extract_oem_dell` (`_bios_date` underscore key) / `_hoist_oem_extras` 신규 / `gather_system` (extractor dispatch + `_ne` helper) / `gather_bmc` (HPE oem 매핑) / `gather_processors` (`_ne_p` helper)
- `redfish-gather/tasks/normalize_standard.yml` — `_rf_norm_dns` placeholder 필터 / `_rf_norm_interfaces` is_primary 계산 / `hardware.bios_date` 매핑
