# Cisco Redfish 비판적 검증 + Fix (2026-04-29)

## 환경

- Jenkins Agent: `10.100.64.154` (Ubuntu 24.04, jenkins-agent-ops)
- Cisco BMC: `10.100.15.2` — Cisco UCS C220 M4
  - CIMC `4.1(2g)`, BIOS `C220M4.4.1.2c.0.0202211901`
  - System UUID `B190019F-56CE-4ED4-A1DD-6571DAAEDAD7`, Serial `FCH2116V1V0`
  - CPU 2× Intel Xeon E5-2699 v4 (raw `TotalThreads=22` quirk)
  - DIMM 16× 64 GiB DDR4-2400, PSU 2× 770W
- 검증 ansible-playbook: `redfish-gather/site.yml` (REPO_ROOT=/home/cloviradmin/clovirone-portal)
- 검증 결과 JSON: 15369 bytes, status=success, errors=0

## 발견 분류

### [HIGH] 데이터 손실 — 코드 fix 적용

| ID | RAW (실측 확정) | 이전 결과 | Fix 후 결과 | 위치 |
|---|---|---|---|---|
| H1 | `Manager NIC NameServers=["10.100.13.9"]` | `network.dns_servers=[]` | `["10.100.13.9"]` | `redfish_gather.py gather_bmc` + `normalize_standard.yml _rf_norm_dns` 신설 |
| H2 | `Manager NIC IPv4Addresses[0].Gateway="10.100.15.254"` | `network.default_gateways=[]` | `[{"family":"ipv4","address":"10.100.15.254"}]` | `gather_bmc` 추출 + `_rf_norm_gateways` BMC NIC union |
| H3 | `PowerSupplies[0].InputRanges[0].OutputWattage=770` (PowerCapacityWatts=null) | `power_supplies[*].power_capacity_w=null` | PSU1=770, PSU2=770 | `gather_power` PSU `power_capacity_w` fallback |
| H4 | PowerControl[0].PowerCapacityWatts=null (Cisco 미응답) | `power.power_control.power_capacity_watts=null` | `1540` (=770+770 PSU 합산) | `gather_power` chassis level fallback |
| L1 | FirmwareInventory `slot-1`/`slot-2` Version=`"N/A"` | firmware 7건 (slot-1, slot-2 노이즈 포함) | 5건 (N/A 필터) | `gather_firmware` Version="N/A"/""/`NA` skip |

### Envelope 무결성

- envelope 13 필드 정합 (`status, schema_version, target_type, collection_method, ip, hostname, vendor, sections, diagnosis, meta, correlation, errors, data`) — 변경 없음
- `bmc` dict — 임시 키 `_network_meta` 누설 검증 → `False` (`_rf_d_bmc_clean` 단계에서 제거)
- `data.bmc.keys()` = `[datetime, datetime_offset, dns_name, firmware_version, health, ip, last_reset_time, mac_address, manager_type, model, name, oem, power_state, state, timezone, uuid]` — 기존 16개 키 유지

### [MED/LOW] 보류 (코드 책임 외 또는 호환성 우려)

| ID | 내용 | 사유 |
|---|---|---|
| M1 | Cisco CIMC 4.1(2g) `TotalThreads = TotalCores = 22` (E5-2699 v4 실 사양 22C/44T) | RAW 응답 자체가 그렇게 보고. 코드 책임 아님. **rule 96 origin 주석 후속** |
| M2 | `bmc.model = chassis Model = "TA-UNODE-G1"` | RAW Manager.Manufacturer=null + Model=chassis Model. Cisco 응답 quirk |
| M3 | `ServiceRoot.Vendor="Cisco Systems Inc."` (마침표) vs `System.Manufacturer="Cisco Systems Inc"` (마침표 없음) | adapter list 두 표기 모두 포함 + `_FALLBACK_VENDOR_MAP` 둘 다 등록 → 매치 OK |
| L2 | `memory.total_mb` 키지만 값은 MiB | schema/field_dictionary 영역. 키 변경 = envelope 변경 (사용자 정책 위반) |
| L3 | `gather_bmc` `dns_name = FQDN or HostName` fallback (의미 혼동) | 호환성 우려, 명확한 버그 아님 |

