# Test Fixtures — Redfish 실장비 응답

> 수집일: 2026-03-18 | 수집 방식: Python urllib + Basic Auth

## 1. 디렉토리 구조

```
tests/fixtures/redfish/
├── lenovo/                       # Lenovo ThinkSystem SR650 V2 (10.50.11.232)
│   ├── service_root.json         # /redfish/v1/
│   ├── systems_collection.json   # /redfish/v1/Systems
│   ├── system.json               # /redfish/v1/Systems/1
│   ├── managers_collection.json  # /redfish/v1/Managers
│   ├── manager.json              # /redfish/v1/Managers/1
│   ├── chassis_collection.json   # /redfish/v1/Chassis
│   ├── chassis.json              # /redfish/v1/Chassis/1
│   ├── system_processors.json    # /redfish/v1/Systems/1/Processors
│   ├── system_processors_0.json  # /redfish/v1/Systems/1/Processors/1
│   ├── system_processors_1.json  # /redfish/v1/Systems/1/Processors/2
│   ├── system_memory.json        # /redfish/v1/Systems/1/Memory
│   ├── system_memory_0.json      # /redfish/v1/Systems/1/Memory/1
│   ├── system_storage.json       # /redfish/v1/Systems/1/Storage
│   ├── system_storage_0.json     # /redfish/v1/Systems/1/Storage/RAID_Slot3
│   ├── storage_RAID_Slot3.json   # 동일 (deep probe 저장)
│   ├── drive_RAID_Slot3_*.json   # Drive 상세
│   ├── system_ethernetinterfaces.json
│   ├── system_ethernetinterfaces_0.json
│   ├── chassis_power.json        # /redfish/v1/Chassis/1/Power
│   ├── chassis_thermal.json      # /redfish/v1/Chassis/1/Thermal
│   ├── update_service.json       # /redfish/v1/UpdateService
│   ├── firmware_inventory.json   # /redfish/v1/UpdateService/FirmwareInventory
│   ├── firmware_0.json           # FirmwareInventory 개별 항목
│   └── memory_summary.json       # 계산된 메모리 요약
│
├── hpe/                          # HPE ProLiant DL380 Gen11 (10.50.11.231)
│   └── (동일 구조)
│
├── dell/                         # Dell PowerEdge R740 (10.50.11.162)
│   └── (동일 구조)
│
├── cisco/                        # Cisco TA-UNODE-G1 (10.100.15.2) — baseline v1 추가
│   └── (동일 구조, 23개)
│
└── dell_r760/                    # Dell PowerEdge R760 (10.100.15.27) — 예외 장비군 raw
    └── (동일 구조, 22개)

tests/fixtures/outputs/           # e2e representative output (raw fixture와 분리)
└── dell_r760_output.json         # R760 대표 노드 e2e 전체 output
```

## 2. 파일명 규칙

| 패턴 | 의미 |
|------|------|
| `service_root.json` | Service Root 응답 |
| `system.json` | Systems 첫 번째 멤버 상세 |
| `system_{section}.json` | Systems 하위 컬렉션 |
| `system_{section}_{N}.json` | 컬렉션 N번째 멤버 상세 |
| `storage_{id}.json` | Storage 컨트롤러별 상세 |
| `drive_{controller}_{N}.json` | Drive 상세 |
| `chassis_{section}.json` | Chassis 하위 (power, thermal) |
| `firmware_{N}.json` | FirmwareInventory 개별 항목 |
| `manager_{section}.json` | Manager 하위 |

## 3. 장비 정보

| 벤더 | 모델 | BMC | 시리얼 | Redfish Ver |
|------|------|-----|--------|-------------|
| Lenovo | ThinkSystem SR650 V2 | XCC 5.70 | J30AF7LC | 1.15.0 |
| HPE | ProLiant DL380 Gen11 | iLO 6 1.73 | SGH504HNZK | 1.20.0 |
| Dell | PowerEdge R740 | iDRAC 9 4.00 | CNIVC009CP0282 | 1.6.0 |
| Cisco | TA-UNODE-G1 | CIMC 4.1(2g) | FCH2116V1V0 | 1.2.0 |
| Dell (R760) | PowerEdge R760 | iDRAC (Gen16) | CNIVC004950455 | 1.20.1 |

## 4. Fixture 파일 수

| 벤더 | 파일 수 |
|------|---------|
| Lenovo | 45 |
| HPE | 47 |
| Dell | 53 |
| Cisco | 23 |
| Dell (R760) | 22 |
| **합계** | **190** |

## 5. Adapter 테스트 재사용 방법

```python
import json

def load_fixture(vendor, name):
    with open(f'tests/fixtures/redfish/{vendor}/{name}.json') as f:
        return json.load(f)

# 예: Dell system fixture로 gather_system 결과 검증
dell_sys = load_fixture('dell', 'system')
assert dell_sys['Manufacturer'] == 'Dell Inc.'
assert dell_sys['Model'] == 'PowerEdge R740'
```

## 6. Expected Normalized Output 예시

### Dell System Section (expected)
```json
{
  "manufacturer": "Dell Inc.",
  "model": "PowerEdge R740",
  "serial": "CNIVC009CP0282",
  "sku": "2BJ8033",
  "uuid": "4c4c4544-0042-4a10-8038-b2c04f303333",
  "hostname": "LENOVO01",
  "power_state": "On",
  "health": "Critical",
  "state": "Enabled",
  "led_state": "Off",
  "bios_version": "2.21.2",
  "cpu_summary": {"count": 2, "model": "Intel(R) Xeon(R) Silver 4214 CPU @ 2.20GHz", "health": "OK"},
  "memory_summary": {"total_gib": 640, "health": "OK"},
  "oem": {"lifecycle_version": null}
}
```

## 7. 주의사항

- Fixture 파일에는 **실제 시리얼 넘버, MAC 주소** 등이 포함됨
- 외부 공개 시 민감 정보 마스킹 필요
- JSON 파일은 pretty-printed (indent=2)
- 수집 시점: 2026-03-18 — BMC 펌웨어 업데이트 후 응답 구조가 변경될 수 있음