### [후속] Baseline 재캡처 필요

| ID | 내용 |
|---|---|
| B1 | `cisco_baseline.json` `power.power_control.power_consumed_watts=440 / avg=436 / max=559` — RAW 현재 `448/438/565`. **회귀 baseline에 dynamic sensor 값 박힘** (rule 21 R1 마찰) |
| B2 | `data.bmc` Phase M/N 신규 필드 (`datetime, datetime_offset, last_reset_time, timezone, mac_address, dns_name, uuid, power_state`) 모두 baseline 부재 — **baseline stale (코드 추가 후 재캡처 안 됨)** |
| B3 | 코드 fix (H1~H4, L1) 적용 후 `cisco_baseline.json` 재캡처 필요. dynamic 필드는 nullify 정책 권장 |

## 변경 파일

```
redfish-gather/library/redfish_gather.py:
  - gather_bmc():       BMC NIC NameServers / IPv4Addresses[*].Gateway 누적
                        result['_network_meta'] (envelope 비노출 임시 키)
  - gather_power():     PSU power_capacity_w + power_control.power_capacity_watts
                        InputRanges[0].OutputWattage / PSU 합산 fallback
  - gather_firmware():  Version "N/A" / "" / "NA" 노이즈 필터

redfish-gather/tasks/normalize_standard.yml:
  - 신규 set_fact "bmc network meta + envelope clean":
      _rf_d_bmc_network (BMC NIC raw 정보)
      _rf_d_bmc_clean   (envelope 노출용 — _network_meta 제거)
  - 변경 set_fact "aggregate gateways + dns_servers":
      _rf_norm_gateways: BMC NIC ipv4_gateways union
      _rf_norm_dns:      BMC NIC name_servers + static_name_servers union
                         (placeholder 0.0.0.0 / :: 필터 — hpe-critical-review 보강)
  - 변경 매핑:
      bmc:         _rf_d_bmc       → _rf_d_bmc_clean
      dns_servers: []              → _rf_norm_dns
```

## 영향 vendor

| Vendor | dns_servers 보강 영향 | power_capacity 보강 영향 | firmware N/A 필터 영향 |
|---|---|---|---|
| Dell    | NameServers 응답 시 채워짐 (이전 [] 이었으나 적용) | 기존 PowerCapacityWatts 응답 시 그대로 | "Previous-" 외 N/A 응답 거의 없음 |
| HPE     | StaticNameServers 응답 시 채워짐 | 기존 PowerCapacityWatts 응답 시 그대로 | 일부 펌웨어 component "" 응답 가능 — 필터 |
| Lenovo  | NameServers 응답 시 채워짐 | 기존 PowerCapacityWatts 응답 시 그대로 | XCC firmware 모두 정상 |
| Supermicro | NameServers 응답 시 채워짐 | 기존 PowerCapacityWatts 응답 시 그대로 | AMI MegaRAC 정상 |
| Cisco   | ✅ 빈 배열 → ["10.100.13.9"] | ✅ null → 770/1540 | ✅ slot-1/2 N/A 제거 (7→5) |

코드 변경은 모두 fallback (primary 키 응답 시 기존 동작 유지). primary 응답하는 vendor는 영향 없음.

## 검증 결과 (실측)

```
status: success
vendor: cisco
schema_version: 1
sections: {system: not_supported, hardware: success, bmc: success, cpu: success,
           memory: success, storage: success, network: success, firmware: success,
           users: not_supported, power: success}
errors: 0

network.dns_servers      = ['10.100.13.9']                    # ← H1 fix
network.default_gateways = [{family: ipv4, address: 10.100.15.254}]  # ← H2 fix
power.power_supplies[0]  = {name: PSU1, power_capacity_w: 770, ...}   # ← H3 fix
power.power_supplies[1]  = {name: PSU2, power_capacity_w: 770, ...}
power.power_control.power_capacity_watts = 1540                # ← H4 fix
firmware count = 5                                              # ← L1 fix (이전 7)
data.bmc 에 _network_meta 키 누설 = False                       # envelope clean
envelope 13 필드 정합 OK
```

- pytest 158/158 PASS (회귀 검사)
- verify_harness_consistency.py PASS (rules:28, skills:43, agents:49, policies:9)
- verify_vendor_boundary.py PASS (common/ + 3-channel gather에 vendor 하드코딩 없음)
- Python py_compile PASS (redfish_gather.py)
- YAML parse PASS (normalize_standard.yml 9 task)
- ansible-playbook 실 BMC 실행 RC=0

## 4 vendor 회귀 검증 (2026-04-29 17:50)

ansible-playbook 4 host 동시 실행 (`-f 4`) — INVENTORY_JSON에 cisco/dell/hpe/lenovo 4대 BMC.

| Vendor | IP | status | dns_servers | default_gateways | PSU cap_w | pc.capacity_w | firmware # | _network_meta 누설 |
|---|---|---|---|---|---|---|---|---|
| cisco | 10.100.15.2 | success | `["10.100.13.9"]` | `[10.100.15.254]` | `[770, 770]` | 1540 | 5 | False |
| dell  | 10.50.11.162 | **failed** | `[]` | `[]` | `[]` | None | 0 | False |
| hpe   | 10.50.11.231 | success | `[]` | `[10.50.11.254]` | `[800, 800]` | 800 | 28 | False |
| lenovo | 10.50.11.232 | success | `[]` | `[10.50.11.254]` | `[None, 750]` | 750 | 17 | False |

### Dell status=failed (코드 fix 회귀 아님)

- ServiceRoot 무인증 GET OK (Vendor=Dell 응답)
- `/redfish/v1/Systems/System.Embedded.1` 인증 시 `HTTP 401`
- vault `dell.yml`의 `root / __REDACTED__` 자격증명 만료/잠금/변경 추정
- **운영 issue** — 우리 fix와 무관. 별도 vault 회전 필요 (`rotate-vault` skill)
- 후속: Dell BMC 비밀번호 확인 + vault 갱신 후 재검증

### HPE — dns_servers 빈 배열 (정상)

- HPE iLO 6의 NameServers 응답이 placeholder (`['0.0.0.0','::']`) — `_rf_norm_dns`의 placeholder 필터로 빈 배열. 정상 동작
- default_gateways 정상 채워짐

### Lenovo — PSU1 power_capacity_w=None (실 hardware 결함)

- PSU1 raw: `Health=Critical`, `InputRanges[0]={OutputWattage:None,...}` — 모두 None
- 실제 PSU 고장 또는 커넥터 분리 상태 (Health=Critical 표시)
- 코드 fallback이 InputRanges도 응답이 None이면 그대로 None — 정상 동작
- 후속: Lenovo PSU1 hardware 점검 (운영 issue, 우리 작업 외)

### 4 vendor 공통 검증

- envelope **13 필드 정합** (4 vendor 모두)
- `bmc._network_meta` 키 **누설 없음** (4 vendor 모두 — `_rf_d_bmc_clean` 정상 동작)
- `gather_firmware` N/A 필터 — Cisco에서 7→5 감소, 다른 vendor는 N/A 응답 거의 없어 변화 미미
- `power_capacity_w` fallback — Cisco PSU 770 채움, Lenovo PSU1은 InputRanges도 None이라 fallback도 미동작 (정상)

## rule 96 R1 origin 주석 추가

- `adapters/redfish/cisco_cimc.yml`에 Quirk Q1~Q7 명시
- `adapters/redfish/cisco_bmc.yml`에 Q1~Q7 reference 표시
